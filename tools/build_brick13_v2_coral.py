#!/usr/bin/env python3
"""Build the corrected Brick13 v2 JSON and its CORAL Update Data process."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_RUN = ROOT / "sync-coral-to-berdl/exports/sync-20260717-174244"
DEFAULT_OUTPUT = ROOT / "coral_import/brick13_v2_20260720"

OLD_NAME = "zhou_otu_count_100ws.ndarray"
NEW_NAME = "zhou_otu_count_100ws_v2.ndarray"
OLD_DESCRIPTION = "Zhou Lab OTU Counts from 100 Well Survey"
NEW_DESCRIPTION = "Zhou Lab OTU Counts from 100 Well Survey (v2)"
OLD_DIMENSION = (
    "dmeta,1,Environmental Sample <ME:0000100>,"
    "Environmental Sample ID <ME:0000102>"
)
NEW_DIMENSION = "dmeta,1,Community <ME:0000231>,Community ID <ME:0000233>"

PROCESS = "Update Data <PROCESS:0000053>"
PERSON = "John-Marc Chandonia <ENIGMA:0000057>"
CAMPAIGN = "100 Well Survey <ENIGMA:0000003>"
PROCESS_DATE = "2026-07-20"

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
    parser.add_argument("--source-run", type=Path, default=DEFAULT_SOURCE_RUN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def java_classpath() -> str:
    required = [JAVA_CLASSES, *JAVA_JARS]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing Java classpath entries: {missing}")
    return os.pathsep.join(str(path) for path in required)


def source_dimension_values(source_csv: Path) -> list[str]:
    values: list[str] = []
    in_first_dimension = False
    with source_csv.open(newline="") as handle:
        for row in csv.reader(handle):
            if row[:2] == ["dmeta", "1"]:
                in_first_dimension = True
                continue
            if row[:2] == ["dmeta", "2"]:
                break
            if in_first_dimension:
                values.append(row[1].rsplit(" <", 1)[0])
    if len(values) != 212 or len(set(values)) != 212:
        raise ValueError(
            f"Expected 212 unique Brick13 first-dimension values, found "
            f"{len(values)} values and {len(set(values))} unique values"
        )
    return values


def validate_community_links(community_tsv: Path, values: list[str]) -> int:
    with community_tsv.open(newline="") as handle:
        rows = {
            row["sdt_community_name"]: row
            for row in csv.DictReader(handle, delimiter="\t")
        }
    missing = sorted(set(values) - rows.keys())
    if missing:
        raise ValueError(f"Brick13 values missing from sdt_community: {missing[:10]}")
    wrong_types = sorted(
        value
        for value in values
        if rows[value]["community_type_sys_oterm_name"] != "Environmental Community"
    )
    if wrong_types:
        raise ValueError(f"Brick13 values with unexpected community types: {wrong_types[:10]}")
    parent_samples = {rows[value]["sdt_sample_name"] for value in values}
    if "" in parent_samples:
        raise ValueError("At least one Brick13 community has no parent sample")
    return len(parent_samples)


def rewrite_source_csv(source: Path, destination: Path) -> None:
    replacements = {
        f"name,{OLD_NAME}".encode(): f"name,{NEW_NAME}".encode(),
        f"description,{OLD_DESCRIPTION}".encode(): f"description,{NEW_DESCRIPTION}".encode(),
        OLD_DIMENSION.encode(): NEW_DIMENSION.encode(),
    }
    counts = {key: 0 for key in replacements}
    with source.open("rb") as src, destination.open("wb") as dst:
        for line in src:
            content = line.rstrip(b"\r\n")
            newline = line[len(content):]
            replacement = replacements.get(content)
            if replacement is not None:
                counts[content] += 1
                content = replacement
            dst.write(content + newline)
    bad_counts = {key.decode(): count for key, count in counts.items() if count != 1}
    if bad_counts:
        raise ValueError(f"Expected each Brick13 metadata replacement once: {bad_counts}")


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


def validate_json_prefix(json_path: Path) -> None:
    with json_path.open("rb") as handle:
        prefix = handle.read(2_000_000)
    required = [
        f'"name":"{NEW_NAME}"'.encode(),
        f'"description":"{NEW_DESCRIPTION}"'.encode(),
        b'"oterm_ref":"ME:0000231"',
        b'"oterm_ref":"ME:0000233"',
        b'"scalar_type":"object_ref"',
    ]
    missing = [snippet.decode() for snippet in required if snippet not in prefix]
    forbidden = [
        b'"oterm_ref":"ME:0000100"',
        b'"oterm_ref":"ME:0000102"',
    ]
    present_forbidden = [snippet.decode() for snippet in forbidden if snippet in prefix]
    if missing or present_forbidden:
        raise ValueError(
            f"Converted JSON metadata mismatch; missing={missing}, "
            f"forbidden={present_forbidden}"
        )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_process(path: Path) -> None:
    fieldnames = [
        "process",
        "person",
        "campaign",
        "protocol",
        "date_start",
        "date_end",
        "input_objects",
        "output_objects",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerow(
            {
                "process": PROCESS,
                "person": PERSON,
                "campaign": CAMPAIGN,
                "protocol": "null",
                "date_start": PROCESS_DATE,
                "date_end": PROCESS_DATE,
                "input_objects": f"Generic: {OLD_NAME}",
                "output_objects": f"Generic: {NEW_NAME}",
            }
        )


def write_import_helpers(output: Path, json_path: Path, process_path: Path) -> None:
    (output / "files_to_import.txt").write_text(
        f"json/{json_path.name}\nprocess/{process_path.name}\n"
    )
    (output / "import_to_coral.py").write_text(
        "# Upload both files listed in files_to_import.txt, then run these in order.\n"
        f"toolx.upload_brick('{json_path.name}')\n"
        f"toolx.upload_process('Update Data', '{process_path.name}')\n"
    )


def main() -> None:
    args = parse_args()
    source_csv = args.source_run / "coral_export/brick_csv/Brick0000013.csv"
    community_tsv = args.source_run / "berdl_upload/data/sdt_community.tsv"
    if not source_csv.exists() or not community_tsv.exists():
        raise FileNotFoundError(
            f"Required source artifacts not found under {args.source_run}"
        )
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {args.output}")

    json_dir = args.output / "json"
    check_dir = args.output / "check"
    process_dir = args.output / "process"
    report_dir = args.output / "reports"
    for directory in (json_dir, check_dir, process_dir, report_dir):
        directory.mkdir(parents=True)

    dimension_values = source_dimension_values(source_csv)
    parent_sample_count = validate_community_links(community_tsv, dimension_values)
    json_path = json_dir / "zhou_otu_count_100ws_v2.json"
    check_path = check_dir / "zhou_otu_count_100ws_v2.json.check"
    process_path = process_dir / "process_update_data_zhou_otu_count_100ws_v2_20260720.tsv"

    with tempfile.TemporaryDirectory(prefix="brick13_v2_", dir="/tmp") as tmpdir:
        corrected_csv = Path(tmpdir) / "zhou_otu_count_100ws_v2.csv"
        rewrite_source_csv(source_csv, corrected_csv)
        converted = run_java(
            "gov.lbl.enigma.app.ConvertGeneric", corrected_csv, json_path
        )
        if converted.returncode != 0:
            raise RuntimeError(
                "ConvertGeneric failed:\n"
                + (converted.stdout or "")
                + (converted.stderr or "")
            )

    validate_json_prefix(json_path)
    checked = run_java("gov.lbl.enigma.app.CheckGeneric", json_path)
    check_output = (checked.stdout or "") + (checked.stderr or "")
    check_path.write_text(check_output)
    if checked.returncode != 0 or "Generic is OK!" not in check_output:
        raise RuntimeError(f"CheckGeneric failed for {json_path}:\n{check_output}")

    write_process(process_path)
    write_import_helpers(args.output, json_path, process_path)
    summary = {
        "source_brick": "Brick0000013",
        "source_name": OLD_NAME,
        "replacement_name": NEW_NAME,
        "replacement_description": NEW_DESCRIPTION,
        "dimension_change": {
            "from": OLD_DIMENSION.removeprefix("dmeta,1,"),
            "to": NEW_DIMENSION.removeprefix("dmeta,1,"),
        },
        "community_values": len(dimension_values),
        "distinct_parent_samples": parent_sample_count,
        "json_file": str(json_path.relative_to(args.output)),
        "json_bytes": json_path.stat().st_size,
        "json_sha256": sha256(json_path),
        "checkgeneric_passed": True,
        "process_file": str(process_path.relative_to(args.output)),
    }
    (report_dir / "brick13_v2_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
