#!/usr/bin/env python3
"""Build a CORAL update package from a newer fitprivate (FEBa) snapshot.

The first import (build_feba_coral_import.py, 2026-08) loaded every in-scope
ENIGMA isolate from one snapshot. This tool compares a newer snapshot with the
one already represented in CORAL and stages only what changed:

- a new organism: Genome, Gene, Condition and TnSeq_Library additions, a new
  fitness brick and its Assay Fitness process;
- an existing organism whose fitness payload changed: Condition additions for
  new experiments, a replacement fitness brick (next _vN name) and a
  one-to-one Update Data process from the current brick;
- a replacement condition-metadata brick covering every in-scope experiment
  of the new snapshot, with its Update Data process.

Organisms whose genes, experiments and fitness values are identical in both
snapshots produce nothing. Brick documents are built with the same helpers as
the first import, so structure, terms and identifier rules are unchanged.

The tool only writes a local package. It never contacts CORAL.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_feba_coral_import as base  # noqa: E402

ROOT = base.ROOT
PROCESS_FIELDS = ["process", "person", "campaign", "protocol", "date_start", "date_end", "input_objects", "output_objects"]
UPDATE_PERSON = "John-Marc Chandonia <ENIGMA:0000057>"
ASSAY_PERSON = "Deutschbauer Lab <ENIGMA:0000058>"
CAMPAIGN = "Predictive Network Biology <ENIGMA:0000006>"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-database", type=Path, required=True, help="Snapshot already represented in CORAL")
    parser.add_argument("--new-database", type=Path, required=True)
    parser.add_argument("--new-database-sha256", required=True, help="Verified SHA-256 of --new-database")
    parser.add_argument("--release-label", required=True, help="Text naming the new fitprivate release, e.g. 2026-10-21")
    parser.add_argument("--scope", type=Path, required=True, help="TSV: fitprivate_orgId, sdt_strain_name (in-scope ENIGMA isolates)")
    parser.add_argument("--genomes", type=Path, required=True, help="TSV: fitprivate_orgId, genome_name (every in-scope organism)")
    parser.add_argument("--library-models", type=Path, required=True, help="TSV: fitprivate_orgId, source_mutant_library, primers_model")
    parser.add_argument("--current-bricks", type=Path, required=True, help="TSV: fitprivate_orgId, brick_name (current CORAL fitness brick)")
    parser.add_argument("--current-metadata-brick", required=True, help="Name of the current condition-metadata brick")
    parser.add_argument("--previous-crosswalk", type=Path, required=True, help="condition_library_genome_crosswalk.tsv of what CORAL already has")
    parser.add_argument("--package-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-checkgeneric", action="store_true")
    return parser.parse_args()


def connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    # A few source TEXT values are Windows-1252 rather than UTF-8.
    connection.text_factory = lambda raw: raw.decode("utf-8") if _is_utf8(raw) else raw.decode("cp1252", errors="replace")
    return connection


def _is_utf8(raw: bytes) -> bool:
    try:
        raw.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def digest_rows(rows) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(repr(tuple(row)).encode())
        digest.update(b"\n")
    return digest.hexdigest()


def genome_fingerprint(connection: sqlite3.Connection, org: str) -> tuple[str, str]:
    assembly = digest_rows(
        (scaffold, sequence.upper())
        for scaffold, sequence in connection.execute(
            "SELECT scaffoldId,sequence FROM ScaffoldSeq WHERE orgId=? ORDER BY scaffoldId", (org,)
        )
    )
    annotation = digest_rows(
        connection.execute(
            "SELECT locusId,sysName,scaffoldId,begin,end,type,strand,gene,desc FROM Gene WHERE orgId=? ORDER BY locusId",
            (org,),
        )
    )
    return assembly, annotation


def fitness_fingerprint(connection: sqlite3.Connection, org: str) -> str | None:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND lower(name)=lower(?)", (f"FitByExp_{org}",)
    ).fetchone()
    if not row:
        return None
    table = base.quote_identifier(row[0])
    return digest_rows(connection.execute(f"SELECT locusId,expName,fit,t FROM {table} ORDER BY locusId,expName"))


def experiments(connection: sqlite3.Connection, org: str) -> dict[str, str]:
    return dict(connection.execute("SELECT expName,mutantLibrary FROM Experiment WHERE orgId=?", (org,)))


def next_brick_name(current: str) -> str:
    stem = current.removesuffix(".ndarray")
    match = re.fullmatch(r"(.*)_v(\d+)", stem)
    if match:
        return f"{match.group(1)}_v{int(match.group(2)) + 1}.ndarray"
    return f"{stem}_v2.ndarray"


def static_rows_for_new_organism(connection, org, strain, genome_name):
    scaffolds = [r[0] for r in connection.execute("SELECT scaffoldId FROM ScaffoldSeq WHERE orgId=? ORDER BY scaffoldId", (org,))]
    numbers = {scaffold: number for number, scaffold in enumerate(scaffolds, start=1)}
    xrefs: dict[str, list[str]] = {}
    for locus, database, xref in connection.execute(
        "SELECT locusId,xrefDb,xrefId FROM LocusXref WHERE orgId=? ORDER BY locusId,xrefDb,xrefId", (org,)
    ):
        xrefs.setdefault(locus, []).append(f"{database}:{xref}")
    gene_rows = []
    for locus, sys_name, scaffold, begin, end, strand, gene, description in connection.execute(
        "SELECT locusId,sysName,scaffoldId,begin,end,strand,gene,desc FROM Gene WHERE orgId=? ORDER BY locusId", (org,)
    ):
        name = base.qualified_gene_name(genome_name, locus)
        aliases: list[str] = []
        for alias in [locus, sys_name, gene, *xrefs.get(locus, [])]:
            if alias and alias != name and alias not in aliases:
                aliases.append(alias)
        gene_rows.append(
            {
                "gene_id": name,
                "genome": genome_name,
                "aliases": ",".join(aliases),
                "contig_number": numbers[scaffold],
                "strand": strand,
                "start": int(begin),
                "stop": int(end),
                "function": description if description else "null",
            }
        )
    genome_row = {
        "name": genome_name,
        "strain": strain,
        "n_contigs": len(scaffolds),
        "n_features": len(gene_rows),
        "link": f"enigma-data-repository/genome_processing/{strain}/assembliesAndAnnotations/{genome_name}/",
    }
    return genome_row, gene_rows


def build_fitness_document(connection, org, strain, genome, name, description, library_lookup):
    table = base.fitness_table(connection, org)
    quoted = base.quote_identifier(table)
    loci = [r[0] for r in connection.execute(f"SELECT DISTINCT locusId FROM {quoted} ORDER BY locusId")]
    exps = [r[0] for r in connection.execute(f"SELECT DISTINCT expName FROM {quoted} ORDER BY expName")]
    source_exps = [r[0] for r in connection.execute("SELECT expName FROM Experiment WHERE orgId=? ORDER BY expName", (org,))]
    if exps != source_exps:
        raise ValueError(f"Fitness experiment set differs from Experiment for {org}")
    source_loci = {r[0] for r in connection.execute("SELECT locusId FROM Gene WHERE orgId=?", (org,))}
    if set(loci) - source_loci:
        raise ValueError(f"Orphan fitness loci for {org}")
    expected = len(loci) * len(exps)
    if connection.execute(f"SELECT count(*) FROM {quoted}").fetchone()[0] != expected:
        raise ValueError(f"Non-rectangular fitness table for {org}")
    exp_library = {exp: library_lookup[(org, library)] for exp, library in experiments(connection, org).items()}
    fit_values: list[float] = []
    t_values: list[float] = []
    for index, (locus, exp, fit, t_value) in enumerate(
        connection.execute(f"SELECT locusId,expName,fit,t FROM {quoted} ORDER BY locusId,expName")
    ):
        if locus != loci[index // len(exps)] or exp != exps[index % len(exps)]:
            raise ValueError(f"Unexpected fitness cell order for {org} at {index}")
        fit_value, statistic = float(fit), float(t_value)
        if not math.isfinite(fit_value) or not math.isfinite(statistic):
            raise ValueError(f"Non-finite fitness value for {org}, {locus}, {exp}")
        fit_values.append(fit_value)
        t_values.append(statistic)
    gene_values = [base.qualified_gene_name(genome, locus) for locus in loci]
    condition_values = [base.condition_name(strain, exp) for exp in exps]
    document = {
        "name": name,
        "description": description,
        "data_type": base.term("fitness_data"),
        "array_context": [base.scalar_property("data_variables_type", "oterm_ref", base.TERMS["fitness_data"].ref)],
        "n_dimensions": 2,
        "dim_context": [
            {
                "data_type": base.term("gene"),
                "size": len(gene_values),
                "typed_values": [
                    base.typed_values("gene_id", "object_ref", gene_values),
                    base.typed_values("genome_id", "object_ref", [genome] * len(gene_values)),
                ],
            },
            {
                "data_type": base.term("condition"),
                "size": len(condition_values),
                "typed_values": [
                    base.typed_values("condition_id", "object_ref", condition_values),
                    base.typed_values("library_name", "object_ref", [exp_library[exp] for exp in exps]),
                ],
            },
        ],
        "typed_values": [
            base.typed_values("fitness", "float", fit_values, unit_key="log_ratio"),
            base.typed_values("average", "float", t_values, unit_key="dimensionless", context=base.t_score_context()),
        ],
    }
    base.validate_data_variables_context(document)
    return document, len(gene_values), len(condition_values)


def build_metadata_document(connection, scope, genome_by_org, library_lookup, name, release_label):
    rows = []
    crosswalk = []
    for org, strain in scope:
        cursor = connection.execute("SELECT * FROM Experiment WHERE orgId=? ORDER BY expName", (org,))
        columns = [item[0] for item in cursor.description]
        for raw in cursor:
            row = dict(zip(columns, raw))
            key = (org, row["mutantLibrary"])
            if key not in library_lookup:
                raise ValueError(f"Experiment library has no approved model: {key}")
            row["condition_name"] = base.condition_name(strain, row["expName"])
            row["library_name"] = library_lookup[key]
            row["genome_name"] = genome_by_org[org]
            rows.append(row)
            crosswalk.append(
                {
                    "fitprivate_orgId": org,
                    "fitprivate_expName": row["expName"],
                    "condition_name": row["condition_name"],
                    "source_mutant_library": row["mutantLibrary"],
                    "tnseq_library_name": row["library_name"],
                    "genome_name": row["genome_name"],
                }
            )
    variables = [
        base.typed_values(
            field.term_key,
            field.scalar_type,
            [base.normalize_value(field, row[field.source]) for row in rows],
            unit_key=field.unit_key,
            context=base.source_context(field.source, field.note),
        )
        for field in base.EXPERIMENT_FIELDS
    ]
    document = {
        "name": name,
        "description": (
            "FEBa TnSeq experimental conditions and quality metadata for ENIGMA isolates, "
            f"from the fitprivate release of {release_label}"
        ),
        "data_type": base.term("metadata_data"),
        "array_context": [
            base.scalar_property("data_variables_type", "oterm_ref", base.TERMS["metadata_data"].ref),
            base.scalar_property("link", "string", "enigma.fitprivate.experiment(orgId, expName)"),
            base.scalar_property(
                "comment",
                "string",
                "Composite external relationship: (fitprivate_orgId, fitprivate_expName) -> enigma.fitprivate.experiment(orgId, expName)",
            ),
        ],
        "n_dimensions": 1,
        "dim_context": [
            {
                "data_type": base.term("condition"),
                "size": len(rows),
                "typed_values": [
                    base.typed_values("condition_id", "object_ref", [row["condition_name"] for row in rows]),
                    base.typed_values("library_name", "object_ref", [row["library_name"] for row in rows]),
                    base.typed_values("genome_id", "object_ref", [row["genome_name"] for row in rows]),
                ],
            }
        ],
        "typed_values": variables,
    }
    base.validate_data_variables_context(document)
    return document, crosswalk


def write_json(stage: Path, document: dict[str, Any], filename: str, allowed: set[str], skip_check: bool) -> dict[str, int]:
    audit = base.validate_object_refs(document, allowed)
    path = stage / "json" / filename
    with path.open("w") as handle:
        json.dump(document, handle, separators=(",", ":"), allow_nan=False)
    if not skip_check:
        base.check_generic(path, stage / "check" / f"{filename}.check")
    return audit


def main() -> None:
    args = parse_args()
    stamp = args.package_date.replace("-", "")
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite existing package: {args.output}")
    if base.sha256(args.new_database) != args.new_database_sha256:
        raise ValueError("--new-database does not match --new-database-sha256")

    scope = [(row["fitprivate_orgId"], row["sdt_strain_name"]) for row in base.read_tsv(args.scope)]
    genome_by_org = {row["fitprivate_orgId"]: row["genome_name"] for row in base.read_tsv(args.genomes)}
    current_brick = {row["fitprivate_orgId"]: row["brick_name"] for row in base.read_tsv(args.current_bricks)}
    models = {(row["fitprivate_orgId"], row["source_mutant_library"]): row["primers_model"] for row in base.read_tsv(args.library_models)}
    previous = base.read_tsv(args.previous_crosswalk)
    previous_conditions = {row["condition_name"] for row in previous}
    previous_libraries = {row["tnseq_library_name"] for row in previous}
    previous_orgs = {row["fitprivate_orgId"] for row in previous}
    previous_genomes = {row["genome_name"] for row in previous}
    previous_metadata_keys = {(row["fitprivate_orgId"], row["fitprivate_expName"]) for row in previous}

    missing = [org for org, _ in scope if org not in genome_by_org]
    if missing:
        raise ValueError(f"No genome name for in-scope organisms: {missing}")
    if previous_orgs - {org for org, _ in scope}:
        raise ValueError("Scope drops organisms that CORAL already has; that is not handled here")

    old = connect(args.old_database)
    new = connect(args.new_database)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{args.output.name}.", dir=args.output.parent))
    try:
        for directory in ("static", "json", "check", "process", "reports"):
            (stage / directory).mkdir()

        library_lookup: dict[tuple[str, str], str] = {}
        genome_rows, gene_rows, condition_rows, library_rows = [], [], [], []
        decisions = []
        allowed_new: set[str] = set()
        for org, strain in scope:
            genome = genome_by_org[org]
            new_exps = experiments(new, org)
            if not new_exps:
                raise ValueError(f"{org} has no experiments in the new snapshot")
            for library in sorted(set(new_exps.values())):
                key = (org, library)
                if key not in models or not models[key]:
                    raise ValueError(f"No approved primers_model for {key}")
                name = base.library_name(genome, library)
                library_lookup[key] = name
                if name not in previous_libraries:
                    library_rows.append(
                        {
                            "name": name,
                            "genome": genome,
                            "primers_model": models[key],
                            **{field: "null" for field in base.STATIC_IMPORT_FIELDS["TnSeq_Library"][3:]},
                        }
                    )
            is_new_org = org not in previous_orgs
            decision = {
                "fitprivate_orgId": org,
                "strain_name": strain,
                "genome_name": genome,
                "experiments_old": 0 if is_new_org else len(experiments(old, org)),
                "experiments_new": len(new_exps),
            }
            if is_new_org:
                if genome in previous_genomes:
                    raise ValueError(f"New organism {org} reuses an existing FEBa genome name {genome}")
                genome_row, genes = static_rows_for_new_organism(new, org, strain, genome)
                genome_rows.append(genome_row)
                gene_rows.extend(genes)
                decision.update(action="new_organism", experiments_added=len(new_exps), experiments_removed=0)
            else:
                if genome not in previous_genomes:
                    raise ValueError(f"{org} is in CORAL under a different genome than {genome}")
                if genome_fingerprint(old, org) != genome_fingerprint(new, org):
                    raise ValueError(f"Genome or annotation of {org} changed; a new genome version is required")
                old_exps = experiments(old, org)
                changed = fitness_fingerprint(old, org) != fitness_fingerprint(new, org)
                decision.update(
                    action="replace_brick" if changed else "unchanged",
                    experiments_added=len(set(new_exps) - set(old_exps)),
                    experiments_removed=len(set(old_exps) - set(new_exps)),
                )
            for exp in sorted(new_exps):
                name = base.condition_name(strain, exp)
                if name not in previous_conditions:
                    condition_rows.append({"name": name})
            decisions.append(decision)

        allowed_new |= {row["name"] for row in genome_rows} | {row["gene_id"] for row in gene_rows}
        allowed_new |= {row["name"] for row in condition_rows} | {row["name"] for row in library_rows}
        # Names already in CORAL from the first import are valid references too.
        allowed_existing = previous_conditions | previous_libraries | previous_genomes

        static_files = []
        for object_type, rows in (("Genome", genome_rows), ("Gene", gene_rows), ("Condition", condition_rows), ("TnSeq_Library", library_rows)):
            if not rows:
                continue
            names = [row[base.STATIC_IMPORT_FIELDS[object_type][0]] for row in rows]
            if len(set(names)) != len(names):
                raise ValueError(f"Duplicate {object_type} names in additions")
            path = stage / "static" / f"{object_type}_feba_additions_{stamp}.tsv"
            base.write_tsv(path, base.STATIC_IMPORT_FIELDS[object_type], rows)
            base.validate_static_import_tsv(path, object_type)
            static_files.append((object_type, path.name, len(rows)))

        brick_results = []
        assay_rows, update_rows = [], []
        for decision in decisions:
            if decision["action"] == "unchanged":
                continue
            org, strain, genome = decision["fitprivate_orgId"], decision["strain_name"], decision["genome_name"]
            if decision["action"] == "new_organism":
                name = base.brick_name(genome)
                description = f"FEBa TnSeq gene fitness scores and t statistics for {strain} using genome {genome}"
            else:
                name = next_brick_name(current_brick[org])
                version = re.search(r"_v(\d+)\.ndarray$", name).group(1)
                description = (
                    f"FEBa TnSeq gene fitness scores and t statistics for {strain} using genome {genome}; "
                    f"v{version} updates the data to the fitprivate release of {args.release_label}"
                )
            document, genes, conditions = build_fitness_document(new, org, strain, genome, name, description, library_lookup)
            gene_names = set(document["dim_context"][0]["typed_values"][0]["values"]["object_refs"])
            filename = f"{name.removesuffix('.ndarray')}_{stamp}.json"
            audit = write_json(stage, document, filename, allowed_new | allowed_existing | gene_names, args.skip_checkgeneric)
            brick_results.append(
                {
                    **decision,
                    "brick_name": name,
                    "json_file": filename,
                    "replaces": "" if decision["action"] == "new_organism" else current_brick[org],
                    "gene_count": genes,
                    "condition_count": conditions,
                    "cell_count": genes * conditions,
                    **audit,
                }
            )
            if decision["action"] == "new_organism":
                dates = sorted(
                    row[0]
                    for row in new.execute("SELECT dateStarted FROM Experiment WHERE orgId=?", (org,))
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", row[0] or "")
                )
                libraries = sorted({library_lookup[(org, library)] for library in experiments(new, org).values()})
                assay_rows.append(
                    {
                        "process": "Assay Fitness <PROCESS:0000010>",
                        "person": ASSAY_PERSON,
                        "campaign": CAMPAIGN,
                        "protocol": "null",
                        "date_start": dates[0] if dates else "null",
                        "date_end": dates[-1] if dates else "null",
                        "input_objects": ", ".join(f"TnSeq_Library: {library}" for library in libraries),
                        "output_objects": f"Generic: {name}",
                    }
                )
            else:
                update_rows.append(
                    {
                        "process": "Update Data <PROCESS:0000053>",
                        "person": UPDATE_PERSON,
                        "campaign": CAMPAIGN,
                        "protocol": "null",
                        "date_start": args.package_date,
                        "date_end": args.package_date,
                        "input_objects": f"Generic: {current_brick[org]}",
                        "output_objects": f"Generic: {name}",
                    }
                )
            print(f"built {name}: {genes} x {conditions}", flush=True)

        metadata_name = f"feba_tnseq_condition_metadata_{stamp}.ndarray"
        metadata_document, crosswalk = build_metadata_document(new, scope, genome_by_org, library_lookup, metadata_name, args.release_label)
        new_metadata_keys = {(row["fitprivate_orgId"], row["fitprivate_expName"]) for row in crosswalk}
        metadata_filename = metadata_name.replace(".ndarray", ".json")
        metadata_audit = write_json(stage, metadata_document, metadata_filename, allowed_new | allowed_existing, args.skip_checkgeneric)
        update_rows.append(
            {
                "process": "Update Data <PROCESS:0000053>",
                "person": UPDATE_PERSON,
                "campaign": CAMPAIGN,
                "protocol": "null",
                "date_start": args.package_date,
                "date_end": args.package_date,
                "input_objects": f"Generic: {args.current_metadata_brick}",
                "output_objects": f"Generic: {metadata_name}",
            }
        )
        print(f"built {metadata_name}: {len(crosswalk)} conditions", flush=True)

        process_files = []
        if assay_rows:
            name = f"process_assay_fitness_feba_{stamp}.tsv"
            base.write_tsv(stage / "process" / name, PROCESS_FIELDS, assay_rows)
            process_files.append(("Assay Fitness", name))
        name = f"process_update_data_feba_{stamp}.tsv"
        base.write_tsv(stage / "process" / name, PROCESS_FIELDS, update_rows)
        process_files.append(("Update Data", name))

        base.write_tsv(
            stage / "reports" / "organism_decisions.tsv",
            ["fitprivate_orgId", "strain_name", "genome_name", "action", "experiments_old", "experiments_new", "experiments_added", "experiments_removed"],
            decisions,
        )
        base.write_tsv(
            stage / "reports" / "brick_manifest.tsv",
            ["fitprivate_orgId", "strain_name", "genome_name", "action", "brick_name", "json_file", "replaces", "gene_count", "condition_count", "cell_count", "experiments_old", "experiments_new", "experiments_added", "experiments_removed", "references", "unique_references"],
            brick_results,
        )
        base.write_tsv(
            stage / "reports" / "condition_library_genome_crosswalk.tsv",
            ["fitprivate_orgId", "fitprivate_expName", "condition_name", "source_mutant_library", "tnseq_library_name", "genome_name"],
            crosswalk,
        )
        summary = {
            "package_date": args.package_date,
            "release_label": args.release_label,
            "old_database": str(args.old_database),
            "new_database": str(args.new_database),
            "new_database_sha256": args.new_database_sha256,
            "organisms_in_scope": len(scope),
            "actions": {action: sum(1 for d in decisions if d["action"] == action) for action in ("new_organism", "replace_brick", "unchanged")},
            "static_additions": {object_type: count for object_type, _, count in static_files},
            "fitness_bricks": len(brick_results),
            "fitness_cells": sum(row["cell_count"] for row in brick_results),
            "condition_metadata_brick": metadata_name,
            "condition_metadata_rows": len(crosswalk),
            "condition_metadata_rows_added": len(new_metadata_keys - previous_metadata_keys),
            "condition_metadata_rows_removed": len(previous_metadata_keys - new_metadata_keys),
            "condition_metadata_reference_audit": metadata_audit,
            "checkgeneric_passed": not args.skip_checkgeneric,
        }
        (stage / "reports" / "package_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

        brick_files = [row["json_file"] for row in brick_results] + [metadata_filename]
        lines = [
            f"# FEBa update {args.package_date}: fitprivate release {args.release_label}.",
            "# Run on the CORAL hub, in order, after copying every file in files_to_import.txt to",
            "# /home/coral/prod/data_import/data/ on coral-enigma.",
            "",
            "# Step 1: static objects, in dependency order.",
            *[f"toolx.update_core('{filename}', '{object_type}')" for object_type, filename, _ in static_files],
            "",
            "# Step 2: bricks.",
            *[f"toolx.upload_brick('{filename}')" for filename in brick_files],
            "",
            "# Step 3: processes (new-brick provenance, then replacements of the superseded bricks).",
            *[f"toolx.upload_process('{process}', '{filename}')" for process, filename in process_files],
        ]
        (stage / "import_to_coral.py").write_text("\n".join(lines) + "\n")
        (stage / "files_to_import.txt").write_text(
            "\n".join(
                [
                    *(f"static/{filename}" for _, filename, _ in static_files),
                    *(f"json/{filename}" for filename in brick_files),
                    *(f"process/{filename}" for _, filename in process_files),
                ]
            )
            + "\n"
        )
        base.write_checksums(stage)
        old.close()
        new.close()
        stage.rename(args.output)
        print(json.dumps(summary, indent=2))
        print(f"complete: {args.output}", flush=True)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


if __name__ == "__main__":
    main()
