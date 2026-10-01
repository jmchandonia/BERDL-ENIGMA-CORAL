#!/usr/bin/env python3
"""Upload and dual-publish a full CORAL sync package into BERDL.

This consumes ``ingest/config.dry_run.json`` from a prepared run directory.
Each enabled table is written first to the supported KBase Iceberg ingest path
and then to the transitional legacy Delta namespace. Disabled brick tables are
treated as obsolete and are dropped from both targets, while their lifecycle
rows remain in the enabled ``ddt_ndarray`` table.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Any


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DEFAULT_BERDL_SCRIPTS = Path("/h/jmc/src/BERIL-research-observatory/scripts")


def _sql_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_column(coldef: dict[str, Any]) -> str:
    return coldef.get("column") or coldef.get("name")


def _quoted_namespace(namespace: str) -> str:
    parts = namespace.split(".")
    if not parts or any(not IDENTIFIER.fullmatch(part) for part in parts):
        raise ValueError(f"Invalid namespace: {namespace!r}")
    return ".".join(f"`{part}`" for part in parts)


def _full_table(namespace: str, table: str) -> str:
    if not IDENTIFIER.fullmatch(table):
        raise ValueError(f"Invalid table name: {table!r}")
    return f"{_quoted_namespace(namespace)}.`{table}`"


def _jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _jsonable(dataclasses.asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


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


def _create_spark_session(*, token: str, app_name: str):
    try:
        from spark_connect_remote import create_spark_session
    except ModuleNotFoundError:
        from pyspark.sql import SparkSession

        remote = (
            "sc://metrics.berdl.kbase.us:443/;"
            f"use_ssl=true;x-kbase-token={token}"
        )
        return (
            SparkSession.builder.remote(remote)
            .appName(app_name)
            .getOrCreate()
        )
    return create_spark_session(
        host_template="metrics.berdl.kbase.us",
        port=443,
        use_ssl=True,
        kbase_token=token,
        app_name=app_name,
    )


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


def _table_csv_options(table: dict[str, Any]) -> dict[str, Any]:
    options: dict[str, Any] = {
        "header": True,
        "delimiter": "\t",
        "quote": '"',
        "escape": '"',
        "multiLine": True,
        "inferSchema": False,
    }
    options.update(table.get("csv") or {})
    # Every source generated by this CORAL pipeline is TSV, even when an old
    # table config happens to carry a stale delimiter.
    options["delimiter"] = "\t"
    return options


def _write_delta_compat_table(
    spark, namespace: str, bronze_s3_base: str, table: dict[str, Any]
) -> dict[str, Any]:
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
    full_table = _full_table(namespace, table["name"])
    source_path = _bronze_s3_path(bronze_s3_base, table)

    raw_schema = StructType([StructField(column, StringType(), nullable=True) for column in columns])
    reader = spark.read.format("csv")
    for option, value in _table_csv_options(table).items():
        reader = reader.option(option, str(value).lower() if isinstance(value, bool) else value)
    raw_df = reader.schema(raw_schema).load(source_path)

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
    return {
        "status": "imported",
        "provider": "delta",
        "namespace": namespace,
        "source_path": source_path,
        "columns": len(columns),
    }


def _supported_ingest_config(
    config: dict[str, Any], bronze_s3_base: str, table: dict[str, Any]
) -> dict[str, Any]:
    """Build a one-table config for KBase's supported Iceberg importer."""
    tenant = config.get("tenant")
    dataset = config.get("dataset")
    if not tenant or not dataset:
        raise ValueError("Supported BERDL ingest requires config tenant and dataset")

    csv_options = _table_csv_options(table)
    table_config: dict[str, Any] = {
        "name": table["name"],
        "enabled": True,
        "format": "tsv",
        "mode": "overwrite",
        "partition_by": table.get("partition_by"),
        "bronze_path": _bronze_s3_path(bronze_s3_base, table),
        "schema": table.get("schema") or [],
        "comment": table.get("table_comment") or "",
    }
    return {
        "pipeline_name": f"sync_coral_{tenant}_{dataset}",
        "tenant": tenant,
        "dataset": dataset,
        "is_tenant": True,
        "paths": {
            "data_plane": f"s3a://cdm-lake/tenant-general-warehouse/{tenant}/",
            "bronze_base": bronze_s3_base.rstrip("/") + "/",
        },
        "defaults": {"tsv": csv_options},
        "tables": [table_config],
    }


