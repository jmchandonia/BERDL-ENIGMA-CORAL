#!/usr/bin/env python3
"""Populate FEBa work-manifest version history from bounded EDR inventories."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organism-manifest", required=True, type=Path)
    parser.add_argument("--phase0-metadata", type=Path)
    parser.add_argument("--active-manifest", required=True, type=Path)
    parser.add_argument("--withdrawn-manifest", required=True, type=Path)
    parser.add_argument(
        "--active-object-keys",
        type=Path,
        help="Optional bounded mc JSONL/plain listing for active candidate prefixes",
    )
    parser.add_argument(
        "--withdrawn-object-keys",
        type=Path,
        help="Optional bounded mc JSONL/plain listing for withdrawn candidate prefixes",
    )
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError(f"TSV has no header: {path}")
        return list(reader.fieldnames), [dict(row) for row in reader]


def write_tsv_atomic(path: Path, columns: list[str], rows: Iterable[dict[str, str]]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def listing_text(path: Path | None, scope: str | None = None) -> str:
    if path is None:
        return ""
    values: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                values.append(line)
                continue
            if (
                scope is not None
                and isinstance(parsed, dict)
                and parsed.get("scope") is not None
                and parsed.get("scope") != scope
            ):
                continue
            collect_listing_values(parsed, values)
    return "\n".join(values)


def collect_listing_values(value: Any, output: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"key", "name", "path", "url", "prefix"} and child:
                output.append(str(child))
            collect_listing_values(child, output)
    elif isinstance(value, list):
        for child in value:
            collect_listing_values(child, output)


def versions_for_strain(text: str, strain_name: str) -> list[int]:
    pattern = re.compile(re.escape(strain_name) + r"\.(\d+)(?!\d)")
    return sorted({int(match.group(1)) for match in pattern.finditer(text)})


def require_columns(columns: list[str], required: Iterable[str]) -> None:
    missing = set(required) - set(columns)
    if missing:
        raise ValueError(f"Organism manifest is missing columns: {sorted(missing)}")


def main() -> int:
    args = parse_args()
    columns, rows = read_tsv(args.organism_manifest)
    require_columns(
        columns,
        (
            "fitprivate_orgId",
            "sdt_strain_name",
            "edr_inventory_status",
            "edr_inventory_checked_at",
            "edr_active_versions_json",
            "edr_withdrawn_versions_json",
        ),
    )
    active_manifest_text = args.active_manifest.read_text(encoding="utf-8", errors="replace")
    withdrawn_manifest_text = args.withdrawn_manifest.read_text(
        encoding="utf-8", errors="replace"
    )
    active_object_text = listing_text(args.active_object_keys, "genome_processing")
    withdrawn_object_text = listing_text(
        args.withdrawn_object_keys, "genome_processing_withdrawn"
    )
    checked_at = datetime.now(timezone.utc).isoformat()

    details: list[dict[str, Any]] = []
    for row in rows:
        strain = row["sdt_strain_name"]
        active_manifest_versions = versions_for_strain(active_manifest_text, strain)
        active_object_versions = versions_for_strain(active_object_text, strain)
        withdrawn_manifest_versions = versions_for_strain(withdrawn_manifest_text, strain)
        withdrawn_object_versions = versions_for_strain(withdrawn_object_text, strain)
        active_versions = sorted(set(active_manifest_versions) | set(active_object_versions))
        withdrawn_versions = sorted(
            set(withdrawn_manifest_versions) | set(withdrawn_object_versions)
        )
        row["edr_inventory_status"] = "complete"
        row["edr_inventory_checked_at"] = checked_at
        row["edr_active_versions_json"] = json.dumps(active_versions)
        row["edr_withdrawn_versions_json"] = json.dumps(withdrawn_versions)
        details.append(
            {
                "fitprivate_orgId": row["fitprivate_orgId"],
                "sdt_strain_name": strain,
                "active_manifest_versions": active_manifest_versions,
                "active_object_versions": active_object_versions,
                "active_versions": active_versions,
                "withdrawn_manifest_versions": withdrawn_manifest_versions,
                "withdrawn_object_versions": withdrawn_object_versions,
                "withdrawn_versions": withdrawn_versions,
            }
        )

    write_tsv_atomic(args.organism_manifest, columns, rows)
    report = {
        "checked_at": checked_at,
        "active_manifest": str(args.active_manifest.resolve()),
        "withdrawn_manifest": str(args.withdrawn_manifest.resolve()),
        "active_object_keys": (
            str(args.active_object_keys.resolve()) if args.active_object_keys else None
        ),
        "withdrawn_object_keys": (
            str(args.withdrawn_object_keys.resolve())
            if args.withdrawn_object_keys
            else None
        ),
        "organisms": len(rows),
        "details": details,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.report.with_name(f".{args.report.name}.tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, args.report)
    if args.phase0_metadata:
        metadata = json.loads(args.phase0_metadata.read_text(encoding="utf-8"))
        metadata["live_edr_inventory"] = "complete"
        metadata["live_edr_inventory_checked_at"] = checked_at
        metadata["live_edr_inventory_report"] = str(args.report.resolve())
        metadata_temporary = args.phase0_metadata.with_name(
            f".{args.phase0_metadata.name}.tmp"
        )
        metadata_temporary.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(metadata_temporary, args.phase0_metadata)
    print(json.dumps({"organisms": len(rows), "checked_at": checked_at}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
