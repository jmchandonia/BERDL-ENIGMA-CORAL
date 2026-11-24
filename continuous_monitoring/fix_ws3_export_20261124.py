#!/usr/bin/env python3
"""One-time rebuild of the hazen_hobo_ws3 rows that came from the Area 3 LI-COR export (ws3-export-est-20261124).

The export licor/area3_2022-2024-2025_05_29_13_27_25_EDT_1.csv prints its times
in Eastern Standard Time all year with no offset.  Until 2026-11-24 cm_build.py
read them as DST-aware local time, so every 'licor export' row of
hazen_hobo_ws3 in daylight-saving time (47,249 rows, stamped -04:00) was one
hour early, and the export's 02:00-02:45 readings on the spring-forward
mornings of 2023-03-12 and 2024-03-10 were dropped (that hour does not exist in
local time).  Verified before the fix: the export's last four readings (stored
as 2024-05-22 19:00-19:45) equal the LI-COR API's 20:00-20:45 rows to 0.0002
inHg and 0.002 F.  WS1 and WS2 are not affected: their exports print -0500 on
every row and were parsed with it.

What this does, once (refused when ws3-export-est-20261124 is in ingest_runs):
  1. checks the live 'licor export' rows of hazen_hobo_ws3 are the expected
     71,441 (47,249 at -04:00, 24,192 at -05:00) and that no row mixes
     provenances; records the table's current Iceberg snapshot id;
  2. DELETEs those rows;
  3. appends the rows staged by the corrected parser
       cm_build.py --mode backfill --exports-only --no-state --out <staging>
     with Loader.append, which skips every timestamp the table already has, so
     the LI-COR API rows from 2024-05-22 20:00 on win over the export exactly
     as in a full build;
  4. checks: no export row shares a timestamp with an API row, no duplicate
     timestamps, the API rows are untouched, and the export rows number
     71,441 - 4 (now overlapping the API) + 8 (recovered spring-forward
     readings) = 71,445; refreshes table_metadata; records the run.

Re-runnable: Loader.append is dedup-safe, so after a failure between the
DELETE and the end of the append, run again with --resume (skips step 1-2).

    fix_ws3_export_20261124.py --staging /data/edr/field_automated_measurements/continuous_monitoring/staging/ws3_export_20261124 [--dry-run]

Run through run_daily.sh --exec (proxy chain up, daily lock held).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import cm_common as cm
import cm_load

RUN_ID = "ws3-export-est-20261124"
TABLE = "hazen_hobo_ws3"
EXPORT = "licor export"
EXPECTED_OLD = {"-04:00": 47249, "-05:00": 24192}
EXPECTED_NEW = sum(EXPECTED_OLD.values()) - 4 + 8


def connect(token: str, wait: int = 300):
    deadline = time.monotonic() + wait
    while True:
        try:
            spark = cm_load.spark_session(token)
            spark.sql("SELECT 1").collect()
            return spark
        except Exception as exc:
            if time.monotonic() > deadline:
                raise
            print(f"Spark Connect not ready ({exc!r}); retrying", flush=True)
            time.sleep(15)


def count(spark, sql: str) -> int:
    return int(spark.sql(sql).collect()[0][0])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--staging", type=Path, required=True, help="staging directory from cm_build.py --mode backfill --exports-only")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true", help="the export rows were already deleted by an earlier run that failed: only append and check")
    args = parser.parse_args()

    manifest = json.loads((args.staging / "manifest.json").read_text())
    if manifest.get("mode") != "backfill" or "licor_export_naive_timestamps" not in manifest.get("stats", {}):
        sys.exit(f"{args.staging} is not a cm_build.py --mode backfill --exports-only staging built with the corrected parser")
    info = manifest["tables"].get(TABLE)
    if not info:
        sys.exit(f"{args.staging} has no {TABLE} table")
    tsv, columns = args.staging / info["tsv"], list(info["columns"])
    print(f"staged {TABLE}: {info['rows']} rows, {info['first_timestamp']} .. {info['last_timestamp']}; "
          f"{manifest['stats']['licor_export_naive_timestamps']} export timestamps read at fixed UTC-5")

    cm.load_env_file(cm.credentials_file())
    spark = connect(os.environ["KBASE_AUTH_TOKEN"])
    ns = ".".join(f"`{p}`" for p in cm.NAMESPACE.split("."))
    target = f"{ns}.`{TABLE}`"
    ts = cm.TIMESTAMP_COLUMN
    if count(spark, f"SELECT count(*) FROM {ns}.ingest_runs WHERE ingest_run_id = '{RUN_ID}'"):
        sys.exit(f"{RUN_ID} is already recorded in ingest_runs; refusing to apply it twice")

    started = datetime.now(timezone.utc)
    details: dict = {"staging": str(args.staging), "staged_rows": info["rows"]}
    try:
        snap = spark.sql(f"SELECT snapshot_id FROM {target}.snapshots ORDER BY committed_at DESC LIMIT 1").collect()
        details["snapshot_before"] = str(snap[0][0]) if snap else None
    except Exception as exc:  # metadata table not reachable: not fatal
        details["snapshot_before"] = f"unavailable ({exc.__class__.__name__})"
    by_offset = {r["off"]: int(r["n"]) for r in spark.sql(
        f"SELECT substr({ts}, -6) AS off, count(*) AS n FROM {target} WHERE provenance = '{EXPORT}' GROUP BY 1").collect()}
    mixed = count(spark, f"SELECT count(*) FROM {target} WHERE provenance LIKE '%{EXPORT}%' AND provenance <> '{EXPORT}'")
    api_before = count(spark, f"SELECT count(*) FROM {target} WHERE provenance <> '{EXPORT}'")
    details.update({"export_rows_at_start": by_offset, "api_rows_before": api_before, "mixed_provenance_rows": mixed, "resume": args.resume})
    print(f"live {TABLE}: export rows by offset {by_offset}, {api_before} API rows, {mixed} mixed rows; snapshot {details['snapshot_before']}")
    if mixed:
        sys.exit("rows mixing export and API provenance exist; this script only handles pure export rows")
    if args.resume:
        # The old parse's first row (file time 13:15 EST read as 13:15 EDT) exists only before the DELETE.
        old_marker = count(spark, f"SELECT count(*) FROM {target} WHERE provenance = '{EXPORT}' AND {ts} = '2022-05-09T13:15:00.000-04:00'")
        if by_offset == EXPECTED_OLD or old_marker:
            sys.exit("--resume given but the old export rows are still present (the DELETE did not happen); run without --resume")
    elif by_offset != EXPECTED_OLD:
        sys.exit(f"export rows are not the expected {EXPECTED_OLD}; stopping (use --resume only after a failed earlier run)")

    if args.dry_run:
        print(f"[dry-run] would delete {sum(by_offset.values())} export rows, append the {info['rows']} staged rows "
              f"(skipping timestamps the API has), and expect {EXPECTED_NEW} export rows afterwards")
        return

    loader = cm_load.Loader(spark, RUN_ID, False)
    existing = loader.existing_tables()
    if not args.resume:
        spark.sql(f"DELETE FROM {target} WHERE provenance = '{EXPORT}'")
        left = count(spark, f"SELECT count(*) FROM {target} WHERE provenance = '{EXPORT}'")
        print(f"deleted the export rows; {left} remain")
        if left:
            sys.exit("DELETE left export rows behind; stopping before the append (re-run without --resume)")
    loader.ensure_table(TABLE, columns, info["metadata"]["description"], existing)
    t0 = time.monotonic()
    staged, appended = loader.append(TABLE, tsv, columns)
    print(f"appended {appended} of {staged} staged rows ({staged - appended} skipped as already present) in {time.monotonic() - t0:.0f}s")

    export_after = {r["off"]: int(r["n"]) for r in spark.sql(
        f"SELECT substr({ts}, -6) AS off, count(*) AS n FROM {target} WHERE provenance = '{EXPORT}' GROUP BY 1").collect()}
    api_after = count(spark, f"SELECT count(*) FROM {target} WHERE provenance <> '{EXPORT}'")
    overlap = count(spark, f"SELECT count(*) FROM {target} e JOIN {target} a ON a.{ts} = e.{ts} "
                           f"WHERE e.provenance = '{EXPORT}' AND a.provenance <> '{EXPORT}'")
    dups = count(spark, f"SELECT count(*) FROM (SELECT {ts} FROM {target} GROUP BY {ts} HAVING count(*) > 1)")
    # The stored strings carry milliseconds: 2023-03-12T03:00:00.000-04:00.
    spring = count(spark, f"SELECT count(*) FROM {target} WHERE provenance = '{EXPORT}' AND substr({ts}, 1, 16) IN "
                          "('2023-03-12T03:00', '2023-03-12T03:15', '2023-03-12T03:30', '2023-03-12T03:45', "
                          "'2024-03-10T03:00', '2024-03-10T03:15', '2024-03-10T03:30', '2024-03-10T03:45')")
    total_export = sum(export_after.values())
    checks = {
        "api_rows_unchanged": api_after == api_before,
        "no_export_api_overlap": overlap == 0,
        "no_duplicate_timestamps": dups == 0,
        # After a --resume the earlier run appended most rows, so only the final count is checkable.
        "export_rows_equal_appended": total_export == appended or args.resume,
        f"export_rows_{EXPECTED_NEW}": total_export == EXPECTED_NEW,
        "spring_forward_readings_recovered_8": spring == 8,
    }
    details.update({"export_rows_after": export_after, "api_rows_after": api_after, "rows_appended": appended,
                    "rows_skipped_as_present": staged - appended, "checks": checks})
    for name, ok in checks.items():
        print(f"  {name}: {'ok' if ok else 'CHECK'}")
    print(f"export rows after: {export_after} (total {total_export}); API rows {api_after}; overlap {overlap}; duplicates {dups}; spring-forward rows {spring}")
    if not all(checks.values()):
        sys.exit("a check failed; nothing recorded in ingest_runs (the append is dedup-safe: investigate, then re-run with --resume)")

    loader.write_table_metadata({}, loader.existing_tables())
    loader.record_run(
        {
            "ingest_run_id": RUN_ID, "mode": "correction",
            "started_at": pd.Timestamp(started), "finished_at": pd.Timestamp.now(tz="UTC"), "status": "ok",
            "tables_loaded": 1, "rows_staged": staged, "rows_appended": appended,
            "details": json.dumps({"correction": f"{TABLE}: the {sum(EXPECTED_OLD.values())} rows from the Area 3 LI-COR export were rebuilt "
                                   "with the export's times read as fixed Eastern Standard Time (they were read as DST-aware local time, "
                                   "which stamped the summer rows one hour early and dropped the spring-forward 02:00-02:45 readings); "
                                   "the API rows were untouched and win where the two overlap", **details}),
        },
        loader.existing_tables(),
    )
    print(f"recorded {RUN_ID} in ingest_runs; table_metadata refreshed")


if __name__ == "__main__":
    main()
