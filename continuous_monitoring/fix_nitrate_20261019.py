#!/usr/bin/env python3
"""One-time correction (2026-10-19): undo the nitrate-N -> nitrate factor.

The pipeline originally applied the CORAL builder's nitrate-N -> nitrate
conversion (x 62.0049/14.0067 = 4.4268) to Aqua TROLL nitrate.  The user
determined that the instrument values are already nitrate (the "NO3- - N"
header is wrong), so cm_build.py no longer converts, and this script divides
the nitrate column of every existing data table by the same factor and
replaces the conversion note in table_metadata.

It refuses to run twice: the correction is recorded in ingest_runs with
mode "correction" and ingest_run_id CORRECTION_ID.  Run it with the BERDL
proxy chain up, holding state/daily.lock so no daily run interleaves.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import cm_common as cm
import cm_load

CORRECTION_ID = "nitrate-not-nitrogen-20261019"
FACTOR = 62.0049 / 14.0067
COLUMN = "concentration_molecule_from_list_nitrate_milligram_per_liter"
# Every row ingested before the fix was deployed was converted; rows appended
# afterwards are not (no load succeeded between 2026-10-17 01:59Z and the fix).
CONVERTED_BEFORE = "2026-10-19 00:00:00"
OLD_NOTE_START = "Nitrate values were converted from the Aqua TROLL 600 nitrate-N basis"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--if-needed", action="store_true", help="exit quietly if the correction is already recorded (used by run_daily.sh)")
    parser.add_argument("--verify-staging", type=Path, help="staging dir built with the fixed cm_build.py; compare nitrate after the update")
    args = parser.parse_args()

    cm.load_env_file(cm.credentials_file())
    spark = cm_load.spark_session(os.environ["KBASE_AUTH_TOKEN"])
    ns = ".".join(f"`{p}`" for p in cm.NAMESPACE.split("."))
    loader = cm_load.Loader(spark, CORRECTION_ID, args.dry_run)

    done = spark.sql(f"SELECT count(*) FROM {ns}.ingest_runs WHERE ingest_run_id = '{CORRECTION_ID}'").collect()[0][0]
    if done and args.if_needed:
        return
    if done:
        sys.exit(f"{CORRECTION_ID} is already recorded in ingest_runs; refusing to divide nitrate twice")

    started = datetime.now(timezone.utc)
    tables = sorted(t for t in loader.existing_tables() if t.startswith("hazen_"))
    per_table = {}
    for table in tables:
        target = f"{ns}.`{table}`"
        if COLUMN not in spark.table(target).columns:
            continue
        converted = f"{COLUMN} IS NOT NULL AND ingested_at < TIMESTAMP '{CONVERTED_BEFORE}'"
        before = spark.sql(f"SELECT count({COLUMN}) AS n, sum({COLUMN}) AS s FROM {target} WHERE {converted}").collect()[0]
        if not before["n"]:
            continue
        if args.dry_run:
            print(f"[dry-run] {table}: would divide {before['n']} nitrate values by {FACTOR:.6f}")
            continue
        spark.sql(f"UPDATE {target} SET {COLUMN} = {COLUMN} / ({FACTOR!r}) WHERE {converted}")
        after = spark.sql(f"SELECT count({COLUMN}) AS n, sum({COLUMN}) AS s FROM {target} WHERE {converted}").collect()[0]
        ok = after["n"] == before["n"] and (before["n"] == 0 or math.isclose(after["s"] * FACTOR, before["s"], rel_tol=1e-9))
        per_table[table] = {"values": int(before["n"]), "sum_before": before["s"], "sum_after": after["s"], "ok": ok}
        print(f"{table}: {before['n']} values divided; sum {before['s']:.6g} -> {after['s']:.6g} ({'ok' if ok else 'CHECK'})")
        if not ok:
            sys.exit(f"sum check failed for {table}; stopping")

    old = spark.sql(f"SELECT table_name, notes FROM {ns}.table_metadata WHERE notes LIKE '%{OLD_NOTE_START}%'").collect()
    if not args.dry_run and old:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import cm_build

        for row in old:
            notes = [cm_build.NITRATE_NOTE if n.startswith(OLD_NOTE_START) else n for n in json.loads(row["notes"])]
            spark.sql(
                f"UPDATE {ns}.table_metadata SET notes = {cm_load.sql_string(json.dumps(notes))} "
                f"WHERE table_name = {cm_load.sql_string(row['table_name'])}"
            )
        print(f"table_metadata: replaced the nitrate note for {len(old)} tables")

    if args.verify_staging:
        manifest = json.loads((args.verify_staging / "manifest.json").read_text())
        checked = mismatched = 0
        for table, info in manifest["tables"].items():
            if COLUMN not in info["columns"]:
                continue
            with (args.verify_staging / info["tsv"]).open(newline="") as handle:
                staged = {r[cm.TIMESTAMP_COLUMN]: r[COLUMN] for r in csv.DictReader(handle, delimiter="\t") if r[COLUMN] != ""}
            live = dict(spark.sql(f"SELECT {cm.TIMESTAMP_COLUMN}, {COLUMN} FROM {ns}.`{table}` WHERE {COLUMN} IS NOT NULL").collect())
            for ts, value in staged.items():
                if ts in live:
                    checked += 1
                    mismatched += not math.isclose(float(value), live[ts], rel_tol=1e-8, abs_tol=1e-9)
        print(f"verification against {args.verify_staging}: {checked} nitrate values compared, {mismatched} differ")

    if not args.dry_run:
        loader.record_run(
            {
                "ingest_run_id": CORRECTION_ID,
                "mode": "correction",
                "started_at": pd.Timestamp(started),
                "finished_at": pd.Timestamp.now(tz="UTC"),
                "status": "ok",
                "tables_loaded": len(per_table),
                "rows_staged": 0,
                "rows_appended": 0,
                "details": json.dumps(
                    {
                        "correction": f"{COLUMN} divided by 62.0049/14.0067 for rows ingested before {CONVERTED_BEFORE} UTC: the instrument values are nitrate, not nitrate-N",
                        "tables": per_table,
                    }
                ),
            },
            loader.existing_tables(),
        )
        print(f"recorded {CORRECTION_ID} in ingest_runs")


if __name__ == "__main__":
    main()
