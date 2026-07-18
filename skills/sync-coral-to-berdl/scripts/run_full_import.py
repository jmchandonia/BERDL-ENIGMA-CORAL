#!/usr/bin/env python3
"""Upload and import a full CORAL sync package into BERDL.

This consumes ``ingest/config.dry_run.json`` from a prepared run directory.
Only tables marked ``enabled`` are imported. Disabled brick tables are treated
as obsolete and are dropped from the target namespace, while their lifecycle
rows remain in the enabled ``ddt_ndarray`` table.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def _sql_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_column(coldef: dict[str, Any]) -> str:
    return coldef.get("column") or coldef.get("name")


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

    normalized = (type_name or "STRING").strip().upper()
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


def _patch_spark_connect_config_defaults(spark) -> None:
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


def _set_remote_connection_env_defaults() -> None:
    os.environ.setdefault("grpc_proxy", "http://127.0.0.1:8123")
    os.environ.setdefault("https_proxy", "http://127.0.0.1:8123")
    os.environ.setdefault("no_proxy", "localhost,127.0.0.1")
    os.environ.setdefault("BERDL_NO_AUTO_SPAWN", "1")


def _table_bronze_key(table: dict[str, Any]) -> str:
    return f"data/{table['name']}.tsv"


def _source_bronze_key(source_file: dict[str, Any]) -> str:
    return source_file["bronze_path"].lstrip("/")


def _upload_plan(config: dict[str, Any], bronze_prefix: str) -> list[tuple[Path, str]]:
    uploads: list[tuple[Path, str]] = []
    for source_file in config.get("source_files", []):
        uploads.append((Path(source_file["local_path"]), f"{bronze_prefix}/{_source_bronze_key(source_file)}"))
    for table in config["tables"]:
        if table.get("enabled"):
            uploads.append((Path(table["local_path"]), f"{bronze_prefix}/{_table_bronze_key(table)}"))
    return uploads


def _mc_upload(local_path: Path, remote_path: str, mc_bin: str, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"local": str(local_path), "remote": remote_path, "status": "dry_run"}
    env = os.environ.copy()
    env["HTTP_PROXY"] = "socks5://127.0.0.1:1338"
    env["HTTPS_PROXY"] = "socks5://127.0.0.1:1338"
    env["NO_PROXY"] = "localhost,127.0.0.1"
    start = time.monotonic()
    result = subprocess.run(
        [mc_bin, "cp", str(local_path), remote_path],
        text=True,
        capture_output=True,
        env=env,
    )
    return {
        "local": str(local_path),
        "remote": remote_path,
        "status": "uploaded" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
        "seconds": round(time.monotonic() - start, 3),
        "bytes": local_path.stat().st_size if local_path.exists() else None,
    }


def _bronze_s3_path(bronze_s3_base: str, table: dict[str, Any]) -> str:
    return f"{bronze_s3_base.rstrip('/')}/{_table_bronze_key(table)}"


def _write_bronze_table(spark, namespace: str, bronze_s3_base: str, table: dict[str, Any]) -> dict[str, Any]:
    from pyspark.sql.functions import col, expr, from_json
    from pyspark.sql.types import ArrayType, StringType, StructField, StructType

    schema_config = table.get("schema") or []
    if not schema_config:
        with Path(table["local_path"]).open(encoding="utf-8", errors="replace") as handle:
            header = handle.readline().rstrip("\n\r").split("\t")
        schema_config = [
            {
                "column": column,
                "type": "STRING",
                "nullable": True,
                "comment": json.dumps({"description": column.replace("_", " ")}),
            }
            for column in header
            if column
        ]
    columns = [_schema_column(coldef) for coldef in schema_config]
    if not all(columns):
        raise ValueError(f"Table {table['name']} has schema entries without column/name")
    types = {_schema_column(coldef): coldef.get("type", "STRING") for coldef in schema_config}
    full_table = f"{namespace}.{table['name']}"
    source_path = _bronze_s3_path(bronze_s3_base, table)

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
        elif type_name == "STRING":
            exprs.append(col(column).alias(column))
        else:
            escaped = column.replace("`", "``")
            exprs.append(expr(f"try_cast(`{escaped}` AS {type_name})").alias(column))
    df = raw_df.select(*exprs)

    spark.sql(f"DROP TABLE IF EXISTS {full_table}")
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(full_table)
    )

    for coldef in schema_config:
        column = _schema_column(coldef)
        comment = coldef.get("comment")
        if column and comment:
            spark.sql(
                f"ALTER TABLE {full_table} ALTER COLUMN `{column}` "
                f"COMMENT '{_sql_string(comment)}'"
            )
    table_comment = table.get("table_comment") or ""
    if table_comment:
        spark.sql(
            f"ALTER TABLE {full_table} "
            f"SET TBLPROPERTIES ('comment' = '{_sql_string(table_comment)}')"
        )
    return {"status": "imported", "source_path": source_path, "columns": len(columns)}


def _load_report(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"uploads": [], "dropped_obsolete": {}, "tables": {}, "errors": []}


def _save_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--namespace", default="enigma_coral")
    parser.add_argument("--skip-upload", action="store_true")
    parser.add_argument("--skip-drop-obsolete", action="store_true")
    parser.add_argument("--skip-import", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--table", action="append", help="Import only this table name; may be repeated.")
    parser.add_argument(
        "--table-file",
        type=Path,
        help="Import only enabled table names listed one per line in this file.",
    )
    parser.add_argument("--mc", default="/h/jmc/bin/mc" if Path("/h/jmc/bin/mc").exists() else "mc")
    parser.add_argument("--report")
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    config = _load_json(run_dir / "ingest" / "config.dry_run.json")
    enabled_tables = [table for table in config["tables"] if table.get("enabled")]
    requested = set(args.table or [])
    if args.table_file:
        requested.update(
            line.strip()
            for line in args.table_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    if requested:
        enabled_tables = [table for table in enabled_tables if table["name"] in requested]
        missing = requested - {table["name"] for table in enabled_tables}
        if missing:
            raise RuntimeError(f"Requested table(s) are not enabled in config: {sorted(missing)}")
    if args.limit:
        enabled_tables = enabled_tables[:args.limit]
    disabled_bricks = [
        table["name"] for table in config["tables"]
        if table.get("source_kind") == "brick" and not table.get("enabled")
    ]

    bronze_mc_prefix = f"berdl-minio/cdm-lake/tenant-general-warehouse/enigma/datasets/coral/{args.run_id}"
    bronze_s3_base = f"s3a://cdm-lake/tenant-general-warehouse/enigma/datasets/coral/{args.run_id}"
    report_path = Path(args.report) if args.report else run_dir / "reports" / f"full_import_{args.run_id}.json"
    report = _load_report(report_path)
    report.update({
        "run_id": args.run_id,
        "namespace": args.namespace,
        "bronze_mc_prefix": bronze_mc_prefix,
        "bronze_s3_base": bronze_s3_base,
        "enabled_tables": len(enabled_tables),
        "disabled_obsolete_brick_tables": len(disabled_bricks),
    })

    if not args.skip_upload:
        upload_config = {**config, "tables": enabled_tables}
        uploads = _upload_plan(upload_config, bronze_mc_prefix)
        completed = {row.get("remote") for row in report.get("uploads", []) if row.get("status") == "uploaded"}
        for index, (local_path, remote_path) in enumerate(uploads, start=1):
            if args.resume and remote_path in completed:
                continue
            print(f"[upload {index}/{len(uploads)}] {local_path} -> {remote_path}", flush=True)
            row = _mc_upload(local_path, remote_path, args.mc, args.dry_run)
            report.setdefault("uploads", []).append(row)
            _save_report(report_path, report)
            if row["status"] == "failed":
                raise RuntimeError(f"Upload failed for {local_path}: {row.get('stderr')}")

    if args.skip_import and args.skip_drop_obsolete:
        _save_report(report_path, report)
        return 0

    token = os.environ.get("KBASE_AUTH_TOKEN") or os.environ.get("KB_AUTH_TOKEN")
    if not token:
        raise RuntimeError("KBASE_AUTH_TOKEN or KB_AUTH_TOKEN must be set")
    _set_remote_connection_env_defaults()

    sys.path.insert(0, "/h/jmc/src/BERIL-research-observatory/scripts")
    import ingest_lib  # noqa: F401
    from spark_connect_remote import create_spark_session

    def make_spark():
        new_spark = create_spark_session(
            host_template="metrics.berdl.kbase.us",
            port=443,
            use_ssl=True,
            kbase_token=token,
            app_name=f"sync-coral-full-import-{args.run_id}",
        )
        _patch_spark_connect_config_defaults(new_spark)
        return new_spark

    spark = make_spark()

    if not args.skip_drop_obsolete:
        completed_drops = report.setdefault("dropped_obsolete", {})
        for index, table_name in enumerate(disabled_bricks, start=1):
            if args.resume and completed_drops.get(table_name) == "dropped":
                continue
            full_table = f"{args.namespace}.{table_name}"
            print(f"[drop obsolete {index}/{len(disabled_bricks)}] {full_table}", flush=True)
            if not args.dry_run:
                spark.sql(f"DROP TABLE IF EXISTS {full_table}")
            completed_drops[table_name] = "dropped" if not args.dry_run else "dry_run"
            if index % 25 == 0:
                _save_report(report_path, report)
        _save_report(report_path, report)

    if not args.skip_import:
        completed_tables = report.setdefault("tables", {})
        for index, table in enumerate(enabled_tables, start=1):
            table_name = table["name"]
            if args.resume and completed_tables.get(table_name, {}).get("status") == "imported":
                continue
            print(f"[import {index}/{len(enabled_tables)}] {args.namespace}.{table_name}", flush=True)
            attempts = 0
            while True:
                attempts += 1
                try:
                    result = {"status": "dry_run"} if args.dry_run else _write_bronze_table(
                        spark, args.namespace, bronze_s3_base, table
                    )
                    completed_tables[table_name] = result
                    _save_report(report_path, report)
                    break
                except Exception as exc:
                    error = str(exc)
                    completed_tables[table_name] = {"status": "failed", "error": error}
                    report.setdefault("errors", []).append({
                        "table": table_name,
                        "attempt": attempts,
                        "error": error,
                    })
                    _save_report(report_path, report)
                    reconnectable = any(
                        marker in error
                        for marker in ["UNAUTHENTICATED", "RST_STREAM", "SparkConnectGrpcException"]
                    )
                    if reconnectable and attempts < 4:
                        print(
                            f"[retry {attempts}/3] reconnecting Spark after transient failure on {table_name}",
                            flush=True,
                        )
                        time.sleep(5)
                        spark = make_spark()
                        continue
                    raise

    _save_report(report_path, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
