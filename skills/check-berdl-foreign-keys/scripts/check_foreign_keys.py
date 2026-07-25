#!/usr/bin/env python3
"""Validate BERDL foreign keys declared in structured column comments."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class ForeignKey:
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    configured_source_type: str
    source_is_collection: bool


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _identifier(value: str, label: str) -> str:
    if not IDENTIFIER.fullmatch(value or ""):
        raise ValueError(f"Invalid {label} identifier: {value!r}")
    return value


def _quoted(value: str, label: str) -> str:
    return f"`{_identifier(value, label)}`"


def _parse_comment(raw: Any, location: str) -> dict[str, Any] | None:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        if "foreign_key" in raw:
            raise ValueError(f"Malformed foreign-key comment at {location}: {exc}") from exc
        return None
    return parsed if isinstance(parsed, dict) else None


def extract_foreign_keys(
    config: dict[str, Any], selected_tables: set[str] | None = None
) -> tuple[list[ForeignKey], list[str]]:
    relations: list[ForeignKey] = []
    errors: list[str] = []
    tables = {table.get("name"): table for table in config.get("tables", [])}
    if selected_tables is not None:
        errors.extend(
            f"Selected table is absent from config: {name}"
            for name in sorted(selected_tables - set(tables))
        )

    for table_name, table in sorted(tables.items()):
        if not table_name or not table.get("enabled", True):
            continue
        if selected_tables is not None and table_name not in selected_tables:
            continue
        for coldef in table.get("schema") or []:
            source_column = coldef.get("column") or coldef.get("name") or ""
            location = f"{table_name}.{source_column or '<unnamed>'}"
            try:
                comment = _parse_comment(coldef.get("comment"), location)
                if not comment or comment.get("type") != "foreign_key":
                    continue
                reference = comment.get("references")
                if not isinstance(reference, str):
                    raise ValueError(
                        f"Foreign key at {location} must reference table.column; "
                        f"got {reference!r}"
                    )
                bracketed = reference.startswith("[") and reference.endswith("]")
                normalized_reference = reference[1:-1] if bracketed else reference
                if normalized_reference.count(".") != 1:
                    raise ValueError(
                        f"Foreign key at {location} must reference table.column or "
                        f"[table.column]; got {reference!r}"
                    )
                target_table, target_column = normalized_reference.split(".")
                _identifier(table_name, "source table")
                _identifier(source_column, "source column")
                _identifier(target_table, "target table")
                _identifier(target_column, "target column")
                relations.append(ForeignKey(
                    source_table=table_name,
                    source_column=source_column,
                    target_table=target_table,
                    target_column=target_column,
                    configured_source_type=str(coldef.get("type") or ""),
                    source_is_collection=(
                        bracketed
                        or str(coldef.get("type") or "").upper().startswith("ARRAY<")
                    ),
                ))
            except ValueError as exc:
                errors.append(str(exc))
    return relations, errors


def _set_remote_connection_env_defaults() -> None:
    os.environ.setdefault("grpc_proxy", "http://127.0.0.1:8123")
    os.environ.setdefault("https_proxy", "http://127.0.0.1:8123")
    os.environ.setdefault("no_proxy", "localhost,127.0.0.1")
    os.environ.setdefault("BERDL_NO_AUTO_SPAWN", "1")


def _make_spark(app_name: str):
    _set_remote_connection_env_defaults()
    try:
        from spark_connect_remote.session import create_spark_session
    except ModuleNotFoundError:
        from pyspark.sql import SparkSession

        remote = (
            "sc://metrics.berdl.kbase.us:443/;"
            f"use_ssl=true;x-kbase-token={os.environ['KBASE_AUTH_TOKEN']}"
        )
        spark = (
            SparkSession.builder.remote(remote)
            .appName(app_name)
            .getOrCreate()
        )
    else:
        spark = create_spark_session(
            host_template="metrics.berdl.kbase.us",
            port=443,
            use_ssl=True,
            kbase_token=os.environ["KBASE_AUTH_TOKEN"],
            app_name=app_name,
        )
    client = getattr(spark, "_client", None)
    if client is not None and not getattr(client, "_fk_config_defaults_patched", False):
        original = client.get_config_dict
        defaults = {
            "spark.sql.timestampType": "TIMESTAMP_LTZ",
            "spark.sql.session.timeZone": "Etc/UTC",
            "spark.sql.execution.arrow.useLargeVarTypes": "false",
        }

        def patched(*keys):
            try:
                values = original(*keys)
            except Exception:
                values = {}
            return {key: values.get(key, defaults.get(key, "false")) for key in keys}

        client.get_config_dict = patched
        client._fk_config_defaults_patched = True
    return spark


class SparkReader:
    def __init__(self, app_name: str):
        self.app_name = app_name
        self.spark = _make_spark(app_name)

    def collect(self, sql: str):
        for attempt in range(1, 5):
            try:
                return self.spark.sql(sql).collect()
            except Exception as exc:
                reconnectable = any(
                    marker in str(exc)
                    for marker in (
                        "UNAUTHENTICATED",
                        "RST_STREAM",
                        "SparkConnectGrpcException",
                    )
                )
                if not reconnectable or attempt == 4:
                    raise
                print(f"[retry {attempt}/3] reconnecting to BERDL", flush=True)
                self.spark = _make_spark(self.app_name)
        raise AssertionError("unreachable")

    def schema(self, full_table: str) -> dict[str, str]:
        return {
            field.name: field.dataType.simpleString()
            for field in self.spark.table(full_table).schema.fields
        }

    def stop(self) -> None:
        try:
            self.spark.stop()
        except Exception:
            pass


def _full_table(namespace: str, table: str) -> str:
    return f"{_quoted(namespace, 'namespace')}.{_quoted(table, 'table')}"


def _source_values_sql(
    namespace: str, relation: ForeignKey, source_type: str | None = None
) -> str:
    source = _full_table(namespace, relation.source_table)
    source_column = _quoted(relation.source_column, "source column")
    source_type = (source_type or relation.configured_source_type).lower()
    if source_type.startswith("array<array<"):
        return f"SELECT EXPLODE(FLATTEN({source_column})) AS fk_value FROM {source}"
    if source_type.startswith("array<"):
        return f"SELECT EXPLODE({source_column}) AS fk_value FROM {source}"
    if relation.source_is_collection:
        return (
            "SELECT EXPLODE(COALESCE("
            f"FLATTEN(FROM_JSON({source_column}, 'array<array<string>>')), "
            f"FROM_JSON({source_column}, 'array<string>'))) AS fk_value "
            f"FROM {source}"
        )
    return (
        f"SELECT {source_column} AS fk_value FROM {source} "
        f"WHERE {source_column} IS NOT NULL"
    )


def build_metrics_sql(
    namespace: str, relation: ForeignKey, source_type: str | None = None
) -> str:
    target = _full_table(namespace, relation.target_table)
    target_column = _quoted(relation.target_column, "target column")
    source_values = _source_values_sql(namespace, relation, source_type)
    return f"""
