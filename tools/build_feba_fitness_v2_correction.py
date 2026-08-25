#!/usr/bin/env python3
"""Build export-compatible replacements for the 22 FEBa fitness bricks.

The source bricks already contain the complete gene-by-condition fit and t
matrices. This correction preserves those dimensions and values, adds CORAL's
required heterogeneous-array marker, assigns new immutable brick names, and
stages one-to-one Update Data process rows.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterable, Sequence

import build_feba_coral_import as base


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PACKAGE = ROOT / "coral_import/feba_20260811/coral_package_20260813"
DEFAULT_OUTPUT = ROOT / "coral_import/feba_20260811/fitness_brick_v2_20260825"
CORRECTION_DATE = "2026-08-25"
DATE_STAMP = "20260825"
EXPECTED_BRICKS = 22
EXPECTED_CELLS = 16_292_891
PROCESS_FIELDS = [
    "process",
    "person",
    "campaign",
    "protocol",
    "date_start",
    "date_end",
    "input_objects",
    "output_objects",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-package", type=Path, default=SOURCE_PACKAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-checkgeneric", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, fieldnames: Sequence[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def new_brick_name(old_name: str) -> str:
    suffix = ".ndarray"
    if not old_name.endswith(suffix):
        raise ValueError(f"Unexpected source brick name: {old_name}")
    return f"{old_name.removesuffix(suffix)}_v2{suffix}"


def values_length(typed_value: dict[str, Any]) -> int:
    values = typed_value["values"]
    scalar_type = values["scalar_type"]
    key = {
        "string": "string_values",
        "int": "int_values",
        "float": "float_values",
        "boolean": "boolean_values",
        "object_ref": "object_refs",
        "oterm_ref": "oterm_refs",
    }[scalar_type]
    return len(values[key])


def immutable_array_payload(document: dict[str, Any]) -> dict[str, Any]:
    """Return the scientific array content that must remain unchanged."""
    return {
        "data_type": document["data_type"],
        "n_dimensions": document["n_dimensions"],
        "dim_context": document["dim_context"],
        "typed_values": document["typed_values"],
    }


def validate_source_shape(document: dict[str, Any], manifest: dict[str, str]) -> None:
    gene_count = int(manifest["gene_count"])
    condition_count = int(manifest["condition_count"])
    cell_count = int(manifest["cell_count"])
    dimensions = document.get("dim_context", [])
    if document.get("n_dimensions") != 2 or len(dimensions) != 2:
        raise ValueError(f"{document.get('name')} is not a two-dimensional fitness array")
    if [dimension.get("size") for dimension in dimensions] != [gene_count, condition_count]:
        raise ValueError(f"Dimension sizes disagree with the source manifest for {document['name']}")
    if gene_count * condition_count != cell_count:
        raise ValueError(f"Non-rectangular manifest counts for {document['name']}")
    for dimension in dimensions:
        expected = int(dimension["size"])
        for variable in dimension.get("typed_values", []):
            if values_length(variable) != expected:
                raise ValueError(f"Dimension-variable length mismatch for {document['name']}")
    measured = document.get("typed_values", [])
    if len(measured) != 2:
        raise ValueError(f"Expected fit and t variables in {document['name']}; found {len(measured)}")
    if any(values_length(variable) != cell_count for variable in measured):
        raise ValueError(f"Measured-value length mismatch for {document['name']}")


def build_replacement_document(source: dict[str, Any], manifest: dict[str, str]) -> dict[str, Any]:
    if source.get("name") != manifest["brick_name"]:
        raise ValueError(
            f"Source name {source.get('name')!r} does not match manifest {manifest['brick_name']!r}"
        )
    validate_source_shape(source, manifest)
    existing_context = source.get("array_context", [])
    marker_ref = base.TERMS["data_variables_type"].ref
    if any(prop.get("value_type", {}).get("oterm_ref") == marker_ref for prop in existing_context):
        raise ValueError(f"Source brick already has a data-variables marker: {source['name']}")

    replacement = dict(source)
    replacement["name"] = new_brick_name(source["name"])
    replacement["description"] = (
        source["description"]
        + "; v2 adds canonical CORAL data-variable context for lossless heterogeneous export"
    )
    replacement["array_context"] = [
        base.scalar_property(
            "data_variables_type", "oterm_ref", replacement["data_type"]["oterm_ref"]
        ),
        *existing_context,
    ]
    base.validate_data_variables_context(replacement)
    validate_source_shape(replacement, manifest)
    if immutable_array_payload(replacement) != immutable_array_payload(source):
        raise ValueError(f"Scientific array content changed while replacing {source['name']}")
    return replacement


def write_helpers(stage: Path, filenames: list[str], process_filename: str) -> None:
    upload_lines = [f"toolx.upload_brick('{filename}')" for filename in filenames]
    stage.joinpath("import_bricks_to_coral.py").write_text(
        "# Copy json/*.json into CORAL's brick import directory, then run these uploads.\n"
        + "\n".join(upload_lines)
        + "\n"
    )
    stage.joinpath("import_update_data_to_coral.py").write_text(
        "# Run only after all 22 replacement bricks pass post-import export validation.\n"
        f"toolx.upload_process('Update Data', '{process_filename}')\n"
    )
    stage.joinpath("files_to_import.txt").write_text(
        "\n".join(
            [
                *(f"json/{filename}" for filename in filenames),
                f"process/{process_filename}",
            ]
        )
        + "\n"
    )


def write_readme(stage: Path, checkgeneric: str) -> None:
    stage.joinpath("README.md").write_text(
        f"""# FEBa fitness brick v2 correction ({CORRECTION_DATE})

