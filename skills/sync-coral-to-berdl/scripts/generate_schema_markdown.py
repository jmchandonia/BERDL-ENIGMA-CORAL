#!/usr/bin/env python3
"""Generate ENIGMA CORAL schema markdown from the BERDL upload package."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Iterable


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _column_name(coldef: dict[str, Any]) -> str:
    return coldef.get("column") or coldef.get("name") or ""


def _type_name(coldef: dict[str, Any]) -> str:
    return (coldef.get("type") or "STRING").lower()


def _nullable(coldef: dict[str, Any]) -> str:
    return "Yes" if coldef.get("nullable", True) else "No"


def _markdown_cell(value: Any) -> str:
    if value is None:
        rendered = "NULL"
    elif isinstance(value, (list, dict)):
        rendered = json.dumps(value, ensure_ascii=True)
    else:
        rendered = str(value)
        if rendered == "":
            rendered = "NULL"
    rendered = rendered.replace("\r\n", "\n").replace("\r", "\n")
    if "\n" in rendered:
        rendered = f"\"{rendered.replace('\n', '<br>')}\""
    return rendered.replace("|", "\\|")


def _read_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.reader(handle, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration:
            return [], []
        return header, list(reader)


def _iter_sample(path: Path, limit: int) -> tuple[list[str], list[list[str]], int]:
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.reader(handle, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration:
            return [], [], 0
        rows = []
        count = 0
        for row in reader:
            count += 1
            if len(rows) < limit:
                rows.append(row)
        return header, rows, count


def _schema_from_header(header: Iterable[str]) -> list[dict[str, Any]]:
    return [
        {
            "column": column,
            "type": "STRING",
            "nullable": True,
            "comment": json.dumps({"description": column.replace("_", " ")}),
        }
        for column in header
    ]


def _table_lookup(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {table["name"]: table for table in config.get("tables", []) if table.get("enabled")}


def _ordered_enabled_tables(config: dict[str, Any]) -> list[dict[str, Any]]:
    priority = {"ddt_ndarray": 0, "sys_ddt_typedef": 1}
    return sorted(
        [table for table in config.get("tables", []) if table.get("enabled")],
        key=lambda table: (priority.get(table["name"], 2), table["name"]),
    )


def _write_schema(handle, schema: list[dict[str, Any]], include_comments: bool) -> None:
    if include_comments:
        handle.write("| Column Name | Data Type | Nullable | Comment |\n")
        handle.write("|-------------|-----------|----------|----------|\n")
        for coldef in schema:
            handle.write(
                "| "
                + " | ".join(
                    [
                        _markdown_cell(_column_name(coldef)),
                        _markdown_cell(_type_name(coldef)),
                        _markdown_cell(_nullable(coldef)),
                        _markdown_cell(coldef.get("comment", "")),
                    ]
                )
                + " |\n"
            )
    else:
        handle.write("| Column Name | Data Type | Nullable |\n")
        handle.write("|-------------|-----------|----------|\n")
        for coldef in schema:
            handle.write(
                "| "
                + " | ".join(
                    [
                        _markdown_cell(_column_name(coldef)),
                        _markdown_cell(_type_name(coldef)),
                        _markdown_cell(_nullable(coldef)),
                    ]
                )
                + " |\n"
            )


def _write_rows(handle, header: list[str], rows: list[list[str]]) -> None:
    if not rows:
        handle.write("*Table is empty*\n")
        return
    handle.write("| " + " | ".join(_markdown_cell(column) for column in header) + " |\n")
    handle.write("|" + "|".join(["---" for _ in header]) + "|\n")
    width = len(header)
    for row in rows:
        padded = row[:width] + [""] * max(0, width - len(row))
        handle.write("| " + " | ".join(_markdown_cell(value) for value in padded) + " |\n")


def export_table_to_markdown(config: dict[str, Any], table_name: str, output_file: Path) -> None:
    table = _table_lookup(config)[table_name]
    data_path = Path(table["local_path"])
    header, rows = _read_rows(data_path)
    schema = table.get("schema") or _schema_from_header(header)

    with output_file.open("w", encoding="utf-8", newline="") as handle:
        handle.write(f"# Table: enigma_coral.{table_name}\n\n")
        table_comment = table.get("table_comment") or ""
        if table_comment:
            handle.write(f"**Description:** {_markdown_cell(table_comment)}\n\n")
        handle.write("## Schema\n\n")
        _write_schema(handle, schema, include_comments=False)
        handle.write("\n")
        handle.write(f"**Total Rows:** {len(rows)}\n\n")
        handle.write("## Data\n\n")
        _write_rows(handle, header, rows)


def export_database_schema(config: dict[str, Any], output_file: Path, sample_rows: int) -> None:
    tables = _ordered_enabled_tables(config)
    with output_file.open("w", encoding="utf-8", newline="") as handle:
        handle.write("# Database Schema: enigma_coral\n\n")
        handle.write(f"Total Tables: {len(tables)}\n\n")
        handle.write("---\n\n")
        for table in tables:
            table_name = table["name"]
            data_path = Path(table["local_path"])
            header, samples, row_count = _iter_sample(data_path, sample_rows)
            schema = table.get("schema") or _schema_from_header(header)

            handle.write(f"## Table: {table_name}\n\n")
            table_comment = table.get("table_comment") or ""
            if table_comment:
                handle.write(f"**Table Description:** {_markdown_cell(table_comment)}\n\n")
            handle.write("### Schema\n\n")
            _write_schema(handle, schema, include_comments=True)
            handle.write("\n")
            handle.write(f"**Total Rows:** {row_count}\n\n")
            handle.write(f"### Sample Data ({sample_rows} rows)\n\n")
            _write_rows(handle, header, samples)
            handle.write("\n---\n\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=Path("sync-coral-to-berdl/exports/dryrun-20260527-143730"),
    )
    parser.add_argument("--schema-dir", type=Path, default=Path("schema"))
    parser.add_argument("--sample-rows", type=int, default=5)
    args = parser.parse_args()

    config = _load_json(args.run_dir / "ingest" / "config.dry_run.json")
    args.schema_dir.mkdir(parents=True, exist_ok=True)
    export_table_to_markdown(config, "ddt_ndarray", args.schema_dir / "ddt_ndarray_table.md")
    export_table_to_markdown(config, "sys_ddt_typedef", args.schema_dir / "sys_ddt_typedef_table.md")
    export_database_schema(config, args.schema_dir / "enigma_coral_schema.md", args.sample_rows)
    print(f"Wrote schema markdown to {args.schema_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