WITH source_values AS (
  {source_values}
), nonnull_source_values AS (
  SELECT fk_value FROM source_values WHERE fk_value IS NOT NULL
), target_values AS (
  SELECT DISTINCT {target_column} AS target_value
  FROM {target}
  WHERE {target_column} IS NOT NULL
)
SELECT
  COUNT(*) AS source_non_null_rows,
  COUNT(DISTINCT s.fk_value) AS source_distinct_values,
  COALESCE(SUM(CASE WHEN t.target_value IS NULL THEN 1 ELSE 0 END), 0) AS orphan_rows,
  COUNT(DISTINCT CASE WHEN t.target_value IS NULL THEN s.fk_value END) AS orphan_values
FROM nonnull_source_values s
LEFT JOIN target_values t ON s.fk_value = t.target_value
""".strip()


def build_duplicate_sql(namespace: str, relation: ForeignKey) -> str:
    target = _full_table(namespace, relation.target_table)
    target_column = _quoted(relation.target_column, "target column")
    return f"""
SELECT
  COUNT(*) AS duplicate_target_values,
  COALESCE(SUM(value_count - 1), 0) AS duplicate_target_rows
FROM (
  SELECT {target_column}, COUNT(*) AS value_count
  FROM {target}
  WHERE {target_column} IS NOT NULL
  GROUP BY {target_column}
  HAVING COUNT(*) > 1
) duplicate_values
""".strip()


def build_orphan_sample_sql(
    namespace: str,
    relation: ForeignKey,
    sample_limit: int,
    source_type: str | None = None,
) -> str:
    target = _full_table(namespace, relation.target_table)
    target_column = _quoted(relation.target_column, "target column")
    source_values = _source_values_sql(namespace, relation, source_type)
    return f"""
