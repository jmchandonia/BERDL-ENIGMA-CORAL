import json
import os
import sys
import time
from typing import Any, Dict, Iterable, List, Optional

import requests

BASE_URL = os.environ.get("BERDL_BASE_URL", "https://hub.berdl.kbase.us/apis/mcp")
DB_NAME = "enigma_coral"
OUTPUT_PATH = os.path.join("schema", "enigma_coral_schema.md")
REQUEST_TIMEOUT = 120
REQUEST_RETRIES = 3
REQUEST_RETRY_DELAY = 2
DEBUG = os.environ.get("BERDL_DEBUG", "").lower() in {"1", "true", "yes"}
SUPERSEDED_SCHEMA_PATHS = [
    os.environ.get("BERDL_SUPERSEDED_SCHEMA_PATH"),
    os.path.join("supercededberdl_schema_data", "enigma_coral_schema.md"),
    os.path.join("..", "convert", "spark-minio", "berdl_schema_data", "enigma_coral_schema.md"),
]


def post_json(path: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Any:
    url = f"{BASE_URL}{path}"
    last_error: Optional[Exception] = None
    for attempt in range(REQUEST_RETRIES):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if DEBUG:
                print(
                    f"[debug] {path} keys={list(data.keys()) if isinstance(data, dict) else type(data)}",
                    file=sys.stderr,
                )
            return data
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
            last_error = exc
            if attempt < REQUEST_RETRIES - 1:
                time.sleep(REQUEST_RETRY_DELAY)
            else:
                raise
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Request failed for {url}")


def try_db_structure(headers: Dict[str, str]) -> Optional[List[Dict[str, Any]]]:
    payload = {"with_schema": True, "use_hms": True}
    try:
        data = post_json("/delta/databases/structure", payload, headers)
    except requests.HTTPError:
        return None
    if not isinstance(data, dict) or "structure" not in data:
        return None
    structure = data.get("structure")
    if not isinstance(structure, dict):
        return None
    db = structure.get(DB_NAME)
    if not isinstance(db, dict):
        return None
    tables = db.get("tables")
    if DEBUG and isinstance(tables, list) and tables:
        sample = tables[0]
        sample_cols = sample.get("columns") if isinstance(sample, dict) else None
        print(
            f"[debug] structure table keys={list(sample.keys()) if isinstance(sample, dict) else type(sample)}",
            file=sys.stderr,
        )
        if isinstance(sample_cols, list) and sample_cols:
            print(
                f"[debug] structure column keys={list(sample_cols[0].keys()) if isinstance(sample_cols[0], dict) else type(sample_cols[0])}",
                file=sys.stderr,
            )
    if isinstance(tables, list):
        return [t for t in tables if isinstance(t, dict)]
    if isinstance(tables, dict):
        return [t for t in tables.values() if isinstance(t, dict)]
    return None


def parse_superseded_schema(path: str) -> Dict[str, Dict[str, Dict[str, str]]]:
    tables: Dict[str, Dict[str, Dict[str, str]]] = {}
    current_table: Optional[str] = None
    in_schema = False
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            if line.startswith("## Table:"):
                current_table = line.split(":", 1)[1].strip()
                in_schema = False
                continue
            if line.startswith("### Schema"):
                in_schema = True
                continue
            if line.startswith("### Sample Data"):
                in_schema = False
                continue
            if not in_schema or not current_table:
                continue
            if line.startswith("| Column Name |"):
                continue
            if not line.startswith("|"):
                continue
            parts = [part.strip() for part in line.strip().strip("|").split("|")]
            if len(parts) < 4:
                continue
            col_name, col_type, nullable, comment = parts[:4]
            tables.setdefault(current_table, {})[col_name] = {
                "type": col_type,
                "nullable": nullable,
                "comment": comment,
            }
    return tables


def load_superseded_schema() -> Dict[str, Dict[str, Dict[str, str]]]:
    for path in SUPERSEDED_SCHEMA_PATHS:
        if not path:
            continue
        if os.path.exists(path):
            if DEBUG:
                print(f"[debug] using superseded schema: {path}", file=sys.stderr)
            return parse_superseded_schema(path)
    if DEBUG:
        print("[debug] no superseded schema found", file=sys.stderr)
    return {}


def list_tables(headers: Dict[str, str]) -> List[str]:
    payload = {"database": DB_NAME, "use_hms": True}
    data = post_json("/delta/databases/tables/list", payload, headers)
    if isinstance(data, dict):
        for key in ("tables", "table_names", "tableNames"):
            if key in data and isinstance(data[key], list):
                return [str(t) for t in data[key]]
    if isinstance(data, list):
        return [str(t) for t in data]
    raise ValueError(f"Unexpected tables list response: {json.dumps(data)[:500]}")


def describe_table(headers: Dict[str, str], table: str) -> Dict[str, Any]:
    payload = {
        "database": DB_NAME,
        "table": table,
        "use_hms": True,
    }
    data = post_json("/delta/databases/tables/schema", payload, headers)
    if isinstance(data, dict):
        if "columns" in data and isinstance(data["columns"], list):
            if DEBUG and data["columns"]:
                print(
                    f"[debug] schema columns type={type(data['columns'][0])}",
                    file=sys.stderr,
                )
            return {
                "name": table,
                "columns": [{"name": col} for col in data["columns"]],
            }
        for key in ("table", "schema", "table_schema"):
            if key in data and isinstance(data[key], dict):
                return data[key]
        return {"name": table, **data}
    raise ValueError(f"Unexpected describe response for {table}: {json.dumps(data)[:500]}")


def extract_tables(data: Any) -> Optional[List[Dict[str, Any]]]:
    if isinstance(data, dict):
        for key in ("tables", "schema", "database_schema"):
            if key in data:
                candidate = data[key]
                if isinstance(candidate, list):
                    return [t for t in candidate if isinstance(t, dict)]
                if isinstance(candidate, dict) and "tables" in candidate:
                    tables = candidate.get("tables")
                    if isinstance(tables, list):
                        return [t for t in tables if isinstance(t, dict)]
    if isinstance(data, list):
        return [t for t in data if isinstance(t, dict)]
    return None


def normalize_table_name(table: Dict[str, Any]) -> str:
    for key in ("name", "table", "table_name"):
        if key in table and table[key]:
            return str(table[key])
    return "unknown_table"


def extract_columns(table: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("columns", "schema", "fields"):
        if key in table and isinstance(table[key], list):
            if all(isinstance(c, str) for c in table[key]):
                return [{"name": c} for c in table[key]]
            return [c for c in table[key] if isinstance(c, dict)]
    return []


def format_markdown(
    tables: Iterable[Dict[str, Any]],
    superseded: Optional[Dict[str, Dict[str, Dict[str, str]]]] = None,
) -> str:
    lines: List[str] = [
        f"# Schema for `{DB_NAME}`",
        "",
        f"Source: `{BASE_URL}`",
        "",
    ]
    superseded = superseded or {}
    for table in tables:
        name = normalize_table_name(table)
        override_columns = superseded.get(name, {})
        lines.append(f"## `{name}`")
        lines.append("")
        lines.append("| Column | Type | Nullable | Comment |")
        lines.append("| --- | --- | --- | --- |")
        columns = extract_columns(table)
        if not columns and override_columns:
            columns = [
                {"name": col_name, **meta} for col_name, meta in override_columns.items()
            ]
        if not columns:
            lines.append("| (no columns reported) |  |  |  |")
        for column in columns:
            col_name = str(column.get("name", column.get("column_name", "")))
            col_type = str(column.get("type", column.get("data_type", "")))
            nullable = column.get("nullable", column.get("is_nullable", ""))
            if isinstance(nullable, bool):
                nullable = "YES" if nullable else "NO"
            comment = str(column.get("comment", column.get("description", "")))
            override = override_columns.get(col_name, {})
            if not col_type:
                col_type = override.get("type", col_type)
            if not nullable:
                nullable = override.get("nullable", nullable)
            if not comment:
                comment = override.get("comment", comment)
            lines.append(f"| {col_name} | {col_type} | {nullable} | {comment} |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    token = os.environ.get("KB_AUTH_TOKEN")
    if not token:
        print("KB_AUTH_TOKEN is not set", file=sys.stderr)
        return 2

    headers = {"Authorization": f"Bearer {token}"}

    tables = try_db_structure(headers)
    if tables is None:
        table_names = list_tables(headers)
        tables = [describe_table(headers, name) for name in table_names]

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    superseded = load_superseded_schema()
    markdown = format_markdown(tables, superseded)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        handle.write(markdown)

    print(f"Wrote schema markdown to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