This package contains 22 immutable replacements for the FEBa TnSeq fitness
bricks imported on 2026-08-13. The original JSON arrays contain the complete
gene-by-condition fit and t matrices, but omit CORAL's heterogeneous-array
marker. The replacement bricks add exactly one array-context property:

`data variables type <ME:0000293> = Gene Knockout Fitness <DA:0000010>`

Each internal brick name ends in `_v2.ndarray`; every staged import filename
contains `{DATE_STAMP}`. No gene, condition, library, genome, dimension, fit
value, t value, unit, or object reference is changed. The replacement manifest
records source/replacement checksums and a shared canonical hash of the
scientific array payload.

CheckGeneric: {checkgeneric}.

## Import sequence

1. Copy all files under `json/` to CORAL's brick import directory and run
   `import_bricks_to_coral.py`.
2. Re-poll the 22 new bricks. For each brick, verify that CORAL reports the
   exported array shape `[2, gene_count, condition_count]`; the converted table
   must contain `gene_count * condition_count` rows with both fit and t values.
   Also sample object references and values against
   `reports/replacement_manifest_{DATE_STAMP}.tsv` and the source bricks.
3. Only after all 22 exports pass, copy the process TSV into CORAL's process
   import directory and run `import_update_data_to_coral.py`. Its 22 one-to-one
   `Update Data` rows obsolete each old fitness brick with its matching v2
   replacement. The prior legacy N2E2 lifecycle remains a chain:
   `tnseq_n2e2.ndarray` -> the 2026-08-13 FEBa N2E2 brick -> its v2 brick.

