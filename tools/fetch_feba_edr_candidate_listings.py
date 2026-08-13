#!/usr/bin/env python3
"""Fetch bounded MinIO directory listings for the selected FEBa strains."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ROOT = (
    "berdl-minio/cdm-lake/tenant-general-warehouse/enigma/datasets/"
    "enigma-data-repository"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organism-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--minio-root", default=DEFAULT_ROOT)
    parser.add_argument("--https-proxy", default="http://127.0.0.1:8123")
    return parser.parse_args()


def read_strains(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    strains = [row["sdt_strain_name"] for row in rows]
    if not strains or len(strains) != len(set(strains)):
        raise ValueError("Organism manifest must contain nonempty unique strains")
    return sorted(strains)


def main() -> int:
    args = parse_args()
    strains = read_strains(args.organism_manifest)
    environment = os.environ.copy()
    environment["https_proxy"] = args.https_proxy
    environment["no_proxy"] = "localhost,127.0.0.1"
    checked_at = datetime.now(timezone.utc).isoformat()
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for scope in ("genome_processing", "genome_processing_withdrawn"):
        for strain in strains:
            prefix = (
                f"{args.minio_root.rstrip('/')}/{scope}/{strain}/"
                "assembliesAndAnnotations/"
            )
            result = subprocess.run(
                ["mc", "ls", "--json", prefix],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            parsed_lines = []
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid mc JSON for {prefix}: {line[:500]}") from exc
                parsed_lines.append(payload)
                records.append(
                    {
                        "scope": scope,
                        "strain": strain,
                        "prefix": prefix,
                        "mc_result": payload,
                    }
                )
            if result.returncode != 0:
                failures.append(
                    {
                        "scope": scope,
                        "strain": strain,
                        "prefix": prefix,
                        "returncode": result.returncode,
                        "stderr": result.stderr.strip()[:1000],
                    }
                )
            elif not parsed_lines:
                records.append(
                    {
                        "scope": scope,
                        "strain": strain,
                        "prefix": prefix,
                        "mc_result": None,
                    }
                )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(f".{args.output.name}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    os.replace(temporary, args.output)

    report = {
        "checked_at": checked_at,
        "minio_root": args.minio_root,
        "strains": len(strains),
        "prefixes_checked": len(strains) * 2,
        "listing_records": len(records),
        "failures": failures,
    }
    report_temporary = args.report.with_name(f".{args.report.name}.tmp")
    report_temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    os.replace(report_temporary, args.report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
