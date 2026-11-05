#!/usr/bin/env python3
"""One-time datetime normalization of the live enigma.sso_staging tables (2026-11-05).

Makes every datetime column the same shape as continuous_monitoring and the
CORAL bricks (ISO 8601, millisecond precision, Eastern UTC offset) and every
date column the CORAL date form:
  * picarro_gas.time_series_datetime: Python isoformat() emitted microseconds or
    nothing (32 / 25 chars) -> `2026-10-04T18:50:50.223-04:00` (29 chars)
  * picarro_gas.firesting_datetime: naive `2026-10-26 18:07:38` -> the same ISO
    form with the row's own UTC offset (the Firesting clock is Eastern wall clock)
  * sample_date in field_metadata / sample_registry / toc_tn_anions:
    YYYYMMDD -> YYYY-MM-DD
  * field_metadata: add pump_on_datetime / pump_off_datetime after pump_time_off
    (NULL until the next load's full refresh fills them from the source sheet)
Column comments are NOT touched here: run `sso_load.py --sync-comments
--comments-only` after.  Verification re-reads every table.

    sso_migrate_20261105_datetimes.py [--dry-run | --verify-only]
"""

from __future__ import annotations

import argparse
import os
import sys

import sso_common as sso
import sso_schema as schema
from sso_load import column_ddl, log, spark_session

