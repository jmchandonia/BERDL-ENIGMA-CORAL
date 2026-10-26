#!/usr/bin/env python3
"""Format a continuous_monitoring load result as a success report.

run_daily.sh emails this on weekday success so a missing weekday mail means a
failure (cron still mails the failure output separately).  Reads the
load_result.json that cm_load.py writes into the staging directory.

    cm_report.py RESULT.json             print the email body
    cm_report.py RESULT.json --subject   print a one-line subject
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def short_ts(ts: str | None) -> str:
    """2026-10-26T08:30:00.000-04:00 -> 2026-10-26 08:30."""
    if not ts:
        return "n/a"
    text = str(ts).replace("T", " ")
    return text[:16]


def subject(data: dict) -> str:
    appended = data.get("rows_appended", 0)
    tables = sum(1 for v in data.get("tables", {}).values() if v.get("appended"))
    return (
        f"[continuous_monitoring] OK {data.get('ingest_run_id', '?')}: "
        f"{appended:,} rows / {tables} tables, latest {short_ts(data.get('latest_timestamp'))}"
    )


def body(data: dict) -> str:
    tables = data.get("tables", {})
    updated = {t: v for t, v in tables.items() if v.get("appended")}
    unchanged = [t for t, v in tables.items() if not v.get("appended")]

    lines = [
        "enigma.continuous_monitoring daily load succeeded.",
        "",
        f"Run:            {data.get('ingest_run_id', '?')}  ({data.get('mode', '?')})",
        f"Finished:       {data.get('finished_at', '?')}",
        f"Rows appended:  {data.get('rows_appended', 0):,} across {len(updated)} tables",
        f"Latest data:    {short_ts(data.get('latest_timestamp'))}",
    ]

    expires = data.get("token_expires")
    days = data.get("token_days_left")
    if expires:
        warn = "  *** RENEW SOON ***" if isinstance(days, int) and days < 14 else ""
        lines.append(f"KBase token:    expires {expires} ({days} days left){warn}")
    else:
        lines.append("KBase token:    expiry unknown")

    lines += ["", f"Tables updated ({len(updated)}) — appended / latest timestamp:"]
    width = max((len(t) for t in updated), default=0)
    for name in sorted(updated):
        info = updated[name]
        lines.append(f"  {name:<{width}}  {info['appended']:>6,}  {short_ts(info.get('last_timestamp'))}")

    if unchanged:
        lines += ["", f"No new rows this run ({len(unchanged)}): {', '.join(sorted(unchanged))}"]

    files_deferred = json.loads(data.get("details", "{}")).get("files_deferred")
    if files_deferred:
        lines += ["", f"Note: {files_deferred} source file(s) deferred to a later run."]

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("result", type=Path, help="load_result.json from the staging directory")
    parser.add_argument("--subject", action="store_true", help="print the one-line subject instead of the body")
    args = parser.parse_args()
    data = load(args.result)
    print(subject(data) if args.subject else body(data), end="" if not args.subject else "\n")


if __name__ == "__main__":
    main()