WITH source_values AS (
  {source_values}
)
SELECT DISTINCT s.fk_value AS orphan_value
FROM source_values s
LEFT ANTI JOIN {target} t ON s.fk_value = t.{target_column}
WHERE s.fk_value IS NOT NULL
ORDER BY orphan_value
LIMIT {sample_limit}
""".strip()


def build_collection_parse_sql(namespace: str, relation: ForeignKey) -> str:
    source = _full_table(namespace, relation.source_table)
    source_column = _quoted(relation.source_column, "source column")
    return f"""
SELECT COUNT(*) AS collection_parse_error_rows
FROM {source}
WHERE {source_column} IS NOT NULL
  AND FROM_JSON({source_column}, 'array<string>') IS NULL
  AND FROM_JSON({source_column}, 'array<array<string>>') IS NULL
""".strip()


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _relation_key(relation: ForeignKey) -> str:
    return f"{relation.source_table}.{relation.source_column}"


def _batches(items: list[Any], batch_size: int):
    for start in range(0, len(items), batch_size):
        yield items[start:start + batch_size]


def _unique_target_relations(relations: list[ForeignKey]) -> list[ForeignKey]:
    by_target: dict[tuple[str, str], ForeignKey] = {}
    for relation in relations:
        by_target.setdefault(
            (relation.target_table, relation.target_column), relation
        )
    return [by_target[key] for key in sorted(by_target)]


def _stack_branch(
    namespace: str,
    table: str,
    entries: list[tuple[str, str]],
    key_alias: str,
    value_alias: str,
) -> str:
    arguments = ", ".join(
        f"{_sql_literal(key)}, CAST({_quoted(column, 'column')} AS STRING)"
        for key, column in entries
    )
    return (
        f"SELECT {key_alias}, {value_alias} "
        f"FROM {_full_table(namespace, table)} "
        f"LATERAL VIEW STACK({len(entries)}, {arguments}) stacked "
        f"AS {key_alias}, {value_alias}"
    )


def build_batched_metrics_sql(
    namespace: str,
    relations: list[ForeignKey],
    source_types: dict[str, str],
) -> str:
    scalar_by_table: dict[str, list[tuple[str, str]]] = {}
    source_branches: list[str] = []
    for relation in relations:
        key = _relation_key(relation)
        source_type = source_types[key]
        if relation.source_is_collection or source_type.startswith("array<"):
            source_branches.append(
                "SELECT "
                f"{_sql_literal(key)} AS relationship_key, "
                "CAST(fk_value AS STRING) AS fk_value FROM ("
                f"{_source_values_sql(namespace, relation, source_type)}"
                ") collection_values"
            )
        else:
            scalar_by_table.setdefault(relation.source_table, []).append(
                (key, relation.source_column)
            )
    source_branches.extend(
        _stack_branch(
            namespace, table, entries, "relationship_key", "fk_value"
        )
        for table, entries in sorted(scalar_by_table.items())
    )

    target_by_table: dict[str, list[tuple[str, str]]] = {}
    for relation in relations:
        target_by_table.setdefault(relation.target_table, []).append(
            (_relation_key(relation), relation.target_column)
        )
    target_branches = [
        _stack_branch(
            namespace, table, entries, "relationship_key", "target_value"
        )
        for table, entries in sorted(target_by_table.items())
    ]
    return f"""
WITH source_values AS (
  {" UNION ALL ".join(source_branches)}
), target_values AS (
  SELECT DISTINCT relationship_key, target_value
  FROM (
    {" UNION ALL ".join(target_branches)}
  ) raw_target_values
  WHERE target_value IS NOT NULL
)
SELECT
  s.relationship_key,
  COUNT(*) AS source_non_null_rows,
  COUNT(DISTINCT s.fk_value) AS source_distinct_values,
  COALESCE(SUM(CASE WHEN t.target_value IS NULL THEN 1 ELSE 0 END), 0) AS orphan_rows,
  COUNT(DISTINCT CASE WHEN t.target_value IS NULL THEN s.fk_value END) AS orphan_values
FROM source_values s
LEFT JOIN target_values t
  ON s.relationship_key = t.relationship_key
 AND s.fk_value = t.target_value
WHERE s.fk_value IS NOT NULL
GROUP BY s.relationship_key
""".strip()


def build_batched_duplicate_sql(
    namespace: str, relations: list[ForeignKey]
) -> str:
    unique_targets = sorted({
        (relation.target_table, relation.target_column) for relation in relations
    })
    by_table: dict[str, list[tuple[str, str]]] = {}
    for table, column in unique_targets:
        by_table.setdefault(table, []).append((f"{table}.{column}", column))
    branches = [
        _stack_branch(namespace, table, entries, "target_key", "target_value")
        for table, entries in sorted(by_table.items())
    ]
    return f"""