def _iceberg_namespace(config: dict[str, Any]) -> str:
    tenant = config.get("tenant")
    dataset = config.get("dataset")
    if not tenant or not dataset:
        raise ValueError("Supported BERDL ingest requires config tenant and dataset")
    return f"{tenant}.{dataset}"


def _load_supported_ingest():
    """Load the KBase-supported ingest function and its MinIO client helper."""
    scripts = Path(os.environ.get("BERDL_INGEST_SCRIPTS", DEFAULT_BERDL_SCRIPTS))
    if not (scripts / "ingest_lib.py").is_file():
        raise FileNotFoundError(f"Supported BERDL ingest helper is absent: {scripts / 'ingest_lib.py'}")
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import ingest_lib
    from data_lakehouse_ingest import ingest

    minio_client = ingest_lib.initialize_minio()
    version = importlib.metadata.version("data-lakehouse-ingest")
    return ingest, minio_client, version


def _write_supported_iceberg_table(
    ingest_fn,
    minio_client,
    spark,
    config: dict[str, Any],
    bronze_s3_base: str,
    table: dict[str, Any],
) -> dict[str, Any]:
    supported_config = _supported_ingest_config(config, bronze_s3_base, table)
    raw_report = ingest_fn(supported_config, spark=spark, minio_client=minio_client)
    report = _jsonable(raw_report)
    if not report.get("success"):
        raise RuntimeError(
            "Supported KBase Iceberg ingest failed for "
            f"{table['name']}: {json.dumps(report.get('errors') or report, default=str)}"
        )
    table_reports = report.get("tables") or []
    if len(table_reports) != 1 or table_reports[0].get("status") != "success":
        raise RuntimeError(
            f"Supported KBase Iceberg ingest returned an unexpected table report for {table['name']}: "
            f"{json.dumps(table_reports, default=str)}"
        )
    return {
        "status": "imported",
        "provider": "iceberg",
        "namespace": _iceberg_namespace(config),
        "source_path": _bronze_s3_path(bronze_s3_base, table),
        "supported_ingest_report": report,
    }


def _target_imported(table_report: dict[str, Any], target: str) -> bool:
    return table_report.get(target, {}).get("status") == "imported"


