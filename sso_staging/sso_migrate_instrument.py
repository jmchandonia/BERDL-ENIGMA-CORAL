#!/usr/bin/env python3
"""One-time backfill of picarro_gas.instrument (2026-11-04).

The table was first modeled with one analyzer; Gas_Data/README.txt (updated
2026-10-28) documents two Picarro G2508s running concurrently.  After
`sso_load.py --add-columns` has added the nullable `instrument` column, this
fills it for every existing row with the same two rules sso_build.py applies
to new rows (sso_schema.GAS_WELL_INSTRUMENT for well-ports, the NH3_dry / O2_%
column signature for reference channels), refusing to write if any row would
be left unattributed or if the two rules disagree on any well-port row.

    sso_migrate_instrument.py [--dry-run]     # dry run prints the counts only
"""

from __future__ import annotations

import argparse
import os
import sys

import sso_common as sso
import sso_schema as schema
from sso_load import log, spark_session

TABLE = sso.full_name("picarro_gas")
NH3_DRY = "concentration_molecule_from_list_ammonia_condition_dry_parts_per_billion"
O2_WET = "concentration_molecule_from_list_dioxygen_instrument_picarro_condition_wet_percent"


def rule_sql() -> tuple[str, str]:
    """(assignment CASE, signature CASE) as SQL expressions over the table's columns."""
    by_serial = {}
    for loc, serial in schema.GAS_WELL_INSTRUMENT.items():
        by_serial.setdefault(serial, []).append(loc)
    assigned = "CASE " + " ".join(
        f"WHEN channel_type = 'well' AND location IN ({', '.join(sso.sql_string(l) for l in locs)}) THEN {sso.sql_string(serial)}"
        for serial, locs in by_serial.items()) + " END"
    sig_col = {"NH3_dry": NH3_DRY, "O2_%": O2_WET}
    signature = "CASE " + " ".join(
        f"WHEN {sso.quoted(sig_col[meta['signature']])} IS NOT NULL THEN {sso.sql_string(serial)}"
        for serial, meta in schema.GAS_INSTRUMENTS.items()) + " END"
    return assigned, signature


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sso.load_env_file(sso.credentials_file())
    token = os.environ.get("KBASE_AUTH_TOKEN") or os.environ.get("KB_AUTH_TOKEN")
    if not token:
        sys.exit("KBASE_AUTH_TOKEN is not set")
    spark = spark_session(token)

    cols = spark.table(TABLE).columns
    if "instrument" not in cols:
        sys.exit("picarro_gas has no instrument column yet: run sso_load.py --add-columns first")
    assigned, signature = rule_sql()
    value = f"COALESCE({assigned}, {signature})"
    q = spark.sql(f"""
        SELECT count(*) total,
               sum(CASE WHEN instrument IS NULL THEN 1 ELSE 0 END) null_now,
               sum(CASE WHEN {value} IS NULL THEN 1 ELSE 0 END) unattributed,
               sum(CASE WHEN {assigned} IS NOT NULL AND {signature} IS NOT NULL AND {assigned} <> {signature} THEN 1 ELSE 0 END) conflicts,
               sum(CASE WHEN instrument IS NOT NULL AND instrument <> {value} THEN 1 ELSE 0 END) would_change
        FROM {TABLE}""").collect()[0]
    log(f"picarro_gas: {q['total']:,} rows; instrument null now {q['null_now']:,}; "
        f"unattributed by the rules {q['unattributed']:,}; conflicts {q['conflicts']:,}; "
        f"already set but different {q['would_change']:,}")
    for r in spark.sql(f"SELECT {value} instrument, channel_type, count(*) n FROM {TABLE} "
                       f"GROUP BY 1, 2 ORDER BY 1, 2").collect():
        log(f"  {r['instrument']}  {r['channel_type']:<9} {r['n']:>9,}")
    if q["unattributed"] or q["conflicts"] or q["would_change"]:
        sys.exit("refusing to backfill: rows unattributed, conflicting, or already set differently (see above)")
    if args.dry_run:
        log("[dry-run] no UPDATE issued")
        return
    spark.sql(f"UPDATE {TABLE} SET instrument = {value} WHERE instrument IS NULL")
    after = spark.sql(f"""
        SELECT count(*) total, sum(CASE WHEN instrument IS NULL THEN 1 ELSE 0 END) null_after,
               count(DISTINCT epoch_time, instrument) distinct_keys
        FROM {TABLE}""").collect()[0]
    log(f"after: {after['total']:,} rows, {after['null_after']:,} null, {after['distinct_keys']:,} distinct (epoch_time, instrument)")
    if after["null_after"] or after["distinct_keys"] != after["total"]:
        sys.exit("post-check FAILED")
    log("backfill complete")


if __name__ == "__main__":
    main()
