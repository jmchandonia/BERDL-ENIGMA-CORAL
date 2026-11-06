#!/usr/bin/env python3
"""One-time link/prune migration of the live enigma.sso_staging tables (2026-11-06).

Gives every sample a key to the field draw it came from and drops the columns
the redundancy review found derivable or constant:
  * field_metadata:  add field_draw_id (primary key, YYYYMMDD-<well-port>-HHMM of
                     the pump start) FIRST, filled from sample_date + well_port +
                     pump_time_on; drop sample_date, pump_time_on, pump_time_off,
                     provenance
  * sample_registry: add field_draw_id after zone, filled where exactly one draw
                     matches the sample's date + well-port (several -> NULL, reported
                     by the build as SAMPLE DRAW AMBIGUOUS); drop assay_token,
                     source_sample_id, provenance
  * toc_tn_anions:   add field_draw_id after sdt_location_name, copied from the
                     sample's registry row; source_file gains the sheet name
                     (from provenance); drop source_sample_id, storage_condition,
                     timepoint, sample_date, well_port, zone, provenance
  * picarro_gas:     drop provenance
All ALTERs are Iceberg metadata operations; the UPDATEs touch the three small
tables only.  Column comments are NOT touched here: run
`sso_load.py --sync-comments --comments-only` after, then a normal load (the
field full refresh and the two upserts rewrite the rows from source).

    sso_migrate_20261106_links.py [--dry-run | --verify-only]
"""

from __future__ import annotations

import argparse
import os
import sys

import sso_common as sso
import sso_schema as schema
from sso_load import column_ddl, log, spark_session

