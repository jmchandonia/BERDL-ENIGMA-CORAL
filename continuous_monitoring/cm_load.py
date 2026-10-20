#!/usr/bin/env python3
"""Append staged continuous-monitoring TSVs to the BERDL lakehouse.

Each staged table is appended to <namespace>.<table>; rows whose
time_series_datetime is already present are skipped, so re-fetched and
overlapping windows never duplicate rows and existing rows are never changed.
New measurement columns are added with ALTER TABLE.  Two bookkeeping tables
are maintained alongside the data tables:

* table_metadata - one row per data table (rewritten every run);
* ingest_runs    - one row per load (appended).

Requires the BERDL proxy chain (SSH SOCKS tunnel on 1338 + pproxy on 8123)
and a running JupyterHub server; run_daily.sh sets those up.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

import cm_common as cm

# Spark Connect requests above a few MB are rejected by the gateway (HTTP 413).
CHUNK_BYTES = 400_000
TOKEN_WARN_DAYS = 14
KBASE_TOKEN_URL = "https://kbase.us/services/auth/api/V2/token"


def log(msg: str) -> None:
    print(msg, flush=True)


def sql_string(text: str) -> str:
    return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"


def quoted(name: str) -> str:
    if not cm.IDENTIFIER.fullmatch(name):
        raise ValueError(f"invalid identifier {name!r}")
    return f"`{name}`"


def full_name(table: str) -> str:
    return ".".join(f"`{part}`" for part in cm.NAMESPACE.split(".")) + "." + quoted(table)


def comment(description: str, **extra) -> str:
    return json.dumps({"description": description, **{k: v for k, v in extra.items() if v is not None}})


def fixed_columns() -> dict[str, tuple[str, str]]:
    """Non-measurement columns: name -> (spark type, JSON comment)."""
    return {
        cm.TIMESTAMP_COLUMN: ("STRING", comment("datetime (ISO 8601 with UTC offset, America/New_York)")),
        cm.LOCATION_COLUMN: (
            "STRING",
            comment("environmental sample location ID", type="foreign_key", references="enigma.coral.sdt_location.sdt_location_name"),
        ),
        cm.PROVENANCE_COLUMN: ("STRING", comment("data source: hydrovu api, licor api, or licor export")),
        cm.SOURCE_COLUMN: ("STRING", comment("raw source file name(s) the row was built from")),
        cm.RUN_COLUMN: ("STRING", comment("load that appended the row", type="foreign_key", references="ingest_runs.ingest_run_id")),
        "ingested_at": ("TIMESTAMP", comment("time the row was appended (UTC)")),
    }


def check_token_expiry(token: str) -> str | None:
    """Return a warning if the KBase token expires within TOKEN_WARN_DAYS."""
    try:
        response = requests.get(KBASE_TOKEN_URL, headers={"Authorization": token}, timeout=30)
        if response.status_code == 401:
            return f"KBase token is invalid or expired; replace KBASE_AUTH_TOKEN in {cm.credentials_file()}"
        response.raise_for_status()
        expires = response.json().get("expires")
    except Exception as exc:  # the load itself will report auth failures
        return f"could not check KBase token expiry: {exc}"
    if not expires:
        return None
    remaining = datetime.fromtimestamp(expires / 1000, tz=timezone.utc) - datetime.now(timezone.utc)
    if remaining.days < TOKEN_WARN_DAYS:
        return f"KBase token expires in {remaining.days} days ({datetime.fromtimestamp(expires / 1000, tz=timezone.utc):%Y-%m-%d}); replace KBASE_AUTH_TOKEN in {cm.credentials_file()}"
    return None


def spark_session(token: str):
    os.environ.setdefault("grpc_proxy", "http://127.0.0.1:8123")
    os.environ.setdefault("https_proxy", "http://127.0.0.1:8123")
    os.environ.setdefault("no_proxy", "localhost,127.0.0.1")
    os.environ.setdefault("BERDL_NO_AUTO_SPAWN", "1")
    from spark_connect_remote import create_spark_session

    spark = create_spark_session(
        host_template="metrics.berdl.kbase.us",
        port=443,
        use_ssl=True,
        kbase_token=token,
        app_name="enigma_continuous_monitoring",
    )
    patch_config_defaults(spark)
    return spark


def patch_config_defaults(spark) -> None:
    """Same Spark Connect client defaults as sync-coral-to-berdl/run_full_import.py."""
    client = getattr(spark, "_client", None)
    if client is None or getattr(client, "_cm_patched", False):
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
    client._cm_patched = True


class Loader:
    def __init__(self, spark, run_id: str, dry_run: bool):
        self.spark = spark
        self.run_id = run_id
        self.dry_run = dry_run
        self.column_map = {v["column"]: v for v in cm.load_column_map()["measurements"].values()}

    def sql(self, statement: str):
        if self.dry_run:
            log(f"[dry-run] {statement[:400]}")
            return None
        return self.spark.sql(statement)

    def existing_tables(self) -> set[str]:
        rows = self.spark.sql(f"SHOW TABLES IN {'.'.join(f'`{p}`' for p in cm.NAMESPACE.split('.'))}").collect()
        return {row["tableName"] for row in rows}

    def measurement_ddl(self, column: str) -> str:
        spec = self.column_map[column]
        return f"{quoted(column)} DOUBLE COMMENT {sql_string(comment(spec['description'], unit=spec.get('unit')))}"

    def ensure_table(self, table: str, columns: list[str], description: str, existing: set[str]) -> None:
        fixed = fixed_columns()
        if table not in existing:
            ddl = [f"{quoted(cm.TIMESTAMP_COLUMN)} {fixed[cm.TIMESTAMP_COLUMN][0]} COMMENT {sql_string(fixed[cm.TIMESTAMP_COLUMN][1])}"]
            ddl += [self.measurement_ddl(c) for c in columns]
            ddl += [f"{quoted(c)} {t} COMMENT {sql_string(cmt)}" for c, (t, cmt) in fixed.items() if c != cm.TIMESTAMP_COLUMN]
            self.sql(
                f"CREATE TABLE {full_name(table)} ({', '.join(ddl)}) USING iceberg "
                f"COMMENT {sql_string(f'{table} - {description}')}"
            )
            log(f"{'would create' if self.dry_run else 'created'} {table}")
            return
        current = set(self.spark.table(full_name(table)).columns)
        missing = [c for c in columns if c not in current]
        if missing:
            self.sql(f"ALTER TABLE {full_name(table)} ADD COLUMNS ({', '.join(self.measurement_ddl(c) for c in missing)})")
            log(f"added columns to {table}: {missing}")

    def append(self, table: str, tsv: Path, columns: list[str]) -> tuple[int, int]:
        from pyspark.sql import types as T

        frame = pd.read_csv(tsv, sep="\t", dtype=str, keep_default_na=False)
        if frame.empty:
            return 0, 0
        for column in columns:
            # Empty cells are nulls (not NaN) in the lakehouse.
            numeric = pd.to_numeric(frame[column].mask(frame[column] == ""), errors="raise")
            frame[column] = numeric.astype(object).where(numeric.notna(), None)
        frame[cm.RUN_COLUMN] = self.run_id
        frame["ingested_at"] = pd.Timestamp.now(tz="UTC")
        order = [cm.TIMESTAMP_COLUMN, *columns, cm.LOCATION_COLUMN, cm.PROVENANCE_COLUMN, cm.SOURCE_COLUMN, cm.RUN_COLUMN, "ingested_at"]
        frame = frame[order]
        for column in (cm.TIMESTAMP_COLUMN, cm.LOCATION_COLUMN, cm.PROVENANCE_COLUMN, cm.SOURCE_COLUMN, cm.RUN_COLUMN):
            # pandas 3 stores strings as Arrow-backed arrays, which Spark Connect cannot slice.
            frame[column] = frame[column].astype(object)
        schema = T.StructType(
            [T.StructField(cm.TIMESTAMP_COLUMN, T.StringType(), False)]
            + [T.StructField(c, T.DoubleType(), True) for c in columns]
            + [T.StructField(c, T.StringType(), True) for c in (cm.LOCATION_COLUMN, cm.PROVENANCE_COLUMN, cm.SOURCE_COLUMN, cm.RUN_COLUMN)]
            + [T.StructField("ingested_at", T.TimestampType(), True)]
        )
        if self.dry_run:
            log(f"[dry-run] would append up to {len(frame)} rows to {table}")
            return len(frame), 0
        target = full_name(table)
        before = self.spark.table(target).count()
        cols = ", ".join(quoted(c) for c in order)
        chunk_rows = max(200, int(CHUNK_BYTES * len(frame) / max(tsv.stat().st_size, 1)))
        for start in range(0, len(frame), chunk_rows):
            chunk = frame.iloc[start : start + chunk_rows]
            self.spark.createDataFrame(chunk, schema=schema).createOrReplaceTempView("cm_stage")
            select = f"SELECT {', '.join('s.' + quoted(c) for c in order)} FROM cm_stage s"
            if before:
                # Skip rows already in the table (re-fetched or overlapping windows).
                select += f" LEFT ANTI JOIN {target} t ON t.{quoted(cm.TIMESTAMP_COLUMN)} = s.{quoted(cm.TIMESTAMP_COLUMN)}"
            # Staged timestamps are unique per table, so an initially empty table needs no check.
            self.spark.sql(f"INSERT INTO {target} ({cols}) {select}")
        after = self.spark.table(target).count()
        return len(frame), after - before

    def write_table_metadata(self, manifest_tables: dict, existing: set[str]) -> None:
        table = "table_metadata"
        specs = {
            "table_name": ("STRING", comment("data table name in this namespace", type="primary_key")),
            cm.LOCATION_COLUMN: ("STRING", comment("environmental sample location ID", type="foreign_key", references="enigma.coral.sdt_location.sdt_location_name")),
            "instrument": ("STRING", comment("instrument model")),
            "instrument_zone": ("STRING", comment("instrument position in the well (SZ1, SZ2, SZ3, VSZ, VZ); null for single-instrument locations")),
            "deployment_depth_m": ("DOUBLE", comment("depth of the instrument below ground surface", unit="meter")),
            "description": ("STRING", comment("table description")),
            "notes": ("STRING", comment("JSON list of processing notes (unit conversions, timestamp and label corrections)")),
            "provenance": ("STRING", comment("JSON list of data sources in the table")),
            "first_timestamp": ("STRING", comment("earliest time_series_datetime in the table")),
            "last_timestamp": ("STRING", comment("latest time_series_datetime in the table")),
            "row_count": ("BIGINT", comment("rows in the table")),
            "updated_at": ("TIMESTAMP", comment("time this row was written (UTC)")),
        }
        if self.dry_run:
            log(f"[dry-run] would rewrite {table} with {len(manifest_tables)} tables")
            return
        if table not in existing:
            ddl = ", ".join(f"{quoted(c)} {t} COMMENT {sql_string(cmt)}" for c, (t, cmt) in specs.items())
            self.sql(f"CREATE TABLE {full_name(table)} ({ddl}) USING iceberg COMMENT {sql_string('table_metadata - one row per continuous-monitoring data table')}")
        previous = {}
        if table in existing:
            for row in self.spark.table(full_name(table)).collect():
                previous[row["table_name"]] = row.asDict()
        data_tables = sorted(t for t in self.existing_tables() if t.startswith("hazen_"))
        rows = []
        for name in data_tables:
            ts = quoted(cm.TIMESTAMP_COLUMN)
            stats = self.spark.sql(
                f"SELECT min_by({ts}, to_timestamp({ts})) AS first_ts, max_by({ts}, to_timestamp({ts})) AS last_ts, count(*) AS n FROM {full_name(name)}"
            ).collect()[0]
            meta = manifest_tables.get(name, {}).get("metadata") or previous.get(name) or {}
            notes = meta.get("notes", [])
            provenance = meta.get("provenance", [])
            rows.append(
                {
                    "table_name": name,
                    cm.LOCATION_COLUMN: meta.get(cm.LOCATION_COLUMN),
                    "instrument": meta.get("instrument"),
                    "instrument_zone": meta.get("instrument_zone"),
                    "deployment_depth_m": meta.get("deployment_depth_m"),
                    "description": meta.get("description"),
                    "notes": notes if isinstance(notes, str) else json.dumps(notes),
                    "provenance": provenance if isinstance(provenance, str) else json.dumps(provenance),
                    "first_timestamp": stats["first_ts"],
                    "last_timestamp": stats["last_ts"],
                    "row_count": int(stats["n"]),
                    "updated_at": pd.Timestamp.now(tz="UTC"),
                }
            )
        frame = pd.DataFrame(rows, columns=list(specs))
        from pyspark.sql import types as T

        type_of = {"STRING": T.StringType(), "DOUBLE": T.DoubleType(), "BIGINT": T.LongType(), "TIMESTAMP": T.TimestampType()}
        schema = T.StructType([T.StructField(c, type_of[t], True) for c, (t, _) in specs.items()])
        self.spark.createDataFrame(frame, schema=schema).createOrReplaceTempView("cm_meta")
        self.spark.sql(f"DELETE FROM {full_name(table)}")
        self.spark.sql(f"INSERT INTO {full_name(table)} SELECT * FROM cm_meta")

    def record_run(self, record: dict, existing: set[str]) -> None:
        table = "ingest_runs"
        specs = {
            "ingest_run_id": ("STRING", comment("load identifier", type="primary_key")),
            "mode": ("STRING", comment("incremental (daily) or backfill")),
            "started_at": ("TIMESTAMP", comment("load start (UTC)")),
            "finished_at": ("TIMESTAMP", comment("load end (UTC)")),
            "status": ("STRING", comment("ok or error")),
            "tables_loaded": ("BIGINT", comment("data tables with staged rows")),
            "rows_staged": ("BIGINT", comment("rows staged for append")),
            "rows_appended": ("BIGINT", comment("rows appended (staged rows minus rows already present)")),
            "details": ("STRING", comment("JSON with per-table counts, deferred files and errors")),
        }
        if self.dry_run:
            log(f"[dry-run] would record run {json.dumps(record, default=str)[:400]}")
            return
        if table not in existing:
            ddl = ", ".join(f"{quoted(c)} {t} COMMENT {sql_string(cmt)}" for c, (t, cmt) in specs.items())
            self.sql(f"CREATE TABLE {full_name(table)} ({ddl}) USING iceberg COMMENT {sql_string('ingest_runs - one row per continuous-monitoring load')}")
        from pyspark.sql import types as T

        type_of = {"STRING": T.StringType(), "BIGINT": T.LongType(), "TIMESTAMP": T.TimestampType()}
        schema = T.StructType([T.StructField(c, type_of[t], True) for c, (t, _) in specs.items()])
        frame = pd.DataFrame([{c: record.get(c) for c in specs}], columns=list(specs))
        self.spark.createDataFrame(frame, schema=schema).createOrReplaceTempView("cm_run")
        self.spark.sql(f"INSERT INTO {full_name(table)} SELECT * FROM cm_run")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--staging", type=Path, required=True, help="staging directory written by cm_build.py")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--dry-run", action="store_true", help="connect and inspect, but do not create or write anything")
    parser.add_argument("--tables", nargs="*", help="only load these tables")
    parser.add_argument("--wait-for-spark", type=int, default=0, help="seconds to keep retrying until Spark Connect answers")
    args = parser.parse_args()

    cm.load_env_file(cm.credentials_file())
    token = os.environ.get("KBASE_AUTH_TOKEN") or os.environ.get("KB_AUTH_TOKEN")
    if not token:
        sys.exit(f"KBASE_AUTH_TOKEN is not set (environment or {cm.credentials_file()})")
    warning = check_token_expiry(token)
    if warning:
        print(f"WARNING: {warning}", file=sys.stderr, flush=True)

    manifest = json.loads((args.staging / "manifest.json").read_text())
    run_id = args.run_id or f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}"
    started = datetime.now(timezone.utc)
    deadline = time.monotonic() + args.wait_for_spark
    while True:
        try:
            spark = spark_session(token)
            spark.sql("SELECT 1").collect()
            break
        except Exception as exc:
            if time.monotonic() > deadline:
                raise
            log(f"Spark Connect not ready ({exc!r}); retrying")
            time.sleep(15)
    loader = Loader(spark, run_id, args.dry_run)
    if not args.dry_run:
        spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {'.'.join(f'`{p}`' for p in cm.NAMESPACE.split('.'))}")
    existing = loader.existing_tables() if not args.dry_run or _namespace_exists(spark) else set()

    per_table: dict[str, dict[str, int]] = {}
    status, error = "ok", None
    try:
        for table, info in sorted(manifest["tables"].items()):
            if args.tables and table not in args.tables:
                continue
            columns = list(info["columns"])
            loader.ensure_table(table, columns, info["metadata"]["description"], existing)
            existing.add(table)
            started_table = time.monotonic()
            staged, appended = loader.append(table, args.staging / info["tsv"], columns)
            per_table[table] = {"staged": staged, "appended": appended}
            log(f"{table}: staged {staged}, appended {appended} ({time.monotonic() - started_table:.0f}s)")
        loader.write_table_metadata(manifest["tables"], existing)
    except Exception as exc:
        status, error = "error", repr(exc)
        raise
    finally:
        record = {
            "ingest_run_id": run_id,
            "mode": manifest.get("mode"),
            "started_at": pd.Timestamp(started),
            "finished_at": pd.Timestamp.now(tz="UTC"),
            "status": status,
            "tables_loaded": len(per_table),
            "rows_staged": sum(v["staged"] for v in per_table.values()),
            "rows_appended": sum(v["appended"] for v in per_table.values()),
            "details": json.dumps({"tables": per_table, "files_deferred": len(manifest.get("files_deferred", [])), "unknown_labels": manifest.get("unknown_labels"), "error": error}),
        }
        try:
            loader.record_run(record, loader.existing_tables() if not args.dry_run else existing)
        except Exception as exc:  # do not mask the original error
            print(f"could not record run: {exc!r}", file=sys.stderr)
        (args.staging / "load_result.json").write_text(json.dumps(record, indent=2, default=str) + "\n")
    log(f"run {run_id}: {record['rows_appended']} rows appended across {len(per_table)} tables")


def _namespace_exists(spark) -> bool:
    try:
        spark.sql(f"SHOW TABLES IN {'.'.join(f'`{p}`' for p in cm.NAMESPACE.split('.'))}").collect()
        return True
    except Exception:
        return False


if __name__ == "__main__":
    main()
