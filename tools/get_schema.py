import argparse
import json
import os
import sys
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

DEFAULT_BASE_URL = "https://hub.berdl.kbase.us/apis/mcp"
BASE_URL = os.environ.get("BERDL_BASE_URL", DEFAULT_BASE_URL)
DB_NAME = "enigma_coral"
OUTPUT_PATH = os.path.join("schema", "enigma_coral_schema.md")
REQUEST_TIMEOUT = 120
REQUEST_RETRIES = 3
REQUEST_RETRY_DELAY = 2
DEBUG = os.environ.get("BERDL_DEBUG", "").lower() in {"1", "true", "yes"}
SAMPLE_ROWS = 5
SCHEMA_MARKDOWN_PATHS = [
    os.environ.get("BERDL_SCHEMA_MARKDOWN_PATH"),
    os.environ.get("BERDL_SUPERSEDED_SCHEMA_PATH"),
    os.path.join("schema", "enigma_coral_schema.md"),
    os.path.join("..", "convert", "spark-minio", "berdl_schema_data", "enigma_coral_schema.md"),
]


def post_json(path: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Any:
    url = f"{BASE_URL}{path}"
    last_error: Optional[Exception] = None
    for attempt in range(REQUEST_RETRIES):
        try:
            if DEBUG:
                print(
                    f"[debug] POST {url} attempt={attempt + 1}/{REQUEST_RETRIES} "
                    f"payload_keys={list(payload.keys())}",
                    file=sys.stderr,
                )
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
            if DEBUG:
                print(
                    f"[debug] request error on {path}: {type(exc).__name__} ({exc})",
                    file=sys.stderr,
                )
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
        if DEBUG:
            print("[debug] attempting /delta/databases/structure", file=sys.stderr)
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


def parse_schema_markdown(
    path: str,
) -> Tuple[Dict[str, Dict[str, Dict[str, str]]], Dict[str, str]]:
    tables: Dict[str, Dict[str, Dict[str, str]]] = {}
    descriptions: Dict[str, str] = {}
    current_table: Optional[str] = None
    in_schema = False
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            if line.startswith("## Table:"):
                current_table = line.split(":", 1)[1].strip()
                in_schema = False
                continue
            if line.startswith("**Table Description:**") and current_table:
                desc = line.split(":", 1)[1].strip()
                descriptions[current_table] = desc.replace("**", "").strip()
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
    return tables, descriptions


def load_schema_markdown(
    schema_paths: Optional[Iterable[Optional[str]]] = None,
) -> Tuple[Dict[str, Dict[str, Dict[str, str]]], Dict[str, str]]:
    paths = list(schema_paths) if schema_paths is not None else SCHEMA_MARKDOWN_PATHS
    for path in paths:
        if not path:
            continue
        if os.path.exists(path):
            if DEBUG:
                print(f"[debug] using schema markdown: {path}", file=sys.stderr)
            return parse_schema_markdown(path)
    if DEBUG:
        print("[debug] no schema markdown found", file=sys.stderr)
    return {}, {}


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
    if DEBUG:
        print(f"[debug] describing table {table}", file=sys.stderr)
    data = post_json("/delta/databases/tables/schema", payload, headers)
    if isinstance(data, dict):
        if "columns" in data and isinstance(data["columns"], list):
            if DEBUG and data["columns"]:
                print(
                    f"[debug] schema columns type={type(data['columns'][0])}",
                    file=sys.stderr,
                )
            columns = data["columns"]
            if all(isinstance(col, dict) for col in columns):
                return {"name": table, "columns": [col for col in columns if isinstance(col, dict)]}
            return {"name": table, "columns": [{"name": col} for col in columns]}
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
    schema_markdown: Optional[Dict[str, Dict[str, Dict[str, str]]]] = None,
    table_descriptions: Optional[Dict[str, str]] = None,
    samples: Optional[Dict[str, Tuple[List[Dict[str, Any]], Optional[str]]]] = None,
) -> str:
    table_list = list(tables)
    lines: List[str] = [
        f"# Database Schema: {DB_NAME}",
        "",
        f"Total Tables: {len(table_list)}",
        "",
        "---",
        "",
    ]
    schema_markdown = schema_markdown or {}
    table_descriptions = table_descriptions or {}
    samples = samples or {}
    for table in table_list:
        name = normalize_table_name(table)
        override_columns = schema_markdown.get(name, {})
        lines.append(f"## Table: {name}")
        lines.append("")
        description = table_descriptions.get(name)
        if description:
            lines.append(f"**Table Description:** {description}")
            lines.append("")
        lines.append("### Schema")
        lines.append("")
        lines.append("| Column Name | Data Type | Nullable | Comment |")
        lines.append("|-------------|-----------|----------|----------|")
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
                nullable = "Yes" if nullable else "No"
            comment = str(column.get("comment", column.get("description", "")))
            override = override_columns.get(col_name, {})
            if not col_type:
                col_type = override.get("type", col_type)
            if not nullable:
                nullable = override.get("nullable", nullable)
            if not comment:
                comment = override.get("comment", comment)
            lines.append(
                f"| {escape_markdown_cell(col_name)} | {escape_markdown_cell(col_type)} | "
                f"{escape_markdown_cell(str(nullable))} | {escape_markdown_cell(comment)} |"
            )
        lines.append("")
        lines.append(f"### Sample Data ({SAMPLE_ROWS} rows)")
        lines.append("")
        sample_rows, sample_error = samples.get(name, ([], None))
        if sample_rows:
            columns_list = list(sample_rows[0].keys())
            lines.append("| " + " | ".join(escape_markdown_cell(col) for col in columns_list) + " |")
            lines.append("|" + "|".join(["---" for _ in columns_list]) + "|")
            for row in sample_rows:
                row_values = [format_cell(row.get(col)) for col in columns_list]
                lines.append("| " + " | ".join(row_values) + " |")
        elif sample_error:
            lines.append(f"*Error retrieving sample data: {sample_error}*")
        else:
            lines.append("*Table is empty*")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def format_cell(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (list, dict)):
        rendered = json.dumps(value, ensure_ascii=True)
    else:
        rendered = str(value)
    rendered = rendered.replace("\n", " ").replace("\r", " ")
    return rendered.replace("|", "\\|")


