#!/usr/bin/env python3
"""Build the staged CORAL import package for the approved FEBa isolate scope.

The generated generic ndarrays use CORAL unique names for every object_ref.
They never use CORAL-assigned primary keys such as Gene0000001.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = Path("/scratch/jmc/fitprivate-rbtnseq/source/feba.db")
DEFAULT_ORGANISMS = ROOT / "coral_import/feba_20260811/phase0/feba_organism_work_manifest_20260811.tsv"
DEFAULT_LIBRARIES = ROOT / "coral_import/feba_20260811/phase0/feba_library_crosswalk_20260811.tsv"
DEFAULT_GENOMES = ROOT / "coral_import/feba_20260811/production_checkout_20260812/genomes_from_feba/genomes_to_record.tsv"
DEFAULT_OUTPUT = ROOT / "coral_import/feba_20260811/coral_package_20260813"

EXPECTED_DB_SHA256 = "6b9e4edce230b2f82bff90242fe9ca46219598905d2eb775ab4f16ea446a1f11"
PACKAGE_DATE = "2026-08-13"

JAVA_CLASSES = Path("/h/jmc/src/java/classes")
JAVA_JARS = [
    Path("/h/jmc/.m2/repository/com/fasterxml/jackson/core/jackson-annotations/2.5.1/jackson-annotations-2.5.1.jar"),
    Path("/h/jmc/.m2/repository/com/fasterxml/jackson/core/jackson-core/2.5.1/jackson-core-2.5.1.jar"),
    Path("/h/jmc/.m2/repository/com/fasterxml/jackson/core/jackson-databind/2.5.1/jackson-databind-2.5.1.jar"),
    Path("/h/jmc/.m2/repository/com/opencsv/opencsv/4.3.2/opencsv-4.3.2.jar"),
    Path("/h/jmc/.m2/repository/org/apache/commons/commons-lang3/3.4/commons-lang3-3.4.jar"),
]

ASSIGNED_ID = re.compile(r"^(?:Gene|Genome|Condition|TnSeq_Library)\d{7}$")
SAFE_COMPONENT = re.compile(r"^[^\x00-\x20:|][^\x00-\x1f:|]*[^\x00-\x20:|]$|^[^\x00-\x20:|]$")

# These are CORAL typedef field_name values, not BERDL/CDM column aliases.
# Primary-key ``id`` fields are omitted because CORAL assigns them on import.
STATIC_IMPORT_FIELDS = {
    "Genome": ["name", "strain", "n_contigs", "n_features", "link"],
    "Gene": ["gene_id", "genome", "aliases", "contig_number", "strand", "start", "stop", "function"],
    "Condition": ["name"],
    "TnSeq_Library": [
        "name",
        "genome",
        "primers_model",
        "n_mapped_reads",
        "n_barcodes",
        "n_usable_barcodes",
        "n_insertion_locations",
        "hit_rate_essential",
        "hit_rate_other",
    ],
}

STATIC_REQUIRED_FIELDS = {
    "Genome": {"name", "n_contigs", "n_features", "link"},
    "Gene": {"gene_id", "genome", "contig_number", "strand", "start", "stop"},
    "Condition": {"name"},
    "TnSeq_Library": {"name", "genome", "primers_model"},
}


@dataclass(frozen=True)
class Term:
    ref: str
    name: str


TERMS = {
    "fitness_data": Term("DA:0000010", "Gene Knockout Fitness"),
    "metadata_data": Term("DA:0000004", "Environmental Measurement"),
    "gene": Term("ME:0000059", "gene"),
    "gene_id": Term("ME:0000224", "gene ID"),
    "genome_id": Term("ME:0000246", "genome ID"),
    "condition": Term("ME:0000006", "condition"),
    "condition_id": Term("ME:0000200", "condition ID"),
    "library_name": Term("ME:0000262", "Tn-Seq library name"),
    "fitness": Term("ME:0000137", "fitness score"),
    # CheckGeneric currently requires data variables to also be marked as
    # dimension variables. Exact metric semantics that lack that flag are
    # retained in value_context on a validator-compatible numeric carrier.
    "average": Term("ME:0000147", "average"),
    "standard_deviation": Term("ME:0000149", "standard deviation"),
    "correlation": Term("ME:0000168", "correlation"),
    "statistic": Term("ME:0000146", "statistic"),
    "t_score": Term("ME:0000157", "T score"),
    "count": Term("ME:0000126", "count"),
    "temperature": Term("ME:0000123", "temperature"),
    "ph": Term("ME:0000121", "pH"),
    "description": Term("ME:0000202", "description"),
    "comment": Term("ME:0000011", "comment"),
    "person": Term("ME:0000205", "person"),
    "date": Term("ME:0000009", "date"),
    "media": Term("ME:0000049", "media name"),
    "vessel": Term("ME:0000486", "culture vessel"),
    "anaerobic": Term("ME:0000015", "anaerobic"),
    "state": Term("ME:0000037", "physiochemical state"),
    "plate": Term("ME:0000409", "microplate name"),
    "wells": Term("ME:0000410", "microplate well name"),
    "link": Term("ME:0000203", "link"),
    "data_variables_type": Term("ME:0000293", "data variables type"),
    "log_ratio": Term("ME:0000379", "log ratio unit"),
    "dimensionless": Term("UO:0000186", "dimensionless unit"),
    "count_unit": Term("UO:0000189", "count unit"),
    "celsius": Term("UO:0000027", "degree Celsius"),
    "ph_unit": Term("UO:0000196", "pH"),
}


@dataclass(frozen=True)
class ExperimentField:
    source: str
    term_key: str
    scalar_type: str
    unit_key: str | None = None
    normalization: str = "empty_to_null"
    missing_rule: str = "JSON null"
    note: str = ""


EXPERIMENT_FIELDS = [
    ExperimentField("orgId", "description", "string", note="Composite source key part 1"),
    ExperimentField("expName", "description", "string", note="Composite source key part 2"),
    ExperimentField("expDesc", "description", "string"),
    ExperimentField("timeZeroSet", "description", "string"),
    ExperimentField("num", "count", "int", "count_unit", "identity"),
    ExperimentField("nMapped", "count", "int", "count_unit", "identity"),
    ExperimentField("nPastEnd", "count", "int", "count_unit", "identity"),
    ExperimentField("nGenic", "count", "int", "count_unit", "identity"),
    ExperimentField("nUsed", "count", "int", "count_unit", "identity"),
    ExperimentField("gMed", "count", "int", "count_unit", "identity"),
    ExperimentField("gMedt0", "count", "int", "count_unit", "identity"),
    ExperimentField("gMean", "average", "float", "dimensionless", "identity"),
    ExperimentField("cor12", "average", "float", "dimensionless", "identity", note="Source metric is correlation; exact source column retained because CheckGeneric rejects the correlation data-variable term"),
    ExperimentField("mad12", "standard_deviation", "float", "dimensionless", "identity"),
    ExperimentField("mad12c", "standard_deviation", "float", "dimensionless", "identity"),
    ExperimentField("mad12c_t0", "standard_deviation", "float", "dimensionless", "identity"),
    ExperimentField("opcor", "average", "float", "dimensionless", "identity", note="Source metric is correlation; exact source column retained because CheckGeneric rejects the correlation data-variable term"),
    ExperimentField("adjcor", "average", "float", "dimensionless", "identity", note="Source metric is correlation; exact source column retained because CheckGeneric rejects the correlation data-variable term"),
    ExperimentField("gccor", "average", "float", "dimensionless", "identity", note="Source metric is correlation; exact source column retained because CheckGeneric rejects the correlation data-variable term"),
    ExperimentField("maxFit", "fitness", "float", "log_ratio", "identity"),
    ExperimentField("expGroup", "description", "string"),
    ExperimentField("expDescLong", "description", "string"),
    ExperimentField("mutantLibrary", "description", "string", note="Raw FEBa library label; named CORAL library is also an object_ref"),
    ExperimentField("person", "description", "string", note="Source semantic is person; exact source column retained because CheckGeneric rejects the person data-variable term"),
    ExperimentField("dateStarted", "date", "string"),
    ExperimentField("setName", "description", "string"),
    ExperimentField("seqindex", "description", "string"),
    ExperimentField("media", "media", "string"),
    ExperimentField("mediaStrength", "description", "string", normalization="number_to_source_string", note="Preserved without asserting an unvalidated unit"),
    ExperimentField("temperature", "temperature", "float", "celsius", "numeric_text_to_float"),
    ExperimentField("pH", "ph", "float", "ph_unit", "numeric_text_to_float"),
    ExperimentField("vessel", "vessel", "string"),
    ExperimentField("aerobic", "anaerobic", "boolean", normalization="aerobic_to_anaerobic", note="Stored as the logically inverted anaerobic flag, whose CORAL term is validator-compatible"),
    ExperimentField("liquid", "state", "string"),
    ExperimentField("shaking", "description", "string"),
    ExperimentField("condition_1", "description", "string", note="Raw treatment slot; paired raw concentration/unit retained separately"),
    ExperimentField("units_1", "description", "string", note="Raw treatment unit"),
    ExperimentField("concentration_1", "description", "string", note="Raw treatment concentration"),
    ExperimentField("condition_2", "description", "string", note="Raw treatment slot"),
    ExperimentField("units_2", "description", "string", note="Raw treatment unit"),
    ExperimentField("concentration_2", "description", "string", note="Raw treatment concentration"),
    ExperimentField("condition_3", "description", "string", note="Raw treatment slot"),
    ExperimentField("units_3", "description", "string", note="Raw treatment unit"),
    ExperimentField("concentration_3", "description", "string", note="Raw treatment concentration"),
    ExperimentField("condition_4", "description", "string", note="Raw treatment slot"),
    ExperimentField("units_4", "description", "string", note="Raw treatment unit"),
    ExperimentField("concentration_4", "description", "string", note="Raw treatment concentration"),
    ExperimentField("growthPlate", "plate", "string"),
    ExperimentField("growthWells", "wells", "string"),
    ExperimentField("nGenerations", "average", "float", "dimensionless", "identity", note="Can be fractional; exact source column retained because count only permits integer"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--organisms", type=Path, default=DEFAULT_ORGANISMS)
    parser.add_argument("--libraries", type=Path, default=DEFAULT_LIBRARIES)
    parser.add_argument("--genomes", type=Path, default=DEFAULT_GENOMES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-checkgeneric", action="store_true")
    parser.add_argument(
        "--verified-database-sha256",
        help="Reuse a SHA-256 verified earlier in the same run session instead of rereading the 29 GB source",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, fieldnames: Sequence[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def validate_static_import_tsv(path: Path, object_type: str) -> None:
    """Validate a generated static TSV against CORAL import field names."""
    expected = STATIC_IMPORT_FIELDS[object_type]
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        actual = reader.fieldnames
        if actual != expected:
            raise ValueError(
                f"{object_type} static import headers do not match CORAL typedef field names: "
                f"expected {expected}, found {actual}"
            )
        for line_number, row in enumerate(reader, start=2):
            for field in STATIC_REQUIRED_FIELDS[object_type]:
                value = row[field]
                if value is None or not value.strip() or value.strip().lower() in {"null", "nan"}:
                    raise ValueError(
                        f"{path.name}:{line_number} has no value for required CORAL property {field!r}"
                    )


def term(key: str) -> dict[str, str]:
    value = TERMS[key]
    return {"term_name": value.name, "oterm_ref": value.ref, "oterm_name": value.name}


def scalar_property(term_key: str, scalar_type: str, value: Any) -> dict[str, Any]:
    key = {"string": "string_value", "oterm_ref": "oterm_ref"}[scalar_type]
    return {"value_type": term(term_key), "value": {"scalar_type": scalar_type, key: value}}


def source_context(source: str, extra: str = "") -> list[dict[str, Any]]:
    value = f"source column: {source}"
    if extra:
        value += f"; {extra}"
    return [scalar_property("comment", "string", value)]


def t_score_context() -> list[dict[str, Any]]:
    return [
        scalar_property("statistic", "oterm_ref", TERMS["t_score"].ref),
        *source_context("t", "FEBa t statistic"),
    ]


def typed_values(
    term_key: str,
    scalar_type: str,
    values: Sequence[Any],
    *,
    unit_key: str | None = None,
    context: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    value_key = {
        "string": "string_values",
        "int": "int_values",
        "float": "float_values",
        "boolean": "boolean_values",
        "object_ref": "object_refs",
    }[scalar_type]
    value_doc: dict[str, Any] = {"scalar_type": scalar_type, value_key: list(values)}
    if scalar_type == "object_ref":
        value_doc["string_values"] = list(values)
    doc: dict[str, Any] = {"value_type": term(term_key), "values": value_doc}
    if unit_key:
        doc["value_units"] = term(unit_key)
    if context:
        doc["value_context"] = context
    return doc


def qualified_gene_name(genome_name: str, locus_id: str) -> str:
    validate_component(genome_name, "genome name")
    validate_component(locus_id, "FEBa locusId")
    return f"{genome_name}:{locus_id}"


def condition_name(strain_name: str, exp_name: str) -> str:
    validate_component(strain_name, "strain name")
    validate_component(exp_name, "FEBa expName")
    return f"{strain_name}:{exp_name}"


def library_name(genome_name: str, source_library: str) -> str:
    validate_component(genome_name, "genome name")
    validate_component(source_library, "FEBa mutantLibrary")
    return f"{genome_name}.{source_library}.tnseq_library"


def brick_name(genome_name: str) -> str:
    validate_component(genome_name, "genome name")
    return f"feba_tnseq_fitness_{genome_name}.ndarray"


def validate_component(value: str, label: str) -> None:
    if not value or not SAFE_COMPONENT.fullmatch(value):
        raise ValueError(f"Unsafe {label}: {value!r}")


def normalize_value(field: ExperimentField, value: Any) -> Any:
    if field.normalization == "identity":
        result = value
    elif field.normalization == "empty_to_null":
        result = None if value == "" else value
    elif field.normalization == "number_to_source_string":
        result = None if value is None or value == "" else str(value)
    elif field.normalization == "numeric_text_to_float":
        result = None if value is None or str(value).strip() == "" else float(value)
    elif field.normalization == "aerobic_to_anaerobic":
        normalized = str(value).strip().lower()
        if not normalized:
            result = None
        elif normalized == "aerobic":
            result = 0
        elif normalized == "anaerobic":
            result = 1
        else:
            raise ValueError(f"Unrecognized aerobic value: {value!r}")
    else:
        raise ValueError(f"Unknown normalization: {field.normalization}")
    if isinstance(result, float) and not math.isfinite(result):
        raise ValueError(f"Non-finite value in {field.source}: {result}")
    return result


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def object_refs(document: Any) -> Iterable[str]:
    if isinstance(document, dict):
        for key, value in document.items():
            if key == "object_refs":
                yield from value
            else:
                yield from object_refs(value)
    elif isinstance(document, list):
        for value in document:
            yield from object_refs(value)


def validate_object_refs(document: dict[str, Any], allowed: set[str]) -> dict[str, int]:
    refs = list(object_refs(document))
    bad_ids = sorted({ref for ref in refs if ASSIGNED_ID.fullmatch(ref)})
    missing = sorted(set(refs) - allowed)
    if bad_ids:
        raise ValueError(f"CORAL-assigned IDs found in object_refs: {bad_ids[:10]}")
    if missing:
        raise ValueError(f"object_refs do not resolve to staged names: {missing[:10]}")
    return {"references": len(refs), "unique_references": len(set(refs))}


def java_classpath() -> str:
    entries = [JAVA_CLASSES, *JAVA_JARS]
    missing = [str(path) for path in entries if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing Java classpath entries: {missing}")
    return os.pathsep.join(str(path) for path in entries)


def check_generic(json_path: Path, check_path: Path) -> None:
    result = subprocess.run(
        ["java", "-Xmx12g", "-cp", java_classpath(), "gov.lbl.enigma.app.CheckGeneric", str(json_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout or "") + (result.stderr or "")
    check_path.write_text(output)
    if result.returncode != 0 or "Generic is OK!" not in output or "Exception:" in output:
        raise RuntimeError(f"CheckGeneric failed for {json_path}:\n{output}")


def validate_inputs(
    connection: sqlite3.Connection,
    organisms: list[dict[str, str]],
    libraries: list[dict[str, str]],
    genomes: list[dict[str, str]],
) -> None:
    if len(organisms) != 22 or len(genomes) != 22 or len(libraries) != 34:
        raise ValueError(
            f"Expected 22 organisms, 22 genomes, and 34 libraries; got "
            f"{len(organisms)}, {len(genomes)}, and {len(libraries)}"
        )
    org_ids = [row["fitprivate_orgId"] for row in organisms]
    if len(set(org_ids)) != len(org_ids):
        raise ValueError("Duplicate organism rows")
    if {row["fitprivate_orgId"] for row in genomes} != set(org_ids):
        raise ValueError("Genome input and organism manifest scopes differ")
    if {row["fitprivate_orgId"] for row in libraries} != set(org_ids):
        raise ValueError("Library crosswalk and organism manifest scopes differ")
    if any(not row["primers_model"] for row in libraries):
        raise ValueError("At least one library has no primers_model")
    tables = {
        row[0].lower(): row[0]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    for org_id in org_ids:
        expected = f"FitByExp_{org_id}".lower()
        if expected not in tables:
            raise ValueError(f"Missing fitness table for {org_id}")


def build_static_objects(
    connection: sqlite3.Connection,
    stage: Path,
    organisms: list[dict[str, str]],
    libraries: list[dict[str, str]],
    genomes: list[dict[str, str]],
) -> tuple[dict[str, Any], dict[str, str], dict[tuple[str, str], str], set[str]]:
    static = stage / "static"
    static.mkdir()
    org_manifest = {row["fitprivate_orgId"]: row for row in organisms}
    genome_input = {row["fitprivate_orgId"]: row for row in genomes}
    genome_by_org = {org: row["genome_name"] for org, row in genome_input.items()}

    genome_rows = []
    genome_names: set[str] = set()
    for row in organisms:
        org = row["fitprivate_orgId"]
        genome = genome_input[org]
        name = genome["genome_name"]
        if name != row["target_coral_genome_name"]:
            raise ValueError(f"Genome-name disagreement for {org}: {name} vs {row['target_coral_genome_name']}")
        genome_names.add(name)
        genome_rows.append(
            {
                "name": name,
                "strain": row["sdt_strain_name"],
                "n_contigs": int(row["scaffold_count"]),
                "n_features": int(row["gene_count"]),
                "link": f"enigma-data-repository/genome_processing/{row['sdt_strain_name']}/assembliesAndAnnotations/{name}/",
            }
        )
    genome_path = static / f"Genome_feba_{PACKAGE_DATE.replace('-', '')}.tsv"
    write_tsv(genome_path, STATIC_IMPORT_FIELDS["Genome"], genome_rows)
    validate_static_import_tsv(genome_path, "Genome")

    scaffold_numbers: dict[tuple[str, str], int] = {}
    gene_names: set[str] = set()
    gene_rows = []
    for row in organisms:
        org = row["fitprivate_orgId"]
        genome_name_value = genome_by_org[org]
        scaffolds = [
            item[0]
            for item in connection.execute(
                "SELECT scaffoldId FROM ScaffoldSeq WHERE orgId=? ORDER BY scaffoldId", (org,)
            )
        ]
        if len(scaffolds) != int(row["scaffold_count"]):
            raise ValueError(f"Scaffold count mismatch for {org}")
        for number, scaffold in enumerate(scaffolds, start=1):
            scaffold_numbers[(org, scaffold)] = number

        xrefs: dict[str, list[str]] = defaultdict(list)
        for locus, database, xref in connection.execute(
            "SELECT locusId,xrefDb,xrefId FROM LocusXref WHERE orgId=? ORDER BY locusId,xrefDb,xrefId",
            (org,),
        ):
            xrefs[locus].append(f"{database}:{xref}")
        source_genes = connection.execute(
            "SELECT locusId,sysName,scaffoldId,begin,end,strand,gene,desc FROM Gene WHERE orgId=? ORDER BY locusId",
            (org,),
        )
        count = 0
        for locus, sys_name, scaffold, begin, end, strand, gene, description in source_genes:
            name = qualified_gene_name(genome_name_value, locus)
            aliases = []
            for alias in [locus, sys_name, gene, *xrefs.get(locus, [])]:
                if alias and alias != name and alias not in aliases:
                    aliases.append(alias)
            gene_names.add(name)
            gene_rows.append(
                {
                    "gene_id": name,
                    "genome": genome_name_value,
                    "aliases": ",".join(aliases),
                    "contig_number": scaffold_numbers[(org, scaffold)],
                    "strand": strand,
                    "start": int(begin),
                    "stop": int(end),
                    "function": description if description else "null",
                }
            )
            count += 1
        if count != int(row["gene_count"]):
            raise ValueError(f"Gene count mismatch for {org}: {count} vs {row['gene_count']}")
    if len(gene_names) != len(gene_rows):
        raise ValueError("Qualified gene names are not globally unique")
    gene_path = static / f"Gene_feba_{PACKAGE_DATE.replace('-', '')}.tsv"
    write_tsv(gene_path, STATIC_IMPORT_FIELDS["Gene"], gene_rows)
    validate_static_import_tsv(gene_path, "Gene")

    condition_rows = []
    condition_names: set[str] = set()
    expected_conditions = 0
    for row in organisms:
        org = row["fitprivate_orgId"]
        strain = row["sdt_strain_name"]
        exps = [item[0] for item in connection.execute("SELECT expName FROM Experiment WHERE orgId=? ORDER BY expName", (org,))]
        expected_conditions += int(row["experiment_count"])
        if len(exps) != int(row["experiment_count"]):
            raise ValueError(f"Experiment count mismatch for {org}")
        for exp in exps:
            name = condition_name(strain, exp)
            condition_names.add(name)
            condition_rows.append({"name": name})
    if len(condition_names) != expected_conditions:
        raise ValueError("Qualified condition names are not globally unique")
    condition_path = static / f"Condition_feba_{PACKAGE_DATE.replace('-', '')}.tsv"
    write_tsv(condition_path, STATIC_IMPORT_FIELDS["Condition"], condition_rows)
    validate_static_import_tsv(condition_path, "Condition")

    library_rows = []
    library_lookup: dict[tuple[str, str], str] = {}
    library_names: set[str] = set()
    for row in libraries:
        org = row["fitprivate_orgId"]
        source = row["source_mutant_library"]
        name = library_name(genome_by_org[org], source)
        library_lookup[(org, source)] = name
        library_names.add(name)
        library_rows.append(
            {
                "name": name,
                "genome": genome_by_org[org],
                "primers_model": row["primers_model"],
                "n_mapped_reads": "null",
                "n_barcodes": "null",
                "n_usable_barcodes": "null",
                "n_insertion_locations": "null",
                "hit_rate_essential": "null",
                "hit_rate_other": "null",
            }
        )
    if len(library_names) != len(library_rows):
        raise ValueError("Generated TnSeq library names are not unique")
    library_path = static / f"TnSeq_Library_feba_{PACKAGE_DATE.replace('-', '')}.tsv"
    write_tsv(library_path, STATIC_IMPORT_FIELDS["TnSeq_Library"], library_rows)
    validate_static_import_tsv(library_path, "TnSeq_Library")
    allowed = gene_names | genome_names | condition_names | library_names
    counts = {
        "genomes": len(genome_rows),
        "genes": len(gene_rows),
        "conditions": len(condition_rows),
        "tnseq_libraries": len(library_rows),
    }
    return counts, genome_by_org, library_lookup, allowed


def build_metadata_brick(
    connection: sqlite3.Connection,
    stage: Path,
    organisms: list[dict[str, str]],
    genome_by_org: dict[str, str],
    library_lookup: dict[tuple[str, str], str],
    allowed_refs: set[str],
    skip_checkgeneric: bool,
) -> tuple[str, int, dict[str, int], list[dict[str, str]]]:
    experiments = []
    crosswalk_rows = []
    for manifest in organisms:
        org = manifest["fitprivate_orgId"]
        cursor = connection.execute("SELECT * FROM Experiment WHERE orgId=? ORDER BY expName", (org,))
        columns = [item[0] for item in cursor.description]
        for raw in cursor:
            row = dict(zip(columns, raw))
            source_library = row["mutantLibrary"]
            key = (org, source_library)
            if key not in library_lookup:
                raise ValueError(f"Experiment library is absent from approved crosswalk: {key}")
            row["condition_name"] = condition_name(manifest["sdt_strain_name"], row["expName"])
            row["library_name"] = library_lookup[key]
            row["genome_name"] = genome_by_org[org]
            experiments.append(row)
            crosswalk_rows.append(
                {
                    "fitprivate_orgId": org,
                    "fitprivate_expName": row["expName"],
                    "condition_name": row["condition_name"],
                    "source_mutant_library": source_library,
                    "tnseq_library_name": row["library_name"],
                    "genome_name": row["genome_name"],
                }
            )
    if len(experiments) != 3846:
        raise ValueError(f"Expected 3,846 experiments, found {len(experiments)}")

    condition_values = [row["condition_name"] for row in experiments]
    library_values = [row["library_name"] for row in experiments]
    genome_values = [row["genome_name"] for row in experiments]
    dim_variables = [
        typed_values("condition_id", "object_ref", condition_values),
        typed_values("library_name", "object_ref", library_values),
        typed_values("genome_id", "object_ref", genome_values),
    ]
    variables = []
    for field in EXPERIMENT_FIELDS:
        values = [normalize_value(field, row[field.source]) for row in experiments]
        variables.append(
            typed_values(
                field.term_key,
                field.scalar_type,
                values,
                unit_key=field.unit_key,
                context=source_context(field.source, field.note),
            )
        )
    name = "feba_tnseq_condition_metadata_20260813.ndarray"
    document = {
        "name": name,
        "description": "FEBa TnSeq experimental conditions and quality metadata for the approved ENIGMA isolate import",
        "data_type": term("metadata_data"),
        "array_context": [
            scalar_property("data_variables_type", "oterm_ref", TERMS["metadata_data"].ref),
            scalar_property("link", "string", "enigma.fitprivate.experiment(orgId, expName)"),
            scalar_property("comment", "string", "Composite external relationship: (fitprivate_orgId, fitprivate_expName) -> enigma.fitprivate.experiment(orgId, expName)"),
        ],
        "n_dimensions": 1,
        "dim_context": [{"data_type": term("condition"), "size": len(experiments), "typed_values": dim_variables}],
        "typed_values": variables,
    }
    ref_audit = validate_object_refs(document, allowed_refs)
    json_dir = stage / "json"
    check_dir = stage / "check"
    json_path = json_dir / name.replace(".ndarray", ".json")
    with json_path.open("w") as handle:
        json.dump(document, handle, separators=(",", ":"), allow_nan=False)
    if not skip_checkgeneric:
        check_generic(json_path, check_dir / f"{json_path.name}.check")
    return name, len(experiments), ref_audit, crosswalk_rows


def fitness_table(connection: sqlite3.Connection, org: str) -> str:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND lower(name)=lower(?)",
        (f"FitByExp_{org}",),
    ).fetchone()
    if not row:
        raise ValueError(f"No FitByExp table for {org}")
    return row[0]


def build_fitness_bricks(
    connection: sqlite3.Connection,
    stage: Path,
    organisms: list[dict[str, str]],
    genome_by_org: dict[str, str],
    library_lookup: dict[tuple[str, str], str],
    allowed_refs: set[str],
    skip_checkgeneric: bool,
) -> tuple[list[dict[str, Any]], int]:
    results = []
    total_cells = 0
    for number, manifest in enumerate(organisms, start=1):
        org = manifest["fitprivate_orgId"]
        strain = manifest["sdt_strain_name"]
        genome = genome_by_org[org]
        table = fitness_table(connection, org)
        loci = [row[0] for row in connection.execute(f"SELECT DISTINCT locusId FROM {quote_identifier(table)} ORDER BY locusId")]
        exps = [row[0] for row in connection.execute(f"SELECT DISTINCT expName FROM {quote_identifier(table)} ORDER BY expName")]
        source_exps = [row[0] for row in connection.execute("SELECT expName FROM Experiment WHERE orgId=? ORDER BY expName", (org,))]
        if exps != source_exps:
            raise ValueError(f"Fitness experiment set differs from Experiment for {org}")
        source_loci = {row[0] for row in connection.execute("SELECT locusId FROM Gene WHERE orgId=?", (org,))}
        orphan_loci = sorted(set(loci) - source_loci)
        if orphan_loci:
            raise ValueError(f"Orphan fitness loci for {org}: {orphan_loci[:10]}")
        expected_cells = len(loci) * len(exps)
        source_count = connection.execute(f"SELECT count(*) FROM {quote_identifier(table)}").fetchone()[0]
        if source_count != expected_cells:
            raise ValueError(f"Non-rectangular fitness table for {org}: {source_count} vs {expected_cells}")

        gene_values = [qualified_gene_name(genome, locus) for locus in loci]
        condition_values = [condition_name(strain, exp) for exp in exps]
        exp_library = {
            exp: library_lookup[(org, library)]
            for exp, library in connection.execute(
                "SELECT expName,mutantLibrary FROM Experiment WHERE orgId=?", (org,)
            )
        }
        library_values = [exp_library[exp] for exp in exps]
        fit_values: list[float] = []
        t_values: list[float] = []
        cursor = connection.execute(
            f"SELECT locusId,expName,fit,t FROM {quote_identifier(table)} ORDER BY locusId,expName"
        )
        for index, (locus, exp, fit, t_value) in enumerate(cursor):
            expected_locus = loci[index // len(exps)]
            expected_exp = exps[index % len(exps)]
            if locus != expected_locus or exp != expected_exp:
                raise ValueError(f"Unexpected fitness cell order/content for {org} at {index}: {(locus, exp)}")
            fit_value = float(fit)
            statistic = float(t_value)
            if not math.isfinite(fit_value) or not math.isfinite(statistic):
                raise ValueError(f"Non-finite fitness value for {org}, {locus}, {exp}")
            fit_values.append(fit_value)
            t_values.append(statistic)
        if len(fit_values) != expected_cells:
            raise ValueError(f"Fitness value count mismatch for {org}")

        name = brick_name(genome)
        document = {
            "name": name,
            "description": f"FEBa TnSeq gene fitness scores and t statistics for {strain} using genome {genome}",
            "data_type": term("fitness_data"),
            "array_context": [],
            "n_dimensions": 2,
            "dim_context": [
                {
                    "data_type": term("gene"),
                    "size": len(gene_values),
                    "typed_values": [
                        typed_values("gene_id", "object_ref", gene_values),
                        typed_values("genome_id", "object_ref", [genome] * len(gene_values)),
                    ],
                },
                {
                    "data_type": term("condition"),
                    "size": len(condition_values),
                    "typed_values": [
                        typed_values("condition_id", "object_ref", condition_values),
                        typed_values("library_name", "object_ref", library_values),
                    ],
                },
            ],
            "typed_values": [
                typed_values("fitness", "float", fit_values, unit_key="log_ratio"),
                typed_values(
                    "average",
                    "float",
                    t_values,
                    unit_key="dimensionless",
                    context=t_score_context(),
                ),
            ],
        }
        ref_audit = validate_object_refs(document, allowed_refs)
        json_path = stage / "json" / name.replace(".ndarray", ".json")
        with json_path.open("w") as handle:
            json.dump(document, handle, separators=(",", ":"), allow_nan=False)
        if not skip_checkgeneric:
            check_generic(json_path, stage / "check" / f"{json_path.name}.check")
        total_cells += expected_cells
        result = {
            "fitprivate_orgId": org,
            "strain_name": strain,
            "genome_name": genome,
            "brick_name": name,
            "gene_count": len(gene_values),
            "condition_count": len(condition_values),
            "cell_count": expected_cells,
            "fitness_value_count": len(fit_values),
            "t_value_count": len(t_values),
            **ref_audit,
        }
        results.append(result)
        print(f"[{number:02d}/{len(organisms)}] built {name}: {len(gene_values)} x {len(exps)} = {expected_cells}", flush=True)
    return results, total_cells


def write_mapping_reports(stage: Path, crosswalk_rows: list[dict[str, str]]) -> None:
    reports = stage / "reports"
    mapping_rows = []
    for field in EXPERIMENT_FIELDS:
        mapping_rows.append(
            {
                "source_column": field.source,
                "coral_term": f"{TERMS[field.term_key].name} <{TERMS[field.term_key].ref}>",
                "scalar_type": field.scalar_type,
                "unit": "" if not field.unit_key else f"{TERMS[field.unit_key].name} <{TERMS[field.unit_key].ref}>",
                "normalization": field.normalization,
                "missing_value": field.missing_rule,
                "notes": field.note,
            }
        )
    mapping_rows.append(
        {
            "source_column": "pubId",
            "coral_term": "EXCLUDED",
            "scalar_type": "",
            "unit": "",
            "normalization": "excluded",
            "missing_value": "not applicable",
            "notes": "Excluded because the approved plan forbids public Fitness Browser provenance for this private snapshot",
        }
    )
    write_tsv(reports / "experiment_column_mapping.tsv", ["source_column", "coral_term", "scalar_type", "unit", "normalization", "missing_value", "notes"], mapping_rows)
    write_tsv(reports / "condition_library_genome_crosswalk.tsv", ["fitprivate_orgId", "fitprivate_expName", "condition_name", "source_mutant_library", "tnseq_library_name", "genome_name"], crosswalk_rows)


def write_processes(
    connection: sqlite3.Connection,
    stage: Path,
    organisms: list[dict[str, str]],
    genome_by_org: dict[str, str],
    library_lookup: dict[tuple[str, str], str],
) -> None:
    rows = []
    for manifest in organisms:
        org = manifest["fitprivate_orgId"]
        libraries = sorted({
            library_lookup[(org, row[0])]
            for row in connection.execute("SELECT DISTINCT mutantLibrary FROM Experiment WHERE orgId=?", (org,))
        })
        dates = sorted({
            row[0]
            for row in connection.execute("SELECT dateStarted FROM Experiment WHERE orgId=?", (org,))
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", row[0] or "")
        })
        rows.append(
            {
                "process": "Assay Fitness <PROCESS:0000010>",
                "person": "Deutschbauer Lab <ENIGMA:0000058>",
                "campaign": "Predictive Network Biology <ENIGMA:0000006>",
                "protocol": "null",
                "date_start": dates[0] if dates else "null",
                "date_end": dates[-1] if dates else "null",
                "input_objects": ", ".join(f"TnSeq_Library: {name}" for name in libraries),
                "output_objects": f"Generic: {brick_name(genome_by_org[org])}",
            }
        )
    write_tsv(stage / "process" / "process_assay_fitness_feba_20260813.tsv", ["process", "person", "campaign", "protocol", "date_start", "date_end", "input_objects", "output_objects"], rows)


def write_import_helpers(stage: Path, fitness_results: list[dict[str, Any]], metadata_name: str) -> None:
    static_files = [
        "Genome_feba_20260813.tsv",
        "Gene_feba_20260813.tsv",
        "Condition_feba_20260813.tsv",
        "TnSeq_Library_feba_20260813.tsv",
    ]
    (stage / "import_static_to_coral.py").write_text(
        "# Copy static/*.tsv into CORAL's entity import directory, then run in order.\n"
        + "\n".join(
            [
                "toolx.update_core('Genome_feba_20260813.tsv', 'Genome')",
                "toolx.update_core('Gene_feba_20260813.tsv', 'Gene')",
                "toolx.update_core('Condition_feba_20260813.tsv', 'Condition')",
                "toolx.update_core('TnSeq_Library_feba_20260813.tsv', 'TnSeq_Library')",
            ]
        )
        + "\n"
    )
    brick_files = [metadata_name.replace(".ndarray", ".json")] + [row["brick_name"].replace(".ndarray", ".json") for row in fitness_results]
    (stage / "import_bricks_to_coral.py").write_text(
        "# Run only after all staged static names and foreign keys have been re-polled and verified.\n"
        + "\n".join(f"toolx.upload_brick('{name}')" for name in brick_files)
        + "\n"
        + "toolx.upload_process('Assay Fitness', 'process_assay_fitness_feba_20260813.tsv')\n"
    )
    (stage / "files_to_import.txt").write_text(
        "\n".join(
            [
                *(f"static/{name}" for name in static_files),
                *(f"json/{name}" for name in brick_files),
                "process/process_assay_fitness_feba_20260813.tsv",
                "post_import/process_update_data_n2e2_after_validation_20260813.tsv",
            ]
        )
        + "\n"
    )
    post = stage / "post_import"
    post.mkdir()
    n2e2 = next(row for row in fitness_results if row["fitprivate_orgId"] == "pseudo6_N2E2")
    write_tsv(
        post / "process_update_data_n2e2_after_validation_20260813.tsv",
        ["process", "person", "campaign", "protocol", "date_start", "date_end", "input_objects", "output_objects"],
        [{
            "process": "Update Data <PROCESS:0000053>",
            "person": "John-Marc Chandonia <ENIGMA:0000057>",
            "campaign": "Predictive Network Biology <ENIGMA:0000006>",
            "protocol": "null",
            "date_start": PACKAGE_DATE,
            "date_end": PACKAGE_DATE,
            "input_objects": "Generic: tnseq_n2e2.ndarray",
            "output_objects": f"Generic: {n2e2['brick_name']}",
        }],
    )
    (stage / "import_n2e2_obsoletion_to_coral.py").write_text(
        "# Run only after validating the new N2E2 brick and its Assay Fitness process.\n"
        "toolx.upload_process('Update Data', "
        "'process_update_data_n2e2_after_validation_20260813.tsv')\n"
    )
    (post / "README.md").write_text(
        "# Deferred N2E2 obsoletion\n\n"
        "Do not import this process with the main package. First import and validate the new N2E2 genome, genes, TnSeq library, fitness brick, object references, values, and producing process. Only then copy `process_update_data_n2e2_after_validation_20260813.tsv` to CORAL's process import directory and run `import_n2e2_obsoletion_to_coral.py` to upload it as an `Update Data` process and obsolete the legacy `tnseq_n2e2.ndarray` brick.\n"
    )


def write_readme(stage: Path, summary: dict[str, Any], skip_checkgeneric: bool) -> None:
    stage.joinpath("README.md").write_text(
        f"""# FEBa CORAL import package ({PACKAGE_DATE})

