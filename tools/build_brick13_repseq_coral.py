#!/usr/bin/env python3
"""Build the Brick13 representative-sequence brick and corrected provenance."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FASTA = ROOT / "rep_seq.fna"
DEFAULT_SOURCE_RUN = ROOT / "sync-coral-to-berdl/exports/sync-20260717-174244"
DEFAULT_PROCESS_SOURCE = Path(
    "/h/jmc/src/CORAL/example/enigma/public_data/"
    "process_otu_inference_zhou_100ws.tsv"
)
DEFAULT_OUTPUT = ROOT / "coral_import/brick13_repseq_20260720"

BRICK_NAME = "zhou_otu_repseq_100ws.ndarray"
BRICK_DESCRIPTION = "Zhou Lab 100 Well Survey OTU 16S Representative Sequences"
BRICK_TYPE = "Microbial Sequence <DA:0000064>"
VALUES = (
    "Sequence <ME:0000282>",
    "Sequence Type <ME:0000189>",
    "16S sequence <ME:0000190>",
)
DIMENSION = ("OTU <ME:0000184>", "OTU ID <ME:0000222>")
EXPECTED_OTUS = 49_904
EXPECTED_PROCESSES = 212
ORIGINAL_OUTPUTS = (
    "Generic: zhou_otu_count_100ws.ndarray",
    "Generic: zhou_otu_id_100ws.ndarray",
)

JAVA_CLASSES = Path("/h/jmc/src/java/classes")
JAVA_JARS = [
    Path("/h/jmc/.m2/repository/com/fasterxml/jackson/core/jackson-annotations/2.5.1/jackson-annotations-2.5.1.jar"),
    Path("/h/jmc/.m2/repository/com/fasterxml/jackson/core/jackson-core/2.5.1/jackson-core-2.5.1.jar"),
    Path("/h/jmc/.m2/repository/com/fasterxml/jackson/core/jackson-databind/2.5.1/jackson-databind-2.5.1.jar"),
    Path("/h/jmc/.m2/repository/com/opencsv/opencsv/4.3.2/opencsv-4.3.2.jar"),
    Path("/h/jmc/.m2/repository/org/apache/commons/commons-lang3/3.4/commons-lang3-3.4.jar"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fasta", type=Path, default=DEFAULT_FASTA)
    parser.add_argument("--source-run", type=Path, default=DEFAULT_SOURCE_RUN)
    parser.add_argument("--process-source", type=Path, default=DEFAULT_PROCESS_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def java_classpath() -> str:
    required = [JAVA_CLASSES, *JAVA_JARS]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing Java classpath entries: {missing}")
    return os.pathsep.join(str(path) for path in required)


def run_java(class_name: str, *args: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "java",
            "-Xmx2g",
            "-cp",
            java_classpath(),
            class_name,
            *(str(arg) for arg in args),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_fasta(path: Path) -> tuple[dict[str, str], dict[str, int]]:
    sequences: dict[str, str] = {}
    aligned_lengths: Counter[int] = Counter()
    current_id: str | None = None
    chunks: list[str] = []

    def commit() -> None:
        nonlocal current_id, chunks
        if current_id is None:
            return
        aligned = "".join(chunks).replace(" ", "").upper()
        if current_id in sequences:
            raise ValueError(f"Duplicate FASTA identifier: {current_id}")
        aligned_lengths[len(aligned)] += 1
        sequence = aligned.replace("-", "")
        invalid = sorted(set(sequence) - set("ACGTN"))
        if invalid:
            raise ValueError(
                f"Invalid sequence characters for {current_id}: {invalid}"
            )
        if not sequence:
            raise ValueError(f"Empty sequence for {current_id}")
        sequences[current_id] = sequence

    with path.open() as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(">"):
                commit()
                current_id = line[1:].split(maxsplit=1)[0]
                if not current_id:
                    raise ValueError(f"Empty FASTA identifier at line {line_number}")
                chunks = []
            else:
                if current_id is None:
                    raise ValueError(
                        f"Sequence before first FASTA header at line {line_number}"
                    )
                chunks.append("".join(line.split()))
    commit()

    if len(sequences) != EXPECTED_OTUS:
        raise ValueError(
            f"Expected {EXPECTED_OTUS} FASTA records, found {len(sequences)}"
        )
    return sequences, dict(sorted(aligned_lengths.items()))


def brick13_otu_ids(path: Path) -> list[str]:
    values: list[str] = []
    in_otu_dimension = False
    with path.open(newline="") as handle:
        for row in csv.reader(handle):
            if row[:2] == ["dmeta", "2"]:
                in_otu_dimension = True
                continue
            if in_otu_dimension and row and row[0] == "data":
                break
            if in_otu_dimension:
                values.append(row[1].rsplit(" <", 1)[0])
    if len(values) != EXPECTED_OTUS or len(set(values)) != EXPECTED_OTUS:
        raise ValueError(
            f"Expected {EXPECTED_OTUS} unique Brick13 OTUs, found "
            f"{len(values)} rows and {len(set(values))} unique IDs"
        )
    return values


def validate_coverage(otu_ids: list[str], sequences: dict[str, str]) -> None:
    missing = sorted(set(otu_ids) - sequences.keys())
    extras = sorted(sequences.keys() - set(otu_ids))
    if missing or extras:
        raise ValueError(
            f"Representative-sequence coverage mismatch: "
            f"missing={missing[:10]}, extras={extras[:10]}"
        )


def write_generic_csv(path: Path, otu_ids: list[str], sequences: dict[str, str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["name", BRICK_NAME])
        writer.writerow(["description", BRICK_DESCRIPTION])
        writer.writerow(["type", BRICK_TYPE])
        writer.writerow(["values", *VALUES])
        writer.writerow(["size", len(otu_ids)])
        writer.writerow(["dmeta", "1", *DIMENSION])
        for index, otu_id in enumerate(otu_ids, start=1):
            writer.writerow([index, f"{otu_id} <{otu_id}>"])
        writer.writerow(["data"])
        for index, otu_id in enumerate(otu_ids, start=1):
            writer.writerow([index, sequences[otu_id]])


def write_corrected_processes(source: Path, destination: Path) -> list[str]:
    with source.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames
        rows = list(reader)
    if fieldnames is None:
        raise ValueError(f"Missing process TSV header: {source}")
    if len(rows) != EXPECTED_PROCESSES:
        raise ValueError(
            f"Expected {EXPECTED_PROCESSES} process rows, found {len(rows)}"
        )

    inputs: list[str] = []
    expected_old = ", ".join(ORIGINAL_OUTPUTS)
    corrected_outputs = f"{expected_old}, Generic: {BRICK_NAME}"
    for row in rows:
        if row["process"] != "Classify OTUs <PROCESS:0000031>":
            raise ValueError(f"Unexpected process term: {row['process']}")
        if row["output_objects"] != expected_old:
            raise ValueError(f"Unexpected original outputs: {row['output_objects']}")
        if not row["input_objects"].startswith("Reads: "):
            raise ValueError(f"Unexpected process input: {row['input_objects']}")
        row["output_objects"] = corrected_outputs
        inputs.append(row["input_objects"])
    if len(set(inputs)) != EXPECTED_PROCESSES:
        raise ValueError("Expected one unique reads input per process row")

    with destination.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    return inputs


def write_aql_files(directory: Path) -> None:
    old_ids = (
        "(FOR n IN 13232..13443 "
        "RETURN CONCAT('SYS_Process/Process00', TO_STRING(n)))"
    )
    target = (
        "FIRST(FOR b IN DDT_Brick "
        f"FILTER b.name == '{BRICK_NAME}' RETURN b._id)"
    )
    (directory / "01_verify_corrected_processes.aql").write_text(
        f"""LET target_id = {target}
