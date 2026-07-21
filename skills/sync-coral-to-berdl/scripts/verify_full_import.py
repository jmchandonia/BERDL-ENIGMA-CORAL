#!/usr/bin/env python3
"""Verify a completed CORAL full import in BERDL."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _make_spark(app_name: str):
    from run_full_import import (
        _patch_spark_connect_config_defaults,
        _set_remote_connection_env_defaults,
    )
    from spark_connect_remote.session import create_spark_session

    _set_remote_connection_env_defaults()
    spark = create_spark_session(
        host_template="metrics.berdl.kbase.us",
        port=443,
        use_ssl=True,
        kbase_token=os.environ["KBASE_AUTH_TOKEN"],
        app_name=app_name,
    )
    _patch_spark_connect_config_defaults(spark)
    return spark


def _describe_comments(rows) -> dict[str, Any]:
    rows = [row.asDict(recursive=True) for row in rows]
    columns = {}
    table_comment = ""
    in_schema = True
    for row in rows:
        column = (row.get("col_name") or "").strip()
        if column.startswith("#"):
            in_schema = False
            continue
        if not in_schema:
            if column == "Comment":
                table_comment = (row.get("data_type") or "").strip()
            continue
        if column:
            columns[column] = (row.get("comment") or "").strip()
    return {"table_comment": table_comment, "columns": columns}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--namespace", default="enigma_coral")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--table-file", type=Path)
    args = parser.parse_args()

    config = _load_json(args.run_dir / "ingest" / "config.dry_run.json")
    enabled = {table["name"] for table in config["tables"] if table.get("enabled")}
    disabled = {table["name"] for table in config["tables"] if not table.get("enabled")}

    spark = _make_spark("sync-coral-full-import-verify")

    def collect_sql(sql: str):
        nonlocal spark
        for attempt in range(1, 5):
            try:
                return spark.sql(sql).collect()
            except Exception as exc:
                error = str(exc)
                reconnectable = any(
                    marker in error
                    for marker in ["UNAUTHENTICATED", "RST_STREAM", "SparkConnectGrpcException"]
                )
                if not reconnectable or attempt == 4:
                    raise
                print(f"[retry {attempt}/3] reconnecting Spark verifier", flush=True)
                spark = _make_spark("sync-coral-full-import-verify")
        raise AssertionError("unreachable")

    imported = {
        row.tableName
        for row in collect_sql(f"SHOW TABLES IN {args.namespace}")
        if not row.isTemporary
    }

    missing_enabled = sorted(enabled - imported)
    present_disabled = sorted(disabled & imported)
    requested_comment_tables = imported
    if args.table_file:
        requested = set(args.table_file.read_text(encoding="utf-8").split())
        requested_comment_tables = imported & requested
        requested_comment_tables_missing = sorted(requested - imported)
    else:
        requested_comment_tables_missing = []

    config_by_name = {table["name"]: table for table in config["tables"]}
    expected_table_comments_missing = []
    expected_column_comments_missing = []
    actual_table_comments_missing = []
    actual_column_comments_missing = []
    table_comment_mismatches = []
    column_comment_mismatches = []
    comment_counts = {"tables": 0, "columns": 0}
    described = []
    for index, table_name in enumerate(sorted(requested_comment_tables), start=1):
        full_table = f"{args.namespace}.{table_name}"
        print(
            f"[verify comments {index}/{len(requested_comment_tables)}] {full_table}",
            flush=True,
        )
        actual = _describe_comments(
            collect_sql(f"DESCRIBE TABLE EXTENDED {full_table}")
        )
        described.append((table_name, actual))

    for table_name, actual in sorted(described):
        comment_counts["tables"] += 1
        comment_counts["columns"] += len(actual["columns"])
        if not actual["table_comment"]:
            actual_table_comments_missing.append(table_name)
        for column, comment in actual["columns"].items():
            if not comment:
                actual_column_comments_missing.append(f"{table_name}.{column}")

        expected_table = config_by_name.get(table_name)
        if not expected_table or not expected_table.get("enabled"):
            continue
        expected_table_comment = (expected_table.get("table_comment") or "").strip()
        if not expected_table_comment:
            expected_table_comments_missing.append(table_name)
        elif expected_table_comment != actual["table_comment"]:
            table_comment_mismatches.append({
                "table": table_name,
                "expected": expected_table_comment,
                "actual": actual["table_comment"],
            })
        for coldef in expected_table.get("schema") or []:
            column = coldef.get("column") or coldef.get("name")
            expected_comment = (coldef.get("comment") or "").strip()
            if not column:
                continue
            if not expected_comment:
                expected_column_comments_missing.append(f"{table_name}.{column}")
            elif expected_comment != actual["columns"].get(column, ""):
                column_comment_mismatches.append({
                    "table": table_name,
                    "column": column,
                    "expected": expected_comment,
                    "actual": actual["columns"].get(column, ""),
                })

    ndarray_rows = collect_sql(
        f"""
        SELECT ddt_ndarray_id, withdrawn_date, superceded_by_ddt_ndarray_id
        FROM {args.namespace}.ddt_ndarray
        """
    )
    ndarray = {row.ddt_ndarray_id: row.asDict() for row in ndarray_rows}

    disabled_brick_ids = {
        "Brick" + table.removeprefix("ddt_brick").zfill(7)
        for table in disabled
        if table.startswith("ddt_brick")
    }
    missing_lifecycle = sorted(
        brick_id
        for brick_id in disabled_brick_ids
        if brick_id not in ndarray
        or (
            not (ndarray[brick_id].get("withdrawn_date") or "").strip()
            and not (ndarray[brick_id].get("superceded_by_ddt_ndarray_id") or "").strip()
        )
    )

    go_terms = collect_sql(
        f"""
        SELECT COUNT(*) AS c
        FROM {args.namespace}.sys_oterm
        WHERE upper(sys_oterm_id) LIKE 'GO:%'
           OR lower(sys_oterm_ontology) LIKE '%gene ontology%'
           OR lower(sys_oterm_ontology) = 'go'
        """
    )[0].c
    ncbitaxon_terms = collect_sql(
        f"""
        SELECT COUNT(*) AS c
        FROM {args.namespace}.sys_oterm
        WHERE upper(sys_oterm_id) LIKE 'NCBITAXON:%'
           OR lower(sys_oterm_ontology) LIKE '%ncbitaxon%'
           OR lower(sys_oterm_ontology) LIKE '%ncbi taxon%'
        """
    )[0].c

    sample_ids = ["Brick0000001", "Brick0000215", "Brick0000453", "Brick0000456"]
    samples = {brick_id: ndarray.get(brick_id) for brick_id in sample_ids}

    result = {
        "enabled_tables_expected": len(enabled),
        "enabled_tables_missing": missing_enabled,
        "comment_tables_requested": len(requested_comment_tables),
        "comment_tables_requested_missing": requested_comment_tables_missing,
        "disabled_tables_expected_absent": len(disabled),
        "disabled_tables_present": present_disabled,
        "disabled_bricks_missing_lifecycle": missing_lifecycle,
        "comment_counts_checked": comment_counts,
        "expected_table_comments_missing": expected_table_comments_missing,
        "expected_column_comments_missing": expected_column_comments_missing,
        "actual_table_comments_missing": actual_table_comments_missing,
        "actual_column_comments_missing": actual_column_comments_missing,
        "table_comment_mismatches": table_comment_mismatches,
        "column_comment_mismatches": column_comment_mismatches,
        "sample_lifecycle": samples,
        "go_terms": go_terms,
        "ncbitaxon_terms": ncbitaxon_terms,
    }
    report_path = args.report or args.run_dir / "reports" / "full_import_verification.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))
    comment_failures = any([
        expected_table_comments_missing,
        expected_column_comments_missing,
        actual_table_comments_missing,
        actual_column_comments_missing,
        table_comment_mismatches,
        column_comment_mismatches,
    ])
    return 1 if (
        missing_enabled
        or requested_comment_tables_missing
        or present_disabled
        or missing_lifecycle
        or go_terms
        or comment_failures
    ) else 0


if __name__ == "__main__":
    raise SystemExit(main())
