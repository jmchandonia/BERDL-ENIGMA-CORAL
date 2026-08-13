#!/usr/bin/env python3
"""Compare downloaded EDR candidate assemblies with FEBa source fingerprints."""

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
    parser.add_argument("--download-report", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def update_digest(digest: Any, *values: object) -> None:
    for value in values:
        encoded = ("" if value is None else str(value)).encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)


def fasta_fingerprint(path: Path) -> tuple[str, int, int]:
    sequences: dict[str, list[str]] = {}
    current: str | None = None
    with path.open(encoding="ascii") as handle:
        for line_number, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                identifier = line[1:].split(None, 1)[0]
                if not identifier or identifier in sequences:
                    raise ValueError(
                        f"Invalid or duplicate FASTA ID at {path}:{line_number}"
                    )
                current = identifier
                sequences[current] = []
            elif current is None:
                raise ValueError(f"Sequence before FASTA header at {path}:{line_number}")
            else:
                sequences[current].append("".join(line.split()).upper())
    if not sequences:
        raise ValueError(f"FASTA contains no sequences: {path}")
    digest = hashlib.sha256()
    total_bases = 0
    for identifier in sorted(sequences):
        sequence = "".join(sequences[identifier])
        total_bases += len(sequence)
        update_digest(digest, "scaffold", identifier, sequence)
    return digest.hexdigest(), len(sequences), total_bases


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def write_tsv_atomic(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def main() -> int:
    args = parse_args()
    columns, manifest_rows = read_tsv(args.organism_manifest)
    required = {
        "fitprivate_orgId",
        "sdt_strain_name",
        "source_assembly_sha256",
        "exact_match_status",
        "exact_match_location",
    }
    missing = required - set(columns)
    if missing:
        raise ValueError(f"Organism manifest is missing columns: {sorted(missing)}")

    downloads = json.loads(args.download_report.read_text(encoding="utf-8"))["completed"]
    fasta_by_strain: dict[str, list[dict[str, Any]]] = {}
    for row in downloads:
        if row["filename"].endswith("_contigs.fasta"):
            fasta_by_strain.setdefault(row["strain"], []).append(row)

    checked_at = datetime.now(timezone.utc).isoformat()
    details: list[dict[str, Any]] = []
    for manifest_row in manifest_rows:
        strain = manifest_row["sdt_strain_name"]
        candidates = fasta_by_strain.get(strain, [])
        if not candidates:
            raise ValueError(f"No downloaded candidate FASTA for {strain}")
        comparisons = []
        assembly_matches = []
        for candidate in sorted(candidates, key=lambda row: (row["scope"], row["version"])):
            fingerprint, scaffold_count, total_bases = fasta_fingerprint(
                Path(candidate["destination"])
            )
            comparison = {
                "scope": candidate["scope"],
                "version": candidate["version"],
                "path": candidate["destination"],
                "fasta_sha256": candidate["sha256"],
                "assembly_fingerprint": fingerprint,
                "scaffold_count": scaffold_count,
                "total_bases": total_bases,
                "matches_source_assembly": fingerprint
                == manifest_row["source_assembly_sha256"],
            }
            comparisons.append(comparison)
            if comparison["matches_source_assembly"]:
                assembly_matches.append(comparison)
        if assembly_matches:
            manifest_row["exact_match_status"] = "annotation_comparison_pending"
            manifest_row["exact_match_location"] = json.dumps(
                [f"{row['scope']}/{row['version']}" for row in assembly_matches]
            )
        else:
            manifest_row["exact_match_status"] = "no_assembly_match"
            manifest_row["exact_match_location"] = ""
        details.append(
            {
                "fitprivate_orgId": manifest_row["fitprivate_orgId"],
                "sdt_strain_name": strain,
                "source_assembly_fingerprint": manifest_row["source_assembly_sha256"],
                "candidate_count": len(comparisons),
                "assembly_match_count": len(assembly_matches),
                "comparisons": comparisons,
            }
        )

    write_tsv_atomic(args.organism_manifest, columns, manifest_rows)
    report = {
        "checked_at": checked_at,
        "organisms": len(manifest_rows),
        "candidate_assemblies": sum(row["candidate_count"] for row in details),
        "organisms_with_assembly_match": sum(
            row["assembly_match_count"] > 0 for row in details
        ),
        "details": details,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.report.with_name(f".{args.report.name}.tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, args.report)
    print(
        json.dumps(
            {key: report[key] for key in ("organisms", "candidate_assemblies", "organisms_with_assembly_match")},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