This staged package contains the approved 22 ENIGMA isolate organisms only. It has not been imported into CORAL.

## Identifier contract

All brick `object_ref` values are stable CORAL unique names, not CORAL-assigned primary keys:

- genes: `<versioned-genome-name>:<FEBa-locusId>`;
- genomes: the allocated EDR/CORAL genome name, such as `FW300-N2E2.3`;
- conditions: `<strain-name>:<FEBa-expName>`;
- TnSeq libraries: `<versioned-genome-name>.<source-mutant-library>.tnseq_library`.

Generation rejects `Gene0000001`, `Genome0000001`, `Condition0000001`, and `TnSeq_Library0000001`-style references and verifies every object reference against the names staged in `static/`.

## Static TSV contract

Static TSV headers are literal CORAL typedef `field_name` values, not BERDL/CDM column aliases. CORAL assigns the primary-key `id`, so additions omit it. The required reference-bearing headers are `Genome.strain`, `Gene.gene_id`, `Gene.genome`, and `TnSeq_Library.genome`; the generator rejects unexpected headers and missing required values before publishing the package.

## Import sequence

1. Copy the four `static/` files into CORAL's entity import directory and run `import_static_to_coral.py`.
2. Stop. Re-poll Genome, Gene, Condition, and TnSeq_Library and verify names, row counts, and foreign keys.
3. Copy the 23 files in `json/` and the Assay Fitness process TSV into the applicable CORAL import directories.
4. Run `import_bricks_to_coral.py` and re-poll/validate each immutable brick and its process.
5. After the new N2E2 objects and Assay Fitness process pass post-import validation, copy the deferred process TSV to CORAL's process import directory and run `import_n2e2_obsoletion_to_coral.py`.