LET producer_ids = (
  FOR e IN SYS_ProcessOutput
    FILTER e._to == target_id
    RETURN DISTINCT e._from
)
LET classified_producers = (
  FOR p IN SYS_Process
    FILTER p._id IN producer_ids
    FILTER p.process_term_id == "PROCESS:0000031"
    RETURN p._id
)
RETURN {{
  target_id,
  producer_count: LENGTH(producer_ids),
  classify_otu_producer_count: LENGTH(classified_producers)
}}
"""
    )
    (directory / "02_delete_original_input_edges.aql").write_text(
        f"""LET old_ids = {old_ids}
LET target_id = {target}
LET corrected_producer_count = LENGTH(
  FOR e IN SYS_ProcessOutput
    FILTER e._to == target_id
    RETURN DISTINCT e._from
)
LET old_process_count = LENGTH(
  FOR p IN SYS_Process
    FILTER p._id IN old_ids
    FILTER p.process_term_id == "PROCESS:0000031"
    RETURN 1
)
FOR e IN SYS_ProcessInput
  FILTER corrected_producer_count == 212
  FILTER old_process_count == 212
  FILTER e._to IN old_ids
  REMOVE e IN SYS_ProcessInput
  RETURN OLD
"""
    )
    (directory / "03_delete_original_output_edges.aql").write_text(
        f"""LET old_ids = {old_ids}
