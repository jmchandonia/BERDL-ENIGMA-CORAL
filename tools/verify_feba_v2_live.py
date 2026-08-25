#!/usr/bin/env python3
"""Verify the live BERDL state of the 22 corrected FEBa v2 fitness bricks."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPTS = ROOT / "skills/sync-coral-to-berdl/scripts"
sys.path.insert(0, str(SYNC_SCRIPTS))

from run_full_import import (  # noqa: E402
    _create_spark_session,
    _patch_spark_connect_config_defaults,
    _set_remote_connection_env_defaults,
)
from run_sync_pipeline import _load_dotenv  # noqa: E402


BRICK_IDS = [f"Brick{i:07d}" for i in range(1699, 1721)]
TABLES = [brick_id.lower().replace("brick", "ddt_brick") for brick_id in BRICK_IDS]
VALUE_COLUMNS = [
    "sdt_gene_gene_id",
    "sdt_genome_name",
    "sdt_condition_name",
    "sdt_tnseq_library_name",
    "fitness_score_log_ratio_unit",
    "average_statistic_t_score_comment_source_column_t_feba_t_statistic_dimensionless_unit",
]
COMO_IDS = {"ME:0000335", "ME:0000336", "ME:0000337", "ME:0000338"}


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def spark_session():
    _set_remote_connection_env_defaults()
    spark = _create_spark_session(
        token=os.environ["KBASE_AUTH_TOKEN"],
        app_name="verify-feba-v2-live",
    )
    _patch_spark_connect_config_defaults(spark)
    return spark


def collect_dicts(frame) -> list[dict[str, Any]]:
    return [row.asDict(recursive=True) for row in frame.collect()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=ROOT / "sync-coral-to-berdl/exports/sync-20260825-113646",
    )
    parser.add_argument("--namespace", default="enigma_coral")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    _load_dotenv(args.env_file.resolve(), prefer_file=True)
    if not os.environ.get("KBASE_AUTH_TOKEN"):
        raise RuntimeError("KBASE_AUTH_TOKEN is absent from the environment and env file")

    manifest = json.loads((run_dir / "manifests/current.json").read_text())
    expected_counts = {
        row["table"]: int(row["row_count"])
        for row in manifest["tables"]
        if row["table"] in TABLES
    }
    if set(expected_counts) != set(TABLES):
        raise ValueError("Current manifest does not contain exactly the 22 v2 tables")

    null_predicate = " OR ".join(f"`{column}` IS NULL" for column in VALUE_COLUMNS)
    stats_sql = " UNION ALL ".join(
        f"SELECT '{table}' AS table_name, COUNT(*) AS row_count, "
        f"SUM(CASE WHEN {null_predicate} THEN 1 ELSE 0 END) AS rows_with_null "
        f"FROM `{args.namespace}`.`{table}`"
        for table in TABLES
    )

    local_ndarray = {
        row["ddt_ndarray_id"]: row
        for row in read_tsv(run_dir / "berdl_upload/data/ddt_ndarray.tsv")
    }
    old_ids = [f"Brick{i:07d}" for i in range(1675, 1697)]
    lifecycle_ids = ["Brick0000006", *old_ids, *BRICK_IDS]
    quoted_ids = ",".join(f"'{value}'" for value in lifecycle_ids)
    lifecycle_sql = (
        "SELECT ddt_ndarray_id, withdrawn_date, superceded_by_ddt_ndarray_id "
        f"FROM `{args.namespace}`.`ddt_ndarray` "
        f"WHERE ddt_ndarray_id IN ({quoted_ids})"
    )

    quoted_terms = ",".join(f"'{value}'" for value in sorted(COMO_IDS))
    como_sql = (
        "SELECT sys_oterm_id, parent_sys_oterm_id, sys_oterm_ontology, "
        "sys_oterm_name, sys_oterm_synonyms, sys_oterm_definition, "
        "sys_oterm_links, sys_oterm_properties "
        f"FROM `{args.namespace}`.`sys_oterm` WHERE sys_oterm_id IN ({quoted_terms})"
    )

    spark = spark_session()
    live_stats = collect_dicts(spark.sql(stats_sql))
    live_lifecycle = collect_dicts(spark.sql(lifecycle_sql))
    live_como = collect_dicts(spark.sql(como_sql))

    count_mismatches = [
        row for row in live_stats
        if int(row["row_count"]) != expected_counts[row["table_name"]]
    ]
    null_failures = [row for row in live_stats if int(row["rows_with_null"] or 0)]
    expected_lifecycle = {
        key: {
            "withdrawn_date": value["withdrawn_date"] or None,
            "superceded_by_ddt_ndarray_id": value["superceded_by_ddt_ndarray_id"] or None,
        }
        for key, value in local_ndarray.items()
        if key in lifecycle_ids
    }
    actual_lifecycle = {
        row["ddt_ndarray_id"]: {
            "withdrawn_date": str(row["withdrawn_date"]) if row["withdrawn_date"] else None,
            "superceded_by_ddt_ndarray_id": row["superceded_by_ddt_ndarray_id"],
        }
        for row in live_lifecycle
    }
    lifecycle_mismatches = {
        key: {"expected": expected_lifecycle.get(key), "actual": actual_lifecycle.get(key)}
        for key in lifecycle_ids
        if expected_lifecycle.get(key) != actual_lifecycle.get(key)
    }

    local_como = {}
    for row in read_tsv(run_dir / "berdl_upload/data/sys_oterm.tsv"):
        if row["sys_oterm_id"] not in COMO_IDS:
            continue
        row["sys_oterm_synonyms"] = json.loads(row["sys_oterm_synonyms"] or "[]")
        row["sys_oterm_links"] = json.loads(row["sys_oterm_links"] or "[]")
        local_como[row["sys_oterm_id"]] = row
    actual_como = {
        row["sys_oterm_id"]: {
            key: (value if value is not None else "")
            for key, value in row.items()
        }
        for row in live_como
    }
    como_mismatches = {
        key: {"expected": local_como.get(key), "actual": actual_como.get(key)}
        for key in sorted(COMO_IDS)
        if local_como.get(key) != actual_como.get(key)
    }

    report = {
        "status": "passed" if not any(
            [count_mismatches, null_failures, lifecycle_mismatches, como_mismatches]
        ) else "failed",
        "tables_checked": len(live_stats),
        "matrix_rows": sum(int(row["row_count"]) for row in live_stats),
        "rows_with_null": sum(int(row["rows_with_null"] or 0) for row in live_stats),
        "count_mismatches": count_mismatches,
        "null_failures": null_failures,
        "lifecycle_rows_checked": len(actual_lifecycle),
        "lifecycle_mismatches": lifecycle_mismatches,
        "como_terms_checked": len(actual_como),
        "como_mismatches": como_mismatches,
        "table_stats": sorted(live_stats, key=lambda row: row["table_name"]),
    }
    report_path = args.report or run_dir / "reports/feba_v2_live_validation.json"
    report_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "table_stats"}, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