The metadata brick contains the experiment data; `reports/condition_library_genome_crosswalk.tsv` is an audit artifact, not a CORAL data sidecar. `pubId` is deliberately excluded. The SQLite location and checksum are recorded only in `reports/package_summary.json` and are not array-level metadata.

CheckGeneric status: {"SKIPPED by request" if skip_checkgeneric else "passed for all 23 bricks"}.

Counts: {summary['static_counts']['genomes']} genomes, {summary['static_counts']['genes']:,} genes, {summary['static_counts']['conditions']:,} conditions, {summary['static_counts']['tnseq_libraries']} TnSeq libraries, {summary['fitness_bricks']} fitness bricks, and {summary['fitness_cells']:,} fitness matrix cells.
"""
    )


def write_checksums(stage: Path) -> None:
    paths = sorted(path for path in stage.rglob("*") if path.is_file() and path.name != "checksums.sha256")
    stage.joinpath("checksums.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(stage)}\n" for path in paths)
    )


def main() -> None:
    args = parse_args()
    for path in (args.database, args.organisms, args.libraries, args.genomes):
        if not path.exists():
            raise FileNotFoundError(path)
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite existing package: {args.output}")
    database_sha = args.verified_database_sha256 or sha256(args.database)
    if database_sha != EXPECTED_DB_SHA256:
        raise ValueError(f"Unexpected feba.db SHA-256: {database_sha}")
    organisms = read_tsv(args.organisms)
    libraries = read_tsv(args.libraries)
    genomes = read_tsv(args.genomes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{args.output.name}.", dir=args.output.parent))
    try:
        for directory in ("json", "check", "process", "reports"):
            (stage / directory).mkdir()
        connection = sqlite3.connect(f"file:{args.database}?mode=ro", uri=True)
        connection.execute("PRAGMA query_only=ON")
        validate_inputs(connection, organisms, libraries, genomes)
        static_counts, genome_by_org, library_lookup, allowed_refs = build_static_objects(
            connection, stage, organisms, libraries, genomes
        )
        print(f"built static objects: {static_counts}", flush=True)
        metadata_name, metadata_conditions, metadata_ref_audit, crosswalk_rows = build_metadata_brick(
            connection, stage, organisms, genome_by_org, library_lookup, allowed_refs, args.skip_checkgeneric
        )
        print(f"built {metadata_name}: {metadata_conditions} conditions", flush=True)
        fitness_results, total_cells = build_fitness_bricks(
            connection, stage, organisms, genome_by_org, library_lookup, allowed_refs, args.skip_checkgeneric
        )
        if total_cells != 16_292_891:
            raise ValueError(f"Expected 16,292,891 fitness cells, found {total_cells}")
        write_mapping_reports(stage, crosswalk_rows)
        write_processes(connection, stage, organisms, genome_by_org, library_lookup)
        connection.close()
        write_tsv(
            stage / "reports" / "fitness_brick_manifest.tsv",
            ["fitprivate_orgId", "strain_name", "genome_name", "brick_name", "gene_count", "condition_count", "cell_count", "fitness_value_count", "t_value_count", "references", "unique_references"],
            fitness_results,
        )
        summary = {
            "package_date": PACKAGE_DATE,
            "source_namespace": "enigma.fitprivate",
            "source_database": str(args.database),
            "source_database_sha256": database_sha,
            "approved_organisms": len(organisms),
            "static_counts": static_counts,
            "condition_metadata_brick": metadata_name,
            "condition_metadata_rows": metadata_conditions,
            "condition_metadata_reference_audit": metadata_ref_audit,
            "fitness_bricks": len(fitness_results),
            "fitness_cells": total_cells,
            "fitness_values": total_cells,
            "t_values": total_cells,
            "generic_bricks": len(fitness_results) + 1,
            "checkgeneric_passed": not args.skip_checkgeneric,
            "object_reference_policy": "stable CORAL unique names only; assigned IDs forbidden",
        }
        (stage / "reports" / "package_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        write_import_helpers(stage, fitness_results, metadata_name)
        write_readme(stage, summary, args.skip_checkgeneric)
        write_checksums(stage)
        stage.rename(args.output)
        print(f"complete: {args.output}", flush=True)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


if __name__ == "__main__":
    main()