LET target_id = {target}
LET corrected_producer_count = LENGTH(
  FOR e IN SYS_ProcessOutput
    FILTER e._to == target_id
    RETURN DISTINCT e._from
)
LET old_process_count = LENGTH(
  FOR p IN SYS_Process
    FILTER p._id IN old_ids
    FILTER p.process_term_id == "PROCESS:0000031"
    RETURN 1
)
FOR e IN SYS_ProcessOutput
  FILTER corrected_producer_count == 212
  FILTER old_process_count == 212
  FILTER e._from IN old_ids
  REMOVE e IN SYS_ProcessOutput
  RETURN OLD
"""
    )
    (directory / "04_delete_original_processes.aql").write_text(
        f"""LET old_ids = {old_ids}
LET target_id = {target}
LET corrected_producer_count = LENGTH(
  FOR e IN SYS_ProcessOutput
    FILTER e._to == target_id
    RETURN DISTINCT e._from
)
LET old_process_count = LENGTH(
  FOR p IN SYS_Process
    FILTER p._id IN old_ids
    FILTER p.process_term_id == "PROCESS:0000031"
    RETURN 1
)
FOR p IN SYS_Process
  FILTER corrected_producer_count == 212
  FILTER old_process_count == 212
  FILTER p._id IN old_ids
  FILTER p.process_term_id == "PROCESS:0000031"
  REMOVE p IN SYS_Process
  RETURN OLD
"""
    )
    (directory / "05_verify_replacement.aql").write_text(
        f"""LET old_ids = {old_ids}
LET target_id = {target}
LET producer_ids = (
  FOR e IN SYS_ProcessOutput
    FILTER e._to == target_id
    RETURN DISTINCT e._from
)
RETURN {{
  target_id,
  corrected_producer_count: LENGTH(producer_ids),
  old_process_count: LENGTH(FOR p IN SYS_Process FILTER p._id IN old_ids RETURN 1),
  old_input_edge_count: LENGTH(FOR e IN SYS_ProcessInput FILTER e._to IN old_ids RETURN 1),
  old_output_edge_count: LENGTH(FOR e IN SYS_ProcessOutput FILTER e._from IN old_ids RETURN 1)
}}
"""
    )


def write_import_helpers(output: Path, json_path: Path, process_path: Path) -> None:
    (output / "files_to_import.txt").write_text(
        f"json/{json_path.name}\nprocess/{process_path.name}\n"
    )
    (output / "import_to_coral.py").write_text(
        "# Upload both files listed in files_to_import.txt, then run in order.\n"
        f"toolx.upload_brick('{json_path.name}')\n"
        f"toolx.upload_process('Classify OTUs', '{process_path.name}')\n"
    )
    (output / "README.md").write_text(
        f"""# Brick13 representative-sequence CORAL import

This package adds `{BRICK_NAME}` as the third co-output of the original 100
Well Survey OTU classification runs. It is not an `Import Historic Data`
operation.

1. Upload and run `json/{json_path.name}` with `toolx.upload_brick`.
2. Upload and run `process/{process_path.name}` with
   `toolx.upload_process('Classify OTUs', ...)`.
3. Run `aql/01_verify_corrected_processes.aql`. Continue only when both counts
   are 212.
4. Run AQL files 02 through 04 separately, in order, to remove the original
   two-output process records and their edges.
5. Run `aql/05_verify_replacement.aql`. The corrected producer count must be
   212 and all three old-object counts must be zero.

The old process IDs are `Process0013232` through `Process0013443`. The guarded
process deletion also requires `PROCESS:0000031` (`Classify OTUs`).
"""
    )


def write_recovery_report(path: Path) -> None:
    path.write_text(
        f"""# Brick13 representative-sequence recovery

Date: 2026-07-20

## Result

`rep_seq.fna` is the complete representative-sequence companion for Brick13.
It contains 49,904 unique FASTA identifiers, exactly matching all 49,904 OTU
IDs in Brick13: no identifiers are missing and none are extra.

All source records are 269-column aligned sequences. The CORAL brick removes
alignment gaps and stores uppercase sequences containing only A, C, G, T, and
N, following the existing Brick15 microbial-sequence representation. Ungapped
lengths range from 240 to 254 bases. There are 49,892 unique sequences; 12
pairs of OTU identifiers legitimately share the same sequence.

## Prior partial publication file

The 28,644 records in the public `100WSc.Rep_Seq.fasta` all match the recovered
file exactly after gap removal. That file accompanied a 91-community,
0.2-micron, 10,800-read rarefied publication subset. It omitted 21,260
Brick13 OTUs because they were outside that selected/rarefied table, not
because the tenant had a documented contamination decision. The prior audit's
identifier list is retained as
`coral_import/brick13_v2_20260720/reports/brick13_previously_missing_recovered_ids.tsv`;
every listed ID is present in `rep_seq.fna`.