`files_to_import.txt` lists only CORAL inputs. The reports and checks are audit
artifacts, not sidecar data required by CORAL.
"""
    )


def write_checksums(stage: Path) -> None:
    paths = sorted(path for path in stage.rglob("*") if path.is_file() and path.name != "checksums.sha256")
    stage.joinpath("checksums.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(stage)}\n" for path in paths)
    )


def main() -> None:
    args = parse_args()
    source_manifest_path = args.source_package / "reports/fitness_brick_manifest.tsv"
    if not source_manifest_path.exists():
        raise FileNotFoundError(source_manifest_path)
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite existing package: {args.output}")
    source_rows = read_tsv(source_manifest_path)
    if len(source_rows) != EXPECTED_BRICKS:
        raise ValueError(f"Expected {EXPECTED_BRICKS} source bricks, found {len(source_rows)}")
    if sum(int(row["cell_count"]) for row in source_rows) != EXPECTED_CELLS:
        raise ValueError("Unexpected total source fitness cell count")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{args.output.name}.", dir=args.output.parent))
    try:
        for directory in ("json", "check", "process", "reports"):
            stage.joinpath(directory).mkdir()
        replacement_rows: list[dict[str, Any]] = []
        process_rows: list[dict[str, str]] = []
        filenames: list[str] = []
        for number, manifest in enumerate(source_rows, start=1):
            old_name = manifest["brick_name"]
            source_path = args.source_package / "json" / old_name.replace(".ndarray", ".json")
            if not source_path.exists():
                raise FileNotFoundError(source_path)
            with source_path.open() as handle:
                source = json.load(handle)
            replacement = build_replacement_document(source, manifest)
            new_name = replacement["name"]
            filename = new_name.replace(".ndarray", f"_{DATE_STAMP}.json")
            destination = stage / "json" / filename
            with destination.open("w") as handle:
                json.dump(replacement, handle, separators=(",", ":"), allow_nan=False)
            with destination.open() as handle:
                round_trip = json.load(handle)
            if round_trip != replacement:
                raise ValueError(f"Replacement JSON did not round-trip exactly: {destination}")
            base.validate_data_variables_context(round_trip)
            validate_source_shape(round_trip, manifest)
            if not args.skip_checkgeneric:
                base.check_generic(destination, stage / "check" / f"{filename}.check")

            payload_hash = canonical_sha256(immutable_array_payload(source))
            if payload_hash != canonical_sha256(immutable_array_payload(round_trip)):
                raise ValueError(f"Scientific payload hash changed for {old_name}")
            replacement_rows.append(
                {
                    "fitprivate_orgId": manifest["fitprivate_orgId"],
                    "old_brick_name": old_name,
                    "new_brick_name": new_name,
                    "source_json": str(source_path.relative_to(ROOT)),
                    "replacement_json": str(destination.relative_to(stage)),
                    "gene_count": manifest["gene_count"],
                    "condition_count": manifest["condition_count"],
                    "cell_count": manifest["cell_count"],
                    "fit_value_count": manifest["fitness_value_count"],
                    "t_value_count": manifest["t_value_count"],
                    "scientific_payload_sha256": payload_hash,
                    "source_file_sha256": sha256(source_path),
                    "replacement_file_sha256": sha256(destination),
                    "data_variables_type": f"{replacement['data_type']['oterm_name']} <{replacement['data_type']['oterm_ref']}>",
                    "checkgeneric": "skipped" if args.skip_checkgeneric else "passed",
                }
            )
            process_rows.append(
                {
                    "process": "Update Data <PROCESS:0000053>",
                    "person": "John-Marc Chandonia <ENIGMA:0000057>",
                    "campaign": "Predictive Network Biology <ENIGMA:0000006>",
                    "protocol": "null",
                    "date_start": CORRECTION_DATE,
                    "date_end": CORRECTION_DATE,
                    "input_objects": f"Generic: {old_name}",
                    "output_objects": f"Generic: {new_name}",
                }
            )
            filenames.append(filename)
            print(
                f"[{number:02d}/{len(source_rows)}] {old_name} -> {new_name}: "
                f"{manifest['gene_count']} x {manifest['condition_count']} = {manifest['cell_count']}",
                flush=True,
            )

        manifest_filename = f"replacement_manifest_{DATE_STAMP}.tsv"
        write_tsv(
            stage / "reports" / manifest_filename,
            list(replacement_rows[0]),
            replacement_rows,
        )
        process_filename = f"process_update_data_feba_tnseq_fitness_v2_{DATE_STAMP}.tsv"
        write_tsv(stage / "process" / process_filename, PROCESS_FIELDS, process_rows)
        summary = {
            "correction_date": CORRECTION_DATE,
            "source_package": str(args.source_package),
            "replacement_bricks": len(replacement_rows),
            "fitness_cells": sum(int(row["cell_count"]) for row in replacement_rows),
            "fit_values": sum(int(row["fit_value_count"]) for row in replacement_rows),
            "t_values": sum(int(row["t_value_count"]) for row in replacement_rows),
            "data_variables_context": "data variables type <ME:0000293> = Gene Knockout Fitness <DA:0000010>",
            "scientific_payloads_unchanged": True,
            "checkgeneric_passed": not args.skip_checkgeneric,
            "update_data_rows": len(process_rows),
        }
        stage.joinpath("reports", f"package_summary_{DATE_STAMP}.json").write_text(
            json.dumps(summary, indent=2) + "\n"
        )
        write_helpers(stage, filenames, process_filename)
        write_readme(stage, "skipped by request" if args.skip_checkgeneric else "passed for all 22 bricks")
        write_checksums(stage)
        stage.rename(args.output)
        print(f"complete: {args.output}", flush=True)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


if __name__ == "__main__":
    main()
