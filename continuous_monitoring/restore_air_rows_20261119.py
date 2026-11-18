#!/usr/bin/env python3
"""One-time restore of channels blanked by the 2026-11-11 25 C rule that the year-round rule keeps.

The 25 C rule (air-readings-20261111) nulled every channel of 1,717 rows whose
temperature exceeded 25 C.  Its replacement (corrections.json out_of_water,
cm_out_of_water.py) nulls only the temperature of such a row unless the sonde
spent that day out of the well (at least half of the day's readings outside
the band).  Two of the blanked episodes were temperature-sensor faults, not
air: M5-SZ1's September 2026 spikes to 114-156 C sit between normal readings
with the depth steady at 11.6-11.9 ft and oxygen at 0, and M4-SZ2's first hot
readings on 2026-06-06/07 are a handful among 96 normal ones.  Their other
channels were real water readings.

This script rebuilds the affected days from the raw HydroVu archive with
cm_build.Builder (current corrections applied), decides the air days exactly
as cm_out_of_water.air_days does, and for every all-NULL live row on a non-air
day whose rebuilt row exists writes the rebuilt values back for every channel
except temperature (which stays NULL: it is outside the band).  Rows on air
days are left all-NULL.  Recorded in ingest_runs as restore-air-rows-20261119
and refused a second time.

    restore_air_rows_20261119.py [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

import cm_build
import cm_common as cm
import cm_load
import cm_out_of_water as oow

RECORD_ID = "restore-air-rows-20261119"
OLD_RULE_ID = "air-readings-20261111"


def log(msg: str) -> None:
    print(msg, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = oow.config()
    columns = cm.load_column_map()["measurements"]
    measurement_cols = {v["column"] for v in columns.values()}
    t_col = columns[cfg["temperature_label"]]["column"]
    d_col = columns[cfg["depth_label"]]["column"]
    band = cfg["water_temperature_c"]

    cm.load_env_file(cm.credentials_file())
    spark = cm_load.spark_session(os.environ["KBASE_AUTH_TOKEN"])
    ns = ".".join(f"`{p}`" for p in cm.NAMESPACE.split("."))
    if spark.sql(f"SELECT count(*) FROM {ns}.ingest_runs WHERE ingest_run_id = '{RECORD_ID}'").collect()[0][0]:
        sys.exit(f"{RECORD_ID} is already recorded in ingest_runs; refusing to run twice")
    old = spark.sql(f"SELECT details FROM {ns}.ingest_runs WHERE ingest_run_id = '{OLD_RULE_ID}'").collect()
    if not old:
        sys.exit(f"{OLD_RULE_ID} is not recorded; nothing to restore")
    tables = sorted(json.loads(old[0]["details"])["tables"])
    log(f"tables blanked by {OLD_RULE_ID}: {tables}")

    # All-NULL live rows per table, grouped by local date.
    blank: dict[str, dict[str, list[str]]] = {}
    locations: dict[str, str] = {}
    for table in tables:
        target = f"{ns}.`{table}`"
        cols = [c for c in spark.table(target).columns if c in measurement_cols]
        rows = spark.sql(
            f"SELECT {cm.TIMESTAMP_COLUMN} AS ts, {cm.LOCATION_COLUMN} AS loc FROM {target} WHERE "
            + " AND ".join(f"{c} IS NULL" for c in cols)
        ).collect()
        by_day: dict[str, list[str]] = defaultdict(list)
        for r in rows:
            by_day[r["ts"][:10]].append(r["ts"])
            locations[table] = r["loc"]
        blank[table] = dict(by_day)
        log(f"{table}: {len(rows)} all-NULL rows on {len(by_day)} days")

    # Rebuild those days from the raw archive (files are named by day, give or take one).
    builder = cm_build.Builder(holdback=None, now=datetime.now(timezone.utc))
    files: set[Path] = set()
    for table, by_day in blank.items():
        site = locations[table].removeprefix("SSO-")
        for d in by_day:
            day = date.fromisoformat(d)
            for off in range(-1, 3):
                f = day + timedelta(days=off)
                files.update((cm.FAM_ROOT / "hydrovu/data" / f"{f:%Y}/{f:%m}").glob(f"{f:%y%m%d}_{site}_*.json"))
    log(f"rebuilding from {len(files)} archive files")
    for path in sorted(files):
        builder.add_hydrovu_file(path, complete=True)
    staged = Path(tempfile.mkdtemp(prefix="restore_air_"))
    manifest = builder.write(staged)

    loader = cm_load.Loader(spark, RECORD_ID, args.dry_run)
    started = datetime.now(timezone.utc)
    per_table: dict = {}
    total = 0
    for table, by_day in blank.items():
        info = manifest["tables"].get(table)
        if not info:
            log(f"WARNING: {table} not rebuilt; skipping")
            continue
        frame = pd.read_csv(staged / info["tsv"], sep="\t", dtype=str, keep_default_na=False).set_index(cm.TIMESTAMP_COLUMN)
        label_of = {col: label for col, label in info["columns"].items()}
        # Air days from the rebuilt (raw-temperature) data, as cm_out_of_water would see them.
        stats = []
        for d, g in frame.groupby(frame.index.str[:10]):
            temps = pd.to_numeric(g[t_col].replace("", None), errors="coerce") if t_col in g else pd.Series(dtype=float)
            depths = pd.to_numeric(g[d_col].replace("", None), errors="coerce") if d_col in g else pd.Series(dtype=float)
            n_t = int(((temps < band["min"]) | (temps > band["max"])).sum())
            n_d = int((depths <= cfg["zero_depth_ft"]).sum())
            t_range = float(temps.max() - temps.min()) if temps.notna().any() else None
            stats.append({"d": d, "n": len(g), "n_t": n_t, "n_d": n_d, "t_range": t_range})
        days = oow.air_days(stats, cfg)
        restored = {}
        for d, timestamps in sorted(by_day.items()):
            if d in days:
                log(f"{table} {d}: air day ({days[d]}); {len(timestamps)} rows stay NULL")
                continue
            n = 0
            for ts in sorted(timestamps):
                if ts not in frame.index:
                    log(f"  {table} {ts}: no rebuilt row (reading not selected by the rebuild); left NULL")
                    continue
                row = frame.loc[ts]
                temp = row.get(t_col, "")
                if temp == "" or not (float(temp) < band["min"] or float(temp) > band["max"]):
                    log(f"  {table} {ts}: rebuilt temperature {temp!r} is inside the band; not an air row, left as is")
                    continue
                sets = [f"{c} = {float(row[c])!r}" for c in label_of if c != t_col and row.get(c, "") != ""]
                if not sets:
                    continue
                n += 1
                if args.dry_run:
                    if n <= 3:
                        log(f"  [dry-run] {table} {ts}: {', '.join(sets)}")
                    continue
                spark.sql(f"UPDATE {ns}.`{table}` SET {', '.join(sets)} WHERE {cm.TIMESTAMP_COLUMN} = '{ts}'")
            restored[d] = n
            total += n
            log(f"{table} {d}: {n} of {len(timestamps)} rows restored (temperature stays NULL)")
        per_table[table] = {"restored": restored, "air_days": {d: days[d] for d in by_day if d in days}}
    log(f"{'would restore' if args.dry_run else 'restored'} {total} rows")
    if not args.dry_run and total:
        loader.record_run(
            {
                "ingest_run_id": RECORD_ID, "mode": "correction",
                "started_at": pd.Timestamp(started), "finished_at": pd.Timestamp.now(tz="UTC"), "status": "ok",
                "tables_loaded": len(per_table), "rows_staged": 0, "rows_appended": 0,
                "details": json.dumps({"correction": f"channels other than temperature restored from the raw archive on rows blanked by "
                                                     f"{OLD_RULE_ID} whose day the out_of_water rule does not judge out of the well",
                                       "tables": per_table}),
            },
            loader.existing_tables(),
        )
        log(f"recorded {RECORD_ID} in ingest_runs")


if __name__ == "__main__":
    main()
