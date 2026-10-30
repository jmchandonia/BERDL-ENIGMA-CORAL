#!/usr/bin/env python3
"""Format an sso_staging load result for the daily email.

Exposes helpers the combined reporter composes into one message:
  subject_fragment(data) -> 'sso OK: gas +N, field N, reg N' (or ALERT ...)
  body_section(data)     -> the sso block of the email body
  has_alert(data)        -> True if anything needs attention (gas silent, new
                            source columns, or held sample ids)

Standalone:
  sso_report.py RESULT.json              print the full sso body
  sso_report.py RESULT.json --subject    print a one-line subject
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def short_ts(ts) -> str:
    if not ts:
        return "n/a"
    return str(ts).replace("T", " ")[:16]


def fmt_age(hours) -> str:
    if hours is None:
        return "?"
    return f"{hours / 24:.1f}d" if hours >= 48 else f"{hours:.0f}h"


def _drift_items(data: dict) -> list[tuple[str, list[str]]]:
    out = []
    for table, d in (data.get("drift") or {}).items():
        new = (d or {}).get("new_columns") or []
        if new:
            out.append((table, new))
    return out


def _held_total(data: dict) -> int:
    return sum(len(v or []) for v in (data.get("held") or {}).values())


def has_alert(data: dict) -> bool:
    return bool(data.get("stale_tables")) or bool(_drift_items(data)) or _held_total(data) > 0


def subject_fragment(data: dict) -> str:
    t = data.get("tables", {})
    gas = (t.get("picarro_gas") or {}).get("appended", 0) or 0
    field = (t.get("field_metadata") or {}).get("refreshed", 0) or 0
    reg = (t.get("sample_registry") or {}).get("upserted", 0) or 0
    core = f"sso gas +{gas:,}, field {field:,}, reg {reg:,}"
    flags = []
    if data.get("stale_tables"):
        flags.append("gas SILENT")
    if _drift_items(data):
        flags.append("NEW COLUMNS")
    if _held_total(data):
        flags.append(f"{_held_total(data)} held")
    return f"sso ALERT: {core} [{'; '.join(flags)}]" if flags else f"sso OK: {core}"


def body_section(data: dict) -> str:
    t = data.get("tables", {})
    lines = ["==== enigma.sso_staging ===="]

    if data.get("stale_tables"):
        for name, info in data["stale_tables"].items():
            lines.append(f"*** ALERT: {name} silent — last reading {short_ts(info.get('last_timestamp'))} "
                         f"({fmt_age(info.get('age_hours'))} ago) ***")
    drift = _drift_items(data)
    if drift:
        lines.append("*** NEW SOURCE COLUMNS — decide how to handle (not loaded): ***")
        for table, cols in drift:
            lines.append(f"    {table}: {', '.join(cols)}")

    status = data.get("status", "?")
    lines += [
        f"Load:     {data.get('ingest_run_id', '?')}  ({data.get('mode', '?')}, {status})",
        f"Finished: {data.get('finished_at', '?')}",
    ]

    def row(name, verb, key):
        info = t.get(name) or {}
        n = info.get(key, 0) or 0
        rc = info.get("row_count")
        last = short_ts(info.get("last_timestamp"))
        extra = ""
        if name == "sample_registry" and info.get("inserted") is not None:
            extra = f", {info['inserted']:,} new"
        if info.get("skipped"):
            extra = f"  [SKIPPED: {info['skipped']}]"
        return f"  {name:<16} {verb} {n:>7,}{extra}   (table now {rc if rc is not None else '?':>7,} rows, latest {last})"

    lines += [
        "",
        "Tables:",
        row("picarro_gas", "appended", "appended"),
        row("field_metadata", "refreshed", "refreshed"),
        row("sample_registry", "upserted", "upserted"),
    ]

    held = _held_total(data)
    if held:
        lines += ["", f"Held sample ids (not loaded): {held}"]
        for table, items in (data.get("held") or {}).items():
            for it in (items or [])[:10]:
                lines.append(f"    {it.get('source_sample_id')!r}: {it.get('reason')}")
            if len(items or []) > 10:
                lines.append(f"    ... and {len(items) - 10} more")

    expires, days = data.get("token_expires"), data.get("token_days_left")
    if expires:
        warn = "  *** RENEW SOON ***" if isinstance(days, int) and days < 14 else ""
        lines.append(f"\nKBase token: expires {expires} ({days} days left){warn}")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("result", type=Path)
    ap.add_argument("--subject", action="store_true")
    args = ap.parse_args()
    data = json.loads(args.result.read_text())
    print(subject_fragment(data) if args.subject else body_section(data), end="" if not args.subject else "\n")


if __name__ == "__main__":
    main()
