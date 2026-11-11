#!/usr/bin/env python3
"""One-time application of a corrections.json offset_range to rows already loaded.

cm_build.py adds the offset to every value it stages from the deployment of the
entry on; this script adds the same offset once to the rows of the live table
that were loaded BEFORE that (ingested_at < --cutoff), so old and new rows agree.
First use: id l9-sz2-depth-offset-20261111 (L9-SZ2 depth to water +4.07 ft from
2026-09-24, the sonde's post-service calibration error).

It refuses to run twice: the correction is recorded in ingest_runs with mode
"correction" and ingest_run_id = the entry's id.  Run it with the BERDL proxy
chain up, holding state/daily.lock so no daily run interleaves.  Never load a
staging directory built by the OLD cm_build.py after this has run: its rows
would carry no offset (rebuild it instead).

    fix_offset_20261111.py --id l9-sz2-depth-offset-20261111 --cutoff "2026-11-11 23:26:00" [--dry-run] [--if-needed]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone

import pandas as pd

import cm_common as cm
import cm_load

# Deployment of the corrected cm_build.py (UTC): rows ingested before it carry no offset.
DEFAULT_CUTOFF = {"l9-sz2-depth-offset-20261111": "2026-11-11 23:26:00"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--id", default="l9-sz2-depth-offset-20261111", help="offset_ranges entry id in corrections.json")
    parser.add_argument("--cutoff", default=None, help="UTC 'YYYY-MM-DD HH:MM:SS': correct rows with ingested_at before this")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--if-needed", action="store_true", help="exit quietly if the correction is already recorded (used by run_daily.sh)")
    args = parser.parse_args()

    entry = next((r for r in cm.load_corrections().get("offset_ranges", []) if r.get("id") == args.id), None)
    if entry is None:
        sys.exit(f"no offset_ranges entry with id {args.id!r} in corrections.json")
    cutoff = args.cutoff or DEFAULT_CUTOFF.get(args.id)
    if not cutoff:
        sys.exit("--cutoff is required for this id")
    columns = cm.load_column_map()["measurements"]
    cols = [columns[label]["column"] for label in entry["labels"]]
    table, offset, start, end = entry["table"], float(entry["offset"]), entry["start"], entry["end"]

    cm.load_env_file(cm.credentials_file())
    spark = cm_load.spark_session(os.environ["KBASE_AUTH_TOKEN"])
    ns = ".".join(f"`{p}`" for p in cm.NAMESPACE.split("."))
    loader = cm_load.Loader(spark, args.id, args.dry_run)

    done = spark.sql(f"SELECT count(*) FROM {ns}.ingest_runs WHERE ingest_run_id = '{args.id}'").collect()[0][0]
    if done and args.if_needed:
        return
    if done:
        sys.exit(f"{args.id} is already recorded in ingest_runs; refusing to apply the offset twice")

    started = datetime.now(timezone.utc)
    target = f"{ns}.`{table}`"
    # Local dates: the range is inclusive and the stored strings carry the Eastern offset.
    in_range = (f"to_date(from_utc_timestamp(to_timestamp({cm.TIMESTAMP_COLUMN}), 'America/New_York')) "
                f"BETWEEN DATE '{start}' AND DATE '{end}' AND ingested_at < TIMESTAMP '{cutoff}'")
    per_column = {}
    for col in cols:
        where = f"{col} IS NOT NULL AND {in_range}"
        before = spark.sql(f"SELECT count({col}) AS n, sum({col}) AS s, min({col}) AS lo, max({col}) AS hi FROM {target} WHERE {where}").collect()[0]
        print(f"{table}.{col}: {before['n']} values in range [{start}, {end}] ingested before {cutoff} UTC; "
              f"raw min {before['lo']} max {before['hi']}")
        if not before["n"]:
            continue
        if args.dry_run:
            print(f"[dry-run] would add {offset:+g} to those {before['n']} values")
            continue
        spark.sql(f"UPDATE {target} SET {col} = round({col} + ({offset!r}), 6) WHERE {where}")
        after = spark.sql(f"SELECT count({col}) AS n, sum({col}) AS s FROM {target} WHERE {where}").collect()[0]
        ok = after["n"] == before["n"] and math.isclose(after["s"], before["s"] + offset * before["n"], rel_tol=1e-9, abs_tol=1e-4)
        per_column[col] = {"values": int(before["n"]), "sum_before": before["s"], "sum_after": after["s"], "ok": ok}
        print(f"  {before['n']} values offset by {offset:+g}; sum {before['s']:.6g} -> {after['s']:.6g} ({'ok' if ok else 'CHECK'})")
        if not ok:
            sys.exit(f"sum check failed for {table}.{col}; stopping")

    if not args.dry_run:
        loader.record_run(
            {
                "ingest_run_id": args.id,
                "mode": "correction",
                "started_at": pd.Timestamp(started),
                "finished_at": pd.Timestamp.now(tz="UTC"),
                "status": "ok",
                "tables_loaded": 1 if per_column else 0,
                "rows_staged": 0,
                "rows_appended": 0,
                "details": json.dumps({"correction": f"{table}: {', '.join(cols)} offset by {offset:+g} for local dates "
                                                     f"{start}..{end}, rows ingested before {cutoff} UTC: {entry['reason']}",
                                       "columns": per_column}),
            },
            loader.existing_tables(),
        )
        print(f"recorded {args.id} in ingest_runs (table_metadata notes refresh on the next load)")


if __name__ == "__main__":
    main()