## CORAL model and provenance

The generated brick is `{BRICK_NAME}` with type `Microbial Sequence
<DA:0000064>`, value `Sequence <ME:0000282>`, fixed value `Sequence Type = 16S
sequence`, and an `OTU ID <ME:0000222>` dimension.

The corrected process TSV uses `Classify OTUs <PROCESS:0000031>`, not `Import
Historic Data`. It retains the original 212 reads inputs and records the count,
taxonomy, and representative-sequence bricks as three co-outputs, matching the
27 Well Survey provenance pattern. The package includes guarded AQL files to
replace the original two-output process records after all 212 corrected records
have been loaded and verified.
"""
    )


def main() -> None:
    args = parse_args()
    source_csv = args.source_run / "coral_export/brick_csv/Brick0000013.csv"
    for required in (args.fasta, source_csv, args.process_source):
        if not required.exists():
            raise FileNotFoundError(required)
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {args.output}")

    json_dir = args.output / "json"
    check_dir = args.output / "check"
    process_dir = args.output / "process"
    aql_dir = args.output / "aql"
    source_dir = args.output / "source"
    report_dir = args.output / "reports"
    for directory in (json_dir, check_dir, process_dir, aql_dir, source_dir, report_dir):
        directory.mkdir(parents=True)

    sequences, aligned_lengths = parse_fasta(args.fasta)
    otu_ids = brick13_otu_ids(source_csv)
    validate_coverage(otu_ids, sequences)
    sequence_lengths = dict(sorted(Counter(map(len, sequences.values())).items()))
    by_sequence: dict[str, list[str]] = defaultdict(list)
    for otu_id, sequence in sequences.items():
        by_sequence[sequence].append(otu_id)
    duplicate_groups = sorted(
        sorted(ids) for ids in by_sequence.values() if len(ids) > 1
    )

    json_path = json_dir / "zhou_otu_repseq_100ws.json"
    check_path = check_dir / "zhou_otu_repseq_100ws.json.check"
    process_path = (
        process_dir / "process_classify_otus_zhou_100ws_with_repseq_20260720.tsv"
    )
    source_copy = source_dir / args.fasta.name
    shutil.copy2(args.fasta, source_copy)

    with tempfile.TemporaryDirectory(prefix="brick13_repseq_", dir="/tmp") as tmpdir:
        generic_csv = Path(tmpdir) / "zhou_otu_repseq_100ws.csv"
        write_generic_csv(generic_csv, otu_ids, sequences)
        converted = run_java("gov.lbl.enigma.app.ConvertGeneric", generic_csv, json_path)
        if converted.returncode != 0:
            raise RuntimeError(
                "ConvertGeneric failed:\n"
                + (converted.stdout or "")
                + (converted.stderr or "")
            )

    checked = run_java("gov.lbl.enigma.app.CheckGeneric", json_path)
    check_output = (checked.stdout or "") + (checked.stderr or "")
    check_path.write_text(check_output)
    if checked.returncode != 0 or "Generic is OK!" not in check_output:
        raise RuntimeError(f"CheckGeneric failed for {json_path}:\n{check_output}")

    process_inputs = write_corrected_processes(args.process_source, process_path)
    write_aql_files(aql_dir)
    write_import_helpers(args.output, json_path, process_path)
    write_recovery_report(report_dir / "brick13_representative_sequence_recovery.md")

    summary = {
        "brick_name": BRICK_NAME,
        "brick_description": BRICK_DESCRIPTION,
        "source_fasta": str(args.fasta),
        "source_fasta_copy": str(source_copy.relative_to(args.output)),
        "source_fasta_sha256": sha256(args.fasta),
        "representative_sequences": len(sequences),
        "brick13_otu_ids": len(otu_ids),
        "missing_otu_ids": 0,
        "extra_otu_ids": 0,
        "aligned_sequence_lengths": aligned_lengths,
        "ungapped_sequence_lengths": sequence_lengths,
        "unique_ungapped_sequences": len(by_sequence),
        "duplicate_sequence_groups": duplicate_groups,
        "json_file": str(json_path.relative_to(args.output)),
        "json_bytes": json_path.stat().st_size,
        "json_sha256": sha256(json_path),
        "checkgeneric_passed": True,
        "process_file": str(process_path.relative_to(args.output)),
        "process_rows": len(process_inputs),
        "unique_reads_inputs": len(set(process_inputs)),
        "process_term": "Classify OTUs <PROCESS:0000031>",
        "co_outputs": [*ORIGINAL_OUTPUTS, f"Generic: {BRICK_NAME}"],
        "replaced_process_ids": ["Process0013232", "Process0013443"],
    }
    (report_dir / "brick13_repseq_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
