#!/usr/bin/env python3
"""Stage a locally inspectable FEBa EDR production checkout package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


METHOD_PATH = "genomes_from_feba/record_feba_genomes_260812.py"
GENOMES_INPUT_PATH = "genomes_from_feba/genomes_to_record.tsv"
EVIDENCE_PATH = "genomes_from_feba/evidence"
DATABASE_SHA256 = "6b9e4edce230b2f82bff90242fe9ca46219598905d2eb775ab4f16ea446a1f11"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organism-manifest", required=True, type=Path)
    parser.add_argument("--version-inventory", required=True, type=Path)
    parser.add_argument("--export-preflight", required=True, type=Path)
    parser.add_argument("--active-manifest", required=True, type=Path)
    parser.add_argument("--withdrawn-manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--manifest-date", default="2026-08-12")
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


def target_number(strain: str, target: str) -> int:
    prefix = strain + "."
    if not target.startswith(prefix) or not target[len(prefix):].isdigit():
        raise ValueError(f"Invalid allocated genome name {target!r} for {strain!r}")
    return int(target[len(prefix):])


def write_tsv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=columns, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise SystemExit(f"Refusing to overwrite existing checkout: {args.output_dir}")

    with args.organism_manifest.open(newline="", encoding="utf-8") as handle:
        organisms = list(csv.DictReader(handle, delimiter="\t"))
    inventory_payload = json.loads(args.version_inventory.read_text(encoding="utf-8"))
    inventory = {
        row["fitprivate_orgId"]: row for row in inventory_payload["details"]
    }
    export_payload = json.loads(args.export_preflight.read_text(encoding="utf-8"))
    exports = {row["fitprivate_orgId"]: row for row in export_payload["exports"]}

    args.output_dir.mkdir(parents=True)
    manifest_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    genomes_input_rows: list[dict[str, Any]] = []
    staged: list[dict[str, Any]] = []

    for organism in organisms:
        org_id = organism["fitprivate_orgId"]
        strain = organism["sdt_strain_name"]
        target = organism["allocated_edr_version"]
        proposed = target_number(strain, target)
        history = inventory.get(org_id)
        export = exports.get(org_id)
        if history is None or export is None:
            raise ValueError(f"Missing inventory or export evidence for {org_id}")

        active_manifest = [int(value) for value in history["active_manifest_versions"]]
        active_objects = [int(value) for value in history["active_object_versions"]]
        withdrawn_manifest = [
            int(value) for value in history["withdrawn_manifest_versions"]
        ]
        withdrawn_objects = [
            int(value) for value in history["withdrawn_object_versions"]
        ]
        active = sorted(set(active_manifest) | set(active_objects))
        withdrawn = sorted(set(withdrawn_manifest) | set(withdrawn_objects))
        previously_used = proposed in set(active) | set(withdrawn)
        expected = next_version(active, withdrawn)
        if previously_used or proposed != expected:
            raise ValueError(
                f"Unsafe version for {org_id}: proposed={proposed}, expected={expected}, "
                f"active={active}, withdrawn={withdrawn}"
            )

        destination = (
            args.output_dir
            / "genome_annotations"
            / strain
            / "assembliesAndAnnotations"
            / target
        )
        destination.mkdir(parents=True)
        copied_files = []
        for filename, expected_metadata in sorted(export["files"].items()):
            if filename not in {f"{strain}_contigs.fasta", f"{strain}_Prodigal.gff"}:
                raise ValueError(f"Unexpected production file for {org_id}: {filename}")
            source = Path(export["local_directory"]) / filename
            if not source.is_file():
                raise ValueError(f"Missing validated export file: {source}")
            if source.stat().st_size != int(expected_metadata["bytes"]):
                raise ValueError(f"Export size changed: {source}")
            if sha256_file(source) != expected_metadata["sha256"]:
                raise ValueError(f"Export checksum changed: {source}")
            output = destination / filename
            shutil.copy2(source, output)
            copied_files.append(
                {
                    "relative_path": output.relative_to(args.output_dir).as_posix(),
                    "bytes": output.stat().st_size,
                    "sha256": sha256_file(output),
                }
            )

        manifest_rows.append(
            {
                "Isolate ID": strain,
                "Date": args.manifest_date,
                "Data Type": "Genome",
                "File Name": (
                    f"{strain}/assembliesAndAnnotations/{target}/"
                    f"{strain}_Prodigal.gff"
                ),
                "Method": METHOD_PATH,
                "Inputs": (
                    f"enigma.fitprivate feba.db SHA-256 {DATABASE_SHA256}; "
                    f"orgId={org_id}"
                ),
            }
        )
        audit_rows.append(
            {
                "fitprivate_orgId": org_id,
                "strain": strain,
                "active_manifest_versions": json.dumps(active_manifest),
                "active_object_versions": json.dumps(active_objects),
                "withdrawn_manifest_versions": json.dumps(withdrawn_manifest),
                "withdrawn_object_versions": json.dumps(withdrawn_objects),
                "all_previously_used_versions": json.dumps(
                    sorted(set(active) | set(withdrawn))
                ),
                "proposed_version": proposed,
                "expected_next_version": expected,
                "proposed_previously_used": "no",
                "status": "passed",
            }
        )
        staged.append(
            {
                "fitprivate_orgId": org_id,
                "strain": strain,
                "target_genome_name": target,
                "files": copied_files,
            }
        )
        files_by_name = {
            Path(item["relative_path"]).name: item for item in copied_files
        }
        fasta = files_by_name[f"{strain}_contigs.fasta"]
        gff = files_by_name[f"{strain}_Prodigal.gff"]
        genomes_input_rows.append(
            {
                "fitprivate_orgId": org_id,
                "strain": strain,
                "genome_name": target,
                "version": proposed,
                "fasta_relative_path": Path(fasta["relative_path"])
                .relative_to("genome_annotations")
                .as_posix(),
                "fasta_bytes": fasta["bytes"],
                "fasta_sha256": fasta["sha256"],
                "gff_relative_path": Path(gff["relative_path"])
                .relative_to("genome_annotations")
                .as_posix(),
                "gff_bytes": gff["bytes"],
                "gff_sha256": gff["sha256"],
                "manifest_date": args.manifest_date,
                "manifest_method": METHOD_PATH,
                "manifest_inputs": (
                    f"enigma.fitprivate feba.db SHA-256 {DATABASE_SHA256}; "
                    f"orgId={org_id}"
                ),
                "active_versions_json": json.dumps(active),
                "withdrawn_versions_json": json.dumps(withdrawn),
                "all_previously_used_versions_json": json.dumps(
                    sorted(set(active) | set(withdrawn))
                ),
                "expected_next_version": expected,
            }
        )

    write_tsv(
        args.output_dir / "manifest_rows.tsv",
        ["Isolate ID", "Date", "Data Type", "File Name", "Method", "Inputs"],
        manifest_rows,
    )
    write_tsv(
        args.output_dir / "historical_version_audit.tsv",
        [
            "fitprivate_orgId",
            "strain",
            "active_manifest_versions",
            "active_object_versions",
            "withdrawn_manifest_versions",
            "withdrawn_object_versions",
            "all_previously_used_versions",
            "proposed_version",
            "expected_next_version",
            "proposed_previously_used",
            "status",
        ],
        audit_rows,
    )
    write_tsv(
        args.output_dir / GENOMES_INPUT_PATH,
        [
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
        ],
        genomes_input_rows,
    )

    method_script = args.output_dir / METHOD_PATH
    method_script.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__).with_name("record_feba_genomes_260812.py"), method_script)
    evidence_dir = args.output_dir / EVIDENCE_PATH
    evidence_dir.mkdir(parents=True)
    evidence_files = {
        "genome_annotations_manifest.tsv": args.active_manifest,
        "genome_annotations_withdrawn_manifest.tsv": args.withdrawn_manifest,
        "edr_version_inventory_report.json": args.version_inventory,
        "feba_edr_export_preflight.json": args.export_preflight,
    }
    for output_name, source in evidence_files.items():
        if not source.is_file():
            raise ValueError(f"Missing evidence input: {source}")
        shutil.copy2(source, evidence_dir / output_name)
    method_readme = method_script.parent / "README.md"
    method_readme.write_text(
        "# FEBa genome manifest recorder\n\n"
        "`record_feba_genomes_260812.py` is self-contained within this handoff. "
        "With no arguments, it reads `genomes_to_record.tsv`, validates the 22 "
        "staged FASTA/GFF pairs and allocated versions against the frozen active "
        "and withdrawn manifest snapshots under `evidence/`, and writes "
        "`../manifest_rows.generated.tsv`. It never edits a production manifest.\n\n"
        "From the package root:\n\n"
        "```bash\n"
        "python3 genomes_from_feba/record_feba_genomes_260812.py --check-only\n"
        "python3 genomes_from_feba/record_feba_genomes_260812.py\n"
        "cmp manifest_rows.tsv manifest_rows.generated.tsv\n"
        "```\n\n"
        "Immediately before production transfer, supply newly fetched manifest "
        "snapshots with `--active-manifest` and `--withdrawn-manifest` so a newly "
        "allocated conflicting version fails validation.\n",
        encoding="utf-8",
    )
    readme = args.output_dir / "README.md"
    readme.write_text(
        "# FEBa genome annotation production checkout\n\n"
        "This package contains 22 locally staged ENIGMA isolate genome versions. "
        "It has not been uploaded or published.\n\n"
        "- `genome_annotations/` contains the production-facing genome directories.\n"
        "- `manifest_rows.tsv` contains one GFF-referencing Genome row per version.\n"
        "- `genomes_from_feba/genomes_to_record.tsv` is the default 22-genome "
        "input to the staged recorder script.\n"
        "- `genomes_from_feba/evidence/` contains the frozen active/withdrawn "
        "manifest snapshots and compact reports used to construct that input.\n"
        "- `historical_version_audit.tsv` proves each proposed number was absent from "
        "both active and withdrawn manifests and object listings.\n"
        "- `checksums.sha256` verifies every staged file.\n\n"
        "Run `python3 genomes_from_feba/record_feba_genomes_260812.py "
        "--check-only` from this directory to validate all default inputs. Re-run "
        "against newly fetched live active/withdrawn manifests immediately before "
        "moving this package into production.\n",
        encoding="utf-8",
    )

    checksum_targets = sorted(
        path
        for path in args.output_dir.rglob("*")
        if path.is_file() and path.name not in {"checksums.sha256", "package_manifest.json"}
    )
    checksum_path = args.output_dir / "checksums.sha256"
    checksum_path.write_text(
        "".join(
            f"{sha256_file(path)}  {path.relative_to(args.output_dir).as_posix()}\n"
            for path in checksum_targets
        ),
        encoding="utf-8",
    )
    package = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "staged_locally_not_published",
        "organisms": len(staged),
        "manifest_rows": len(manifest_rows),
        "version_audit_rows": len(audit_rows),
        "active_and_withdrawn_version_checks_passed": all(
            row["status"] == "passed" for row in audit_rows
        ),
        "source_database_sha256": DATABASE_SHA256,
        "genomes_input": GENOMES_INPUT_PATH,
        "method": METHOD_PATH,
        "evidence": [
            f"{EVIDENCE_PATH}/{name}" for name in sorted(evidence_files)
        ],
        "checksums_sha256": sha256_file(checksum_path),
        "staged": staged,
    }
    (args.output_dir / "package_manifest.json").write_text(
        json.dumps(package, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": package["status"],
                "organisms": package["organisms"],
                "manifest_rows": package["manifest_rows"],
                "output_dir": str(args.output_dir.resolve()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
