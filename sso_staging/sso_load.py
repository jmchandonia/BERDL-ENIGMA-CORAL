#!/usr/bin/env python3
"""Load staged sso_staging TSVs into the BERDL lakehouse.

Three load modes, dispatched from the manifest sso_build.py wrote:
  * picarro_gas    append + dedup on epoch_time (LEFT ANTI JOIN; re-ingesting a
                   cumulative export never duplicates rows).
  * field_metadata full refresh (DELETE + INSERT); a shrink-guard refuses to wipe
                   the table when the source suddenly has far fewer rows.
  * sample_registry upsert (MERGE) by sdt_sample_name; rows are updated in place,
                   never deleted, so a sample dropped from the manifest survives.

Also rewrites three bookkeeping tables each run: ddt_brick (the COMO microtype per
measurement column, from sso_schema), table_metadata (one row per data table) and
ingest_runs (one row per load, appended).  Writes load_result.json for the report.

Requires the BERDL proxy chain + a running JupyterHub server (run_daily.sh).
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

import sso_common as sso
import sso_schema as schema

CHUNK_ROWS = 20_000  # hard cap on rows per uploaded local relation
CHUNK_BYTES = 400_000  # target bytes per uploaded chunk.  Spark Connect rejects
# large local relations (HTTP 413), so size each chunk by the staged TSV's
# bytes/row like cm_load, not a fixed row count -- a wide table (e.g. the 28-col
# gas table) overflows the gateway at a fixed 20k rows.
TOKEN_WARN_DAYS = 14
KBASE_TOKEN_URL = "https://kbase.us/services/auth/api/V2/token"
STALE_HOURS = float(os.environ.get("SSO_STALE_HOURS", "36"))  # gas trailer-wide silence alert
SHRINK_GUARD = float(os.environ.get("SSO_SHRINK_GUARD", "0.5"))  # refuse full-refresh below this fraction

SQL_TYPE = {"STRING": "STRING", "DOUBLE": "DOUBLE", "INT": "BIGINT", "TIMESTAMP": "TIMESTAMP"}


def log(msg: str) -> None:
    print(msg, flush=True)


# --- Spark (same client defaults as continuous_monitoring / sync-coral-to-berdl) ---

def spark_session(token: str):
    os.environ.setdefault("grpc_proxy", "http://127.0.0.1:8123")
    os.environ.setdefault("https_proxy", "http://127.0.0.1:8123")
    os.environ.setdefault("no_proxy", "localhost,127.0.0.1")
    os.environ.setdefault("BERDL_NO_AUTO_SPAWN", "1")
    from spark_connect_remote import create_spark_session

    spark = create_spark_session(
        host_template="metrics.berdl.kbase.us", port=443, use_ssl=True,
        kbase_token=token, app_name="enigma_sso_staging",
    )
    _patch_config_defaults(spark)
    return spark


def _patch_config_defaults(spark) -> None:
    client = getattr(spark, "_client", None)
    if client is None or getattr(client, "_sso_patched", False):
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
    client._sso_patched = True


# --- token expiry (same as cm_load) ---

def token_expiry(token: str) -> tuple[datetime | None, int | None]:
    try:
        r = requests.get(KBASE_TOKEN_URL, headers={"Authorization": token}, timeout=30)
        r.raise_for_status()
        expires = r.json().get("expires")
    except Exception:
        return None, None
    if not expires:
        return None, None
    dt = datetime.fromtimestamp(expires / 1000, tz=timezone.utc)
    return dt, (dt - datetime.now(timezone.utc)).days


def check_token_expiry(token: str) -> str | None:
    try:
        r = requests.get(KBASE_TOKEN_URL, headers={"Authorization": token}, timeout=30)
        if r.status_code == 401:
            return f"KBase token is invalid or expired; replace KBASE_AUTH_TOKEN in {sso.credentials_file()}"
        r.raise_for_status()
    except Exception as exc:
        return f"could not check KBase token expiry: {exc}"
    dt, days = token_expiry(token)
    if dt is not None and days < TOKEN_WARN_DAYS:
        return f"KBase token expires in {days} days ({dt:%Y-%m-%d}); replace KBASE_AUTH_TOKEN in {sso.credentials_file()}"
    return None


# --- SQL building from the schema ---

def column_comment(col: dict) -> str:
    fields = schema.column_comment_fields(col)
    desc = fields.pop("description")
    return sso.comment(desc, **fields)


def column_ddl(col: dict) -> str:
    return f"{sso.quoted(col['name'])} {SQL_TYPE[col['type']]} COMMENT {sso.sql_string(column_comment(col))}"


def spark_schema(columns: list[dict]):
    from pyspark.sql import types as T

    kind = {"STRING": T.StringType(), "DOUBLE": T.DoubleType(), "INT": T.LongType(), "TIMESTAMP": T.TimestampType()}
    return T.StructType([T.StructField(c["name"], kind[c["type"]], True) for c in columns])


def staged_frame(tsv: Path, columns: list[dict], run_id: str) -> pd.DataFrame:
    """Read a staged TSV and coerce to the column types; '' becomes null."""
    raw = pd.read_csv(tsv, sep="\t", dtype=str, keep_default_na=False) if tsv.stat().st_size else pd.DataFrame()
    out = pd.DataFrame(index=range(len(raw)))
    now = pd.Timestamp.now(tz="UTC")
    for c in columns:
        name, typ = c["name"], c["type"]
        if name == "ingest_run_id":
            out[name] = run_id
        elif name == "ingested_at":
            out[name] = now
        elif name not in raw.columns:
            out[name] = None
        elif typ == "DOUBLE":
            v = pd.to_numeric(raw[name].mask(raw[name] == ""), errors="coerce")
            out[name] = v.astype(object).where(v.notna(), None)
        elif typ == "INT":
            v = pd.to_numeric(raw[name].mask(raw[name] == ""), errors="coerce")
            out[name] = v.astype("Int64").astype(object).where(v.notna(), None)
        else:  # STRING
            s = raw[name].astype(object)
            out[name] = s.where(raw[name] != "", None)
    return out


class Loader:
    def __init__(self, spark, run_id: str, dry_run: bool):
        self.spark = spark
        self.run_id = run_id
        self.dry_run = dry_run
        self._tsv_bytes = 0  # staged TSV size of the table currently loading

    def sql(self, statement: str):
        if self.dry_run:
            log(f"[dry-run] {statement[:300]}")
            return None
        return self.spark.sql(statement)

    def existing_tables(self) -> set[str]:
        try:
            rows = self.spark.sql(f"SHOW TABLES IN {'.'.join(f'`{p}`' for p in sso.NAMESPACE.split('.'))}").collect()
            return {r["tableName"] for r in rows}
        except Exception:
            return set()

    def ensure_table(self, table: str, columns: list[dict], description: str, existing: set[str]) -> None:
        if table not in existing:
            ddl = ", ".join(column_ddl(c) for c in columns)
            self.sql(f"CREATE TABLE {sso.full_name(table)} ({ddl}) USING iceberg "
                     f"COMMENT {sso.sql_string(f'{table} - {description}')}")
            log(f"{'would create' if self.dry_run else 'created'} {table}")
            return
        current = set(self.spark.table(sso.full_name(table)).columns)
        missing = [c for c in columns if c["name"] not in current]
        if missing:
            self.sql(f"ALTER TABLE {sso.full_name(table)} ADD COLUMNS ({', '.join(column_ddl(c) for c in missing)})")
            log(f"added columns to {table}: {[c['name'] for c in missing]}")

    def _chunk_rows(self, frame: pd.DataFrame) -> int:
        """Rows per uploaded chunk, sized so each local relation stays well under
        the Spark Connect gateway's few-MB limit (HTTP 413).  Mirrors cm_load:
        scale by the staged TSV's bytes/row, falling back to a pandas memory
        estimate when the byte size is unknown."""
        n = max(1, len(frame))
        nbytes = self._tsv_bytes or int(frame.memory_usage(deep=True).sum())
        return max(200, min(CHUNK_ROWS, int(CHUNK_BYTES * n / max(nbytes, 1))))

    def _insert_chunks(self, frame: pd.DataFrame, columns: list[dict], select_sql, view="sso_stage"):
        chunk_rows = self._chunk_rows(frame)
        for start in range(0, len(frame), chunk_rows):
            chunk = frame.iloc[start:start + chunk_rows]
            self.spark.createDataFrame(chunk, schema=spark_schema(columns)).createOrReplaceTempView(view)
            self.spark.sql(select_sql(view))

    def append_dedup(self, table: str, frame: pd.DataFrame, columns: list[dict], key: str) -> dict:
        target = sso.full_name(table)
        if self.dry_run:
            log(f"[dry-run] would append up to {len(frame)} rows to {table} (dedup on {key})")
            return {"staged": len(frame), "appended": len(frame)}
        before = self.spark.table(target).count()
        cols = ", ".join(sso.quoted(c["name"]) for c in columns)

        def select(view):
            sel = f"SELECT {', '.join('s.' + sso.quoted(c['name']) for c in columns)} FROM {view} s"
            if before:
                sel += f" LEFT ANTI JOIN {target} t ON t.{sso.quoted(key)} = s.{sso.quoted(key)}"
            return f"INSERT INTO {target} ({cols}) {sel}"

        self._insert_chunks(frame, columns, select)
        after = self.spark.table(target).count()
        return {"staged": len(frame), "appended": after - before}

    def full_refresh(self, table: str, frame: pd.DataFrame, columns: list[dict], existing_before: bool) -> dict:
        target = sso.full_name(table)
        before = self.spark.table(target).count() if (existing_before and not self.dry_run) else 0
        if before and len(frame) < max(10, SHRINK_GUARD * before):
            msg = f"shrink-guard: source has {len(frame)} rows vs {before} in {table}; refusing full refresh"
            log(f"WARNING: {msg}")
            return {"staged": len(frame), "refreshed": 0, "skipped": msg}
        if self.dry_run:
            log(f"[dry-run] would replace {table} with {len(frame)} rows")
            return {"staged": len(frame), "refreshed": len(frame)}
        cols = ", ".join(sso.quoted(c["name"]) for c in columns)
        self.spark.sql(f"DELETE FROM {target}")
        self._insert_chunks(frame, columns, lambda v: f"INSERT INTO {target} ({cols}) "
                            f"SELECT {', '.join('s.' + sso.quoted(c['name']) for c in columns)} FROM {v} s")
        return {"staged": len(frame), "refreshed": len(frame)}

    def upsert(self, table: str, frame: pd.DataFrame, columns: list[dict], key: str) -> dict:
        target = sso.full_name(table)
        if self.dry_run:
            log(f"[dry-run] would MERGE {len(frame)} rows into {table} on {key}")
            return {"staged": len(frame), "upserted": len(frame)}
        before = self.spark.table(target).count()
        # Chunk by bytes (the upsert key is unique, so per-chunk MERGEs are
        # disjoint and safe) to keep each local relation under the 413 limit.
        chunk_rows = self._chunk_rows(frame)
        for start in range(0, len(frame), chunk_rows):
            chunk = frame.iloc[start:start + chunk_rows]
            self.spark.createDataFrame(chunk, schema=spark_schema(columns)).createOrReplaceTempView("sso_stage")
            self.spark.sql(
                f"MERGE INTO {target} t USING sso_stage s ON t.{sso.quoted(key)} = s.{sso.quoted(key)} "
                f"WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *"
            )
        after = self.spark.table(target).count()
        return {"staged": len(frame), "upserted": len(frame), "inserted": after - before}

    # --- bookkeeping tables ---

    def write_ddt_brick(self, existing: set[str]) -> None:
        table = "ddt_brick"
        specs = {
            "table_name": "STRING", "column_name": "STRING", "description": "STRING",
            "value_type_sys_oterm_id": "STRING", "value_type_sys_oterm_name": "STRING",
            "molecule_sys_oterm_id": "STRING", "molecule_sys_oterm_name": "STRING",
            "context_metadata": "STRING", "unit_sys_oterm_id": "STRING", "unit_sys_oterm_name": "STRING",
            "scalar_type": "STRING", "note": "STRING", "withdrawn_date": "STRING",
        }
        comments = {
            "table_name": "data table this column lives in", "column_name": "column name in the data table",
            "description": "CORAL microtype label", "value_type_sys_oterm_id": "measurement term id (ME:)",
            "value_type_sys_oterm_name": "measurement term name", "molecule_sys_oterm_id": "molecule id (CHEBI:)",
            "molecule_sys_oterm_name": "molecule name", "context_metadata": "JSON list of [property, value] context pairs (free-text method/condition/instrument)",
            "unit_sys_oterm_id": "unit term id (null if not yet minted)", "unit_sys_oterm_name": "unit name",
            "scalar_type": "stored scalar type", "note": "human note", "withdrawn_date": "withdrawal date, or null",
        }
        rows = []
        for tbl, spec in schema.TABLES.items():
            for col in schema.measurement_columns(tbl):
                d = col["ddt"]
                rows.append({
                    "table_name": tbl, "column_name": col["name"], "description": schema.microtype_label(d),
                    "value_type_sys_oterm_id": d["value_oterm"], "value_type_sys_oterm_name": d["value_type"],
                    "molecule_sys_oterm_id": d["molecule_chebi"], "molecule_sys_oterm_name": d["molecule"],
                    "context_metadata": json.dumps(d["context"]), "unit_sys_oterm_id": d["unit_oterm"],
                    "unit_sys_oterm_name": d["unit"], "scalar_type": "float", "note": col.get("note"),
                    "withdrawn_date": None,
                })
        self._rewrite(table, specs, comments, rows, existing, "ddt_brick - COMO microtype per measurement column")

    def write_table_metadata(self, per_table: dict, manifest: dict, existing: set[str]) -> dict:
        table = "table_metadata"
        specs = {
            "table_name": "STRING", "description": "STRING", "load_mode": "STRING", "source_files": "STRING",
            "row_count": "BIGINT", "first_timestamp": "STRING", "last_timestamp": "STRING", "updated_at": "TIMESTAMP",
        }
        comments = {
            "table_name": "data table name", "description": "table description", "load_mode": "append_dedup / full_refresh / upsert",
            "source_files": "JSON list of source files", "row_count": "rows in the table",
            "first_timestamp": "earliest time/date in the table", "last_timestamp": "latest time/date in the table",
            "updated_at": "time this row was written (UTC)",
        }
        time_col = {"picarro_gas": "time_series_datetime", "field_metadata": "sample_date", "sample_registry": "sample_date"}
        latest, rows = {}, []
        for tbl, spec in schema.TABLES.items():
            if self.dry_run and tbl not in existing:
                continue
            tc = time_col[tbl]
            stats = self.spark.sql(
                f"SELECT count(*) n, min({sso.quoted(tc)}) lo, max({sso.quoted(tc)}) hi FROM {sso.full_name(tbl)}"
            ).collect()[0]
            latest[tbl] = {"row_count": int(stats["n"]), "last_timestamp": stats["hi"]}
            rows.append({
                "table_name": tbl, "description": spec["description"], "load_mode": spec["load_mode"],
                "source_files": json.dumps(manifest["tables"].get(tbl, {}).get("source_files", [])),
                "row_count": int(stats["n"]), "first_timestamp": stats["lo"], "last_timestamp": stats["hi"],
                "updated_at": pd.Timestamp.now(tz="UTC"),
            })
        self._rewrite(table, specs, comments, rows, existing, "table_metadata - one row per sso_staging data table")
        return latest

    def record_run(self, record: dict, existing: set[str]) -> None:
        table = "ingest_runs"
        specs = {
            "ingest_run_id": "STRING", "mode": "STRING", "started_at": "TIMESTAMP", "finished_at": "TIMESTAMP",
            "status": "STRING", "tables_loaded": "BIGINT", "rows_staged": "BIGINT", "rows_written": "BIGINT", "details": "STRING",
        }
        comments = {
            "ingest_run_id": "load identifier", "mode": "incremental or backfill", "started_at": "load start (UTC)",
            "finished_at": "load end (UTC)", "status": "ok or error", "tables_loaded": "data tables touched",
            "rows_staged": "rows staged across tables", "rows_written": "rows appended/refreshed/upserted",
            "details": "JSON: per-table counts, drift, held ids, errors",
        }
        self._rewrite(table, specs, comments, [record], existing,
                      "ingest_runs - one row per sso_staging load", append=True, pk="ingest_run_id")

    def _rewrite(self, table, specs, comments, rows, existing, table_comment, append=False, pk=None):
        if self.dry_run:
            log(f"[dry-run] would write {len(rows)} row(s) to {table}")
            return
        from pyspark.sql import types as T

        if table not in existing:
            ddl = ", ".join(f"{sso.quoted(c)} {specs[c]} COMMENT {sso.sql_string(sso.comment(comments[c], **({'type': 'primary_key'} if c == pk else {})))}" for c in specs)
            self.spark.sql(f"CREATE TABLE {sso.full_name(table)} ({ddl}) USING iceberg COMMENT {sso.sql_string(table_comment)}")
            existing.add(table)
        kind = {"STRING": T.StringType(), "BIGINT": T.LongType(), "TIMESTAMP": T.TimestampType()}
        sschema = T.StructType([T.StructField(c, kind[specs[c]], True) for c in specs])
        frame = pd.DataFrame([{c: r.get(c) for c in specs} for r in rows], columns=list(specs))
        frame = frame.astype(object).where(pd.notna(frame), None)
        self.spark.createDataFrame(frame, schema=sschema).createOrReplaceTempView("sso_meta")
        if not append:
            self.spark.sql(f"DELETE FROM {sso.full_name(table)}")
        self.spark.sql(f"INSERT INTO {sso.full_name(table)} SELECT {', '.join(sso.quoted(c) for c in specs)} FROM sso_meta")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--staging", type=Path, required=True)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--wait-for-spark", type=int, default=0)
    ap.add_argument("--check-staleness", action="store_true")
    args = ap.parse_args()

    sso.load_env_file(sso.credentials_file())
    token = os.environ.get("KBASE_AUTH_TOKEN") or os.environ.get("KB_AUTH_TOKEN")
    if not token:
        sys.exit(f"KBASE_AUTH_TOKEN is not set (environment or {sso.credentials_file()})")
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
        spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {'.'.join(f'`{p}`' for p in sso.NAMESPACE.split('.'))}")
    existing = loader.existing_tables()

    per_table, status, error = {}, "ok", None
    try:
        for table, info in manifest["tables"].items():
            spec = schema.TABLES[table]
            columns = spec["columns"]
            existed = table in existing
            loader.ensure_table(table, columns, spec["description"], existing)
            existing.add(table)
            frame = staged_frame(args.staging / info["tsv"], columns, run_id)
            loader._tsv_bytes = (args.staging / info["tsv"]).stat().st_size
            mode = spec["load_mode"]
            if mode == "append_dedup":
                res = loader.append_dedup(table, frame, columns, spec["dedup_key"])
            elif mode == "full_refresh":
                res = loader.full_refresh(table, frame, columns, existed)
            elif mode == "upsert":
                res = loader.upsert(table, frame, columns, spec["upsert_key"])
            else:
                raise ValueError(f"unknown load_mode {mode!r}")
            per_table[table] = res
            log(f"{table} [{mode}]: {res}")
        loader.write_ddt_brick(existing)
        latest = loader.write_table_metadata(per_table, manifest, existing)
    except Exception as exc:
        status, error = "error", repr(exc)
        raise
    finally:
        rows_written = sum(v.get("appended", 0) + v.get("refreshed", 0) + v.get("upserted", 0) for v in per_table.values())
        record = {
            "ingest_run_id": run_id, "mode": manifest.get("mode"),
            "started_at": pd.Timestamp(started), "finished_at": pd.Timestamp.now(tz="UTC"),
            "status": status, "tables_loaded": len(per_table),
            "rows_staged": sum(v.get("staged", 0) for v in per_table.values()), "rows_written": rows_written,
            "details": json.dumps({"tables": per_table, "drift": manifest.get("drift"),
                                    "held": manifest.get("held"), "error": error}),
        }
        try:
            loader.record_run(record, loader.existing_tables() if not args.dry_run else existing)
        except Exception as exc:
            print(f"could not record run: {exc!r}", file=sys.stderr)
        _write_result(args, manifest, record, per_table, locals().get("latest", {}), token, run_id)
    log(f"run {run_id}: {record['rows_written']} rows written across {len(per_table)} tables")


def _write_result(args, manifest, record, per_table, latest, token, run_id) -> None:
    expires_dt, days = token_expiry(token)
    stale = {}
    if args.check_staleness:
        info = latest.get("picarro_gas") or {}
        last = info.get("last_timestamp")
        if last:
            try:
                last_dt = datetime.fromisoformat(str(last))
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                age = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
                if age > STALE_HOURS:
                    stale["picarro_gas"] = {"last_timestamp": last, "age_hours": round(age, 1)}
            except ValueError:
                pass
    summary = dict(record)
    summary["tables"] = {t: {**per_table[t], "row_count": (latest.get(t) or {}).get("row_count"),
                             "last_timestamp": (latest.get(t) or {}).get("last_timestamp")} for t in per_table}
    summary["drift"] = manifest.get("drift")
    summary["held"] = manifest.get("held")
    summary["stale_tables"] = stale
    summary["token_expires"] = f"{expires_dt:%Y-%m-%d}" if expires_dt else None
    summary["token_days_left"] = days
    (args.staging / "load_result.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()
