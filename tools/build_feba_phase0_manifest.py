#!/usr/bin/env python3
"""Build the durable Phase 0 manifests for the FEBa-to-CORAL import."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sqlite3
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable


SOURCE_NAMESPACE = "enigma.fitprivate"
EXPECTED_REVIEWED_ORGANISMS = 25

SCOPE_COLUMNS = (
    "fitprivate_orgId",
    "include",
    "scope_class",
    "decision_reason",
)

TYPE_TO_FEATURE = {
    1: "CDS",
    2: "rRNA",
    3: "rRNA",
    4: "rRNA",
    5: "tRNA",
    6: "ncRNA",
    7: "pseudogene",
    8: "ncRNA",
    9: "repeat_region",
    10: "repeat_region",
    11: "antisense_RNA",
    99: "sequence_feature",
}

ORGANISM_PROGRESS_COLUMNS = (
    "coral_match_live_status",
    "coral_match_live_checked_at",
    "edr_inventory_status",
    "edr_inventory_checked_at",
    "edr_active_versions_json",
    "edr_withdrawn_versions_json",
    "source_fingerprint_status",
    "exact_match_status",
    "exact_match_location",
    "reused_edr_version",
    "allocated_edr_version",
    "target_coral_genome_name",
    "export_status",
    "edr_publication_status",
    "coral_genome_import_status",
    "validation_status",
    "notes",
)

ORGANISM_COLUMNS = (
    "source_namespace",
    "fitprivate_orgId",
    "fitprivate_organism",
    "scaffold_count",
    "total_bases",
    "gene_count",
    "xref_count",
    "source_assembly_sha256",
    "source_annotation_structure_sha256",
    "source_annotation_metadata_sha256",
    "experiment_count",
    "gene_fitness_count",
    "distinct_mutant_library_count",
    "mutant_libraries_json",
    "sdt_strain_id",
    "sdt_strain_name",
    "match_basis",
    *ORGANISM_PROGRESS_COLUMNS,
)

STRAIN_COLUMNS = (
    "sdt_strain_id",
    "sdt_strain_name",
    "fitprivate_organism_count",
    "fitprivate_orgIds_json",
    "fitprivate_organisms_json",
    "scaffold_count",
    "total_bases",
    "gene_count",
    "xref_count",
    "experiment_count",
    "gene_fitness_count",
    "distinct_mutant_library_count",
    "mutant_libraries_json",
    "coral_match_live_status",
    "genome_barrier_status",
    "notes",
)

LIBRARY_COLUMNS = (
    "fitprivate_orgId",
    "sdt_strain_name",
    "source_mutant_library",
    "experiment_count",
    "base_library_lineage",
    "primers_model",
    "transposon",
    "assignment_basis",
    "source_value",
    "notes",
)

MODEL_INPUT_COLUMNS = (
    "fitprivate_orgId",
    "source_mutant_library",
    "base_library_lineage",
    "primers_model",
    "transposon",
    "assignment_basis",
    "source_value",
    "notes",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--crosswalk", required=True, type=Path)
    parser.add_argument("--scope", required=True, type=Path)
    parser.add_argument("--library-models", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--run-date",
        default=date.today().strftime("%Y%m%d"),
        help="Date suffix in YYYYMMDD format (default: today)",
    )
    parser.add_argument(
        "--database-sha256",
        required=True,
        help="Previously verified SHA-256 of the immutable SQLite source",
    )
    return parser.parse_args()


def read_tsv(path: Path, required_columns: Iterable[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = set(reader.fieldnames or [])
        missing = set(required_columns) - fieldnames
        if missing:
            raise ValueError(f"{path} is missing columns: {sorted(missing)}")
        return [dict(row) for row in reader]


def read_existing_by_key(path: Path, key: str) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    rows = read_tsv(path, [key])
    return {row[key]: row for row in rows}


def write_tsv_atomic(path: Path, columns: Iterable[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(columns),
            delimiter="\t",
            lineterminator="\n",
            extrasaction="raise",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    os.replace(temporary, path)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def organism_name(row: sqlite3.Row) -> str:
    return " ".join(str(row[key]) for key in ("genus", "species", "strain") if row[key])


def scalar(connection: sqlite3.Connection, query: str, org_id: str) -> int:
    value = connection.execute(query, (org_id,)).fetchone()[0]
    return int(value or 0)


def update_digest(digest: Any, *values: object) -> None:
    """Add an unambiguous length-framed record to a SHA-256 digest."""
    for value in values:
        encoded = ("" if value is None else str(value)).encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)


def source_fingerprints(connection: sqlite3.Connection, org_id: str) -> dict[str, str]:
    assembly = hashlib.sha256()
    structure = hashlib.sha256()
    metadata = hashlib.sha256()

    for row in connection.execute(
        "SELECT scaffoldId, sequence FROM ScaffoldSeq "
        "WHERE orgId = ? ORDER BY scaffoldId",
        (org_id,),
    ):
        sequence = "".join(str(row["sequence"]).split()).upper()
        update_digest(assembly, "scaffold", row["scaffoldId"], sequence)

    xrefs: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for row in connection.execute(
        "SELECT locusId, xrefDb, xrefId FROM LocusXref "
        "WHERE orgId = ? ORDER BY locusId, xrefDb, xrefId",
        (org_id,),
    ):
        xrefs[str(row["locusId"])].append((str(row["xrefDb"]), str(row["xrefId"])))

    for row in connection.execute(
        "SELECT locusId, sysName, scaffoldId, begin, end, type, strand, gene, desc, GC "
        "FROM Gene WHERE orgId = ? ORDER BY scaffoldId, begin, end, locusId",
        (org_id,),
    ):
        feature_type = TYPE_TO_FEATURE.get(int(row["type"]))
        if feature_type is None:
            raise ValueError(
                f"Unsupported FEBa feature type {row['type']} for "
                f"{org_id}:{row['locusId']}"
            )
        structural_values = (
            "feature",
            row["locusId"],
            row["scaffoldId"],
            row["begin"],
            row["end"],
            row["strand"],
            feature_type,
        )
        update_digest(structure, *structural_values)
        update_digest(
            metadata,
            *structural_values,
            row["sysName"],
            row["gene"],
            row["desc"],
            "" if row["GC"] is None else repr(float(row["GC"])),
            json.dumps(xrefs.get(str(row["locusId"]), []), separators=(",", ":")),
        )

    return {
        "source_assembly_sha256": assembly.hexdigest(),
        "source_annotation_structure_sha256": structure.hexdigest(),
        "source_annotation_metadata_sha256": metadata.hexdigest(),
    }


def collect_source_row(
    connection: sqlite3.Connection, crosswalk: dict[str, str]
) -> tuple[dict[str, Any], list[tuple[str, int]]]:
    org_id = crosswalk["fitprivate_orgId"]
    source_organism = connection.execute(
        "SELECT genus, species, strain FROM Organism WHERE orgId = ?", (org_id,)
    ).fetchone()
    if source_organism is None:
        raise ValueError(f"Crosswalk organism is absent from SQLite: {org_id}")
    source_name = organism_name(source_organism)
    if source_name != crosswalk["fitprivate_organism"]:
        raise ValueError(
            f"Organism text differs for {org_id}: SQLite={source_name!r}, "
            f"crosswalk={crosswalk['fitprivate_organism']!r}"
        )

    scaffold_count, total_bases = connection.execute(
        "SELECT COUNT(*), COALESCE(SUM(LENGTH(sequence)), 0) "
        "FROM ScaffoldSeq WHERE orgId = ?",
        (org_id,),
    ).fetchone()
    libraries = [
        (str(row[0]), int(row[1]))
        for row in connection.execute(
            "SELECT mutantLibrary, COUNT(*) FROM Experiment "
            "WHERE orgId = ? GROUP BY mutantLibrary ORDER BY mutantLibrary",
            (org_id,),
        )
    ]
    experiment_count = sum(count for _, count in libraries)
    expected_experiments = int(crosswalk["experiment_count"])
    if experiment_count != expected_experiments:
        raise ValueError(
            f"Experiment count differs for {org_id}: SQLite={experiment_count}, "
            f"crosswalk={expected_experiments}"
        )

    row: dict[str, Any] = {
        "source_namespace": SOURCE_NAMESPACE,
        "fitprivate_orgId": org_id,
        "fitprivate_organism": source_name,
        "scaffold_count": int(scaffold_count),
        "total_bases": int(total_bases),
        "gene_count": scalar(
            connection, "SELECT COUNT(*) FROM Gene WHERE orgId = ?", org_id
        ),
        "xref_count": scalar(
            connection, "SELECT COUNT(*) FROM LocusXref WHERE orgId = ?", org_id
        ),
        "experiment_count": experiment_count,
        "gene_fitness_count": scalar(
            connection, "SELECT COUNT(*) FROM GeneFitness WHERE orgId = ?", org_id
        ),
        "distinct_mutant_library_count": len(libraries),
        "mutant_libraries_json": json.dumps([name for name, _ in libraries]),
        "sdt_strain_id": crosswalk["sdt_strain_id"],
        "sdt_strain_name": crosswalk["sdt_strain_name"],
        "match_basis": crosswalk["match_basis"],
    }
    row.update(source_fingerprints(connection, org_id))
    return row, libraries


def validate_crosswalk(rows: list[dict[str, str]]) -> None:
    if len(rows) != EXPECTED_REVIEWED_ORGANISMS:
        raise ValueError(
            f"Expected {EXPECTED_REVIEWED_ORGANISMS} reviewed crosswalk rows, "
            f"found {len(rows)}"
        )
    org_ids = [row["fitprivate_orgId"] for row in rows]
    strain_ids = [row["sdt_strain_id"] for row in rows]
    strain_names = [row["sdt_strain_name"] for row in rows]
    for label, values in (
        ("fitprivate_orgId", org_ids),
        ("sdt_strain_id", strain_ids),
        ("sdt_strain_name", strain_names),
    ):
        if len(values) != len(set(values)):
            raise ValueError(f"Crosswalk contains duplicate {label} values")


def select_scope(
    crosswalk_rows: list[dict[str, str]], scope_rows: list[dict[str, str]]
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    crosswalk_org_ids = {row["fitprivate_orgId"] for row in crosswalk_rows}
    scope_by_org: dict[str, dict[str, str]] = {}
    for row in scope_rows:
        org_id = row["fitprivate_orgId"]
        if org_id in scope_by_org:
            raise ValueError(f"Scope contains duplicate fitprivate_orgId: {org_id}")
        if row["include"] not in {"yes", "no"}:
            raise ValueError(f"Scope include must be yes or no for {org_id}")
        if not row["scope_class"] or not row["decision_reason"]:
            raise ValueError(f"Scope decision is incomplete for {org_id}")
        scope_by_org[org_id] = row

    scope_org_ids = set(scope_by_org)
    if scope_org_ids != crosswalk_org_ids:
        raise ValueError(
            "Scope must cover exactly the reviewed crosswalk orgIds; "
            f"missing={sorted(crosswalk_org_ids - scope_org_ids)}, "
            f"unexpected={sorted(scope_org_ids - crosswalk_org_ids)}"
        )

    selected = [
        row
        for row in crosswalk_rows
        if scope_by_org[row["fitprivate_orgId"]]["include"] == "yes"
    ]
    excluded = [scope_by_org[row["fitprivate_orgId"]] for row in crosswalk_rows if row not in selected]
    if not selected:
        raise ValueError("Scope excludes every reviewed organism")
    return selected, excluded


def load_model_map(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    rows = read_tsv(path, MODEL_INPUT_COLUMNS)
    result: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["fitprivate_orgId"], row["source_mutant_library"])
        if key in result:
            raise ValueError(f"Duplicate library model assignment: {key}")
        if not row["primers_model"] or not row["assignment_basis"]:
            raise ValueError(f"Incomplete library model assignment: {key}")
        result[key] = row
    return result


def build_strain_rows(organism_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in organism_rows:
        grouped[(row["sdt_strain_id"], row["sdt_strain_name"])].append(row)

    output = []
    for (strain_id, strain_name), members in sorted(grouped.items(), key=lambda item: item[0][1]):
        library_names = sorted(
            {
                library
                for member in members
                for library in json.loads(member["mutant_libraries_json"])
            }
        )
        live_statuses = {member["coral_match_live_status"] for member in members}
        output.append(
            {
                "sdt_strain_id": strain_id,
                "sdt_strain_name": strain_name,
                "fitprivate_organism_count": len(members),
                "fitprivate_orgIds_json": json.dumps(
                    sorted(member["fitprivate_orgId"] for member in members)
                ),
                "fitprivate_organisms_json": json.dumps(
                    sorted(member["fitprivate_organism"] for member in members)
                ),
                "scaffold_count": sum(member["scaffold_count"] for member in members),
                "total_bases": sum(member["total_bases"] for member in members),
                "gene_count": sum(member["gene_count"] for member in members),
                "xref_count": sum(member["xref_count"] for member in members),
                "experiment_count": sum(member["experiment_count"] for member in members),
                "gene_fitness_count": sum(member["gene_fitness_count"] for member in members),
                "distinct_mutant_library_count": len(library_names),
                "mutant_libraries_json": json.dumps(library_names),
                "coral_match_live_status": live_statuses.pop() if len(live_statuses) == 1 else "mixed",
                "genome_barrier_status": "pending",
                "notes": "",
            }
        )
    return output


def main() -> int:
    args = parse_args()
    if len(args.run_date) != 8 or not args.run_date.isdigit():
        raise SystemExit("--run-date must use YYYYMMDD")
    if not args.database.is_file():
        raise SystemExit(f"Database not found: {args.database}")
    if len(args.database_sha256) != 64:
        raise SystemExit("--database-sha256 must be a 64-character SHA-256")

    crosswalk_rows = read_tsv(
        args.crosswalk,
        (
            "fitprivate_orgId",
            "fitprivate_organism",
            "experiment_count",
            "sdt_strain_id",
            "sdt_strain_name",
            "match_basis",
        ),
    )
    validate_crosswalk(crosswalk_rows)
    scope_rows = read_tsv(args.scope, SCOPE_COLUMNS)
    selected_crosswalk_rows, excluded_scope_rows = select_scope(crosswalk_rows, scope_rows)
    model_map = load_model_map(args.library_models)

    output_dir = args.output_dir.resolve()
    organism_path = output_dir / f"feba_organism_work_manifest_{args.run_date}.tsv"
    strain_path = output_dir / f"feba_strain_rollup_{args.run_date}.tsv"
    library_path = output_dir / f"feba_library_crosswalk_{args.run_date}.tsv"
    metadata_path = output_dir / f"feba_phase0_metadata_{args.run_date}.json"
    existing = read_existing_by_key(organism_path, "fitprivate_orgId")

    connection = sqlite3.connect(f"file:{args.database.resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        organism_rows: list[dict[str, Any]] = []
        library_rows: list[dict[str, Any]] = []
        source_library_keys: set[tuple[str, str]] = set()
        for crosswalk in selected_crosswalk_rows:
            row, libraries = collect_source_row(connection, crosswalk)
            prior = existing.get(row["fitprivate_orgId"], {})
            for column in ORGANISM_PROGRESS_COLUMNS:
                if column == "source_fingerprint_status":
                    row[column] = "complete"
                else:
                    row[column] = prior.get(
                        column, "pending" if column.endswith("status") else ""
                    )
            organism_rows.append(row)

            for library_name, experiment_count in libraries:
                key = (row["fitprivate_orgId"], library_name)
                source_library_keys.add(key)
                assignment = model_map.get(key)
                if assignment is None:
                    raise ValueError(f"Missing library model assignment: {key}")
                library_rows.append(
                    {
                        "fitprivate_orgId": row["fitprivate_orgId"],
                        "sdt_strain_name": row["sdt_strain_name"],
                        "source_mutant_library": library_name,
                        "experiment_count": experiment_count,
                        **{column: assignment[column] for column in MODEL_INPUT_COLUMNS[2:]},
                    }
                )
    finally:
        connection.close()

    selected_org_ids = {row["fitprivate_orgId"] for row in selected_crosswalk_rows}
    reviewed_org_ids = {row["fitprivate_orgId"] for row in crosswalk_rows}
    unexpected_assignments = {
        key for key in model_map if key[0] in selected_org_ids and key not in source_library_keys
    }
    if unexpected_assignments:
        raise ValueError(
            "Library model assignments absent from the selected source: "
            f"{sorted(unexpected_assignments)}"
        )
    assignments_for_other_orgs = {key for key in model_map if key[0] not in reviewed_org_ids}
    if assignments_for_other_orgs:
        raise ValueError(
            "Library model assignments include organisms outside the reviewed universe: "
            f"{sorted(assignments_for_other_orgs)}"
        )

    organism_rows.sort(key=lambda row: row["fitprivate_orgId"])
    library_rows.sort(key=lambda row: (row["fitprivate_orgId"], row["source_mutant_library"]))
    strain_rows = build_strain_rows(organism_rows)

    write_tsv_atomic(organism_path, ORGANISM_COLUMNS, organism_rows)
    write_tsv_atomic(strain_path, STRAIN_COLUMNS, strain_rows)
    write_tsv_atomic(library_path, LIBRARY_COLUMNS, library_rows)

    totals = {
        "organisms": len(organism_rows),
        "strains": len(strain_rows),
        "scaffolds": sum(row["scaffold_count"] for row in organism_rows),
        "total_bases": sum(row["total_bases"] for row in organism_rows),
        "genes": sum(row["gene_count"] for row in organism_rows),
        "xrefs": sum(row["xref_count"] for row in organism_rows),
        "experiments": sum(row["experiment_count"] for row in organism_rows),
        "gene_fitness_rows": sum(row["gene_fitness_count"] for row in organism_rows),
        "libraries": len(library_rows),
    }
    metadata = {
        "run_date": args.run_date,
        "source_namespace": SOURCE_NAMESPACE,
        "source_database": str(args.database.resolve()),
        "source_database_bytes": args.database.stat().st_size,
        "source_database_sha256": args.database_sha256.lower(),
        "crosswalk": str(args.crosswalk.resolve()),
        "scope": str(args.scope.resolve()),
        "reviewed_organisms": len(crosswalk_rows),
        "excluded_organisms": [
            {
                "fitprivate_orgId": row["fitprivate_orgId"],
                "scope_class": row["scope_class"],
                "decision_reason": row["decision_reason"],
            }
            for row in excluded_scope_rows
        ],
        "library_models": str(args.library_models.resolve()),
        "live_coral_validation": "pending",
        "live_edr_inventory": "pending",
        "outputs": {
            "organism_manifest": organism_path.name,
            "strain_rollup": strain_path.name,
            "library_crosswalk": library_path.name,
        },
        "totals": totals,
    }
    write_json_atomic(metadata_path, metadata)
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
