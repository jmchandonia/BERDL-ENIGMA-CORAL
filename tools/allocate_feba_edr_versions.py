#!/usr/bin/env python3
"""Allocate proposed EDR versions for FEBa genomes with no exact match."""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organism-manifest", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def next_version(active: list[int], withdrawn: list[int]) -> int:
    reserved = set(active) | set(withdrawn)
    proposed = max(reserved, default=0) + 1
    return 3 if proposed == 2 else proposed


def main() -> int:
    args = parse_args()
    with args.organism_manifest.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        columns = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    required = {
        "fitprivate_orgId", "sdt_strain_name", "edr_inventory_status",
        "edr_active_versions_json", "edr_withdrawn_versions_json",
        "exact_match_status", "allocated_edr_version", "target_coral_genome_name",
    }
    missing = required - set(columns)
    if missing:
        raise ValueError(f"Organism manifest is missing columns: {sorted(missing)}")

    allocations = []
    for row in rows:
        if row["edr_inventory_status"] != "complete":
            raise ValueError(f"EDR inventory is incomplete for {row['fitprivate_orgId']}")
        if row["exact_match_status"] not in {"no_assembly_match", "no_exact_match"}:
            raise ValueError(
                f"Exact-match decision is unresolved for {row['fitprivate_orgId']}: "
                f"{row['exact_match_status']}"
            )
        active = [int(value) for value in json.loads(row["edr_active_versions_json"])]
        withdrawn = [int(value) for value in json.loads(row["edr_withdrawn_versions_json"])]
        version_number = next_version(active, withdrawn)
        version_name = f"{row['sdt_strain_name']}.{version_number}"
        row["allocated_edr_version"] = version_name
        row["target_coral_genome_name"] = version_name
        allocations.append(
            {
                "fitprivate_orgId": row["fitprivate_orgId"],
                "sdt_strain_name": row["sdt_strain_name"],
                "active_versions": active,
                "withdrawn_versions": withdrawn,
                "allocated_version": version_number,
                "target_genome_name": version_name,
                "target_repository_directory": (
                    f"genome_processing/{row['sdt_strain_name']}/"
                    f"assembliesAndAnnotations/{version_name}/"
                ),
            }
        )

    temporary = args.organism_manifest.with_name(f".{args.organism_manifest.name}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, args.organism_manifest)
    report = {
        "allocated_at": datetime.now(timezone.utc).isoformat(),
        "status": "proposed_not_published",
        "allocations": allocations,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    report_temporary = args.report.with_name(f".{args.report.name}.tmp")
    report_temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    os.replace(report_temporary, args.report)
    print(json.dumps({"allocations": len(allocations), "status": report["status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
