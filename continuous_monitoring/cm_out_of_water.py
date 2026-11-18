#!/usr/bin/env python3
"""Null Aqua TROLL readings taken out of the well, on the live tables (year-round rule).

corrections.json "out_of_water" describes the rule; this script applies it to
every hazen_aquatroll600_* table in the lakehouse:

  1. depth to water at or below zero_depth_ft -> depth NULL.  No water above
     the pressure sensor; the water table never came within 0.33 ft of the
     surface here, even at the peak of a storm.
  2. temperature outside water_temperature_c -> temperature NULL.  Groundwater
     here is 14-21 C (10.6 C after winter storms at L7, 22.6 C at the 99th
     percentile); outside 8-25 C the sonde is in air, a shed or a bucket.
  3. A sonde-day on which at least air_day_share of the readings are outside
     the temperature band, or at least that share have no depth while the
     temperature swings more than air_day_temperature_range_c (water never
     does; air does), is a day the sonde spent out of the well: every channel
     of every reading flagged by 1 or 2 that day is nulled.  Rows that are
     already all-NULL count as flagged, so a day stays an air day when late
     readings arrive for it.  Days with fewer than MIN_ROWS readings are not
     judged (the row rules still apply).

Oxygen, conductivity and water-level swings are deliberately not used: every
big storm raises oxygen to saturation, halves the conductivity and moves the
water table 4-10 ft in several of these fracture-fed wells at once, which is
exactly what a lifted sonde looks like on those channels.

The rule is applied after the load rather than at stage time because the
day-level decision needs whole days and the loader appends partial days.
Every action is idempotent and only ever nulls more, so re-evaluating a
window of recent days each run is safe.

    cm_out_of_water.py --run-id RUN --result STAGE/load_result.json   (run_daily.sh: last window_days)
    cm_out_of_water.py --since 2024-01-01 --record-id out-of-water-20261119 [--dry-run]   (once, history)

What was nulled is written into the --result JSON under "out_of_water" (the
daily report shows it) and, when anything changed, recorded in ingest_runs
(mode "correction").  Requires the BERDL proxy chain, like cm_load.py.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

import cm_common as cm
import cm_load

EASTERN = ZoneInfo("America/New_York")
MIN_ROWS = 3  # readings a sonde-day needs before it can be judged out of the well


def log(msg: str) -> None:
    print(msg, flush=True)


def config() -> dict:
    cfg = cm.load_corrections().get("out_of_water")
    if not cfg:
        sys.exit("corrections.json has no out_of_water entry")
    return cfg


def air_days(stats: list[dict], cfg: dict) -> dict[str, str]:
    """Decide which sonde-days were spent out of the well.

    stats: one dict per local date with n (rows), n_t (rows with temperature
    outside the band, or all-NULL), n_d (rows with depth at or below the zero
    threshold, or all-NULL) and t_range (max - min temperature of the day's
    non-NULL readings, None if none).  Returns {date: reason}.
    """
    share = float(cfg["air_day_share"])
    swing = float(cfg["air_day_temperature_range_c"])
    out: dict[str, str] = {}
    for s in stats:
        n = s["n"]
        if n < MIN_ROWS:
            continue
        if s["n_t"] / n >= share:
            out[s["d"]] = "temperature"
        elif s["n_d"] / n >= share and s.get("t_range") is not None and s["t_range"] > swing:
            out[s["d"]] = "zero depth"
    return out


class Checker:
    def __init__(self, spark, cfg: dict, dry_run: bool):
        self.spark = spark
        self.cfg = cfg
        self.dry_run = dry_run
        self.ns = ".".join(f"`{p}`" for p in cm.NAMESPACE.split("."))
        columns = cm.load_column_map()["measurements"]
        self.measurement_cols = {v["column"] for v in columns.values()}
        self.t_col = columns[cfg["temperature_label"]]["column"]
        self.d_col = columns[cfg["depth_label"]]["column"]
        band = cfg["water_temperature_c"]
        self.t_min, self.t_max = float(band["min"]), float(band["max"])
        self.zero = float(cfg["zero_depth_ft"])
        self.ts = cm.TIMESTAMP_COLUMN

    def tables(self) -> list[str]:
        rows = self.spark.sql(f"SHOW TABLES IN {self.ns}").collect()
        return sorted(r["tableName"] for r in rows if r["tableName"].startswith(self.cfg["table_prefix"]))

    def count(self, target: str, where: str) -> int:
        return int(self.spark.sql(f"SELECT count(*) AS n FROM {target} WHERE {where}").collect()[0]["n"])

    def update(self, target: str, assignments: str, where: str) -> int:
        """Run an UPDATE (unless dry-run) and verify nothing matching remains; returns rows matched."""
        n = self.count(target, where)
        if not n:
            return 0
        if self.dry_run:
            log(f"  [dry-run] would UPDATE {target} SET {assignments[:80]}... WHERE {where[:160]}  ({n} rows)")
            return n
        self.spark.sql(f"UPDATE {target} SET {assignments} WHERE {where}")
        left = self.count(target, where)
        if left:
            sys.exit(f"{target}: {left} rows still match after UPDATE; stopping")
        return n

    def check_table(self, table: str, since: str, until: str) -> dict:
        target = f"{self.ns}.`{table}`"
        cols = self.spark.table(target).columns
        if self.t_col not in cols:
            return {}
        meas = [c for c in cols if c in self.measurement_cols]
        has_depth = self.d_col in cols
        ts, T, D = self.ts, self.t_col, self.d_col
        date_expr = f"substr({ts}, 1, 10)"
        in_window = f"{date_expr} BETWEEN '{since}' AND '{until}'"
        all_null = " AND ".join(f"{c} IS NULL" for c in meas)
        flag_t = f"({T} < {self.t_min!r} OR {T} > {self.t_max!r})"
        flag_d = f"({D} <= {self.zero!r})" if has_depth else None
        stats = self.spark.sql(
            f"SELECT {date_expr} AS d, count(*) AS n, "
            f"sum(CASE WHEN {flag_t} OR ({all_null}) THEN 1 ELSE 0 END) AS n_t, "
            f"sum(CASE WHEN {flag_d + ' OR ' if flag_d else ''}({all_null}) THEN 1 ELSE 0 END) AS n_d, "
            f"max({T}) - min({T}) AS t_range "
            f"FROM {target} WHERE {in_window} GROUP BY 1"
        ).collect()
        days = air_days([{"d": r["d"], "n": int(r["n"]), "n_t": int(r["n_t"]), "n_d": int(r["n_d"]), "t_range": r["t_range"]} for r in stats], self.cfg)
        result: dict = {"air_days": {}, "temperature_nulled": 0, "depth_nulled": 0}
        if days:
            flagged = " OR ".join(x for x in (flag_t, flag_d) if x)
            null_all = ", ".join(f"{c} = NULL" for c in meas)
            for d in sorted(days):
                n = self.update(target, null_all, f"{date_expr} = '{d}' AND ({flagged})")
                if n:
                    result["air_days"][d] = {"rows": n, "why": days[d]}
                    log(f"{table} {d}: {n} readings out of the well ({days[d]}); every channel nulled")
        n = self.update(target, f"{T} = NULL", f"{in_window} AND {flag_t}")
        if n:
            result["temperature_nulled"] = n
            log(f"{table}: {n} temperatures outside {self.t_min:g}-{self.t_max:g} C nulled")
        if flag_d:
            n = self.update(target, f"{D} = NULL", f"{in_window} AND {flag_d}")
            if n:
                result["depth_nulled"] = n
                log(f"{table}: {n} depths at or below {self.zero:g} ft nulled")
        return result if (result["air_days"] or result["temperature_nulled"] or result["depth_nulled"]) else {}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-id", default=None, help="daily run id; the ingest_runs record is <run-id>-out-of-water")
    parser.add_argument("--record-id", default=None, help="record under this id instead (one-time history pass; refused if already recorded)")
    parser.add_argument("--since", default=None, help="first local date to evaluate (default: today - window_days)")
    parser.add_argument("--until", default=None, help="last local date to evaluate (default: today)")
    parser.add_argument("--tables", nargs="*", help="only these tables")
    parser.add_argument("--result", type=Path, default=None, help="JSON file to merge the summary into under 'out_of_water' (load_result.json)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--wait-for-spark", type=int, default=0)
    args = parser.parse_args()

    cfg = config()
    today = datetime.now(EASTERN).date()
    until = args.until or today.isoformat()
    since = args.since or (today - timedelta(days=int(cfg["window_days"]))).isoformat()
    record_id = args.record_id or f"{args.run_id or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-out-of-water"

    cm.load_env_file(cm.credentials_file())
    token = os.environ.get("KBASE_AUTH_TOKEN") or os.environ.get("KB_AUTH_TOKEN")
    if not token:
        sys.exit(f"KBASE_AUTH_TOKEN is not set (environment or {cm.credentials_file()})")
    deadline = time.monotonic() + args.wait_for_spark
    while True:
        try:
            spark = cm_load.spark_session(token)
            spark.sql("SELECT 1").collect()
            break
        except Exception as exc:
            if time.monotonic() > deadline:
                raise
            log(f"Spark Connect not ready ({exc!r}); retrying")
            time.sleep(15)
    checker = Checker(spark, cfg, args.dry_run)
    if args.record_id:
        done = spark.sql(f"SELECT count(*) FROM {checker.ns}.ingest_runs WHERE ingest_run_id = '{args.record_id}'").collect()[0][0]
        if done:
            sys.exit(f"{args.record_id} is already recorded in ingest_runs; refusing to apply it twice")

    started = datetime.now(timezone.utc)
    log(f"out-of-water check {since}..{until}{' (dry run)' if args.dry_run else ''}")
    summary: dict = {"id": record_id, "since": since, "until": until, "tables": {}, "rows_nulled": 0, "temperature_nulled": 0, "depth_nulled": 0}
    for table in checker.tables():
        if args.tables and table not in args.tables:
            continue
        result = checker.check_table(table, since, until)
        if result:
            summary["tables"][table] = result
            summary["rows_nulled"] += sum(v["rows"] for v in result["air_days"].values())
            summary["temperature_nulled"] += result["temperature_nulled"]
            summary["depth_nulled"] += result["depth_nulled"]
    changed = summary["rows_nulled"] or summary["temperature_nulled"] or summary["depth_nulled"]
    log(f"out-of-water check done: {summary['rows_nulled']} readings nulled on air days, "
        f"{summary['temperature_nulled']} temperatures and {summary['depth_nulled']} depths nulled"
        f"{' (dry run: nothing written)' if args.dry_run else ''}")
    if args.result is not None and not args.dry_run:
        data = json.loads(args.result.read_text()) if args.result.exists() else {}
        data["out_of_water"] = summary
        args.result.write_text(json.dumps(data, indent=2, default=str) + "\n")
    if changed and not args.dry_run:
        loader = cm_load.Loader(spark, record_id, False)
        loader.record_run(
            {
                "ingest_run_id": record_id, "mode": "correction",
                "started_at": pd.Timestamp(started), "finished_at": pd.Timestamp.now(tz="UTC"), "status": "ok",
                "tables_loaded": len(summary["tables"]), "rows_staged": 0, "rows_appended": 0,
                "details": json.dumps({"correction": f"out_of_water rule applied to local dates {since}..{until}: {cfg['reason']}",
                                       "tables": summary["tables"]}),
            },
            loader.existing_tables(),
        )
        log(f"recorded {record_id} in ingest_runs")


if __name__ == "__main__":
    main()