WITH target_values AS (
  {" UNION ALL ".join(branches)}
), duplicate_values AS (
  SELECT target_key, target_value, COUNT(*) AS value_count
  FROM target_values
  WHERE target_value IS NOT NULL
  GROUP BY target_key, target_value
  HAVING COUNT(*) > 1
)
SELECT
  target_key,
  COUNT(*) AS duplicate_target_values,
  COALESCE(SUM(value_count - 1), 0) AS duplicate_target_rows
FROM duplicate_values
GROUP BY target_key
""".strip()


def build_batched_duplicate_sample_sql(
    namespace: str, relations: list[ForeignKey], sample_limit: int
) -> str:
    unique_targets = sorted({
        (relation.target_table, relation.target_column) for relation in relations
    })
    by_table: dict[str, list[tuple[str, str]]] = {}
    for table, column in unique_targets:
        by_table.setdefault(table, []).append((f"{table}.{column}", column))
    branches = [
        _stack_branch(namespace, table, entries, "target_key", "target_value")
        for table, entries in sorted(by_table.items())
    ]
    return f"""
WITH target_values AS (
  {" UNION ALL ".join(branches)}
), duplicate_values AS (
  SELECT target_key, target_value, COUNT(*) AS duplicate_count
  FROM target_values
  WHERE target_value IS NOT NULL
  GROUP BY target_key, target_value
  HAVING COUNT(*) > 1
), ranked AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY target_key ORDER BY target_value
  ) AS sample_rank
  FROM duplicate_values
)
SELECT target_key, target_value, duplicate_count
FROM ranked
WHERE sample_rank <= {sample_limit}
ORDER BY target_key, target_value
""".strip()


def build_batched_collection_parse_sql(
    namespace: str, relations: list[ForeignKey], source_types: dict[str, str]
) -> str | None:
    by_table: dict[str, list[tuple[str, str]]] = {}
    for relation in relations:
        key = _relation_key(relation)
        if not relation.source_is_collection or source_types[key] != "string":
            continue
        column = _quoted(relation.source_column, "source column")
        expression = (
            f"CASE WHEN {column} IS NOT NULL "
            f"AND FROM_JSON({column}, 'array<string>') IS NULL "
            f"AND FROM_JSON({column}, 'array<array<string>>') IS NULL "
            "THEN 1 ELSE 0 END"
        )
        by_table.setdefault(relation.source_table, []).append((key, expression))
    if not by_table:
        return None
    branches = []
    for table, entries in sorted(by_table.items()):
        arguments = ", ".join(
            f"{_sql_literal(key)}, {expression}" for key, expression in entries
        )
        branches.append(
            "SELECT relationship_key, SUM(parse_error) AS collection_parse_error_rows "
            f"FROM {_full_table(namespace, table)} "
            f"LATERAL VIEW STACK({len(entries)}, {arguments}) stacked "
            "AS relationship_key, parse_error GROUP BY relationship_key"
        )
    return " UNION ALL ".join(branches)


def _row_dict(row: Any) -> dict[str, Any]:
    return row.asDict(recursive=True)


def _new_check(relation: ForeignKey) -> dict[str, Any]:
    return {
        **asdict(relation),
        "status": "pass",
        "source_type": "",
        "target_type": "",
        "source_non_null_rows": 0,
        "source_distinct_values": 0,
        "orphan_rows": 0,
        "orphan_values": 0,
        "duplicate_target_values": 0,
        "duplicate_target_rows": 0,
        "duplicate_target_samples": [],
        "collection_parse_error_rows": 0,
        "orphan_samples": [],
        "errors": [],
    }


def _configured_schema(table: dict[str, Any]) -> dict[str, str]:
    return {
        str(column.get("column") or column.get("name")): str(column.get("type") or "")
        for column in table.get("schema") or []
    }


def _iter_local_rows(table: dict[str, Any]):
    path = Path(table.get("local_path") or "")
    if not path.is_file():
        raise FileNotFoundError(f"Missing staged table file: {path}")
    options = table.get("csv") or {}
    delimiter = options.get("delimiter", "\t")
    quotechar = options.get("quote", '"')
    # Staged TSVs are emitted by an RFC-style CSV writer even when the Spark
    # config disables quote handling downstream.
    if quotechar == "\x00":
        quotechar = '"'
    escapechar = options.get("escape", "\\")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(
            handle,
            delimiter=delimiter,
            quotechar=quotechar,
            escapechar=escapechar,
        )
        yield from reader


def _local_values(
    raw: str | None, source_type: str, source_is_collection: bool = False
) -> tuple[list[str], bool]:
    if raw in (None, "", "\\N"):
        return [], False
    if not source_is_collection and not source_type.upper().startswith("ARRAY<"):
        return [raw], False
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return [], True
    if not isinstance(parsed, list):
        return [], True
    values: list[str] = []
    for value in parsed:
        nested = value if isinstance(value, list) else [value]
        for item in nested:
            if item is not None:
                values.append(str(item))
    return values, False


def validate_local(
    config: dict[str, Any],
    namespace: str,
    relations: list[ForeignKey],
    declaration_errors: list[str],
    sample_limit: int,
) -> dict[str, Any]:
    tables = {table.get("name"): table for table in config.get("tables", [])}
    schemas = {name: _configured_schema(table) for name, table in tables.items()}
    checks = [_new_check(relation) for relation in relations]
    checks_by_key = {
        _relation_key(relation): check
        for relation, check in zip(relations, checks)
    }

    for relation, check in zip(relations, checks):
        source_schema = schemas.get(relation.source_table)
        target_schema = schemas.get(relation.target_table)
        if source_schema is None:
            check["errors"].append(
                f"Missing configured source table: {relation.source_table}"
            )
        elif relation.source_column not in source_schema:
            check["errors"].append(
                f"Missing configured source column: {relation.source_table}."
                f"{relation.source_column}"
            )
        else:
            check["source_type"] = source_schema[relation.source_column].lower()
        if target_schema is None:
            check["errors"].append(
                f"Missing configured target table: {relation.target_table}"
            )
        elif relation.target_column not in target_schema:
            check["errors"].append(
                f"Missing configured target column: {relation.target_table}."
                f"{relation.target_column}"
            )
        else:
            check["target_type"] = target_schema[relation.target_column].lower()
        effective_source_type = check["source_type"]
        while effective_source_type.startswith("array<"):
            effective_source_type = effective_source_type[6:-1]
        if (
            check["source_type"]
            and check["target_type"]
            and effective_source_type != check["target_type"]
        ):
            check["errors"].append(
                f"Incompatible configured types: {check['source_type']} and "
                f"{check['target_type']}"
            )

    target_values: dict[str, set[str]] = {}
    target_relations = _unique_target_relations([
        relation for relation, check in zip(relations, checks)
        if not check["errors"]
    ])
    targets_by_table: dict[str, list[ForeignKey]] = {}
    for relation in target_relations:
        targets_by_table.setdefault(relation.target_table, []).append(relation)
    for table_number, (table_name, table_relations) in enumerate(
        sorted(targets_by_table.items()), start=1
    ):
        print(
            f"[foreign keys local] target table {table_number}/"
            f"{len(targets_by_table)}: {table_name}",
            flush=True,
        )
        seen = {
            f"{relation.target_table}.{relation.target_column}": set()
            for relation in table_relations
        }
        duplicate_counts = {key: {} for key in seen}
        try:
            for row in _iter_local_rows(tables[table_name]):
                for relation in table_relations:
                    target_key = (
                        f"{relation.target_table}.{relation.target_column}"
                    )
                    value = row.get(relation.target_column)
                    if value in (None, "", "\\N"):
                        continue
                    if value in seen[target_key]:
                        counts = duplicate_counts[target_key]
                        counts[value] = counts.get(value, 1) + 1
                    else:
                        seen[target_key].add(value)
        except (FileNotFoundError, csv.Error) as exc:
            for relation in table_relations:
                checks_by_key[_relation_key(relation)]["errors"].append(str(exc))
            continue
        for relation in table_relations:
            target_key = f"{relation.target_table}.{relation.target_column}"
            target_values[target_key] = seen[target_key]
            duplicates = duplicate_counts[target_key]
            for check, candidate in zip(checks, relations):
                if (
                    candidate.target_table,
                    candidate.target_column,
                ) != (relation.target_table, relation.target_column):
                    continue
                check["duplicate_target_values"] = len(duplicates)
                check["duplicate_target_rows"] = sum(
                    count - 1 for count in duplicates.values()
                )
                check["duplicate_target_samples"] = [
                    {"target_value": value, "duplicate_count": count}
                    for value, count in sorted(duplicates.items())[:sample_limit]
                ]

    sources_by_table: dict[str, list[ForeignKey]] = {}
    for relation, check in zip(relations, checks):
        if not check["errors"]:
            sources_by_table.setdefault(relation.source_table, []).append(relation)
    distinct_values = {_relation_key(relation): set() for relation in relations}
    orphan_values = {_relation_key(relation): set() for relation in relations}
    for table_number, (table_name, table_relations) in enumerate(
        sorted(sources_by_table.items()), start=1
    ):
        print(
            f"[foreign keys local] source table {table_number}/"
            f"{len(sources_by_table)}: {table_name}",
            flush=True,
        )
        try:
            for row in _iter_local_rows(tables[table_name]):
                for relation in table_relations:
                    key = _relation_key(relation)
                    check = checks_by_key[key]
                    values, parse_error = _local_values(
                        row.get(relation.source_column),
                        check["source_type"],
                        relation.source_is_collection,
                    )
                    if parse_error:
                        check["collection_parse_error_rows"] += 1
                        continue
                    target_key = (
                        f"{relation.target_table}.{relation.target_column}"
                    )
                    valid_targets = target_values.get(target_key, set())
                    for value in values:
                        check["source_non_null_rows"] += 1
                        distinct_values[key].add(value)
                        if value not in valid_targets:
                            check["orphan_rows"] += 1
                            orphan_values[key].add(value)
        except (FileNotFoundError, csv.Error) as exc:
            for relation in table_relations:
                checks_by_key[_relation_key(relation)]["errors"].append(str(exc))

    for relation, check in zip(relations, checks):
        key = _relation_key(relation)
        check["source_distinct_values"] = len(distinct_values[key])
        check["orphan_values"] = len(orphan_values[key])
        check["orphan_samples"] = sorted(orphan_values[key])[:sample_limit]
        if check["collection_parse_error_rows"]:
            check["errors"].append(
                f"{check['collection_parse_error_rows']} source rows contain "
                "invalid JSON arrays"
            )
        if check["orphan_values"]:
            check["errors"].append(
                f"{check['orphan_values']} distinct source values are orphaned"
            )
        if check["duplicate_target_values"]:
            check["errors"].append(
                f"{check['duplicate_target_values']} referenced target values "
                "are duplicated"
            )
        if check["errors"]:
            check["status"] = "fail"

    failed = [check for check in checks if check["status"] != "pass"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "namespace": namespace,
        "config_namespace": config.get("namespace"),
        "validation_mode": "local_package",
        "declaration_errors": declaration_errors,
        "checks": checks,
        "summary": {
            "relationships_checked": len(checks),
            "passed": len(checks) - len(failed),
            "failed": len(failed),
            "declaration_errors": len(declaration_errors),
            "source_tables_checked": len({r.source_table for r in relations}),
        },
    }


def _write_reports(report_dir: Path, result: dict[str, Any]) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "foreign_key_validation.json").write_text(
        json.dumps(result, indent=2, default=str), encoding="utf-8"
    )
    fields = [
        "source_table",
        "source_column",
        "target_table",
        "target_column",
        "status",
        "source_type",
        "target_type",
        "source_non_null_rows",
        "source_distinct_values",
        "orphan_rows",
        "orphan_values",
        "duplicate_target_values",
        "duplicate_target_rows",
        "duplicate_target_samples",
        "collection_parse_error_rows",
        "orphan_samples",
        "errors",
    ]
    with (report_dir / "foreign_key_validation.tsv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for check in result.get("checks", []):
            row = {field: check.get(field, "") for field in fields}
            row["orphan_samples"] = json.dumps(row["orphan_samples"])
            row["duplicate_target_samples"] = json.dumps(
                row["duplicate_target_samples"]
            )
            row["errors"] = json.dumps(row["errors"])
            writer.writerow(row)


def validate(
    config: dict[str, Any],
    namespace: str,
    relations: list[ForeignKey],
    declaration_errors: list[str],
    sample_limit: int,
    relationship_batch_size: int,
) -> dict[str, Any]:
    reader = SparkReader("check-berdl-foreign-keys")
    checks: list[dict[str, Any]] = []
    schema_cache: dict[str, dict[str, str]] = {}
    try:
        live_tables = {
            _row_dict(row).get("tableName")
            for row in reader.collect(
                f"SHOW TABLES IN {_quoted(namespace, 'namespace')}"
            )
            if not _row_dict(row).get("isTemporary")
        }
        for relation in relations:
            checks.append(_new_check(relation))

        print(f"[foreign keys] inspecting {len(set(
            table for relation in relations
            for table in (relation.source_table, relation.target_table)
        ))} live table schemas", flush=True)
        for check, relation in zip(checks, relations):
            for table_name, role in (
                (relation.source_table, "source"),
                (relation.target_table, "target"),
            ):
                if table_name not in live_tables:
                    check["errors"].append(f"Missing live {role} table: {table_name}")
                elif table_name not in schema_cache:
                    schema_cache[table_name] = reader.schema(
                        _full_table(namespace, table_name)
                    )
            if check["errors"]:
                continue
            source_schema = schema_cache[relation.source_table]
            target_schema = schema_cache[relation.target_table]
            if relation.source_column not in source_schema:
                check["errors"].append(
                    f"Missing live source column: {relation.source_table}."
                    f"{relation.source_column}"
                )
            if relation.target_column not in target_schema:
                check["errors"].append(
                    f"Missing live target column: {relation.target_table}."
                    f"{relation.target_column}"
                )
            if check["errors"]:
                continue
            check["source_type"] = source_schema[relation.source_column]
            check["target_type"] = target_schema[relation.target_column]
            effective_source_type = check["source_type"]
            while effective_source_type.startswith("array<"):
                effective_source_type = effective_source_type[6:-1]
            if effective_source_type != check["target_type"]:
                check["errors"].append(
                    f"Incompatible live types: {check['source_type']} and "
                    f"{check['target_type']}"
                )

        valid_relations = [
            relation for check, relation in zip(checks, relations) if not check["errors"]
        ]
        source_types = {
            _relation_key(relation): check["source_type"]
            for check, relation in zip(checks, relations)
            if not check["errors"]
        }
        checks_by_key = {_relation_key(relation): check for check, relation in zip(
            checks, relations
        )}

        if valid_relations:
            print(
                f"[foreign keys] checking values for {len(valid_relations)} relationships",
                flush=True,
            )
            metric_batches = list(_batches(valid_relations, relationship_batch_size))
            for batch_number, batch in enumerate(metric_batches, start=1):
                print(
                    f"[foreign keys] value batch {batch_number}/"
                    f"{len(metric_batches)} ({len(batch)} relationships)",
                    flush=True,
                )
                for row in reader.collect(build_batched_metrics_sql(
                    namespace, batch, source_types
                )):
                    metrics = _row_dict(row)
                    key = metrics.pop("relationship_key")
                    checks_by_key[key].update(metrics)

            print("[foreign keys] checking referenced-key uniqueness", flush=True)
            duplicate_by_target = {}
            target_relations = _unique_target_relations(valid_relations)
            target_batches = list(_batches(
                target_relations, relationship_batch_size
            ))
            for batch_number, batch in enumerate(target_batches, start=1):
                print(
                    f"[foreign keys] uniqueness batch {batch_number}/"
                    f"{len(target_batches)} ({len(batch)} targets)",
                    flush=True,
                )
                for row in reader.collect(build_batched_duplicate_sql(
                    namespace, batch
                )):
                    duplicate = _row_dict(row)
                    duplicate_by_target[duplicate.pop("target_key")] = duplicate
            for check, relation in zip(checks, relations):
                target_key = f"{relation.target_table}.{relation.target_column}"
                check.update(duplicate_by_target.get(target_key, {
                    "duplicate_target_values": 0,
                    "duplicate_target_rows": 0,
                }))

            duplicate_samples_by_target: dict[str, list[dict[str, Any]]] = {}
            if duplicate_by_target:
                print("[foreign keys] sampling duplicate target keys", flush=True)
                duplicate_relations = [
                    relation for relation in target_relations
                    if f"{relation.target_table}.{relation.target_column}"
                    in duplicate_by_target
                ]
                duplicate_batches = list(_batches(
                    duplicate_relations, relationship_batch_size
                ))
                for batch_number, batch in enumerate(duplicate_batches, start=1):
                    print(
                        f"[foreign keys] duplicate sample batch {batch_number}/"
                        f"{len(duplicate_batches)} ({len(batch)} targets)",
                        flush=True,
                    )
                    for row in reader.collect(build_batched_duplicate_sample_sql(
                        namespace, batch, sample_limit
                    )):
                        sample = _row_dict(row)
                        target_key = sample.pop("target_key")
                        duplicate_samples_by_target.setdefault(
                            target_key, []
                        ).append(sample)
                for check, relation in zip(checks, relations):
                    target_key = f"{relation.target_table}.{relation.target_column}"
                    check["duplicate_target_samples"] = (
                        duplicate_samples_by_target.get(target_key, [])
                    )

            print("[foreign keys] checking serialized collections", flush=True)
            for batch in _batches(valid_relations, relationship_batch_size):
                parse_sql = build_batched_collection_parse_sql(
                    namespace, batch, source_types
                )
                if parse_sql:
                    for row in reader.collect(parse_sql):
                        parsed = _row_dict(row)
                        key = parsed.pop("relationship_key")
                        checks_by_key[key].update(parsed)

        for check, relation in zip(checks, relations):
            if check["collection_parse_error_rows"]:
                check["errors"].append(
                    f"{check['collection_parse_error_rows']} source rows contain "
                    "invalid JSON arrays"
                )
            if check["orphan_values"]:
                check["orphan_samples"] = [
                    _row_dict(row).get("orphan_value")
                    for row in reader.collect(build_orphan_sample_sql(
                        namespace, relation, sample_limit, check["source_type"]
                    ))
                ]
                check["errors"].append(
                    f"{check['orphan_values']} distinct source values are orphaned"
                )
            if check["duplicate_target_values"]:
                check["errors"].append(
                    f"{check['duplicate_target_values']} referenced target values "
                    "are duplicated"
                )
            if check["errors"]:
                check["status"] = "fail"
    finally:
        reader.stop()

    failed = [check for check in checks if check["status"] != "pass"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "namespace": namespace,
        "config_namespace": config.get("namespace"),
        "declaration_errors": declaration_errors,
        "checks": checks,
        "summary": {
            "relationships_checked": len(checks),
            "passed": len(checks) - len(failed),
            "failed": len(failed),
            "declaration_errors": len(declaration_errors),
            "source_tables_checked": len({r.source_table for r in relations}),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--run-dir", type=Path)
    source.add_argument("--config", type=Path)
    parser.add_argument("--namespace")
    parser.add_argument("--table-file", type=Path)
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--sample-limit", type=int, default=20)
    parser.add_argument("--relationship-batch-size", type=int, default=25)
    parser.add_argument(
        "--local-package",
        action="store_true",
        help="validate the exact staged files instead of querying live Spark",
    )
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()

    if args.sample_limit < 1:
        parser.error("--sample-limit must be at least 1")
    if args.relationship_batch_size < 1:
        parser.error("--relationship-batch-size must be at least 1")
    run_dir = args.run_dir.resolve() if args.run_dir else None
    config_path = (
        args.config.resolve()
        if args.config
        else run_dir / "ingest" / "config.dry_run.json"
    )
    config = _load_json(config_path)
    namespace = args.namespace or config.get("namespace")
    if not namespace:
        parser.error("namespace is absent from the config; pass --namespace")
    selected_tables = (
        set(args.table_file.read_text(encoding="utf-8").split())
        if args.table_file
        else None
    )
    relations, declaration_errors = extract_foreign_keys(config, selected_tables)
    plan = {
        "namespace": namespace,
        "config": str(config_path),
        "selected_tables": sorted(selected_tables) if selected_tables is not None else None,
        "relationships": [asdict(relation) for relation in relations],
        "declaration_errors": declaration_errors,
    }
    if args.plan_only:
        print(json.dumps(plan, indent=2))
        return 1 if declaration_errors else 0

    report_dir = (
        args.report_dir.resolve()
        if args.report_dir
        else (run_dir / "reports" if run_dir else Path.cwd() / "reports")
    )
    if not relations and not declaration_errors:
        result = {
            **plan,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "checks": [],
            "summary": {
                "relationships_checked": 0,
                "passed": 0,
                "failed": 0,
                "declaration_errors": 0,
                "source_tables_checked": 0,
            },
        }
    else:
        if args.local_package:
            result = validate_local(
                config,
                namespace,
                relations,
                declaration_errors,
                args.sample_limit,
            )
        else:
            result = validate(
                config,
                namespace,
                relations,
                declaration_errors,
                args.sample_limit,
                args.relationship_batch_size,
            )
        result["config"] = str(config_path)
        result["selected_tables"] = plan["selected_tables"]
    _write_reports(report_dir, result)
    print(json.dumps(result["summary"], indent=2))
    return 1 if result["summary"]["failed"] or declaration_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
