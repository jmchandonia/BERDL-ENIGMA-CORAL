#!/usr/bin/env python3
"""Compose ONE daily email covering both the sso_staging and the
continuous_monitoring loads, so the operator gets a single message per day.

run_daily.sh runs both loads (each writes its own load_result.json), then calls
this with both results.  Layout:

  header   "enigma lakehouse -- daily load, <local time>", Drive-mirror changes
  STATUS   OK / ACTION NEEDED (n) / FAILED, with the items a human must look at
  sso_staging section first (short), then continuous_monitoring (long table list)

What counts as ACTION: a load that failed or produced no result, a data file in
the SSO source folder the pipeline does not ingest, a new or missing source
column, held sample ids, a cm instrument that newly stopped reporting, a cm
table held back because a source label is not in column_map.json, lakehouse
comments that differ from the schema (never auto-applied), a KBase token
expiring soon.  No new sso data is NOT an action (irregular cadence), and
cm always appends rows, so neither is in the subject.

    combined_report.py --sso SSO_RESULT [--cm CM_RESULT] [--cm-state FILE]
                       [--sso-state FILE] [--subject] [--commit]

--subject prints the one-line subject; otherwise the body.  --commit advances the
cm silent-instrument state and the sso report state (run once per message).
CM_CODE_DIR must point at the continuous_monitoring code dir so cm_report can be
imported (falls back to sso-only if it cannot).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import sso_report

RUN_TAG = "[enigma lakehouse]"
LOCAL_TZ = ZoneInfo("America/Los_Angeles")
TOKEN_WARN_DAYS = 14


def _load(path):
    return json.loads(Path(path).read_text()) if path and Path(path).exists() else None


def _import_cm_report():
    cm_dir = os.environ.get("CM_CODE_DIR")
    if cm_dir and cm_dir not in sys.path:
        sys.path.insert(0, cm_dir)
    try:
        import cm_report
        return cm_report
    except Exception:
        return None


def run_time(run_id) -> tuple[str, str]:
    """('2026-11-03', 'Tue 2026-11-03 06:30 PST') from a 20261103T143001Z run id."""
    try:
        utc = datetime.strptime(str(run_id), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return str(run_id), str(run_id)
    local = utc.astimezone(LOCAL_TZ)
    return local.strftime("%Y-%m-%d"), local.strftime("%a %Y-%m-%d %H:%M %Z")


def attention(cm_data, cm_diff, sso_data) -> tuple[list[tuple[str, str, str]], bool]:
    """All (label, short, detail) items across both namespaces, and whether any is a failure."""
    items, failed = [], False
    if sso_data is None:
        items.append(("SSO LOAD MISSING", "sso load missing", "no sso_staging result this run (build or load did not run)"))
        failed = True
    else:
        items += sso_report.attention_items(sso_data)
        failed = failed or any(label == "LOAD FAILED" for label, _, _ in items)
    if cm_data is None:
        items.append(("CM LOAD MISSING", "cm load missing", "no continuous_monitoring result this run"))
        failed = True
    else:
        if cm_diff and cm_diff.get("newly"):
            names = sorted(cm_diff["newly"])
            items.append(("CM NEWLY SILENT", f"{len(names)} cm instrument(s) newly silent",
                          f"{len(names)} instrument(s) stopped reporting since the last report: {', '.join(names)}"))
        unknown = cm_data.get("unknown_labels")
        if unknown is None:  # older load_result: only inside details
            try:
                unknown = json.loads(cm_data.get("details") or "{}").get("unknown_labels")
            except ValueError:
                unknown = None
        for table, labels in sorted((unknown or {}).items()):
            items.append(("CM NEW SOURCE LABEL", f"cm {table} held back (unknown label)",
                          f"continuous_monitoring {table}: source label(s) not in column_map.json: "
                          f"{', '.join(repr(l) for l in labels)} -- the whole table is HELD BACK (nothing loaded) "
                          "until the label is mapped (build_column_map.py) or the source header is fixed."))
        for table, cols in sorted((cm_data.get("comment_drift") or {}).items()):
            items.append(("CM COMMENT DRIFT", f"{len(cols)} cm comment(s) in {table} differ",
                          f"continuous_monitoring {table}: {len(cols)} column/table comment(s) differ from the "
                          f"loader's ({', '.join(cols[:4])}{', ...' if len(cols) > 4 else ''}) -- NOT changed by "
                          "the daily run; review, then run cm_load.py --sync-comments."))
    for data in (sso_data, cm_data):
        days, expires = (data or {}).get("token_days_left"), (data or {}).get("token_expires")
        if isinstance(days, int) and days < TOKEN_WARN_DAYS:
            items.append(("KBASE TOKEN", f"token expires in {days} d",
                          f"KBase token expires {expires} ({days} days left) -- replace KBASE_AUTH_TOKEN in credentials.env"))
            break
    return items, failed


def build(cm_data, cm_diff, cm_mod, sso_data, sso_prev):
    run = (sso_data or cm_data or {}).get("ingest_run_id", "?")
    date, when = run_time(run)
    items, failed = attention(cm_data, cm_diff, sso_data)
    sso_frag = sso_report.subject_fragment(sso_data, sso_prev) if sso_data else "sso: no result"

    if failed:
        verdict = "FAILED"
    elif items:
        verdict = f"ACTION ({len(items)})"
    else:
        verdict = "OK"
    reasons = "; ".join(short for _, short, _ in items[:2]) + (" ..." if len(items) > 2 else "")
    subject = f"{RUN_TAG} {date} {verdict}" + (f": {reasons}" if items else "") + f" | {sso_frag}"

    # --- body ---
    lines = [f"enigma lakehouse -- daily load, {when}        run {run}"]
    if sso_data is not None and sso_data.get("sources"):
        if (sso_prev or {}).get("source_mtimes"):
            upd = [Path(e["path"]).name for e in sso_report.source_updates(sso_data, sso_prev)]
            lines.append("Drive mirror: " + (f"{len(upd)} source file(s) updated since last run: {', '.join(upd)}"
                                             if upd else "no source files changed since last run"))
        else:
            lines.append("Drive mirror: first run with source tracking (no previous state to compare)")
    lines.append("")
    if failed:
        lines.append("STATUS: FAILED")
    elif items:
        lines.append(f"STATUS: ACTION NEEDED ({len(items)})")
    else:
        lines.append("STATUS: OK -- sso_staging and continuous_monitoring loads succeeded; nothing needs your attention.")
    if items:
        width = max(len(label) for label, _, _ in items)
        for label, _, detail in items:
            lines.append(f"  * {label:<{width}}  {detail}")
    lines.append("")

    lines.append("-" * 64)
    lines.append(sso_report.body_section(sso_data, sso_prev) if sso_data else "sso_staging: no result this run.\n")
    lines.append("-" * 64)
    if cm_data is not None and cm_mod is not None:
        lines.append(cm_mod.body(cm_data, cm_diff))
    elif cm_data is not None:
        lines.append(f"continuous_monitoring: {cm_data.get('rows_appended', 0):,} rows appended "
                     f"(cm_report unavailable for detail).\n")
    else:
        lines.append("continuous_monitoring: no result this run.\n")
    return subject, "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sso", required=True)
    ap.add_argument("--cm")
    ap.add_argument("--cm-state")
    ap.add_argument("--sso-state")
    ap.add_argument("--subject", action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    sso_data = _load(args.sso)
    sso_prev = sso_report.load_state(args.sso_state) if args.sso_state else {}
    cm_data = _load(args.cm)
    cm_mod = _import_cm_report() if cm_data is not None else None
    cm_diff = None
    if cm_data is not None and cm_mod is not None:
        cm_diff = cm_mod.stale_diff(cm_data, Path(args.cm_state) if args.cm_state else None)
        if args.commit and args.cm_state and cm_diff["new_state"] is not None:
            Path(args.cm_state).write_text(json.dumps(cm_diff["new_state"], indent=2) + "\n")
    # Only a clean sso load advances the sso state; a failed one keeps the last good counts.
    if args.commit and args.sso_state and sso_data is not None and sso_data.get("status") == "ok":
        Path(args.sso_state).write_text(json.dumps(sso_report.new_state(sso_data), indent=2) + "\n")

    subject, body = build(cm_data, cm_diff, cm_mod, sso_data, sso_prev)
    print(subject if args.subject else body, end="\n" if args.subject else "")


if __name__ == "__main__":
    main()
