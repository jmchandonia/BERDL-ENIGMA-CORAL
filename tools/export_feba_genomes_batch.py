#!/usr/bin/env python3
"""Export all allocated FEBa genomes and build an EDR publication preflight."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--database-sha256", required=True)
    parser.add_argument("--organism-manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def split_version(strain: str, allocated: str) -> int:
    prefix = strain + "."
    if not allocated.startswith(prefix) or not allocated[len(prefix):].isdigit():
        raise ValueError(f"Invalid allocated version {allocated!r} for strain {strain!r}")
    return int(allocated[len(prefix):])


def main() -> int:
    args = parse_args()
    with args.organism_manifest.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        columns = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    exporter = Path(__file__).with_name("export_feba_genome.py")
    exports = []
    for row in rows:
        strain = row["sdt_strain_name"]
        allocated = row["allocated_edr_version"]
        version = split_version(strain, allocated)
        destination = (
            args.output_dir / "genome_processing" / strain
            / "assembliesAndAnnotations" / allocated
        )
        manifest_path = destination / f"{allocated}_export_manifest.json"
        command = [
            sys.executable, str(exporter), str(args.database), row["fitprivate_orgId"],
            str(destination), "--strain-name", strain, "--genome-version", str(version),
            "--source-database-sha256", args.database_sha256,
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"Genome export failed for {row['fitprivate_orgId']}: "
                f"{result.stderr[:3000]}"
            )
        if not manifest_path.is_file():
            raise ValueError(f"Exporter did not create manifest: {manifest_path}")
        export_manifest = json.loads(manifest_path.read_text(encoding="ascii"))
        if export_manifest["output_validation"]["status"] != "passed":
            raise ValueError(f"Export validation failed for {row['fitprivate_orgId']}")
        row["export_status"] = "complete"
        exports.append(
            {
                "fitprivate_orgId": row["fitprivate_orgId"],
                "sdt_strain_name": strain,
                "target_genome_name": allocated,
                "target_repository_directory": (
                    f"genome_processing/{strain}/assembliesAndAnnotations/{allocated}/"
                ),
                "local_directory": str(destination.resolve()),
                "manifest": str(manifest_path.resolve()),
                "scaffolds": export_manifest["scaffolds"],
                "total_bases": export_manifest["total_bases"],
                "source_gene_rows": export_manifest["source_gene_rows"],
                "files": export_manifest["files"],
                "validation": export_manifest["output_validation"],
            }
        )

    temporary = args.organism_manifest.with_name(f".{args.organism_manifest.name}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, args.organism_manifest)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "local_exports_complete_not_published",
        "source_database": str(args.database.resolve()),
        "source_database_sha256": args.database_sha256.lower(),
        "exports": exports,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    report_temporary = args.report.with_name(f".{args.report.name}.tmp")
    report_temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    os.replace(report_temporary, args.report)
    print(json.dumps({"exports": len(exports), "status": report["status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
