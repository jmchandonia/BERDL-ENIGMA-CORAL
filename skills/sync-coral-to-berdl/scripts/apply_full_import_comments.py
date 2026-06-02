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
from run_full_import import _patch_spark_connect_config_defaults, _sql_string


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _make_spark(app_name: str):
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--namespace", default="enigma_coral")
    parser.add_argument("--no-update-config", action="store_true")
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
    for table in config["tables"]:
        if not table.get("enabled"):
            continue
        full_table = f"{args.namespace}.{table['name']}"
        table_comment = table.get("table_comment") or ""
        if table_comment:
            _apply_table_comment(spark, full_table, table_comment)
            table_comment_count += 1
        for coldef in table.get("schema") or []:
            comment = coldef.get("comment") or ""
            column = coldef.get("column") or coldef.get("name")
            if column and comment and table["name"] in {"ddt_ndarray", "sys_ddt_typedef"}:
                _apply_column_comment(spark, full_table, column, comment)
                column_comment_count += 1

    print(json.dumps({
        "table_comments_applied": table_comment_count,
        "ddt_metadata_column_comments_applied": column_comment_count,
        "config_updated": not args.no_update_config,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