DROPS = {
    "field_metadata": ["sample_date", "pump_time_on", "pump_time_off", "provenance"],
    "sample_registry": ["assay_token", "source_sample_id", "provenance"],
    "toc_tn_anions": ["source_sample_id", "storage_condition", "timepoint", "sample_date", "well_port", "zone", "provenance"],
    "picarro_gas": ["provenance"],
}
ADDS = {  # table -> (column, position clause)
    "field_metadata": ("field_draw_id", "FIRST"),
    "sample_registry": ("field_draw_id", "AFTER zone"),
    "toc_tn_anions": ("field_draw_id", "AFTER sdt_location_name"),
}


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

    F, R, T, G = (sso.full_name(t) for t in ("field_metadata", "sample_registry", "toc_tn_anions", "picarro_gas"))
    tables = list(DROPS)
    before = {t: spark.table(sso.full_name(t)).count() for t in tables}
    log(f"row counts before: {before}")

    cols = {t: {c["name"]: c for c in schema.TABLES[t]["columns"]} for t in ADDS}
    live = {t: spark.table(sso.full_name(t)).columns for t in tables}
    for t, (col, pos) in ADDS.items():
        if col not in live[t]:
            run(f"ALTER TABLE {sso.full_name(t)} ADD COLUMN {column_ddl(cols[t][col])} {pos}")

    # field_metadata: key from the columns about to be dropped
    if "pump_time_on" in live["field_metadata"]:
        run(f"UPDATE {F} SET field_draw_id = concat(replace(sample_date, '-', ''), '-', well_port, '-', "
            f"substr(pump_time_on, 1, 2), substr(pump_time_on, 4, 2)) WHERE field_draw_id IS NULL")
    # sample_registry: the one matching draw, else NULL
    run(f"""MERGE INTO {R} r USING (
              SELECT r2.sdt_sample_name, max(f.field_draw_id) draw, count(*) n
              FROM {R} r2 JOIN {F} f ON f.well_port = r2.well_port
                   AND substr(f.pump_on_datetime, 1, 10) = r2.sample_date
              GROUP BY r2.sdt_sample_name) m
            ON m.sdt_sample_name = r.sdt_sample_name AND m.n = 1
            WHEN MATCHED THEN UPDATE SET r.field_draw_id = m.draw""")
    # toc_tn_anions: via the sample; sheet name folded into source_file
    run(f"""MERGE INTO {T} t USING {R} r ON r.sdt_sample_name = t.sdt_sample_name
            WHEN MATCHED THEN UPDATE SET t.field_draw_id = r.field_draw_id""")
    if "provenance" in live["toc_tn_anions"]:
        run(f"UPDATE {T} SET source_file = regexp_extract(provenance, '^chakraborty toc/tn/anions (.*)$', 1) "
            f"WHERE provenance RLIKE '^chakraborty toc/tn/anions .* \\\\[.*\\\\]$'")
    for t, names in DROPS.items():
        present = [n for n in names if n in live[t]]
        if present:
            run(f"ALTER TABLE {sso.full_name(t)} DROP COLUMN {', '.join(sso.quoted(n) for n in present)}")

    if args.dry_run:
        log("dry run: nothing changed")
        return

    # --- verify ---
    problems = []
    after = {t: spark.table(sso.full_name(t)).count() for t in tables}
    if after != before:
        problems.append(f"row counts changed: {before} -> {after}")
    for t in tables:
        want = [c["name"] for c in schema.TABLES[t]["columns"]]
        have = spark.table(sso.full_name(t)).columns
        if have != want:
            problems.append(f"{t} columns differ from schema: live {have} vs schema {want}")
    f = one(f"SELECT count(*) n, count(DISTINCT field_draw_id) keys, sum(CASE WHEN field_draw_id IS NULL OR NOT field_draw_id "
            f"RLIKE '^[0-9]{{8}}-[A-Z0-9-]+-[0-9]{{4}}$' THEN 1 ELSE 0 END) bad, "
            f"sum(CASE WHEN field_draw_id != concat(replace(substr(pump_on_datetime,1,10),'-',''), '-', well_port, '-', "
            f"substr(pump_on_datetime,12,2), substr(pump_on_datetime,15,2)) THEN 1 ELSE 0 END) mismatch FROM {F}")
    log(f"field_metadata verify: {f.asDict()}")
    if f["keys"] != f["n"] or f["bad"] or f["mismatch"]:
        problems.append("field_draw_id not unique / malformed / inconsistent with pump_on_datetime")
    r = one(f"SELECT count(*) n, sum(CASE WHEN r.field_draw_id IS NOT NULL THEN 1 ELSE 0 END) linked, "
            f"sum(CASE WHEN r.field_draw_id IS NOT NULL AND f.field_draw_id IS NULL THEN 1 ELSE 0 END) orphan, "
            f"sum(CASE WHEN f.field_draw_id IS NOT NULL AND (f.well_port != r.well_port OR substr(f.pump_on_datetime,1,10) != r.sample_date) "
            f"THEN 1 ELSE 0 END) wrong_draw FROM {R} r LEFT JOIN {F} f ON f.field_draw_id = r.field_draw_id")
    log(f"sample_registry verify: {r.asDict()}")
    if r["orphan"] or r["wrong_draw"]:
        problems.append("sample_registry field_draw_id orphans or wrong draws")
    t = one(f"SELECT count(*) n, sum(CASE WHEN t.field_draw_id IS NOT NULL THEN 1 ELSE 0 END) linked, "
            f"sum(CASE WHEN t.field_draw_id <=> r.field_draw_id THEN 0 ELSE 1 END) differs_from_registry, "
            f"sum(CASE WHEN t.source_file RLIKE '\\\\[.*\\\\]$' THEN 0 ELSE 1 END) no_sheet FROM {T} t LEFT JOIN {R} r ON r.sdt_sample_name = t.sdt_sample_name")
    log(f"toc_tn_anions verify: {t.asDict()}")
    if t["differs_from_registry"] or t["no_sheet"]:
        problems.append("toc_tn_anions field_draw_id differs from the registry or source_file lacks the sheet")
    if problems:
        sys.exit("VERIFY FAILED:\n  " + "\n  ".join(problems))
    log("VERIFY OK")


if __name__ == "__main__":
    main()
