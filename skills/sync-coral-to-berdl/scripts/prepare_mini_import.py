#!/usr/bin/env python3
"""Prepare a two-table BERDL mini-import bundle for CORAL sync testing.

The mini bundle intentionally uses TSV and structured schema JSON so the BERDL
ingest package can apply column comments without relying on CSV quoting edge
cases or SQL comment parsing.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from pathlib import Path

from dry_run_tools import parse_schema_file


ASV_TABLE_COMMENT = (
    "ASV (Amplicon Sequence Variant) or OTU (Operational Taxonomic Unit) for older datasets"
)
ASV_SCHEMA = [
    {
        "column": "sdt_asv_id",
        "type": "string",
        "nullable": False,
        "comment": json.dumps({
            "description": "Unique identifier for each ASV/OTU (Primary key)",
            "type": "primary_key",
        }),
    },
    {
        "column": "sdt_asv_name",
        "type": "string",
        "nullable": False,
        "comment": json.dumps({
            "description": "Unique name assigned to the ASV/OTU, usually md5sum",
            "type": "unique_key",
        }),
    },
]
TEXT_REWRITES = (
    ("https://genomics.lbl.gov/enigma-data/", "enigma-data-repository/"),
    ("/auto/sahara/namib/home/gtl/enigma-data-repository/", "enigma-data-repository/"),
)
SYS_OTERM_PROPERTIES_COMMENT = json.dumps({
    "description": "Semicolon-separated map of properties to values for terms that are CORAL microtypes, including scalar data_type, is_valid_data_variable, is_valid_dimension, is_valid_data_variable, is_valid_dimension_variable, is_valid_property, valid_units, and valid_units_parent"
})


def _normalize_text(value: str) -> str:
    normalized = value or ""
    for old, new in TEXT_REWRITES:
        normalized = normalized.replace(old, new)
    return normalized


def _load_table_metadata(run_dir: Path) -> tuple[dict[str, list[dict[str, object]]], dict[str, str]]:
    metadata_dir = run_dir / "metadata"
    schemas_path = metadata_dir / "table_schemas.json"
    comments_path = metadata_dir / "table_comments.json"
    schemas = json.loads(schemas_path.read_text(encoding="utf-8")) if schemas_path.exists() else {}
    comments = json.loads(comments_path.read_text(encoding="utf-8")) if comments_path.exists() else {}
    return schemas, comments


def _copy_tsv_with_selected_columns(src: Path, dst: Path, columns: list[str]) -> int:
    rows = 0
    with src.open(newline="", encoding="utf-8") as in_handle:
        reader = csv.DictReader(in_handle, delimiter="\t")
        missing = [col for col in columns if col not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{src} is missing expected column(s): {', '.join(missing)}")
        with dst.open("w", newline="", encoding="utf-8") as out_handle:
            writer = csv.DictWriter(out_handle, delimiter="\t", fieldnames=columns)
            writer.writeheader()
            for row in reader:
                writer.writerow({col: _normalize_text(row.get(col, "")) for col in columns})
                rows += 1
    return rows


def _write_test_sdt_asv(src: Path, dst: Path) -> int:
    rows = 0
    with src.open(newline="", encoding="utf-8") as in_handle:
        reader = csv.DictReader(in_handle, delimiter="\t")
        required = {"id", "name"}
        missing = sorted(required - set(reader.fieldnames or []))
        if missing:
            raise ValueError(f"{src} is missing expected column(s): {', '.join(missing)}")
        with dst.open("w", newline="", encoding="utf-8") as out_handle:
            writer = csv.DictWriter(
                out_handle,
                delimiter="\t",
                fieldnames=["sdt_asv_id", "sdt_asv_name"],
            )
            writer.writeheader()
            for row in reader:
                writer.writerow({
                    "sdt_asv_id": re.sub(r"^OTU", "ASV", row.get("id", "")),
                    "sdt_asv_name": row.get("name", ""),
                })
                rows += 1
    return rows


def _spark_type_from_schema_type(type_name: str) -> str:
    return {
        "STRING": "string",
        "INT": "int",
        "INTEGER": "int",
        "DOUBLE": "double",
        "FLOAT": "float",
        "BOOLEAN": "boolean",
        "BIGINT": "bigint",
        "LONG": "bigint",
        "DATE": "date",
        "TIMESTAMP": "timestamp",
    }.get(type_name.upper(), "string")


def _load_brick_schema(schema_path: Path) -> list[dict[str, object]]:
    schema = []
    for col in parse_schema_file(schema_path):
        schema.append({
            "column": col["column"],
            "type": _spark_type_from_schema_type(col["type"]),
            "nullable": bool(col.get("nullable", True)),
            "comment": col.get("comment", ""),
        })
    return schema


def _load_brick_table_comment(ddt_ndarray_path: Path, brick_id: str) -> str:
    with ddt_ndarray_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row.get("ddt_ndarray_id") != brick_id:
                continue
            parts = [
                (row.get("ddt_ndarray_name") or "").strip(),
                (row.get("ddt_ndarray_description") or "").strip(),
            ]
            return " - ".join(part for part in parts if part)
    return ""


def _sql_string(value: str) -> str:
    return value.replace("'", "''")


def prepare(run_dir: Path, brick_id: str, out_dir: Path) -> dict[str, object]:
    data_dir = run_dir / "berdl_upload" / "data"
    schema_dir = run_dir / "berdl_upload" / "schema"
    table_schemas, table_comments_source = _load_table_metadata(run_dir)
    out_data = out_dir / "data"
    out_config = out_dir / "config"
    out_reports = out_dir / "reports"
    out_data.mkdir(parents=True, exist_ok=True)
    out_config.mkdir(parents=True, exist_ok=True)
    out_reports.mkdir(parents=True, exist_ok=True)

    asv_source = data_dir / "sdt_asv.tsv"
    if asv_source.exists():
        asv_rows = _copy_tsv_with_selected_columns(
            asv_source,
            out_data / "test_sdt_asv.tsv",
            [col["column"] for col in table_schemas.get("sdt_asv", ASV_SCHEMA)],
        )
    else:
        asv_rows = _write_test_sdt_asv(data_dir / "OTU.tsv", out_data / "test_sdt_asv.tsv")

    sys_oterm_schema = table_schemas.get("sys_oterm", [])
    for col in sys_oterm_schema:
        if col.get("column") == "sys_oterm_properties":
            col["comment"] = SYS_OTERM_PROPERTIES_COMMENT
    sys_oterm_columns = [col["column"] for col in sys_oterm_schema]
    sys_oterm_rows = _copy_tsv_with_selected_columns(
        data_dir / "sys_oterm.tsv",
        out_data / "test_sys_oterm.tsv",
        sys_oterm_columns,
    )

    brick_table = f"test_ddt_{brick_id.lower()}"
    brick_src = data_dir / f"{brick_id}.tsv"
    brick_schema = _load_brick_schema(schema_dir / f"{brick_id}_schema.py")
    brick_columns = [col["column"] for col in brick_schema]
    brick_rows = _copy_tsv_with_selected_columns(brick_src, out_data / f"{brick_table}.tsv", brick_columns)

    table_comments = {
        "test_sdt_asv": table_comments_source.get("sdt_asv", ASV_TABLE_COMMENT),
        "test_sys_oterm": table_comments_source.get("sys_oterm", "Ontology terms used in CORAL"),
        brick_table: _load_brick_table_comment(data_dir / "ddt_ndarray.tsv", brick_id),
    }
    schema = {
        "test_sdt_asv": table_schemas.get("sdt_asv", ASV_SCHEMA),
        "test_sys_oterm": sys_oterm_schema,
        brick_table: brick_schema,
    }
    ingest_config = {
        "tenant": "enigma",
        "dataset": "coral",
        "namespace": "enigma_coral",
        "mode": "overwrite",
        "file_ext": ".tsv",
        "delimiter": "\t",
        "notes": [
            "Mini-import only: test tables must be dropped after validation.",
            "Structured schema is used so data_lakehouse_ingest applies column comments.",
            "Table comments are emitted separately because the current ingest package only applies column comments.",
            "The static table schema and comments are generated from CORAL typedef.json.",
            "test_sys_oterm stores sys_oterm_properties as JSON STRING for BERDL ingest compatibility.",
        ],
        "tables": [
            {
                "name": table,
                "enabled": True,
                "local_path": str(out_data / f"{table}.tsv"),
                "format": "tsv",
                "schema": schema[table],
            }
            for table in ["test_sdt_asv", "test_sys_oterm", brick_table]
        ],
    }
    (out_config / "ingest_config.json").write_text(json.dumps(ingest_config, indent=2), encoding="utf-8")
    (out_config / "table_comments.json").write_text(json.dumps(table_comments, indent=2), encoding="utf-8")

    sql_lines = []
    for table, comment in table_comments.items():
        if comment:
            sql_lines.append(f"COMMENT ON TABLE enigma_coral.{table} IS '{_sql_string(comment)}';")
    sql_lines.extend([
        f"DROP TABLE IF EXISTS enigma_coral.test_sdt_asv;",
        f"DROP TABLE IF EXISTS enigma_coral.{brick_table};",
    ])
    (out_config / "post_ingest_table_comments_and_cleanup.sql").write_text(
        "\n".join(sql_lines) + "\n",
        encoding="utf-8",
    )

    report = {
        "run_dir": str(run_dir),
        "out_dir": str(out_dir),
        "tables": {
            "test_sdt_asv": {
                "rows": asv_rows,
                "columns": [col["column"] for col in schema["test_sdt_asv"]],
                "source": str(asv_source if asv_source.exists() else data_dir / "OTU.tsv"),
            },
            "test_sys_oterm": {
                "rows": sys_oterm_rows,
                "columns": sys_oterm_columns,
                "source": str(data_dir / "sys_oterm.tsv"),
            },
            brick_table: {
                "rows": brick_rows,
                "columns": brick_columns,
                "source": str(brick_src),
            },
        },
        "table_comments": table_comments,
    }
    (out_reports / "mini_import_summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--brick-id", default="Brick0000521")
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    out_dir = args.out_dir.resolve() if args.out_dir else run_dir / "mini_import"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    report = prepare(run_dir, args.brick_id, out_dir)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
