#!/usr/bin/env python3
"""Verify proposed FEBa EDR versions against a refreshed bounded inventory."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organism-manifest", required=True, type=Path)
    parser.add_argument("--version-inventory", required=True, type=Path)
    parser.add_argument("--prefix-listings", required=True, type=Path)
    parser.add_argument("--active-manifest", required=True, type=Path)
    parser.add_argument("--withdrawn-manifest", required=True, type=Path)
    parser.add_argument("--export-preflight", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def next_version(active: list[int], withdrawn: list[int]) -> int:
    proposed = max(set(active) | set(withdrawn), default=0) + 1
    return 3 if proposed == 2 else proposed


def listed_versions(path: Path) -> set[tuple[str, str, str]]:
    values = set()
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            record = json.loads(raw)
            result = record.get("mc_result")
            if not isinstance(result, dict) or result.get("type") != "folder":
                continue
            key = str(result.get("key", "")).rstrip("/")
            if key:
                values.add((str(record["scope"]), str(record["strain"]), key))
    return values


def main() -> int:
    args = parse_args()
    with args.organism_manifest.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    inventory = json.loads(args.version_inventory.read_text(encoding="utf-8"))
    inventory_by_org = {row["fitprivate_orgId"]: row for row in inventory["details"]}
    existing = listed_versions(args.prefix_listings)
    export = json.loads(args.export_preflight.read_text(encoding="utf-8"))
    exports_by_org = {row["fitprivate_orgId"]: row for row in export["exports"]}

    checks: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for row in rows:
        org_id = row["fitprivate_orgId"]
        strain = row["sdt_strain_name"]
        target = row["allocated_edr_version"]
        prefix = strain + "."
        if not target.startswith(prefix) or not target[len(prefix):].isdigit():
            raise ValueError(f"Invalid allocated version {target!r} for {org_id}")
        target_number = int(target[len(prefix):])
        current = inventory_by_org[org_id]
        expected_number = next_version(
            current["active_versions"], current["withdrawn_versions"]
        )
        path_collisions = sorted(
            scope
            for scope in ("genome_processing", "genome_processing_withdrawn")
            if (scope, strain, target) in existing
        )
        export_row = exports_by_org.get(org_id)
        file_checks = []
        if export_row:
            for filename, metadata in sorted(export_row["files"].items()):
                path = Path(export_row["local_directory"]) / filename
                file_checks.append(
                    {
                        "filename": filename,
                        "exists": path.is_file(),
                        "expected_bytes": metadata["bytes"],
                        "actual_bytes": path.stat().st_size if path.is_file() else None,
                        "expected_sha256": metadata["sha256"],
                        "actual_sha256": sha256_file(path) if path.is_file() else None,
                    }
                )
        reasons = []
        if target_number != expected_number:
            reasons.append(
                f"allocated version {target_number} is not current next version {expected_number}"
            )
        if path_collisions:
            reasons.append(f"target path exists in {path_collisions}")
        if export_row is None:
            reasons.append("missing export preflight row")
        for item in file_checks:
            if not item["exists"]:
                reasons.append(f"missing local export {item['filename']}")
            elif item["actual_bytes"] != item["expected_bytes"]:
                reasons.append(f"size mismatch for {item['filename']}")
            elif item["actual_sha256"] != item["expected_sha256"]:
                reasons.append(f"checksum mismatch for {item['filename']}")
        check = {
            "fitprivate_orgId": org_id,
            "sdt_strain_name": strain,
            "active_versions": current["active_versions"],
            "withdrawn_versions": current["withdrawn_versions"],
            "allocated_version": target,
            "expected_next_version": expected_number,
            "path_collisions": path_collisions,
            "files": file_checks,
            "status": "passed" if not reasons else "failed",
            "failure_reasons": reasons,
        }
        checks.append(check)
        if reasons:
            failures.append(check)

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed_awaiting_publication_approval" if not failures else "failed",
        "active_manifest": {
            "path": str(args.active_manifest.resolve()),
            "bytes": args.active_manifest.stat().st_size,
            "sha256": sha256_file(args.active_manifest),
        },
        "withdrawn_manifest": {
            "path": str(args.withdrawn_manifest.resolve()),
            "bytes": args.withdrawn_manifest.stat().st_size,
            "sha256": sha256_file(args.withdrawn_manifest),
        },
        "organisms": len(checks),
        "passed": len(checks) - len(failures),
        "failures": failures,
        "checks": checks,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.report.with_name(f".{args.report.name}.tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, args.report)
    print(
        json.dumps(
            {key: report[key] for key in ("status", "organisms", "passed")},
            indent=2,
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
