#!/usr/bin/env python3
"""Strictly compare annotations for EDR candidates with matching FEBa assemblies."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import unquote


TYPE_TO_FEATURE = {
    1: "CDS", 2: "rRNA", 3: "rRNA", 4: "rRNA", 5: "tRNA",
    6: "ncRNA", 7: "pseudogene", 8: "ncRNA", 9: "repeat_region",
    10: "repeat_region", 11: "antisense_RNA", 99: "sequence_feature",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--organism-manifest", required=True, type=Path)
    parser.add_argument("--assembly-report", required=True, type=Path)
    parser.add_argument("--download-report", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument(
        "--all-candidates",
        action="store_true",
        help="Compare annotations for every downloaded version, not only assembly matches",
    )
    return parser.parse_args()


def parse_attributes(value: str) -> dict[str, str]:
    return {
        key: unquote(item)
        for field in value.split(";")
        if "=" in field
        for key, item in [field.split("=", 1)]
    }


def parse_gff(path: Path) -> dict[str, dict[str, Any]]:
    features: dict[str, dict[str, Any]] = {}
    duplicate_counts: dict[str, int] = defaultdict(int)
    with path.open(encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            if raw.startswith("##FASTA"):
                break
            if raw.startswith("#") or not raw.strip():
                continue
            fields = raw.rstrip("\n").split("\t")
            if len(fields) != 9:
                raise ValueError(f"Invalid GFF row at {path}:{line_number}")
            attributes = parse_attributes(fields[8])
            feature_id = attributes.get("ID")
            if not feature_id:
                continue
            if feature_id in features:
                duplicate_counts[feature_id] += 1
                storage_id = f"{feature_id}#duplicate{duplicate_counts[feature_id]}"
            else:
                storage_id = feature_id
            features[storage_id] = {
                "declared_id": feature_id,
                "scaffold_id": fields[0],
                "feature_type": fields[2],
                "begin": int(fields[3]),
                "end": int(fields[4]),
                "strand": fields[6],
                "attributes": attributes,
            }
    return features


def normalize_xref_database(value: str) -> str:
    normalized = value.lower()
    return "uniprot" if normalized in {"uniprot", "uniprotkb"} else normalized


def source_features(connection: sqlite3.Connection, org_id: str) -> dict[str, dict[str, Any]]:
    xrefs: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for locus_id, database, identifier in connection.execute(
        "SELECT locusId, xrefDb, xrefId FROM LocusXref WHERE orgId = ?", (org_id,)
    ):
        xrefs[str(locus_id)].add(
            (normalize_xref_database(str(database)), str(identifier))
        )
    result = {}
    for row in connection.execute(
        "SELECT locusId, sysName, scaffoldId, begin, end, type, strand, gene, desc, GC "
        "FROM Gene WHERE orgId = ?",
        (org_id,),
    ):
        feature_type = TYPE_TO_FEATURE.get(int(row[5]))
        if feature_type is None:
            raise ValueError(f"Unsupported source feature type {row[5]} for {org_id}")
        result[str(row[0])] = {
            "sys_name": str(row[1] or row[0]),
            "scaffold_id": str(row[2]),
            "begin": int(row[3]),
            "end": int(row[4]),
            "feature_type": feature_type,
            "strand": str(row[6]),
            "gene": str(row[7] or ""),
            "description": str(row[8] or ""),
            "gc_fraction": "" if row[9] is None else repr(float(row[9])),
            "xrefs": xrefs.get(str(row[0]), set()),
        }
    return result


def candidate_xrefs(attributes: dict[str, str]) -> set[tuple[str, str]]:
    result = set()
    for value in attributes.get("Dbxref", "").split(","):
        if ":" in value:
            database, identifier = value.split(":", 1)
            result.add((normalize_xref_database(database), identifier))
    return result


def compare(source: dict[str, dict[str, Any]], candidate: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source_ids = set(source)
    candidate_ids = set(candidate)
    missing = sorted(source_ids - candidate_ids)
    extra = sorted(candidate_ids - source_ids)
    structural = []
    metadata = []
    for feature_id in sorted(source_ids & candidate_ids):
        expected = source[feature_id]
        actual = candidate[feature_id]
        structural_fields = ("scaffold_id", "begin", "end", "feature_type", "strand")
        differences = {
            field: {"source": expected[field], "candidate": actual[field]}
            for field in structural_fields
            if expected[field] != actual[field]
        }
        if differences:
            structural.append({"feature_id": feature_id, "differences": differences})
        attributes = actual["attributes"]
        metadata_differences = {}
        for field, attribute in (
            ("sys_name", "locus_tag"),
            ("gene", "gene"),
            ("description", "product"),
            ("gc_fraction", "gc_fraction"),
        ):
            if expected[field] != attributes.get(attribute, ""):
                metadata_differences[field] = {
                    "source": expected[field], "candidate": attributes.get(attribute, "")
                }
        actual_xrefs = candidate_xrefs(attributes)
        missing_xrefs = sorted(expected["xrefs"] - actual_xrefs)
        extra_xrefs = sorted(actual_xrefs - expected["xrefs"])
        if missing_xrefs:
            metadata_differences["missing_source_xrefs"] = missing_xrefs
        if extra_xrefs:
            metadata_differences["extra_candidate_xrefs"] = extra_xrefs
        if metadata_differences:
            metadata.append({"feature_id": feature_id, "differences": metadata_differences})
    return {
        "source_features": len(source),
        "candidate_features": len(candidate),
        "missing_source_feature_ids": missing,
        "extra_candidate_feature_ids": extra,
        "structural_mismatches": structural,
        "metadata_mismatches": metadata,
        "exact_annotation_match": not (missing or extra or structural or metadata),
    }


def main() -> int:
    args = parse_args()
    with args.organism_manifest.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        columns = list(reader.fieldnames or [])
        manifest_rows = [dict(row) for row in reader]
    by_org = {row["fitprivate_orgId"]: row for row in manifest_rows}
    assembly = json.loads(args.assembly_report.read_text(encoding="utf-8"))
    downloads = json.loads(args.download_report.read_text(encoding="utf-8"))["completed"]
    gffs = {
        (row["scope"], row["strain"], row["version"]): Path(row["destination"])
        for row in downloads
        if row["filename"].endswith("_Prodigal.gff")
    }
    connection = sqlite3.connect(f"file:{args.database.resolve()}?mode=ro", uri=True)
    details = []
    try:
        for item in assembly["details"]:
            matches = [
                row
                for row in item["comparisons"]
                if args.all_candidates or row["matches_source_assembly"]
            ]
            if not matches:
                continue
            org_id = item["fitprivate_orgId"]
            source = source_features(connection, org_id)
            candidate_results = []
            for match in matches:
                key = (match["scope"], item["sdt_strain_name"], match["version"])
                result = compare(source, parse_gff(gffs[key]))
                candidate_results.append({**match, **result})
            accepted = [
                row
                for row in candidate_results
                if row["matches_source_assembly"] and row["exact_annotation_match"]
            ]
            manifest_row = by_org[org_id]
            if accepted:
                chosen = accepted[0]
                scope = chosen["scope"]
                manifest_row["exact_match_status"] = (
                    "exact_active_match" if scope == "genome_processing"
                    else "exact_withdrawn_match_decision_required"
                )
                manifest_row["exact_match_location"] = f"{scope}/{chosen['version']}"
                if scope == "genome_processing":
                    manifest_row["reused_edr_version"] = chosen["version"]
            else:
                manifest_row["exact_match_status"] = "no_exact_match"
                manifest_row["exact_match_location"] = ""
            details.append({"fitprivate_orgId": org_id, "candidates": candidate_results})
    finally:
        connection.close()

    temporary = args.organism_manifest.with_name(f".{args.organism_manifest.name}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(manifest_rows)
    os.replace(temporary, args.organism_manifest)
    report = {
        "comparison_scope": "all_candidates" if args.all_candidates else "assembly_matches",
        "organisms_compared": len(details),
        "exact_annotation_matches": sum(
            row["exact_annotation_match"]
            for item in details for row in item["candidates"]
        ),
        "exact_assembly_and_annotation_matches": sum(
            row["matches_source_assembly"] and row["exact_annotation_match"]
            for item in details for row in item["candidates"]
        ),
        "details": details,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    report_temporary = args.report.with_name(f".{args.report.name}.tmp")
    report_temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    os.replace(report_temporary, args.report)
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "comparison_scope",
                    "organisms_compared",
                    "exact_annotation_matches",
                    "exact_assembly_and_annotation_matches",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