def _live_tables(spark, namespace: str) -> set[str]:
    try:
        rows = spark.sql(f"SHOW TABLES IN {_quoted_namespace(namespace)}").collect()
    except Exception as exc:
        error = str(exc).lower()
        if any(marker in error for marker in ("schema_not_found", "no_such_namespace", "namespace not found")):
            return set()
        raise
    return {
        row.asDict(recursive=True).get("tableName")
        for row in rows
        if not row.asDict(recursive=True).get("isTemporary")
    }


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
    parser.add_argument(
        "--namespace",
        dest="delta_namespace",
        default=argparse.SUPPRESS,
        help="deprecated alias for --delta-namespace",
    )
    parser.add_argument("--delta-namespace")
    parser.add_argument("--iceberg-namespace")
    parser.add_argument(
        "--skip-delta-compat",
        action="store_true",
        help="write only canonical Iceberg tables after KBase retires Delta compatibility",
    )
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
    parser.add_argument(
        "--drop-table-file",
        type=Path,
        help="Drop only disabled brick table names listed one per line in this file.",
    )
    parser.add_argument("--mc", default="/h/jmc/bin/mc" if Path("/h/jmc/bin/mc").exists() else "mc")
    parser.add_argument("--report")
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    config = _load_json(run_dir / "ingest" / "config.dry_run.json")
    iceberg_namespace = _iceberg_namespace(config)
    if args.iceberg_namespace and args.iceberg_namespace != iceberg_namespace:
        raise ValueError(
            f"Iceberg namespace is determined by tenant/dataset as {iceberg_namespace!r}; "
            f"received {args.iceberg_namespace!r}"
        )
    delta_namespace = args.delta_namespace or config.get("namespace") or "enigma_coral"
    all_enabled_tables = [table for table in config["tables"] if table.get("enabled")]
    requested = set(args.table or [])
    selection_filter_present = bool(args.table) or args.table_file is not None
    if args.table_file:
        requested.update(
            line.strip()
            for line in args.table_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    if selection_filter_present:
        selected_tables = [table for table in all_enabled_tables if table["name"] in requested]
        missing = requested - {table["name"] for table in selected_tables}
        if missing:
            raise RuntimeError(f"Requested table(s) are not enabled in config: {sorted(missing)}")
    else:
        selected_tables = list(all_enabled_tables)
    if args.limit:
        selected_tables = selected_tables[:args.limit]
    disabled_bricks = [
        table["name"] for table in config["tables"]
        if table.get("source_kind") == "brick" and not table.get("enabled")
    ]
    if args.drop_table_file:
        requested_drops = {
            line.strip()
            for line in args.drop_table_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        invalid_drops = requested_drops - set(disabled_bricks)
        if invalid_drops:
            raise RuntimeError(
                "Requested drop table(s) are not disabled brick tables in config: "
                f"{sorted(invalid_drops)}"
            )
        disabled_bricks = sorted(requested_drops)

    bronze_mc_prefix = f"berdl-minio/cdm-lake/tenant-general-warehouse/enigma/datasets/coral/{args.run_id}"
    bronze_s3_base = f"s3a://cdm-lake/tenant-general-warehouse/enigma/datasets/coral/{args.run_id}"
    report_path = Path(args.report) if args.report else run_dir / "reports" / f"full_import_{args.run_id}.json"
    report = _load_report(report_path)
    report.update({
        "run_id": args.run_id,
        "iceberg_namespace": iceberg_namespace,
        "delta_namespace": None if args.skip_delta_compat else delta_namespace,
        "write_policy": "iceberg_plus_delta_compat" if not args.skip_delta_compat else "iceberg_only",
        "bronze_mc_prefix": bronze_mc_prefix,
        "bronze_s3_base": bronze_s3_base,
        "enabled_tables_in_config": len(all_enabled_tables),
        "delta_tables_selected": len(selected_tables),
        "disabled_obsolete_brick_tables": len(disabled_bricks),
    })

    if not args.skip_upload:
        upload_config = {
            **config,
            "source_files": config.get("source_files", []) if selected_tables else [],
            "tables": selected_tables,
        }
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

    def make_spark():
        new_spark = _create_spark_session(
            token=token,
            app_name=f"sync-coral-full-import-{args.run_id}",
        )
        _patch_spark_connect_config_defaults(new_spark)
        return new_spark

    spark = make_spark()
    ingest_fn = minio_client = ingest_version = None
    if not args.skip_import and not args.dry_run:
        ingest_fn, minio_client, ingest_version = _load_supported_ingest()
        report["supported_ingest"] = {
            "package": "data-lakehouse-ingest",
            "version": ingest_version,
            "provider": "iceberg",
            "namespace": iceberg_namespace,
        }
        _save_report(report_path, report)

    delta_table_names = {table["name"] for table in selected_tables}
    iceberg_table_names = set(delta_table_names)
    live_iceberg_tables: set[str] = set()
    if not args.dry_run and (not args.skip_import or not args.skip_drop_obsolete):
        live_iceberg_tables = _live_tables(spark, iceberg_namespace)
    if not args.skip_import and not args.dry_run:
        iceberg_scope = selected_tables if args.limit else all_enabled_tables
        missing_iceberg_tables = {
            table["name"] for table in iceberg_scope
        } - live_iceberg_tables
        iceberg_table_names.update(missing_iceberg_tables)
        prior_backfill_tables = set(
            report.get("iceberg_backfill", {}).get("missing_enabled_tables", [])
        )
        cumulative_backfill_tables = prior_backfill_tables | missing_iceberg_tables
        report["iceberg_backfill"] = {
            "live_tables_before_import": len(live_iceberg_tables),
            "missing_enabled_tables_this_attempt": sorted(missing_iceberg_tables),
            "missing_enabled_tables": sorted(cumulative_backfill_tables),
            "tables_selected_count": len(iceberg_table_names),
        }
        _save_report(report_path, report)

        if missing_iceberg_tables and not args.skip_upload:
            backfill_tables = [
                table for table in all_enabled_tables
                if table["name"] in missing_iceberg_tables
            ]
            uploads = _upload_plan(
                {**config, "source_files": [], "tables": backfill_tables},
                bronze_mc_prefix,
            )
            completed = {
                row.get("remote")
                for row in report.get("uploads", [])
                if row.get("status") == "uploaded"
            }
            for index, (local_path, remote_path) in enumerate(uploads, start=1):
                if remote_path in completed:
                    continue
                print(
                    f"[upload Iceberg backfill {index}/{len(uploads)}] "
                    f"{local_path} -> {remote_path}",
                    flush=True,
                )
                row = _mc_upload(local_path, remote_path, args.mc, False)
                report.setdefault("uploads", []).append(row)
                _save_report(report_path, report)
                if row["status"] == "failed":
                    raise RuntimeError(
                        f"Iceberg backfill upload failed for {local_path}: {row.get('stderr')}"
                    )

    if not args.skip_drop_obsolete:
        completed_drops = report.setdefault("dropped_obsolete", {})
        for index, table_name in enumerate(disabled_bricks, start=1):
            required_drop_targets = ["iceberg"] + ([] if args.skip_delta_compat else ["delta_compat"])
            existing_drop = completed_drops.get(table_name, {})
            if args.resume and all(
                existing_drop.get(target) in {"dropped", "already_absent"}
                for target in required_drop_targets
            ):
                continue
            drop_targets = [("iceberg", iceberg_namespace)]
            if not args.skip_delta_compat:
                drop_targets.append(("delta_compat", delta_namespace))
            table_drop = completed_drops.setdefault(table_name, {})
            for target, namespace in drop_targets:
                if args.resume and table_drop.get(target) in {"dropped", "already_absent"}:
                    continue
                if target == "iceberg" and not args.dry_run and table_name not in live_iceberg_tables:
                    table_drop[target] = "already_absent"
                    continue
                full_table = _full_table(namespace, table_name)
                print(
                    f"[drop obsolete {index}/{len(disabled_bricks)} {target}] {full_table}",
                    flush=True,
                )
                if not args.dry_run:
                    spark.sql(f"DROP TABLE IF EXISTS {full_table}")
                table_drop[target] = "dropped" if not args.dry_run else "dry_run"
            if index % 25 == 0:
                _save_report(report_path, report)
        _save_report(report_path, report)

    if not args.skip_import:
        completed_tables = report.setdefault("tables", {})
        import_tables = [
            table for table in all_enabled_tables
            if table["name"] in iceberg_table_names or table["name"] in delta_table_names
        ]
        for index, table in enumerate(import_tables, start=1):
            table_name = table["name"]
            table_report = completed_tables.setdefault(table_name, {})
            required_targets = []
            if table_name in iceberg_table_names:
                required_targets.append("iceberg")
            if not args.skip_delta_compat and table_name in delta_table_names:
                required_targets.append("delta_compat")
            def target_complete(target: str) -> bool:
                if target == "iceberg" and table_name not in live_iceberg_tables:
                    return False
                return _target_imported(table_report, target)

            if args.resume and all(target_complete(target) for target in required_targets):
                continue
            target_writers = []
            if table_name in iceberg_table_names:
                target_writers.append((
                    "iceberg",
                    iceberg_namespace,
                    lambda: _write_supported_iceberg_table(
                        ingest_fn, minio_client, spark, config, bronze_s3_base, table
                    ),
                ))
            if not args.skip_delta_compat and table_name in delta_table_names:
                target_writers.append(
                    (
                        "delta_compat",
                        delta_namespace,
                        lambda: _write_delta_compat_table(
                            spark, delta_namespace, bronze_s3_base, table
                        ),
                    )
                )
            for target, namespace, writer in target_writers:
                if args.resume and target_complete(target):
                    continue
                print(
                    f"[import {index}/{len(import_tables)} {target}] {namespace}.{table_name}",
                    flush=True,
                )
                attempts = 0
                while True:
                    attempts += 1
                    try:
                        result = {"status": "dry_run", "namespace": namespace} if args.dry_run else writer()
                        table_report[target] = result
                        table_report["status"] = (
                            "imported"
                            if all(_target_imported(table_report, item) for item in required_targets)
                            else "partial"
                        )
                        _save_report(report_path, report)
                        break
                    except Exception as exc:
                        error = str(exc)
                        table_report[target] = {"status": "failed", "error": error, "namespace": namespace}
                        table_report["status"] = "failed"
                        report.setdefault("errors", []).append({
                            "table": table_name,
                            "target": target,
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
                                f"[retry {attempts}/3] reconnecting Spark after transient failure on "
                                f"{table_name} ({target})",
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
