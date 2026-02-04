import argparse
import json
import os
import sys
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

DEFAULT_BASE_URL = "https://hub.berdl.kbase.us/apis/mcp"
BASE_URL = os.environ.get("BERDL_BASE_URL", DEFAULT_BASE_URL)
DB_NAME = os.environ.get("BERDL_DATABASE", "enigma_coral")
OUTPUT_DIR = os.environ.get("BERDL_OUTPUT_DIR", "schema")
REQUEST_TIMEOUT = 120
REQUEST_RETRIES = 3
REQUEST_RETRY_DELAY = 2
DEBUG = os.environ.get("BERDL_DEBUG", "").lower() in {"1", "true", "yes"}
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
            if len(parts) < 3:
                continue
            col_name, col_type, nullable = parts[:3]
            tables.setdefault(current_table, {})[col_name] = {
                "type": col_type,
                "nullable": nullable,
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


def get_table_schema(headers: Dict[str, str], table: str) -> List[str]:
    payload = {"database": DB_NAME, "table": table}
    data = post_json("/delta/databases/tables/schema", payload, headers)
    columns = data.get("columns") if isinstance(data, dict) else None
    if not isinstance(columns, list):
        raise ValueError(f"Unexpected schema response for {table}: {json.dumps(data)[:500]}")
    if columns and all(isinstance(col, dict) for col in columns):
        names: List[str] = []
        for col in columns:
            name = col.get("name") or col.get("column_name")
            if name:
                names.append(str(name))
        return names
    return [str(col) for col in columns]


def count_table_rows(headers: Dict[str, str], table: str) -> int:
    payload = {"database": DB_NAME, "table": table}
    data = post_json("/delta/tables/count", payload, headers)
    if isinstance(data, dict) and "count" in data:
        return int(data["count"])
    raise ValueError(f"Unexpected count response for {table}: {json.dumps(data)[:500]}")


def fetch_table_rows(
    headers: Dict[str, str],
    table: str,
    columns: List[str],
    total: int,
    limit: int,
    max_rows: Optional[int],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    target = min(total, max_rows) if max_rows is not None else total
    if target == 0:
        return rows
    order_by = [{"column": columns[0], "direction": "ASC"}] if columns else None
    for offset in range(0, target, limit):
        payload: Dict[str, Any] = {
            "database": DB_NAME,
            "table": table,
            "limit": min(limit, target - offset),
            "offset": offset,
        }
        if columns:
            payload["columns"] = [{"column": col} for col in columns]
        if order_by:
            payload["order_by"] = order_by
        data = post_json("/delta/tables/select", payload, headers)
        batch = data.get("data") if isinstance(data, dict) else None
        if not isinstance(batch, list):
            raise ValueError(f"Unexpected select response for {table}: {json.dumps(data)[:500]}")
        rows.extend(batch)
    return rows


def format_cell(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (list, dict)):
        rendered = json.dumps(value, ensure_ascii=True)
    else:
        rendered = str(value)
    rendered = rendered.replace("\n", " ").replace("\r", " ")
    return rendered.replace("|", "\\|")


def format_markdown(
    table: str,
    columns: Iterable[str],
    rows: Iterable[Dict[str, Any]],
    total_rows: int,
    overrides: Dict[str, Dict[str, str]],
    description: Optional[str],
) -> str:
    lines: List[str] = [
        f"# Table: {DB_NAME}.{table}",
        "",
    ]
    if description:
        lines.extend([f"**Description:** {description}", ""])
    lines.extend(["## Schema", ""])
    lines.append("| Column Name | Data Type | Nullable |")
    lines.append("|-------------|-----------|----------|")
    for col in columns:
        meta = overrides.get(col, {})
        col_type = meta.get("type", "")
        nullable = meta.get("nullable", "")
        lines.append(f"| {col} | {col_type} | {nullable} |")
    lines.extend(["", f"**Total Rows:** {total_rows}", "", "## Data", ""])
    columns_list = list(columns)
    header = "| " + " | ".join(columns_list) + " |"
    divider = "| " + " | ".join("---" for _ in columns_list) + " |"
    lines.append(header)
    lines.append(divider)
    for row in rows:
        row_values = [format_cell(row.get(col)) for col in columns_list]
        lines.append("| " + " | ".join(row_values) + " |")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download a BERDL table to markdown.")
    parser.add_argument("table", help="Table name (without database prefix)")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BERDL_BASE_URL", DEFAULT_BASE_URL),
        help=f"MCP base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--schema-dir",
        default=None,
        help="Directory to read schema markdown (defaults to ./schema).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debugging, including BERDL API calls.",
    )
    parser.add_argument("--limit", type=int, default=1000, help="Rows per page (max 1000)")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Optional maximum number of rows to fetch",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output markdown path (defaults to berdl_table_data/{db}.{table}.md)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    global BASE_URL
    global DEBUG
    BASE_URL = args.base_url
    if args.debug:
        DEBUG = True
    token = os.environ.get("KB_AUTH_TOKEN")
    if not token:
        print("KB_AUTH_TOKEN is not set", file=sys.stderr)
        return 2

    if args.limit <= 0 or args.limit > 1000:
        print("limit must be between 1 and 1000", file=sys.stderr)
        return 2

    headers = {"Authorization": f"Bearer {token}"}

    schema_paths: List[Optional[str]] = []
    if args.schema_dir:
        schema_paths.append(os.path.join(args.schema_dir, "enigma_coral_schema.md"))
    schema_paths.extend(SCHEMA_MARKDOWN_PATHS)
    overrides, descriptions = load_schema_markdown(schema_paths)
    table_overrides = overrides.get(args.table, {})
    description = descriptions.get(args.table)

    columns = get_table_schema(headers, args.table)
    total_rows = count_table_rows(headers, args.table)
    rows = fetch_table_rows(
        headers,
        args.table,
        columns,
        total_rows,
        args.limit,
        args.max_rows,
    )

    output_path = args.output
    if not output_path:
        output_path = os.path.join(OUTPUT_DIR, f"{args.table}_table.md")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    markdown = format_markdown(
        args.table,
        columns,
        rows,
        total_rows,
        table_overrides,
        description,
    )
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(markdown)

    print(f"Wrote table markdown to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
