#!/usr/bin/env python3
"""Validate staged FEBa genomes and generate EDR manifest rows."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
DEFAULT_GENOMES = SCRIPT_DIR / "genomes_to_record.tsv"
DEFAULT_ACTIVE_MANIFEST = SCRIPT_DIR / "evidence" / "genome_annotations_manifest.tsv"
DEFAULT_WITHDRAWN_MANIFEST = (
    SCRIPT_DIR / "evidence" / "genome_annotations_withdrawn_manifest.tsv"
)
DEFAULT_OUTPUT = PACKAGE_ROOT / "manifest_rows.generated.tsv"


REQUIRED_COLUMNS = (
    "fitprivate_orgId",
    "strain",
    "genome_name",
    "version",
    "fasta_relative_path",
    "fasta_bytes",
    "fasta_sha256",
    "gff_relative_path",
    "gff_bytes",
    "gff_sha256",
    "manifest_date",
    "manifest_method",
    "manifest_inputs",
    "active_versions_json",
    "withdrawn_versions_json",
    "all_previously_used_versions_json",
    "expected_next_version",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--genomes", type=Path, default=DEFAULT_GENOMES)
    parser.add_argument("--genome-root", type=Path)
    parser.add_argument("--active-manifest", type=Path, default=DEFAULT_ACTIVE_MANIFEST)
    parser.add_argument(
        "--withdrawn-manifest", type=Path, default=DEFAULT_WITHDRAWN_MANIFEST
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate all inputs without writing generated manifest rows",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_genomes(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Genome input TSV is missing columns: {sorted(missing)}")
        rows = [dict(row) for row in reader]
    if not rows:
        raise ValueError("Genome input TSV contains no rows")
    for column in ("fitprivate_orgId", "strain", "genome_name"):
        values = [row[column] for row in rows]
        if len(values) != len(set(values)):
            raise ValueError(f"Genome input TSV contains duplicate {column}")
    return rows


def resolve_genome_root(argument: Path | None) -> Path:
    if argument is not None:
        return argument.resolve()
    packaged = PACKAGE_ROOT / "genome_annotations"
    return packaged if packaged.is_dir() else PACKAGE_ROOT


def manifest_contains_version(text: str, strain: str, genome_name: str) -> bool:
    expected_prefix = strain + "."
    if not genome_name.startswith(expected_prefix):
        raise ValueError(f"Genome name {genome_name!r} does not belong to {strain!r}")
    return re.search(re.escape(genome_name) + r"(?!\d)", text) is not None


def validate_and_build(
    rows: list[dict[str, str]],
    genome_root: Path,
    active_manifest_text: str,
    withdrawn_manifest_text: str,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    manifest_rows = []
    checks = []
    for row in rows:
        strain = row["strain"]
        genome_name = row["genome_name"]
        version = int(row["version"])
        expected_name = f"{strain}.{version}"
        if genome_name != expected_name:
            raise ValueError(
                f"Genome name mismatch for {row['fitprivate_orgId']}: "
                f"{genome_name} != {expected_name}"
            )
        active_versions = [int(value) for value in json.loads(row["active_versions_json"])]
        withdrawn_versions = [
            int(value) for value in json.loads(row["withdrawn_versions_json"])
        ]
        all_previous = [
            int(value) for value in json.loads(row["all_previously_used_versions_json"])
        ]
        expected_next = int(row["expected_next_version"])
        if sorted(set(active_versions) | set(withdrawn_versions)) != sorted(set(all_previous)):
            raise ValueError(f"Inconsistent version history for {row['fitprivate_orgId']}")
        if version in all_previous or version != expected_next:
            raise ValueError(
                f"Unsafe staged version for {row['fitprivate_orgId']}: "
                f"version={version}, prior={all_previous}, expected={expected_next}"
            )
        if manifest_contains_version(active_manifest_text, strain, genome_name):
            raise ValueError(f"Version already occurs in active manifest: {genome_name}")
        if manifest_contains_version(withdrawn_manifest_text, strain, genome_name):
            raise ValueError(f"Version already occurs in withdrawn manifest: {genome_name}")

        file_checks = []
        for kind in ("fasta", "gff"):
            relative = Path(row[f"{kind}_relative_path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Unsafe relative path for {genome_name}: {relative}")
            path = genome_root / relative
            expected_bytes = int(row[f"{kind}_bytes"])
            expected_sha256 = row[f"{kind}_sha256"]
            if not path.is_file():
                raise ValueError(f"Missing staged {kind.upper()} file: {path}")
            actual_bytes = path.stat().st_size
            actual_sha256 = sha256_file(path)
            if actual_bytes != expected_bytes or actual_sha256 != expected_sha256:
                raise ValueError(f"Staged file integrity failure: {path}")
            file_checks.append(
                {
                    "kind": kind,
                    "path": str(path),
                    "bytes": actual_bytes,
                    "sha256": actual_sha256,
                }
            )

        manifest_rows.append(
            {
                "Isolate ID": strain,
                "Date": row["manifest_date"],
                "Data Type": "Genome",
                "File Name": row["gff_relative_path"],
                "Method": row["manifest_method"],
                "Inputs": row["manifest_inputs"],
            }
        )
        checks.append(
            {
                "fitprivate_orgId": row["fitprivate_orgId"],
                "genome_name": genome_name,
                "status": "passed",
                "files": file_checks,
            }
        )
    return manifest_rows, checks


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["Isolate ID", "Date", "Data Type", "File Name", "Method", "Inputs"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def main() -> int:
    args = parse_args()
    rows = read_genomes(args.genomes)
    genome_root = resolve_genome_root(args.genome_root)
    active_text = args.active_manifest.read_text(encoding="utf-8", errors="replace")
    withdrawn_text = args.withdrawn_manifest.read_text(
        encoding="utf-8", errors="replace"
    )
    manifest_rows, checks = validate_and_build(
        rows, genome_root, active_text, withdrawn_text
    )
    if not args.check_only:
        write_manifest(args.output, manifest_rows)
    print(
        json.dumps(
            {
                "status": "passed",
                "genomes": len(checks),
                "manifest_rows": len(manifest_rows),
                "genomes_input": str(args.genomes.resolve()),
                "genome_root": str(genome_root),
                "active_manifest": str(args.active_manifest.resolve()),
                "withdrawn_manifest": str(args.withdrawn_manifest.resolve()),
                "output": None if args.check_only else str(args.output.resolve()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
