#!/usr/bin/env python3
"""Export a Fitness Browser organism's embedded assembly and annotations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote, unquote

from build_feba_phase0_manifest import source_fingerprints


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export ScaffoldSeq and Gene rows from a FEBa SQLite database."
    )
    parser.add_argument("database", type=Path, help="Path to feba.db")
    parser.add_argument("org_id", help="Organism ID, for example pseudo6_N2E2")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--prefix",
        default=None,
        help="Output filename prefix; defaults to the organism ID",
    )
    parser.add_argument(
        "--strain-name",
        default=None,
        help="Target CORAL/EDR strain name; enables repository-required filenames",
    )
    parser.add_argument(
        "--genome-version",
        type=int,
        default=None,
        help="Allocated EDR genome version; requires --strain-name",
    )
    parser.add_argument(
        "--source-database-sha256",
        default=None,
        help="Verified SHA-256 of the immutable FEBa SQLite source",
    )
    return parser.parse_args()


def gff_escape(value: object) -> str:
    safe = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.:^*$@!+_?-|/"
    return quote(str(value), safe=safe)


def attributes(items: list[tuple[str, object | None]]) -> str:
    rendered = []
    for key, value in items:
        if value is None or value == "" or value == []:
            continue
        if isinstance(value, list):
            encoded_value = ",".join(gff_escape(item) for item in value)
        else:
            encoded_value = gff_escape(value)
        rendered.append(f"{key}={encoded_value}")
    return ";".join(rendered)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_gff_attributes(raw: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in raw.split(";"):
        if not item:
            continue
        if "=" not in item:
            raise ValueError(f"Malformed GFF3 attribute: {item!r}")
        key, value = item.split("=", 1)
        if key in parsed:
            raise ValueError(f"Duplicate GFF3 attribute: {key}")
        parsed[key] = unquote(value)
    return parsed


def read_fasta(path: Path) -> dict[str, str]:
    records: dict[str, list[str]] = {}
    current: str | None = None
    with path.open(encoding="ascii") as handle:
        for line_number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                current = line[1:].split(None, 1)[0]
                if not current or current in records:
                    raise ValueError(f"Invalid or duplicate FASTA ID at line {line_number}")
                records[current] = []
            elif current is None:
                raise ValueError(f"FASTA sequence before first header at line {line_number}")
            else:
                records[current].append(line)
    return {name: "".join(parts).upper() for name, parts in records.items()}


def validate_generated_files(
    fasta_path: Path,
    gff_path: Path,
    scaffolds: list[sqlite3.Row],
    genes: list[sqlite3.Row],
) -> dict[str, int | str]:
    expected_sequences = {
        str(row["scaffoldId"]): "".join(str(row["sequence"]).split()).upper()
        for row in scaffolds
    }
    actual_sequences = read_fasta(fasta_path)
    if actual_sequences != expected_sequences:
        raise ValueError("Generated FASTA does not exactly match source ScaffoldSeq rows")

    expected_genes = {str(row["locusId"]): row for row in genes}
    gene_ids: set[str] = set()
    child_parents: set[str] = set()
    all_feature_ids: set[str] = set()
    with gff_path.open(encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.strip() or raw.startswith("#"):
                continue
            fields = raw.rstrip("\n").split("\t")
            if len(fields) != 9:
                raise ValueError(f"GFF3 line {line_number} does not have nine columns")
            scaffold_id, source, feature_type, begin, end, _, strand, _, raw_attrs = fields
            if scaffold_id not in expected_sequences:
                raise ValueError(f"Unknown GFF3 sequence ID at line {line_number}: {scaffold_id}")
            if source != "FEBa":
                raise ValueError(f"Unexpected GFF3 source at line {line_number}: {source}")
            attrs = parse_gff_attributes(raw_attrs)
            feature_id = attrs.get("ID")
            if not feature_id or feature_id in all_feature_ids:
                raise ValueError(f"Missing or duplicate GFF3 ID at line {line_number}")
            all_feature_ids.add(feature_id)

            if feature_type == "gene":
                locus_id = feature_id
                if locus_id in gene_ids or locus_id not in expected_genes:
                    raise ValueError(f"Unexpected or duplicate gene feature: {locus_id}")
                gene_ids.add(locus_id)
            else:
                locus_id = attrs.get("Parent") or ""
                if locus_id in child_parents or locus_id not in expected_genes:
                    raise ValueError(f"Unexpected or duplicate child feature for: {locus_id}")
                expected_type = TYPE_TO_FEATURE[int(expected_genes[locus_id]["type"])]
                if feature_type != expected_type:
                    raise ValueError(
                        f"Feature type differs for {locus_id}: {feature_type} != {expected_type}"
                    )
                child_parents.add(locus_id)

            expected = expected_genes[locus_id]
            observed_location = (
                scaffold_id,
                int(begin),
                int(end),
                strand,
            )
            expected_location = (
                str(expected["scaffoldId"]),
                int(expected["begin"]),
                int(expected["end"]),
                str(expected["strand"]),
            )
            if observed_location != expected_location:
                raise ValueError(
                    f"GFF3 location differs for {locus_id}: "
                    f"{observed_location} != {expected_location}"
                )

    expected_ids = set(expected_genes)
    if gene_ids != expected_ids or child_parents != expected_ids:
        raise ValueError("Generated GFF3 does not contain exactly one gene and child per source row")
    return {
        "status": "passed",
        "fasta_records": len(actual_sequences),
        "gff_gene_features": len(gene_ids),
        "gff_child_features": len(child_parents),
    }


def main() -> int:
    args = parse_args()
    if not args.database.is_file():
        raise SystemExit(f"Database not found: {args.database}")
    if (args.strain_name is None) != (args.genome_version is None):
        raise SystemExit("--strain-name and --genome-version must be provided together")
    if args.genome_version is not None and args.genome_version < 1:
        raise SystemExit("--genome-version must be positive")
    if args.source_database_sha256 is not None and len(args.source_database_sha256) != 64:
        raise SystemExit("--source-database-sha256 must be a 64-character SHA-256")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.strain_name is not None:
        prefix = args.strain_name
        fasta_path = output_dir / f"{prefix}_contigs.fasta"
        gff_path = output_dir / f"{prefix}_Prodigal.gff"
        manifest_path = output_dir / f"{prefix}.{args.genome_version}_export_manifest.json"
    else:
        prefix = args.prefix or args.org_id
        fasta_path = output_dir / f"{prefix}_contigs.fasta"
        gff_path = output_dir / f"{prefix}_annotations.gff3"
        manifest_path = output_dir / f"{prefix}_export_manifest.json"
    fasta_temporary = fasta_path.with_name(f".{fasta_path.name}.tmp")
    gff_temporary = gff_path.with_name(f".{gff_path.name}.tmp")

    connection = sqlite3.connect(f"file:{args.database.resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        organism = connection.execute(
            "SELECT * FROM Organism WHERE orgId = ?", (args.org_id,)
        ).fetchone()
        if organism is None:
            raise SystemExit(f"Organism not found: {args.org_id}")

        scaffolds = connection.execute(
            """
            SELECT scaffoldId, sequence
            FROM ScaffoldSeq
            WHERE orgId = ?
            ORDER BY scaffoldId
            """,
            (args.org_id,),
        ).fetchall()
        if not scaffolds:
            raise SystemExit(f"No ScaffoldSeq rows found for {args.org_id}")

        genes = connection.execute(
            """
            SELECT locusId, sysName, scaffoldId, begin, end, type, strand,
                   gene, desc, GC
            FROM Gene
            WHERE orgId = ?
            ORDER BY scaffoldId, begin, end, locusId
            """,
            (args.org_id,),
        ).fetchall()
        xref_rows = connection.execute(
            """
            SELECT locusId, xrefDb, xrefId
            FROM LocusXref
            WHERE orgId = ?
            ORDER BY locusId, xrefDb, xrefId
            """,
            (args.org_id,),
        ).fetchall()
    finally:
        connection.close()

    scaffold_lengths = {row["scaffoldId"]: len(row["sequence"]) for row in scaffolds}
    xrefs: dict[str, list[str]] = defaultdict(list)
    for row in xref_rows:
        database = {"refseq": "RefSeq", "uniprot": "UniProtKB"}.get(
            row["xrefDb"].lower(), row["xrefDb"]
        )
        xrefs[row["locusId"]].append(f"{database}:{row['xrefId']}")

    feature_counts: Counter[str] = Counter()
    with fasta_temporary.open("w", encoding="ascii", newline="\n") as fasta:
        for row in scaffolds:
            sequence = row["sequence"].upper()
            fasta.write(f">{row['scaffoldId']}\n")
            for offset in range(0, len(sequence), 60):
                fasta.write(sequence[offset : offset + 60] + "\n")

    organism_name = " ".join(
        str(organism[key])
        for key in ("genus", "species", "strain")
        if key in organism.keys() and organism[key]
    )
    with gff_temporary.open("w", encoding="utf-8", newline="\n") as gff:
        gff.write("##gff-version 3\n")
        for row in scaffolds:
            gff.write(
                f"##sequence-region {row['scaffoldId']} 1 {len(row['sequence'])}\n"
            )
        gff.write(f"# source FEBa/Fitness Browser organism {args.org_id}\n")
        if organism_name:
            gff.write(f"# organism {organism_name}\n")
        gff.write("# source-database enigma.fitprivate\n")
        if args.source_database_sha256:
            gff.write(f"# source-database-sha256 {args.source_database_sha256.lower()}\n")

        for row in genes:
            locus_id = row["locusId"]
            scaffold_id = row["scaffoldId"]
            begin = row["begin"]
            end = row["end"]
            feature_type = TYPE_TO_FEATURE.get(row["type"])
            if feature_type is None:
                raise ValueError(f"Unsupported FEBa feature type {row['type']} for {locus_id}")
            if scaffold_id not in scaffold_lengths:
                raise ValueError(f"Unknown scaffold {scaffold_id} for {locus_id}")
            if begin < 1 or end < begin or end > scaffold_lengths[scaffold_id]:
                raise ValueError(
                    f"Invalid coordinates for {locus_id}: {scaffold_id}:{begin}-{end}"
                )
            if row["strand"] not in {"+", "-"}:
                raise ValueError(f"Invalid strand for {locus_id}: {row['strand']}")
            common = [
                ("Name", locus_id),
                ("locus_tag", row["sysName"] or locus_id),
                ("gene", row["gene"]),
                ("product", row["desc"]),
                ("gc_fraction", row["GC"]),
            ]
            if xrefs.get(locus_id):
                common.append(("Dbxref", xrefs[locus_id]))

            gene_attrs = attributes([("ID", locus_id), *common])
            gff.write(
                "\t".join(
                    [
                        scaffold_id,
                        "FEBa",
                        "gene",
                        str(begin),
                        str(end),
                        ".",
                        row["strand"],
                        ".",
                        gene_attrs,
                    ]
                )
                + "\n"
            )
            feature_counts["gene"] += 1

            child_id = f"{locus_id}.{feature_type}"
            child_attrs = attributes(
                [("ID", child_id), ("Parent", locus_id), *common]
            )
            phase = "0" if feature_type == "CDS" else "."
            gff.write(
                "\t".join(
                    [
                        scaffold_id,
                        "FEBa",
                        feature_type,
                        str(begin),
                        str(end),
                        ".",
                        row["strand"],
                        phase,
                        child_attrs,
                    ]
                )
                + "\n"
            )
            feature_counts[feature_type] += 1

    output_validation = validate_generated_files(
        fasta_temporary, gff_temporary, scaffolds, genes
    )
    os.replace(fasta_temporary, fasta_path)
    os.replace(gff_temporary, gff_path)

    fingerprint_connection = sqlite3.connect(
        f"file:{args.database.resolve()}?mode=ro", uri=True
    )
    fingerprint_connection.row_factory = sqlite3.Row
    try:
        source_hashes = source_fingerprints(fingerprint_connection, args.org_id)
    finally:
        fingerprint_connection.close()

    manifest = {
        "source_namespace": "enigma.fitprivate",
        "source_database": str(args.database.resolve()),
        "source_database_sha256": (
            args.source_database_sha256.lower() if args.source_database_sha256 else None
        ),
        "organism_id": args.org_id,
        "organism": organism_name,
        "target_strain_name": args.strain_name,
        "target_genome_version": args.genome_version,
        "target_genome_name": (
            f"{args.strain_name}.{args.genome_version}" if args.strain_name else None
        ),
        "scaffolds": len(scaffolds),
        "total_bases": sum(scaffold_lengths.values()),
        "source_gene_rows": len(genes),
        "gff_feature_counts": dict(sorted(feature_counts.items())),
        "xref_rows": len(xref_rows),
        "source_fingerprints": source_hashes,
        "output_validation": output_validation,
        "files": {
            fasta_path.name: {
                "bytes": fasta_path.stat().st_size,
                "sha256": sha256_file(fasta_path),
            },
            gff_path.name: {
                "bytes": gff_path.stat().st_size,
                "sha256": sha256_file(gff_path),
            },
        },
    }
    manifest_temporary = manifest_path.with_name(f".{manifest_path.name}.tmp")
    manifest_temporary.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="ascii"
    )
    os.replace(manifest_temporary, manifest_path)

    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
