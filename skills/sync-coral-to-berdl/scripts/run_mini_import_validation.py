#!/usr/bin/env python3
"""Run the CORAL-to-BERDL mini import and validation.

This creates two temporary tables in `enigma_coral`, compares them with the
existing production tables, writes a JSON report, and drops the temporary
tables before exiting.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def _sql_string(value: str) -> str:
    return value.replace("'", "''")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _column_type(type_name: str):
    from pyspark.sql.types import (
        BooleanType,
        DoubleType,
        FloatType,
        IntegerType,
        LongType,
        StringType,
    )

    return {
        "boolean": BooleanType(),
        "double": DoubleType(),
        "float": FloatType(),
        "int": IntegerType(),
        "integer": IntegerType(),
        "bigint": LongType(),
        "long": LongType(),
        "string": StringType(),
    }.get(type_name.lower(), StringType())


def _describe_table(spark, table: str) -> dict[str, Any]:
    rows = [row.asDict(recursive=True) for row in spark.sql(f"DESCRIBE EXTENDED {table}").collect()]
    columns = {}
    table_comment = ""
    for row in rows:
        col_name = row.get("col_name") or ""
        if not col_name:
            continue
        if col_name == "Comment":
            table_comment = row.get("data_type") or ""
        if col_name.startswith("#"):
            continue
        if col_name in {"Name", "Type", "Location", "Provider", "Owner", "Table Properties"}:
            continue
        columns[col_name] = {
            "data_type": row.get("data_type") or "",
            "comment": row.get("comment") or "",
        }
    return {"columns": columns, "table_comment": table_comment}


def _compare_tables(spark, old_table: str, test_table: str) -> dict[str, Any]:
    from pyspark.sql.functions import col, from_json, to_json
    from pyspark.sql.types import MapType, StringType

    old_df = spark.table(old_table)
    test_df = spark.table(test_table)
    columns = old_df.columns
    old_types = dict(old_df.dtypes)
    test_types = dict(test_df.dtypes)
    if columns != test_df.columns:
        return {
            "columns_match": False,
            "old_columns": columns,
            "test_columns": test_df.columns,
        }
    old_exprs = []
    test_exprs = []
    tolerated_type_differences = {}
    for column in columns:
        if (
            old_table.endswith(".sys_oterm")
            and test_table.endswith(".test_sys_oterm")
            and column == "sys_oterm_properties"
        ):
            map_type = MapType(StringType(), StringType())
            if old_types.get(column, "").startswith("map"):
                old_exprs.append(to_json(col(column)).alias(column))
            else:
                old_exprs.append(col(column).cast("string").alias(column))
            if test_types.get(column, "").startswith("map"):
                test_exprs.append(to_json(col(column)).alias(column))
            else:
                test_exprs.append(to_json(from_json(col(column), map_type)).alias(column))
            tolerated_type_differences[column] = {
                "old": old_types.get(column, ""),
                "test": test_types.get(column, ""),
            }
        else:
            old_exprs.append(col(column))
            test_exprs.append(col(column))
    old_selected = old_df.select(*old_exprs)
    test_selected = test_df.select(*test_exprs)
    old_count = old_selected.count()
    test_count = test_selected.count()
    old_minus_test = old_selected.exceptAll(test_selected).count()
    test_minus_old = test_selected.exceptAll(old_selected).count()
    return {
        "columns_match": True,
        "columns": columns,
        "old_count": old_count,
        "test_count": test_count,
        "old_minus_test": old_minus_test,
        "test_minus_old": test_minus_old,
        "data_match": old_count == test_count and old_minus_test == 0 and test_minus_old == 0,
        "tolerated_type_differences": tolerated_type_differences,
    }


def _comments_match(old_meta: dict[str, Any], test_meta: dict[str, Any]) -> dict[str, Any]:
    old_columns = old_meta["columns"]
    test_columns = test_meta["columns"]
    column_results = {}
    for col, old_def in old_columns.items():
        test_def = test_columns.get(col, {})
        column_results[col] = {
            "old": old_def.get("comment", ""),
            "test": test_def.get("comment", ""),
            "match": old_def.get("comment", "") == test_def.get("comment", ""),
        }
    return {
        "table_comment": {
            "old": old_meta.get("table_comment", ""),
            "test": test_meta.get("table_comment", ""),
            "match": old_meta.get("table_comment", "") == test_meta.get("table_comment", ""),
        },
        "columns": column_results,
        "all_match": all(item["match"] for item in column_results.values())
        and old_meta.get("table_comment", "") == test_meta.get("table_comment", ""),
    }


def _build_ingest_config(mini_dir: Path, run_id: str) -> dict[str, Any]:
    config = _load_json(mini_dir / "config" / "ingest_config.json")
    bronze_base = f"s3a://cdm-lake/tenant-general-warehouse/enigma/datasets/coral/{run_id}/data"
    config["tenant"] = "enigma"
    config["dataset"] = "coral"
    config["is_tenant"] = True
    config["paths"] = {
        "data_plane": "s3a://cdm-lake/tenant-general-warehouse/enigma/",
        "bronze_base": bronze_base,
        "silver_base": "s3a://cdm-lake/tenant-sql-warehouse/enigma/enigma_coral.db",
    }
    config["defaults"] = {"csv": {"header": True, "delimiter": "\t", "inferSchema": False}}
    for table in config["tables"]:
        table["mode"] = "overwrite"
        table["format"] = "tsv"
        table["bronze_path"] = f"{table['name']}.tsv"
    return config


def _spark_type(type_name: str):
    from pyspark.sql.types import (
        ArrayType,
        BooleanType,
        DoubleType,
        FloatType,
        IntegerType,
        LongType,
        StringType,
    )

    normalized = type_name.strip().upper()
    if normalized == "ARRAY<STRING>":
        return ArrayType(StringType())
    return {
        "BOOLEAN": BooleanType(),
        "DOUBLE": DoubleType(),
        "FLOAT": FloatType(),
        "INT": IntegerType(),
        "INTEGER": IntegerType(),
        "BIGINT": LongType(),
        "LONG": LongType(),
        "STRING": StringType(),
    }.get(normalized, StringType())


def _parse_cell(value: str, type_name: str):
    if value == "":
        return None
    normalized = type_name.strip().upper()
    if normalized == "ARRAY<STRING>":
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        return parsed if isinstance(parsed, list) else [str(parsed)]
    if normalized in {"INT", "INTEGER", "BIGINT", "LONG"}:
        return int(value)
    if normalized in {"DOUBLE", "FLOAT"}:
        return float(value)
    if normalized == "BOOLEAN":
        return value.strip().lower() in {"true", "1", "yes"}
    return value


def _schema_from_config(schema_config: list[dict[str, Any]]):
    from pyspark.sql.types import StructField, StructType

    return StructType([
        StructField(
            col["column"],
            _spark_type(col.get("type", "STRING")),
            nullable=True,
            metadata={"comment": col.get("comment", "")} if col.get("comment") else {},
        )
        for col in schema_config
    ])


def _write_direct_table(spark, table: dict[str, Any], table_comment: str, chunk_size: int) -> dict[str, Any]:
    import csv

    schema_config = table.get("schema") or []
    schema = _schema_from_config(schema_config)
    columns = [col["column"] for col in schema_config]
    types = {col["column"]: col.get("type", "STRING") for col in schema_config}
    full_table = f"enigma_coral.{table['name']}"
    spark.sql(f"DROP TABLE IF EXISTS {full_table}")

    chunks = 0
    rows = 0
    buffer = []

    def flush(mode: str) -> None:
        nonlocal chunks, buffer
        if not buffer:
            return
        df = spark.createDataFrame(buffer, schema=schema)
        writer = df.write.format("delta").mode(mode)
        if mode == "overwrite":
            writer = writer.option("overwriteSchema", "true")
        writer.saveAsTable(full_table)
        chunks += 1
        buffer = []

    with Path(table["local_path"]).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            buffer.append(tuple(_parse_cell(row.get(column, ""), types[column]) for column in columns))
            rows += 1
            if len(buffer) >= chunk_size:
                flush("overwrite" if chunks == 0 else "append")
        flush("overwrite" if chunks == 0 else "append")

    for coldef in schema_config:
        comment = coldef.get("comment")
        if comment:
            spark.sql(
                f"ALTER TABLE {full_table} ALTER COLUMN `{coldef['column']}` "
                f"COMMENT '{_sql_string(comment)}'"
            )
    if table_comment:
        spark.sql(
            f"ALTER TABLE {full_table} "
            f"SET TBLPROPERTIES ('comment' = '{_sql_string(table_comment)}')"
        )
    return {"rows": rows, "chunks": chunks, "mode": "direct_spark_connect"}


def _direct_import(spark, mini_dir: Path, config: dict[str, Any], chunk_size: int) -> dict[str, Any]:
    table_comments = _load_json(mini_dir / "config" / "table_comments.json")
    results = {}
    for table in config["tables"]:
        results[table["name"]] = _write_direct_table(
            spark,
            table,
            table_comments.get(table["name"], ""),
            chunk_size,
        )
    return {"success": True, "direct_import": results}


def _bronze_path(config: dict[str, Any], table: dict[str, Any]) -> str:
    bronze_base = config["paths"]["bronze_base"].rstrip("/")
    bronze_path = table["bronze_path"]
    if bronze_path.startswith("s3a://"):
        return bronze_path
    return f"{bronze_base}/{bronze_path}"


def _write_bronze_table(spark, config: dict[str, Any], table: dict[str, Any], table_comment: str) -> dict[str, Any]:
    from pyspark.sql.functions import col, from_json
    from pyspark.sql.types import ArrayType, StringType, StructField, StructType

    schema_config = table.get("schema") or []
    columns = [coldef["column"] for coldef in schema_config]
    types = {coldef["column"]: coldef.get("type", "STRING") for coldef in schema_config}
    full_table = f"enigma_coral.{table['name']}"
    source_path = _bronze_path(config, table)
    spark.sql(f"DROP TABLE IF EXISTS {full_table}")

    raw_schema = StructType([StructField(column, StringType(), nullable=True) for column in columns])
    raw_df = (
        spark.read.format("csv")
        .option("header", "true")
        .option("delimiter", "\t")
        .option("quote", '"')
        .option("escape", '"')
        .option("multiLine", "true")
        .option("inferSchema", "false")
        .schema(raw_schema)
        .load(source_path)
    )

    exprs = []
    for column in columns:
        type_name = types[column].strip().upper()
        if type_name == "ARRAY<STRING>":
            exprs.append(from_json(col(column), ArrayType(StringType())).alias(column))
        else:
            exprs.append(col(column).cast(_spark_type(type_name)).alias(column))
    df = raw_df.select(*exprs)

    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(full_table)
    )

    for coldef in schema_config:
        comment = coldef.get("comment")
        if comment:
            spark.sql(
                f"ALTER TABLE {full_table} ALTER COLUMN `{coldef['column']}` "
                f"COMMENT '{_sql_string(comment)}'"
            )
    if table_comment:
        spark.sql(
            f"ALTER TABLE {full_table} "
            f"SET TBLPROPERTIES ('comment' = '{_sql_string(table_comment)}')"
        )
    return {
        "rows": spark.table(full_table).count(),
        "mode": "direct_bronze_spark_read",
        "source_path": source_path,
    }


def _direct_bronze_import(spark, mini_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    table_comments = _load_json(mini_dir / "config" / "table_comments.json")
    results = {}
    for table in config["tables"]:
        results[table["name"]] = _write_bronze_table(
            spark,
            config,
            table,
            table_comments.get(table["name"], ""),
        )
    return {"success": True, "direct_import": results}


def _patch_spark_connect_config_defaults(spark) -> None:
    """Work around older Spark Connect servers missing newer local-relation configs."""
    client = getattr(spark, "_client", None)
    if client is None or getattr(client, "_coral_config_defaults_patched", False):
        return

    original = client.get_config_dict
    defaults = {
        "spark.sql.timestampType": "TIMESTAMP_LTZ",
        "spark.sql.session.timeZone": "Etc/UTC",
        "spark.sql.session.localRelationCacheThreshold": "67108864",
        "spark.sql.session.localRelationChunkSizeRows": "10000",
        "spark.sql.session.localRelationChunkSizeBytes": "1048576",
        "spark.sql.session.localRelationBatchOfChunksSizeBytes": "10485760",
        "spark.sql.execution.pandas.convertToArrowArraySafely": "false",
        "spark.sql.execution.pandas.inferPandasDictAsMap": "false",
        "spark.sql.pyspark.inferNestedDictAsStruct.enabled": "false",
        "spark.sql.pyspark.legacy.inferArrayTypeFromFirstElement.enabled": "false",
        "spark.sql.pyspark.legacy.inferMapTypeFromFirstPair.enabled": "false",
        "spark.sql.execution.arrow.useLargeVarTypes": "false",
    }

    def patched(*keys):
        try:
            values = original(*keys)
        except Exception:
            values = {}
        return {key: values.get(key, defaults.get(key, "false")) for key in keys}

    client.get_config_dict = patched
    client._coral_config_defaults_patched = True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mini-dir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--direct-local", action="store_true")
    parser.add_argument("--direct-bronze", action="store_true")
    parser.add_argument("--chunk-size", type=int, default=50000)
    args = parser.parse_args()

    mini_dir = args.mini_dir.resolve()
    report_path = args.report or (mini_dir / "reports" / "mini_import_validation_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    token = os.environ.get("KBASE_AUTH_TOKEN") or os.environ.get("KB_AUTH_TOKEN")
    if not token:
        raise RuntimeError("KBASE_AUTH_TOKEN or KB_AUTH_TOKEN must be set")

    os.environ.setdefault("grpc_proxy", "http://127.0.0.1:8123")
    os.environ.setdefault("https_proxy", "http://127.0.0.1:8123")
    os.environ.setdefault("no_proxy", "localhost,127.0.0.1")
    os.environ.setdefault("BERDL_NO_AUTO_SPAWN", "1")

    beril_scripts = Path("/h/jmc/src/BERIL-research-observatory/scripts")
    sys.path.insert(0, str(beril_scripts))
    import ingest_lib  # noqa: F401  # injects BERDL notebook stubs
    from data_lakehouse_ingest import ingest
    from spark_connect_remote import create_spark_session

    spark = create_spark_session(
        host_template="metrics.berdl.kbase.us",
        port=443,
        use_ssl=True,
        kbase_token=token,
        app_name="sync-coral-mini-import",
    )
    if args.direct_local:
        _patch_spark_connect_config_defaults(spark)
    if args.direct_bronze:
        _patch_spark_connect_config_defaults(spark)

    config = _build_ingest_config(mini_dir, args.run_id)
    test_tables = [table["name"] for table in config["tables"]]
    old_by_test = {table: table.removeprefix("test_") for table in test_tables}
    full_test_tables = [f"enigma_coral.{table}" for table in test_tables]
    report: dict[str, Any] = {
        "run_id": args.run_id,
        "mini_dir": str(mini_dir),
        "staged_bronze": f"s3a://cdm-lake/tenant-general-warehouse/enigma/datasets/coral/{args.run_id}/",
        "ingest_report": None,
        "tables": {},
        "cleanup": {},
    }

    try:
        for table in full_test_tables:
            spark.sql(f"DROP TABLE IF EXISTS {table}")

        report["ingest_config"] = config
        if args.direct_local:
            ingest_report = _direct_import(spark, mini_dir, config, args.chunk_size)
        elif args.direct_bronze:
            ingest_report = _direct_bronze_import(spark, mini_dir, config)
        else:
            ingest_report = ingest(config, spark=spark, minio_client=object())
        report["ingest_report"] = ingest_report

        if not args.direct_local:
            table_comments = _load_json(mini_dir / "config" / "table_comments.json")
            for table, comment in table_comments.items():
                spark.sql(
                    f"ALTER TABLE enigma_coral.{table} "
                    f"SET TBLPROPERTIES ('comment' = '{_sql_string(comment)}')"
                )

        for test_table in test_tables:
            old_table = old_by_test[test_table]
            old_full = f"enigma_coral.{old_table}"
            test_full = f"enigma_coral.{test_table}"
            old_meta = _describe_table(spark, old_full)
            test_meta = _describe_table(spark, test_full)
            report["tables"][test_table] = {
                "compared_to": old_table,
                "data": _compare_tables(spark, old_full, test_full),
                "comments": _comments_match(old_meta, test_meta),
                "old_metadata": old_meta,
                "test_metadata": test_meta,
            }

    finally:
        for table in full_test_tables:
            try:
                spark.sql(f"DROP TABLE IF EXISTS {table}")
                report["cleanup"][table] = "dropped"
            except Exception as exc:
                report["cleanup"][table] = f"failed: {exc}"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))

    failed = []
    for table, table_report in report["tables"].items():
        if not table_report["data"].get("data_match"):
            failed.append(f"{table}: data mismatch")
        if not table_report["comments"].get("all_match"):
            failed.append(f"{table}: comment mismatch")
    if failed:
        print("Mini import validation failed: " + "; ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
