#!/usr/bin/env python3
"""Apply CORAL table and column comments after a full BERDL import."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from dry_run_tools import (
    DDT_NDARRAY_COMMENTS,
    DDT_NDARRAY_TABLE_COMMENT,
    SYS_DDT_TYPEDEF_COMMENTS,
    SYS_DDT_TYPEDEF_TABLE_COMMENT,
    _brick_table_comments,
    _schema_from_comments,
)
from run_full_import import (
    _patch_spark_connect_config_defaults,
    _set_remote_connection_env_defaults,
    _sql_string,
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _make_spark(app_name: str):
    _set_remote_connection_env_defaults()
    sys.path.insert(0, "/h/jmc/src/BERIL-research-observatory/scripts")
    import ingest_lib  # noqa: F401
    from spark_connect_remote import create_spark_session

    spark = create_spark_session(
        host_template="metrics.berdl.kbase.us",
        port=443,
        use_ssl=True,
        kbase_token=os.environ["KBASE_AUTH_TOKEN"],
        app_name=app_name,
    )
    _patch_spark_connect_config_defaults(spark)
    return spark


def _refresh_known_comments(schema: list[dict[str, Any]], comments: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    refreshed = []
    for coldef in schema:
        coldef = dict(coldef)
        column = coldef.get("column") or coldef.get("name")
        if column in comments:
            coldef["comment"] = json.dumps(comments[column])
        refreshed.append(coldef)
    return refreshed


def _apply_table_comment(spark, full_table: str, comment: str) -> None:
    spark.sql(
        f"ALTER TABLE {full_table} "
        f"SET TBLPROPERTIES ('comment' = '{_sql_string(comment)}')"
    )


def _apply_column_comment(spark, full_table: str, column: str, comment: str) -> None:
    spark.sql(
        f"ALTER TABLE {full_table} ALTER COLUMN `{column}` "
        f"COMMENT '{_sql_string(comment)}'"
    )


def _describe_comments(spark, full_table: str) -> dict[str, Any]:
    rows = [
        row.asDict(recursive=True)
        for row in spark.sql(f"DESCRIBE TABLE EXTENDED {full_table}").collect()
    ]
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
    parser.add_argument("--no-update-config", action="store_true")
    parser.add_argument("--table-file", type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    config_path = run_dir / "ingest" / "config.dry_run.json"
    data_dir = run_dir / "berdl_upload" / "data"
    config = _load_json(config_path)

    brick_comments = _brick_table_comments(data_dir / "ddt_ndarray.tsv")
    for table in config["tables"]:
        name = table["name"]
        if name.startswith("ddt_brick") and table.get("enabled"):
            table["table_comment"] = brick_comments.get(name, table.get("table_comment", ""))
        elif name == "ddt_ndarray":
            table["schema"] = table.get("schema") or _schema_from_comments(
                Path(table["local_path"]), DDT_NDARRAY_COMMENTS
            )
            table["schema"] = _refresh_known_comments(table["schema"], DDT_NDARRAY_COMMENTS)
            table["table_comment"] = table.get("table_comment") or DDT_NDARRAY_TABLE_COMMENT
        elif name == "sys_ddt_typedef":
            table["schema"] = table.get("schema") or _schema_from_comments(
                Path(table["local_path"]), SYS_DDT_TYPEDEF_COMMENTS
            )
            table["schema"] = _refresh_known_comments(table["schema"], SYS_DDT_TYPEDEF_COMMENTS)
            table["table_comment"] = table.get("table_comment") or SYS_DDT_TYPEDEF_TABLE_COMMENT

    if not args.no_update_config:
        _save_json(config_path, config)

    spark = _make_spark("sync-coral-apply-comments")
    table_comment_count = 0
    column_comment_count = 0
    table_comments_current = 0
    column_comments_current = 0
    enabled_tables = [table for table in config["tables"] if table.get("enabled")]
    live_tables = {
        row.asDict(recursive=True).get("tableName")
        for row in spark.sql(f"SHOW TABLES IN {args.namespace}").collect()
    }
    missing_enabled_tables = sorted(
        table["name"] for table in enabled_tables if table["name"] not in live_tables
    )
    if args.table_file:
        selected = set(args.table_file.read_text(encoding="utf-8").split())
        enabled_tables = [table for table in enabled_tables if table["name"] in selected]
    for index, table in enumerate(enabled_tables, start=1):
        if table["name"] in missing_enabled_tables:
            continue
        full_table = f"{args.namespace}.{table['name']}"
        print(f"[comments {index}/{len(enabled_tables)}] {full_table}", flush=True)
        actual = _describe_comments(spark, full_table)
        table_comment = table.get("table_comment") or ""
        if table_comment and table_comment != actual["table_comment"]:
            _apply_table_comment(spark, full_table, table_comment)
            table_comment_count += 1
        elif table_comment:
            table_comments_current += 1
        for coldef in table.get("schema") or []:
            comment = coldef.get("comment") or ""
            column = coldef.get("column") or coldef.get("name")
            if column and comment and comment != actual["columns"].get(column, ""):
                _apply_column_comment(spark, full_table, column, comment)
                column_comment_count += 1
            elif column and comment:
                column_comments_current += 1

    print(json.dumps({
        "table_comments_applied": table_comment_count,
        "column_comments_applied": column_comment_count,
        "table_comments_already_current": table_comments_current,
        "column_comments_already_current": column_comments_current,
        "missing_enabled_tables": missing_enabled_tables,
        "config_updated": not args.no_update_config,
    }, indent=2))
    return 1 if missing_enabled_tables else 0


if __name__ == "__main__":
    raise SystemExit(main())