DATE_TABLES = ["field_metadata", "sample_registry", "toc_tn_anions"]
NEW_FIELD_COLUMNS = ["pump_on_datetime", "pump_off_datetime"]
TS, FS = "time_series_datetime", "firesting_datetime"
# [0-9] rather than \d: Spark SQL string literals treat the backslash as an escape.
ISO_RE = "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[.][0-9]{3}[+-][0-9]{2}:[0-9]{2}$"
DATE_RE = "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify-only", action="store_true", help="skip the statements, re-run the verification")
    args = ap.parse_args()

    sso.load_env_file(sso.credentials_file())
    token = os.environ.get("KBASE_AUTH_TOKEN") or os.environ.get("KB_AUTH_TOKEN")
    if not token:
        sys.exit("KBASE_AUTH_TOKEN is not set")
    spark = spark_session(token)
    one = lambda q: spark.sql(q).collect()[0]  # noqa: E731

    def run(statement):
        if args.verify_only:
            return
        log(("[dry-run] " if args.dry_run else "") + " ".join(statement.split())[:240])
        if not args.dry_run:
            spark.sql(statement)

    gas = sso.full_name("picarro_gas")
    tables = ["picarro_gas", *DATE_TABLES]
    before = {t: spark.table(sso.full_name(t)).count() for t in tables}
    gas_before = one(f"SELECT sum(CASE WHEN {FS} IS NULL OR {FS} = '' THEN 1 ELSE 0 END) fs_null, "
                     f"count(DISTINCT epoch_time, picarro_serial) keys FROM {gas}")
    log(f"row counts before: {before}; gas rows without a Firesting reading: {gas_before['fs_null']}; "
        f"distinct (epoch_time, picarro_serial): {gas_before['keys']}")
    shapes = {r["len"]: r["n"] for r in spark.sql(f"SELECT length({TS}) len, count(*) n FROM {gas} GROUP BY 1").collect()}
    log(f"gas {TS} lengths before: {shapes}")

    # 1. picarro_gas.time_series_datetime -> millisecond form (two string shapes today)
    run(f"UPDATE {gas} SET {TS} = concat(substr({TS}, 1, 19), '.000', substr({TS}, 20)) WHERE length({TS}) = 25")
    run(f"UPDATE {gas} SET {TS} = concat(substr({TS}, 1, 23), substr({TS}, 27)) WHERE length({TS}) = 32")
    # 2. firesting_datetime -> ISO with the row's offset (offset = last 6 chars of the normalized TS)
    run(f"UPDATE {gas} SET {FS} = concat(replace({FS}, ' ', 'T'), '.000', substr({TS}, 24, 6)) "
        f"WHERE {FS} IS NOT NULL AND {FS} != '' AND length({FS}) = 19")
    # 3. sample_date -> YYYY-MM-DD
    for t in DATE_TABLES:
        run(f"UPDATE {sso.full_name(t)} SET sample_date = concat(substr(sample_date, 1, 4), '-', "
            f"substr(sample_date, 5, 2), '-', substr(sample_date, 7, 2)) WHERE sample_date RLIKE '^[0-9]{{8}}$'")
    # 4. field_metadata: the two derived datetime columns, positioned per the schema
    cols = schema.TABLES["field_metadata"]["columns"]
    names = [c["name"] for c in cols]
    live = spark.table(sso.full_name("field_metadata")).columns
    for c in cols:
        if c["name"] in NEW_FIELD_COLUMNS and c["name"] not in live:
            run(f"ALTER TABLE {sso.full_name('field_metadata')} ADD COLUMN {column_ddl(c)} "
                f"AFTER {sso.quoted(names[names.index(c['name']) - 1])}")

    if args.dry_run:
        log("dry run: nothing changed")
        return

    # --- verify ---
    problems = []
    after = {t: spark.table(sso.full_name(t)).count() for t in tables}
    if after != before:
        problems.append(f"row counts changed: {before} -> {after}")
    g = one(f"SELECT sum(CASE WHEN {TS} RLIKE '{ISO_RE}' THEN 0 ELSE 1 END) bad_ts, "
            f"sum(CASE WHEN to_timestamp({TS}) IS NULL THEN 1 ELSE 0 END) unparsed_ts, "
            f"sum(CASE WHEN abs(unix_micros(to_timestamp({TS})) / 1000 - round(epoch_time * 1000)) > 0.5 THEN 1 ELSE 0 END) ts_vs_epoch, "
            f"sum(CASE WHEN {FS} IS NULL OR {FS} = '' THEN 1 ELSE 0 END) fs_null, "
            f"sum(CASE WHEN {FS} IS NOT NULL AND {FS} != '' AND NOT {FS} RLIKE '{ISO_RE}' THEN 1 ELSE 0 END) bad_fs, "
            f"sum(CASE WHEN {FS} IS NOT NULL AND {FS} != '' AND abs(unix_timestamp(to_timestamp({FS})) - epoch_time) > 31 THEN 1 ELSE 0 END) fs_far, "
            f"sum(CASE WHEN substr({FS}, 24, 6) != substr({TS}, 24, 6) THEN 1 ELSE 0 END) fs_offset, "
            f"count(DISTINCT epoch_time, picarro_serial) keys FROM {gas}")
    log(f"gas verify: {g.asDict()}")
    for k in ("bad_ts", "unparsed_ts", "ts_vs_epoch", "bad_fs", "fs_far", "fs_offset"):
        if g[k]:
            problems.append(f"picarro_gas {k} = {g[k]}")
    if g["fs_null"] != gas_before["fs_null"] or g["keys"] != gas_before["keys"]:
        problems.append("picarro_gas firesting-null count or key count changed")
    for t in DATE_TABLES:
        bad = one(f"SELECT sum(CASE WHEN sample_date RLIKE '{DATE_RE}' THEN 0 ELSE 1 END) bad, "
                  f"sum(CASE WHEN to_date(sample_date) IS NULL THEN 1 ELSE 0 END) unparsed FROM {sso.full_name(t)}")
        log(f"{t} sample_date verify: {bad.asDict()}")
        if bad["bad"] or bad["unparsed"]:
            problems.append(f"{t} sample_date not YYYY-MM-DD on {bad['bad']} rows ({bad['unparsed']} unparsed)")
    for t in tables:
        want = [c["name"] for c in schema.TABLES[t]["columns"]]
        have = spark.table(sso.full_name(t)).columns
        if have != want:
            problems.append(f"{t} columns differ from schema: live {have} vs schema {want}")
    if problems:
        sys.exit("VERIFY FAILED:\n  " + "\n  ".join(problems))
    log("VERIFY OK (pump_on_datetime / pump_off_datetime are NULL until the next load's full refresh)")


if __name__ == "__main__":
    main()
