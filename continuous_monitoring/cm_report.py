#!/usr/bin/env python3
"""Format a continuous_monitoring load result as a success report.

run_daily.sh emails this on weekday success so a missing weekday mail means a
failure (cron still mails the failure output separately).  Reads the
load_result.json that cm_load.py writes into the staging directory.

    cm_report.py RESULT.json                    print the email body
    cm_report.py RESULT.json --subject          print a one-line subject
    cm_report.py RESULT.json --state FILE        alert only on instruments that
                                                 went silent since FILE was written
    cm_report.py RESULT.json --state FILE --commit   also update FILE

With --state, the silent-instrument alert is stateful: it fires only for tables
that newly crossed into "stale" since the last report, so instruments that have
been dead for months (and were already reported once) stop reappearing every
morning.  --commit advances the state; run it once per message.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def short_ts(ts: str | None) -> str:
    """2026-10-26T08:30:00.000-04:00 -> 2026-10-26 08:30."""
    if not ts:
        return "n/a"
    text = str(ts).replace("T", " ")
    return text[:16]


def fmt_age(hours: float | None) -> str:
    if hours is None:
        return "?"
    if hours >= 48:
        return f"{hours / 24:.1f}d"
    return f"{hours:.0f}h"


def stale_diff(data: dict, state_path: Path | None) -> dict:
    """Split the current stale set into newly silent vs. already-reported.

    Without --state, every stale table is "newly" silent (legacy behaviour, used
    for manual checks).  With --state and no file yet, the current set is taken as
    the baseline and nothing is reported new (so long-dead instruments do not
    flood the first message).  Otherwise only tables absent from the last report
    count as new, and tables that dropped out of the set count as resumed.
    """
    current = data.get("stale_tables") or {}
    new_state = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reported": {n: current[n].get("last_timestamp") for n in current},
    }
    if state_path is None:
        return {"newly": current, "carried": {}, "resumed": [], "baseline": False, "new_state": None}
    if not state_path.exists():
        return {"newly": {}, "carried": current, "resumed": [], "baseline": True, "new_state": new_state}
    prior_names = set(json.loads(state_path.read_text()).get("reported", {}))
    newly = {n: v for n, v in current.items() if n not in prior_names}
    carried = {n: v for n, v in current.items() if n in prior_names}
    resumed = sorted(prior_names - set(current))
    return {"newly": newly, "carried": carried, "resumed": resumed, "baseline": False, "new_state": new_state}


def subject(data: dict, diff: dict) -> str:
    appended = data.get("rows_appended", 0)
    tables = sum(1 for v in data.get("tables", {}).values() if v.get("appended"))
    newly = diff["newly"]
    if newly:
        return (
            f"[continuous_monitoring] ALERT {data.get('ingest_run_id', '?')}: "
            f"{len(newly)} instrument(s) newly silent; {appended:,} rows / {tables} tables appended"
        )
    return (
        f"[continuous_monitoring] OK {data.get('ingest_run_id', '?')}: "
        f"{appended:,} rows / {tables} tables, latest {short_ts(data.get('latest_timestamp'))}"
    )


def body(data: dict, diff: dict) -> str:
    tables = data.get("tables", {})
    updated = {t: v for t, v in tables.items() if v.get("appended")}
    newly = diff["newly"]

    lines = []
    if newly:
        lines += [
            f"*** ALERT: {len(newly)} instrument(s) newly not reporting ***",
            "The load itself succeeded, but these tables stopped reporting since",
            "the last report — check whether the instrument or its upload has stopped:",
            "",
        ]
        width = max(len(t) for t in newly)
        for name in sorted(newly):
            info = newly[name]
            lines.append(
                f"  {name:<{width}}  last seen {short_ts(info.get('last_timestamp'))} "
                f"({fmt_age(info.get('age_hours'))} ago)"
            )
        lines += ["", "-" * 60, ""]

    lines += [
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

    # Quiet instrument-status footer: recoveries, and a count of the long-silent
    # instruments that were already reported and are not repeated above.
    resumed = diff["resumed"]
    carried = diff["carried"]
    if resumed:
        lines += ["", f"Resumed since last report: {', '.join(resumed)}"]
    if carried:
        lines += ["", f"({len(carried)} instrument(s) still silent from earlier reports — not repeated here.)"]

    files_deferred = json.loads(data.get("details", "{}")).get("files_deferred")
    if files_deferred:
        lines += ["", f"Note: {files_deferred} source file(s) deferred to a later run."]

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("result", type=Path, help="load_result.json from the staging directory")
    parser.add_argument("--subject", action="store_true", help="print the one-line subject instead of the body")
    parser.add_argument("--state", type=Path, help="reported-stale state file; alert only on instruments silent since it was written")
    parser.add_argument("--commit", action="store_true", help="write the updated stale state back to --state (run once per message)")
    args = parser.parse_args()
    data = load(args.result)
    diff = stale_diff(data, args.state)
    if args.commit and args.state and diff["new_state"] is not None:
        args.state.write_text(json.dumps(diff["new_state"], indent=2) + "\n")
    print(subject(data, diff) if args.subject else body(data, diff), end="\n" if args.subject else "")


if __name__ == "__main__":
    main()
