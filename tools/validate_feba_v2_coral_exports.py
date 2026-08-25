#!/usr/bin/env python3
"""Validate the 22 CORAL-exported FEBa v2 bricks against their staged JSON."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = ROOT / "coral_import/feba_20260811/fitness_brick_v2_20260825"
DEFAULT_BRICK_DIR = (
    ROOT
    / "sync-coral-to-berdl/exports/sync-20260825-113646/coral_export/brick_csv"
)
DEFAULT_DOWNLOAD_MANIFEST = DEFAULT_BRICK_DIR.parent / "brick_download_manifest.json"
DEFAULT_CONVERTED_DIR = DEFAULT_BRICK_DIR.parents[1] / "berdl_upload/data"
DEFAULT_REPORT = (
    ROOT
    / "sync-coral-to-berdl/exports/sync-20260825-113646/reports/"
    "feba_v2_coral_export_validation.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--brick-dir", type=Path, default=DEFAULT_BRICK_DIR)
    parser.add_argument(
        "--download-manifest", type=Path, default=DEFAULT_DOWNLOAD_MANIFEST
    )
    parser.add_argument("--converted-dir", type=Path, default=DEFAULT_CONVERTED_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def term_text(term: dict[str, str]) -> str:
    return f"{term['oterm_name']} <{term['oterm_ref']}>"


def parse_metadata(reader: csv.reader) -> tuple[dict[str, str], list[list[list[str]]]]:
    scalar: dict[str, str] = {}
    blocks: list[list[list[str]]] = []
    current: list[list[str]] | None = None
    for row in reader:
        if not row:
            continue
        if row[0] == "data":
            if current is not None:
                blocks.append(current)
            return scalar, blocks
        if row[0] == "dmeta":
            if current is not None:
                blocks.append(current)
            current = [row]
        elif current is not None:
            current.append(row)
        else:
            scalar[row[0]] = ",".join(row[1:])
    raise ValueError("CORAL CSV has no data marker")


def validate_indexed_refs(
    block: list[list[str]], expected_header: list[str], expected_refs: list[str]
) -> None:
    if block[0] != expected_header:
        raise ValueError(f"Unexpected dmeta header: {block[0]} != {expected_header}")
    rows = block[1:]
    if len(rows) != len(expected_refs):
        raise ValueError(
            f"Dimension metadata length mismatch: {len(rows)} != {len(expected_refs)}"
        )
    for index, (row, expected) in enumerate(zip(rows, expected_refs), start=1):
        if row != [str(index), f"{expected} <{expected}>"]:
            raise ValueError(
                f"Dimension metadata mismatch at index {index}: {row!r}"
            )


def validate_one(
    brick_id: str,
    csv_path: Path,
    converted_path: Path,
    source_path: Path,
    manifest: dict[str, str],
) -> dict[str, Any]:
    with source_path.open(encoding="utf-8") as handle:
        source = json.load(handle)
    gene_count = int(manifest["gene_count"])
    condition_count = int(manifest["condition_count"])
    cell_count = int(manifest["cell_count"])
    if source["name"] != manifest["new_brick_name"]:
        raise ValueError(f"Staged name mismatch for {brick_id}")
    dimensions = source["dim_context"]
    if [dimension["size"] for dimension in dimensions] != [gene_count, condition_count]:
        raise ValueError(f"Staged dimensions disagree with manifest for {brick_id}")
    variables = source["typed_values"]
    if len(variables) != 2:
        raise ValueError(f"Expected two staged data variables for {brick_id}")
    expected_values = [variable["values"]["float_values"] for variable in variables]
    if any(len(values) != cell_count for values in expected_values):
        raise ValueError(f"Staged data-variable length mismatch for {brick_id}")

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        scalar, blocks = parse_metadata(reader)
        if scalar.get("name") != source["name"]:
            raise ValueError(f"CORAL export name mismatch for {brick_id}")
        expected_size = f"2,{gene_count},{condition_count}"
        if scalar.get("size") != expected_size:
            raise ValueError(
                f"CORAL export shape mismatch for {brick_id}: "
                f"{scalar.get('size')} != {expected_size}"
            )
        if len(blocks) != 5 or [block[0][1] for block in blocks] != ["1", "2", "2", "3", "3"]:
            raise ValueError(f"Unexpected CORAL dmeta block structure for {brick_id}")
        if len(blocks[0]) != 3:
            raise ValueError(f"CORAL variable-axis metadata does not contain two variables for {brick_id}")
        for index, variable in enumerate(variables, start=1):
            if blocks[0][index][0] != str(index) or blocks[0][index][1] != term_text(variable["value_type"]):
                raise ValueError(f"CORAL variable-axis metadata mismatch for {brick_id}, variable {index}")

        for block, dimension_index, variable_index, csv_dimension in [
            (blocks[1], 0, 0, 2),
            (blocks[2], 0, 1, 2),
            (blocks[3], 1, 0, 3),
            (blocks[4], 1, 1, 3),
        ]:
            dimension = dimensions[dimension_index]
            variable = dimension["typed_values"][variable_index]
            validate_indexed_refs(
                block,
                [
                    "dmeta",
                    str(csv_dimension),
                    term_text(dimension["data_type"]),
                    term_text(variable["value_type"]),
                ],
                variable["values"]["object_refs"],
            )

        row_count = 0
        for row_count, row in enumerate(reader, start=1):
            if len(row) != 4:
                raise ValueError(f"Malformed data row {row_count} for {brick_id}: {row!r}")
            zero_based = row_count - 1
            variable_index = zero_based // cell_count
            cell_index = zero_based % cell_count
            expected_indices = [
                str(variable_index + 1),
                str(cell_index // condition_count + 1),
                str(cell_index % condition_count + 1),
            ]
            if row[:3] != expected_indices:
                raise ValueError(
                    f"Index mismatch in {brick_id} row {row_count}: "
                    f"{row[:3]} != {expected_indices}"
                )
            if variable_index >= 2:
                raise ValueError(f"Too many data rows in {brick_id}")
            exported = float(row[3])
            expected = expected_values[variable_index][cell_index]
            if exported != expected:
                raise ValueError(
                    f"Value mismatch in {brick_id} at variable {variable_index + 1}, "
                    f"cell {cell_index + 1}: {exported!r} != {expected!r}"
                )
        if row_count != 2 * cell_count:
            raise ValueError(
                f"Data row count mismatch for {brick_id}: {row_count} != {2 * cell_count}"
            )

    genes = dimensions[0]["typed_values"][0]["values"]["object_refs"]
    genomes = dimensions[0]["typed_values"][1]["values"]["object_refs"]
    conditions = dimensions[1]["typed_values"][0]["values"]["object_refs"]
    libraries = dimensions[1]["typed_values"][1]["values"]["object_refs"]
    with converted_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader)
        if len(header) != 6:
            raise ValueError(f"Converted table for {brick_id} has {len(header)} columns, not 6")
        converted_rows = 0
        for converted_rows, row in enumerate(reader, start=1):
            if len(row) != 6:
                raise ValueError(
                    f"Malformed converted row {converted_rows} for {brick_id}: {row!r}"
                )
            cell_index = converted_rows - 1
            gene_index = cell_index // condition_count
            condition_index = cell_index % condition_count
            expected_keys = [
                genes[gene_index],
                genomes[gene_index],
                conditions[condition_index],
                libraries[condition_index],
            ]
            if row[:4] != expected_keys:
                raise ValueError(
                    f"Converted dimension mismatch for {brick_id}, row {converted_rows}"
                )
            if float(row[4]) != expected_values[0][cell_index]:
                raise ValueError(
                    f"Converted fit mismatch for {brick_id}, row {converted_rows}"
                )
            if float(row[5]) != expected_values[1][cell_index]:
                raise ValueError(
                    f"Converted t mismatch for {brick_id}, row {converted_rows}"
                )
        if converted_rows != cell_count:
            raise ValueError(
                f"Converted row count mismatch for {brick_id}: "
                f"{converted_rows} != {cell_count}"
            )

    return {
        "brick_id": brick_id,
        "name": source["name"],
        "shape": [2, gene_count, condition_count],
        "matrix_rows_after_conversion": cell_count,
        "raw_data_rows": 2 * cell_count,
        "fit_values_compared": cell_count,
        "t_values_compared": cell_count,
        "dimension_references_compared": 2 * gene_count + 2 * condition_count,
        "raw_csv_sha256": sha256(csv_path),
        "converted_tsv_sha256": sha256(converted_path),
        "converted_columns": header,
        "staged_json_sha256": sha256(source_path),
        "status": "passed",
    }


def main() -> int:
    args = parse_args()
    replacement_manifest = read_tsv(
        args.package_dir / "reports/replacement_manifest_20260825.tsv"
    )
    expected_by_name = {row["new_brick_name"]: row for row in replacement_manifest}
    download = json.loads(args.download_manifest.read_text(encoding="utf-8"))
    new_ids = download["downloaded_new_ids"]
    if len(expected_by_name) != 22 or len(new_ids) != 22:
        raise ValueError(
            f"Expected 22 replacement names and 22 new CORAL IDs; found "
            f"{len(expected_by_name)} and {len(new_ids)}"
        )

    csv_by_name: dict[str, tuple[str, Path]] = {}
    for brick_id in new_ids:
        path = args.brick_dir / f"{brick_id}.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            first = next(csv.reader(handle))
        if len(first) != 2 or first[0] != "name":
            raise ValueError(f"No name row in {path}")
        if first[1] in csv_by_name:
            raise ValueError(f"Duplicate exported brick name: {first[1]}")
        csv_by_name[first[1]] = (brick_id, path)
    if set(csv_by_name) != set(expected_by_name):
        raise ValueError(
            "The 22 newly exported CORAL brick names do not exactly match the replacement manifest"
        )

    results = []
    for index, manifest in enumerate(replacement_manifest, start=1):
        name = manifest["new_brick_name"]
        brick_id, csv_path = csv_by_name[name]
        source_path = args.package_dir / manifest["replacement_json"]
        result = validate_one(
            brick_id,
            csv_path,
            args.converted_dir / f"{brick_id}.tsv",
            source_path,
            manifest,
        )
        results.append(result)
        print(
            f"[{index:02d}/22] {brick_id} {name}: "
            f"{manifest['gene_count']} x {manifest['condition_count']} passed",
            flush=True,
        )

    report = {
        "status": "passed",
        "bricks": len(results),
        "matrix_rows": sum(row["matrix_rows_after_conversion"] for row in results),
        "raw_data_rows": sum(row["raw_data_rows"] for row in results),
        "fit_values_compared": sum(row["fit_values_compared"] for row in results),
        "t_values_compared": sum(row["t_values_compared"] for row in results),
        "dimension_references_compared": sum(
            row["dimension_references_compared"] for row in results
        ),
        "results": results,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