def escape_markdown_cell(value: str) -> str:
    rendered = value.replace("\n", " ").replace("\r", " ")
    return rendered.replace("|", "\\|")


def fetch_sample_data(
    headers: Dict[str, str], table: str, limit: int = SAMPLE_ROWS
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    payload = {"database": DB_NAME, "table": table, "limit": limit}
    if DEBUG:
        print(f"[debug] fetching sample rows for {table}", file=sys.stderr)
    try:
        data = post_json("/delta/tables/sample", payload, headers)
    except Exception as exc:
        return [], str(exc)
    if not isinstance(data, dict):
        return [], None
    sample = data.get("sample")
    if isinstance(sample, list):
        return [row for row in sample if isinstance(row, dict)], None
    return [], None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch BERDL schema metadata to markdown.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BERDL_BASE_URL", DEFAULT_BASE_URL),
        help=f"MCP base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--schema-dir",
        default=None,
        help="Directory to read/write schema markdown (defaults to ./schema).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debugging, including BERDL API calls.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    global BASE_URL
    global DEBUG
    BASE_URL = args.base_url
    if args.debug:
        DEBUG = True
    if DEBUG:
        print(f"[debug] base_url={BASE_URL}", file=sys.stderr)
    output_path = OUTPUT_PATH
    schema_paths: List[Optional[str]] = []
    if args.schema_dir:
        output_path = os.path.join(args.schema_dir, os.path.basename(OUTPUT_PATH))
        schema_paths.append(output_path)
    schema_paths.extend(SCHEMA_MARKDOWN_PATHS)
    if DEBUG:
        print(f"[debug] output_path={output_path}", file=sys.stderr)
        print(f"[debug] schema search paths={schema_paths}", file=sys.stderr)
    token = os.environ.get("KB_AUTH_TOKEN")
    if not token:
        print("KB_AUTH_TOKEN is not set", file=sys.stderr)
        return 2

    headers = {"Authorization": f"Bearer {token}"}

    table_names = list_tables(headers)
    if DEBUG:
        print(f"[debug] discovered {len(table_names)} tables", file=sys.stderr)
    tables = [describe_table(headers, name) for name in table_names]
    samples = {name: fetch_sample_data(headers, name, SAMPLE_ROWS) for name in table_names}

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    schema_markdown, table_descriptions = load_schema_markdown(schema_paths)
    markdown = format_markdown(tables, schema_markdown, table_descriptions, samples)
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(markdown)

    print(f"Wrote schema markdown to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
