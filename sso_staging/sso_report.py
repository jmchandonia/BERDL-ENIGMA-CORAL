#!/usr/bin/env python3
"""Format an sso_staging load result for the daily lakehouse email.

Helpers the combined reporter (combined_report.py) composes into one message:
  attention_items(data) -> [(label, short, detail)] things a human must look at:
                           a failed load, a data file in the source folder the
                           pipeline does not ingest, a new or missing source
                           column, lakehouse comments or columns that differ
                           from the schema (never auto-applied), held sample
                           ids, gas rows whose analyzer attribution disagrees
                           with the port assignment.  "No new data" is never an
                           item: the campaign sources arrive on an irregular
                           schedule, so an unchanged table is expected.
  has_alert(data)       -> bool(attention_items(data))
  subject_fragment(data, prev) -> 'sso: field +18, gas/registry unchanged'
  source_updates(data, prev)   -> ingested source files whose mtime changed
  body_section(data, prev)     -> the sso block of the email body
  load_state / new_state       -> report_state.json: last run's row counts and
                                  source mtimes, so the report can show net change

Standalone:
  sso_report.py RESULT.json [--state report_state.json] [--subject]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ORDER = ["picarro_gas", "field_metadata", "sample_registry", "toc_tn_anions"]
LABEL = {"picarro_gas": "gas", "field_metadata": "field", "sample_registry": "registry", "toc_tn_anions": "toc/anions"}
HOW = {"picarro_gas": "append", "field_metadata": "full refresh", "sample_registry": "merge by sample id",
       "toc_tn_anions": "merge by sample id"}
SOURCE_NAME = {"picarro_gas": "gas CSV", "field_metadata": "Field Metadata", "sample_registry": "Assay Metadata",
               "toc_tn_anions": "TOC/TN/anion workbook"}


def short_ts(ts) -> str:
    if not ts:
        return "n/a"
    s = str(ts).replace("T", " ")
    return s[:16] if len(s) > 10 else s  # a bare '20261028' date stays as is


def fmt_age(hours) -> str:
    if hours is None:
        return "?"
    return f"{hours / 24:.1f} d" if hours >= 48 else f"{hours:.0f} h"


def fmt_size(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _tables(data: dict) -> dict:
    return data.get("tables") or {}


def _sources(data: dict) -> dict:
    return data.get("sources") or {}


def _held_total(data: dict) -> int:
    return sum(len(v or []) for v in (data.get("held") or {}).values())


def _drift(data: dict) -> list[tuple[str, str, list[str]]]:
    out = []
    for table, d in (data.get("drift") or {}).items():
        for kind in ("new_columns", "missing_columns"):
            cols = (d or {}).get(kind) or []
            if cols:
                out.append((table, kind, cols))
    return out


_INSTRUMENT_LABEL = {"ORNL-EA-031620": "A", "ORNL-EA-007299": "B"}


def _label(serial) -> str:
    """'A (ORNL-EA-031620)' for the email; the serial alone if unknown."""
    if not serial:
        return "?"
    lab = _INSTRUMENT_LABEL.get(serial)
    return f"{lab} ({serial})" if lab else str(serial)


def _instrument_line(data: dict) -> str:
    """'A (ORNL-EA-031620) 2026-10-26 22:01 (8.7 d ago), B (...) ...' or ''."""
    inst = data.get("instruments") or {}
    parts = []
    for serial, v in sorted(inst.items(), key=lambda kv: (kv[1].get("label") or "~", kv[0])):
        age = v.get("age_hours")
        parts.append(f"{_label(serial)} {short_ts(v.get('last_timestamp'))}"
                     + (f" ({fmt_age(age)} ago)" if age is not None else ""))
    return ", ".join(parts)


def _error(data: dict) -> str:
    try:
        return str(json.loads(data.get("details") or "{}").get("error") or "")
    except ValueError:
        return ""


# --- what needs a human ---

def attention_items(data: dict) -> list[tuple[str, str, str]]:
    items = []
    status = data.get("status", "?")
    if status != "ok":
        err = _error(data)
        items.append(("LOAD FAILED", "sso load failed",
                      f"sso_staging load status {status!r}" + (f": {err[:200]}" if err else "")))
    for u in _sources(data).get("unknown") or []:
        name = Path(u["path"]).name
        ignore_entry = json.dumps({"path": u["path"], "mtime": u.get("mtime")})
        items.append(("NEW SOURCE FILE", f"new source file {name}",
                      f"{u['path']} ({fmt_size(u.get('size'))}, modified {short_ts(u.get('mtime'))[:10]}) -- "
                      "a data file the pipeline does not ingest.  Model it in sso_staging, or add "
                      f"{ignore_entry} to state/ignored_sources.json to stop this notice while the "
                      "file is unchanged."))
    for table, kind, cols in _drift(data):
        src = SOURCE_NAME.get(table, table)
        if kind == "new_columns":
            label, what = "NEW COLUMN", "not loaded until sso_schema.py maps it"
        else:
            label, what = "MISSING COLUMN", "the parser expects it; those values now load empty"
        items.append((label, f"{label.lower()} in {src}",
                      f"{src}: {', '.join(repr(c) for c in cols)} -- {what}."))
    for table, cols in (data.get("comment_drift") or {}).items():
        items.append(("COMMENT DRIFT", f"{len(cols)} comment(s) in {table} differ from schema",
                      f"{table}: {len(cols)} column/table comment(s) in the lakehouse differ from sso_schema.py "
                      f"({', '.join(cols[:4])}{', ...' if len(cols) > 4 else ''}) -- NOT changed by the daily run; "
                      "review the schema change, then run sso_load.py --sync-comments."))
    for table, cols in (data.get("schema_drift") or {}).items():
        items.append(("TABLE LACKS COLUMN", f"{table} not loaded: lacks {', '.join(cols)}",
                      f"{table}: the lakehouse table has no column {', '.join(repr(c) for c in cols)} that sso_schema.py "
                      "defines -- NOT loaded and NOT altered by the daily run; review the schema change, then run "
                      "sso_load.py --add-columns (and backfill the new column) to resume loading."))
    gc = data.get("gas_checks") or {}
    if gc.get("conflicts"):
        held_rows = sum(c["rows"] for c in gc["conflicts"])
        detail = "; ".join(f"{c['well_port']}: assigned {_label(c['assigned'])}, rows look like {_label(c['signature'])} "
                           f"({c['rows']:,} rows)" for c in gc["conflicts"][:6])
        items.append(("GAS PORT MOVED?", f"{held_rows:,} gas rows held: analyzer attribution conflict",
                      f"picarro_gas: {detail} -- the README port assignment in sso_schema.py disagrees with the rows' "
                      "column signature; those rows are HELD (not loaded).  Confirm the new assignment with Kris, "
                      "update GAS_PORT_ASSIGNMENT (new valid_from), then re-stage with sso_build.py --full-gas."))
    if gc.get("unattributed"):
        n = sum(c["rows"] for c in gc["unattributed"])
        detail = "; ".join(f"{c['channel'] or '(no port or channel name)'} ({c['rows']:,} rows)" for c in gc["unattributed"][:6])
        items.append(("GAS ROWS UNATTRIBUTED", f"{n:,} gas rows held: no analyzer attribution",
                      f"picarro_gas: {detail} -- neither the port assignment nor the column signature (NH3_dry / O2_%) "
                      "identifies the analyzer, or the row names no well-port / reference channel; HELD (not loaded).  "
                      "Check the export with Kris; re-stage with --full-gas."))
    if gc.get("unknown_ports"):
        detail = "; ".join(f"{c['well_port']} -> {_label(c['picarro_serial'])} ({c['rows']:,} rows)" for c in gc["unknown_ports"][:6])
        items.append(("GAS NEW PORT", f"gas well-port(s) not in the assignment table: "
                      f"{', '.join(c['well_port'] for c in gc['unknown_ports'][:4])}",
                      f"picarro_gas: {detail} -- loaded with the analyzer from the column signature, but the well-port is not "
                      "in GAS_PORT_ASSIGNMENT (sso_schema.py).  Add it after confirming with Kris."))
    if gc.get("port_map_mismatch"):
        detail = "; ".join(f"{_label(c['picarro_serial'])} port {c['multiplexer_on_state']}: rows say {c['channel']}, "
                           f"README says {c['assigned_channel']} ({c['rows']:,} rows)" for c in gc["port_map_mismatch"][:6])
        items.append(("GAS PORT MAP", "multiplexer port -> well-port differs from the README table",
                      f"picarro_gas: {detail} -- rows are loaded as exported (Port column wins); update "
                      "GAS_PORT_ASSIGNMENT or ask Kris which is right."))
    held = _held_total(data)
    if held:
        items.append(("HELD SAMPLE IDS", f"{held} held sample id(s)",
                      f"{held} sample id(s) / field draws not loaded (illegal character, duplicate, or a draw "
                      "without a pump start) -- listed in the sso_staging section."))
    amb = data.get("draw_ambiguous") or []
    if amb:
        by_day: dict[str, set] = {}
        for a in amb:
            for c in a.get("candidates") or []:
                by_day.setdefault(c[:8] + " " + c[9:-5], set()).add(c)
        detail = "; ".join(f"{k}: {len(v)} draws" for k, v in sorted(by_day.items())[:6])
        items.append(("SAMPLE DRAW AMBIGUOUS", f"{len(amb)} sample(s) match several field draws",
                      f"sample_registry: {len(amb)} sample(s) have field_draw_id NULL because their well-port was "
                      f"pumped more than once that day ({detail}).  Ask the field team which draw filled each "
                      "sample and record it in state/draw_overrides.json ({\"<sdt_sample_name>\": \"<field_draw_id>\"})."))
    return items


def has_alert(data: dict) -> bool:
    return bool(attention_items(data))


# --- report state (last run's counts + source mtimes) ---

def load_state(path) -> dict:
    try:
        return json.loads(Path(path).read_text())
    except (TypeError, FileNotFoundError, ValueError):
        return {}


def new_state(data: dict) -> dict:
    return {
        "ingest_run_id": data.get("ingest_run_id"),
        "row_counts": {t: (v or {}).get("row_count") for t, v in _tables(data).items()},
        "source_mtimes": {e["path"]: e.get("mtime") for e in (_sources(data).get("ingested") or [])},
    }


def _deltas(data: dict, prev: dict | None) -> dict:
    before_all = (prev or {}).get("row_counts") or {}
    out = {}
    for t, v in _tables(data).items():
        now, before = (v or {}).get("row_count"), before_all.get(t)
        out[t] = (now, now - before if isinstance(now, int) and isinstance(before, int) else None)
    return out


def source_updates(data: dict, prev: dict | None) -> list[dict]:
    prev_m = (prev or {}).get("source_mtimes") or {}
    return [e for e in (_sources(data).get("ingested") or [])
            if e.get("mtime") and e.get("mtime") != prev_m.get(e["path"])]


# --- subject + body ---

def subject_fragment(data: dict, prev: dict | None = None) -> str:
    d = _deltas(data, prev)
    grew, shrank, nostate, same = [], [], [], []
    for t in ORDER + [t for t in d if t not in ORDER]:
        if t not in d:
            continue
        now, delta = d[t]
        lab = LABEL.get(t, t)
        if delta is None:
            nostate.append(f"{lab} {now:,} rows" if isinstance(now, int) else f"{lab} ?")
        elif delta > 0:
            grew.append(f"{lab} +{delta:,}")
        elif delta < 0:
            shrank.append(f"{lab} {delta:,}")
        else:
            same.append(lab)
    parts = grew + shrank + nostate
    if same:
        parts.append("/".join(same) + " unchanged")
    return "sso: " + (", ".join(parts) if parts else "no tables")


def body_section(data: dict, prev: dict | None = None) -> str:
    t, src = _tables(data), _sources(data)
    prev_m = (prev or {}).get("source_mtimes") or {}
    have_prev = bool(prev_m)
    lines = ["==== enigma.sso_staging ===="]
    lines.append(f"Load:  {data.get('ingest_run_id', '?')}  ({data.get('mode', '?')}, {data.get('status', '?')})"
                 f"   finished {short_ts(data.get('finished_at'))} UTC")

    if src:
        lines += ["", "Sources (SSO campaign folder on the Drive mirror):"]
        shown = (src.get("ingested") or []) + (src.get("unknown") or []) + (src.get("ignored") or [])
        width = max((len(e["path"]) for e in shown), default=20)
        stale = data.get("stale_tables") or {}
        for e in src.get("ingested") or []:
            mtime = short_ts(e.get("mtime"))[:10]
            if not have_prev:
                change = f"modified {mtime}"
            elif e.get("mtime") != prev_m.get(e["path"]):
                change = f"UPDATED (modified {mtime})"
            else:
                change = f"unchanged since {mtime}"
            dest = f"-> {e.get('table')}" if e.get("read_this_run") else "(older gas file, not re-read)"
            extra = ""
            if e.get("table") == "picarro_gas" and e.get("read_this_run"):
                per_inst = _instrument_line(data)
                if per_inst:
                    extra = f"; last reading {per_inst}"
                else:
                    last = (t.get("picarro_gas") or {}).get("last_timestamp")
                    age = (stale.get("picarro_gas") or {}).get("age_hours")
                    extra = f"; last reading {short_ts(last)}" + (f" ({fmt_age(age)} ago)" if age is not None else "")
            lines.append(f"  {e['path']:<{width}}  {change} {dest}{extra}")
        for e in src.get("unknown") or []:
            lines.append(f"  {e['path']:<{width}}  NOT INGESTED -- data file, {fmt_size(e.get('size'))}, "
                         f"modified {short_ts(e.get('mtime'))[:10]}   <-- ACTION")
        for e in src.get("ignored") or []:
            lines.append(f"  {e['path']:<{width}}  ignored (state/ignored_sources.json)")
        docs = [Path(e["path"]).name for e in src.get("docs") or []]
        if docs:
            lines.append(f"  documentation: {', '.join(docs)}")

    d = _deltas(data, prev)
    lines += ["", "Tables:"]
    for name in ORDER + [n for n in t if n not in ORDER]:
        if name not in t:
            continue
        info = t.get(name) or {}
        now, delta = d.get(name, (info.get("row_count"), None))
        rows = f"{now:>9,} rows" if isinstance(now, int) else f"{'?':>9} rows"
        if info.get("inserted") is not None:  # upsert tables report inserts vs merged
            change = f"+{info['inserted']:,} new; existing rows merged"
        elif delta is None:
            change = "(no previous run to compare)" if not prev else "n/a"
        else:
            change = f"{delta:+,} since last run"
        if info.get("skipped"):
            change += f"   [SKIPPED: {info['skipped']}]"
        lines.append(f"  {name:<16} {rows}   {change}  ({HOW.get(name, '')})")
        if name == "picarro_gas" and data.get("instruments"):
            by = (data.get("gas_checks") or {}).get("rows_by_serial") or {}
            for serial, v in sorted(data["instruments"].items(), key=lambda kv: (kv[1].get("label") or "~", kv[0])):
                n = v.get("row_count")
                staged = f", {by[serial]:,} staged this run (dedup decides)" if by.get(serial) else ""
                lines.append(f"      {_label(serial):<22} {n:>9,} rows{staged}" if isinstance(n, int)
                             else f"      {_label(serial):<22} {'?':>9} rows")
            held_rows = (data.get("gas_checks") or {}).get("rows_held") or 0
            if held_rows:
                lines.append(f"      HELD (not loaded)      {held_rows:>9,} rows   <-- ACTION (see above)")
    lines.append("Source files arrive on an irregular schedule; \"unchanged\" above is expected.")

    held = _held_total(data)
    if held:
        lines += ["", f"Held sample ids (not loaded): {held}"]
        for table, items in (data.get("held") or {}).items():
            for it in (items or [])[:10]:
                lines.append(f"    {it.get('source_sample_id')!r}: {it.get('reason')}")
            if len(items or []) > 10:
                lines.append(f"    ... and {len(items) - 10} more")
    amb = data.get("draw_ambiguous") or []
    if amb:
        lines += ["", f"Samples not linked to a field draw (ambiguous): {len(amb)}"]
        for a in amb[:12]:
            lines.append(f"    {a['sdt_sample_name']}: {', '.join(a.get('candidates') or [])}")
        if len(amb) > 12:
            lines.append(f"    ... and {len(amb) - 12} more")

    expires, days = data.get("token_expires"), data.get("token_days_left")
    if expires:
        warn = "  *** RENEW SOON ***" if isinstance(days, int) and days < 14 else ""
        lines.append(f"\nKBase token: expires {expires} ({days} days left){warn}")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("result", type=Path)
    ap.add_argument("--state", type=Path, default=None, help="report_state.json from the previous run")
    ap.add_argument("--subject", action="store_true")
    args = ap.parse_args()
    data = json.loads(args.result.read_text())
    prev = load_state(args.state) if args.state else None
    print(subject_fragment(data, prev) if args.subject else body_section(data, prev),
          end="\n" if args.subject else "")


if __name__ == "__main__":
    main()
