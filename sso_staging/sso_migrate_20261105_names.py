#!/usr/bin/env python3
"""One-time rename/reshape of the live enigma.sso_staging tables (2026-11-05).

Brings the live tables in line with sso_schema after the naming review:
  * every data table:  location -> well_port;  drop well
  * picarro_gas:       instrument -> picarro_serial;  add reference_channel after
                       well_port, filled from well_port on the reference rows
                       (well_port set NULL there);  drop channel_type
Everything but the one UPDATE is an Iceberg metadata operation.  Column comments
are NOT touched here: run `sso_load.py --sync-comments --comments-only` after.
The obsolete bookkeeping tables (ddt_brick, instrument_port) are dropped only
with --drop-obsolete (column_typedef is created by the next load).

    sso_migrate_20261105_names.py [--dry-run] [--drop-obsolete]
"""

from __future__ import annotations

import argparse
import os
import sys

import sso_common as sso
import sso_schema as schema
from sso_load import log, spark_session

RENAMES = {  # table -> [(old, new)]
    "picarro_gas": [("instrument", "picarro_serial"), ("location", "well_port")],
    "field_metadata": [("location", "well_port")],
    "sample_registry": [("location", "well_port")],
    "toc_tn_anions": [("location", "well_port")],
}
DROPS = {"picarro_gas": ["well", "channel_type"], "field_metadata": ["well"], "toc_tn_anions": ["well"]}
OBSOLETE_TABLES = ["ddt_brick", "instrument_port"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--drop-obsolete", action="store_true", help="also DROP TABLE ddt_brick, instrument_port")
    args = ap.parse_args()

    sso.load_env_file(sso.credentials_file())
    token = os.environ.get("KBASE_AUTH_TOKEN") or os.environ.get("KB_AUTH_TOKEN")
    if not token:
        sys.exit("KBASE_AUTH_TOKEN is not set")
    spark = spark_session(token)

    def run(statement):
        log(("[dry-run] " if args.dry_run else "") + statement[:220])
        if not args.dry_run:
            spark.sql(statement)

    before = {t: spark.table(sso.full_name(t)).count() for t in RENAMES}
    gas = sso.full_name("picarro_gas")
    ref_rows = spark.sql(f"SELECT count(*) n FROM {gas} WHERE channel_type = 'reference'").collect()[0]["n"] \
        if "channel_type" in spark.table(gas).columns else None
    log(f"row counts before: {before}; reference rows: {ref_rows}")

    for table, pairs in RENAMES.items():
        live = set(spark.table(sso.full_name(table)).columns)
        for old, new in pairs:
            if old in live and new not in live:
                run(f"ALTER TABLE {sso.full_name(table)} RENAME COLUMN {sso.quoted(old)} TO {sso.quoted(new)}")
            elif new in live:
                log(f"{table}.{new} already present; skipping rename of {old}")
            else:
                sys.exit(f"{table}: expected column {old!r} not found")

    live = set(spark.table(gas).columns)
    if "reference_channel" not in live:
        spec = next(c for c in schema.GAS_COLUMNS if c["name"] == "reference_channel")
        from sso_load import column_ddl
        run(f"ALTER TABLE {gas} ADD COLUMN {column_ddl(spec)} AFTER `well_port`")
    if "channel_type" in live:
        run(f"UPDATE {gas} SET reference_channel = well_port, well_port = NULL WHERE channel_type = 'reference'")

    for table, cols in DROPS.items():
        live = set(spark.table(sso.full_name(table)).columns)
        for col in cols:
            if col in live:
                run(f"ALTER TABLE {sso.full_name(table)} DROP COLUMN {sso.quoted(col)}")

    if args.drop_obsolete:
        for table in OBSOLETE_TABLES:
            run(f"DROP TABLE IF EXISTS {sso.full_name(table)}")

    if args.dry_run:
        log("[dry-run] no changes made")
        return

    # --- verify
    ok = True
    for table, spec in schema.TABLES.items():
        live = spark.table(sso.full_name(table)).columns
        want = [c["name"] for c in spec["columns"]]
        if live != want:
            ok = False
            log(f"MISMATCH {table}: live {live} != schema {want}")
        n = spark.table(sso.full_name(table)).count()
        if n != before[table]:
            ok = False
            log(f"MISMATCH {table}: {before[table]} rows before, {n} after")
    q = spark.sql(f"""SELECT count(*) total,
                sum(CASE WHEN reference_channel IS NOT NULL THEN 1 ELSE 0 END) ref,
                sum(CASE WHEN reference_channel IS NOT NULL AND well_port IS NOT NULL THEN 1 ELSE 0 END) both,
                sum(CASE WHEN reference_channel IS NULL AND well_port IS NULL THEN 1 ELSE 0 END) neither,
                sum(CASE WHEN picarro_serial IS NULL THEN 1 ELSE 0 END) no_serial,
                count(DISTINCT epoch_time, picarro_serial) keys FROM {gas}""").collect()[0]
    log(f"picarro_gas after: {dict(q.asDict())}")
    if ref_rows is not None and q["ref"] != ref_rows or q["both"] or q["neither"] or q["no_serial"] or q["keys"] != q["total"]:
        ok = False
    print("VERIFY", "OK" if ok else "FAILED", flush=True)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
