#!/usr/bin/env python3
"""Build CORAL Community, Sampling-process, and taxonomy-brick corrections."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_RUN = (
    ROOT / "sync-coral-to-berdl/exports/sync-20260723-145923"
)
DEFAULT_OUTPUT = ROOT / "coral_import/community_taxonomy_corrections_20260724"
PROCESS_DATE = "2026-07-24"
CURATOR = "John-Marc Chandonia <ENIGMA:0000057>"
UPDATE_PROCESS = "Update Data <PROCESS:0000053>"
COMMUNITY_TYPE = "Environmental Community <ME:0000326>"

BRICK_SPECS: dict[str, dict[str, Any]] = {
    "Brick0000454": {
        "name": "zhou_lab_100ws_spring19_corepilot_27ws_cpt_ASV_taxonomy.ndarray",
        "description": "Zhou Lab 100WS Spring19 CorePilot 27WS CPT ASV Taxonomy",
        "campaign": "Environmental Atlas <ENIGMA:0000167>",
        "corrections": {
            "Alphaproteobacteria_Incertae_Sedis": (
                "Alphaproteobacteria_incertae_sedis",
                1,
            ),
            "Gammaproteobacteria_Incertae_Sedis": (
                "Gammaproteobacteria_incertae_sedis",
                630,
            ),
            "Rhizobiales_Incertae_Sedis": (
                "Rhizobiales_incertae_sedis",
                180,
            ),
            "RsaHf231": ("RsaHF231", 6),
        },
    },
    "Brick0000458": {
        "name": "zhou_lab_sso_sediment_ASV_taxonomy.ndarray",
        "description": "Zhou Lab SSO Sediment ASV Taxonomy",
        "campaign": "Subsurface Observatory <ENIGMA:0000166>",
        "corrections": {
            "20-Jan": ("1-20", 13),
            "24-Nov": ("11-24", 12),
            "29-Apr": ("4-29", 2),
            "4/29/2001": ("4-29-1", 43),
        },
    },
    "Brick0000461": {
        "name": "zhou_lab_sso_pump_test_ASV_taxonomy.ndarray",
        "description": "Zhou Lab SSO Pump Test ASV Taxonomy",
        "campaign": "Subsurface Observatory <ENIGMA:0000166>",
        "corrections": {
            "24-Nov": ("11-24", 8),
            "4/29/2001": ("4-29-1", 11),
        },
    },
    "Brick0000478": {
        "name": "zhou_lab_sso_pilot_time_series_ASV_taxonomy.ndarray",
        "description": "Zhou Lab SSO Pilot Time Series ASV Taxonomy",
        "campaign": "Subsurface Observatory <ENIGMA:0000166>",
        "corrections": {
            "24-Nov": ("11-24", 18),
            "4/29/2001": ("4-29-1", 11),
        },
    },
}

JAVA_CLASSES = Path("/h/jmc/src/java/classes")
JAVA_JARS = [
    Path(
        "/h/jmc/.m2/repository/com/fasterxml/jackson/core/"
        "jackson-annotations/2.5.1/jackson-annotations-2.5.1.jar"
    ),
    Path(
        "/h/jmc/.m2/repository/com/fasterxml/jackson/core/"
        "jackson-core/2.5.1/jackson-core-2.5.1.jar"
    ),
    Path(
        "/h/jmc/.m2/repository/com/fasterxml/jackson/core/"
        "jackson-databind/2.5.1/jackson-databind-2.5.1.jar"
    ),
    Path(
        "/h/jmc/.m2/repository/com/opencsv/opencsv/"
        "4.3.2/opencsv-4.3.2.jar"
    ),
    Path(
        "/h/jmc/.m2/repository/org/apache/commons/commons-lang3/"
        "3.4/commons-lang3-3.4.jar"
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, default=DEFAULT_SOURCE_RUN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(
    path: Path, fieldnames: list[str], rows: list[dict[str, str]]
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def java_classpath() -> str:
    required = [JAVA_CLASSES, *JAVA_JARS]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing Java classpath entries: {missing}")
    return os.pathsep.join(str(path) for path in required)


def run_java(class_name: str, *paths: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "java",
            "-Xmx4g",
            "-cp",
            java_classpath(),
            class_name,
            *(str(path) for path in paths),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def extract_dimension_values(path: Path, dimension: int) -> list[str]:
    values: list[str] = []
    active = False
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.reader(handle):
            if row and row[0] == "dmeta":
                active = int(row[1]) == dimension
                continue
            if row and row[0] == "data":
                break
            if active:
                values.append(row[1].rsplit(" <", 1)[0])
    return values


def build_community_rows(
    source_run: Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    static_dir = source_run / "coral_export/static_tsv"
    brick_path = source_run / "coral_export/brick_csv/Brick0000459.csv"
    names = extract_dimension_values(brick_path, 2)
    if len(names) != 37 or len(set(names)) != 37:
        raise ValueError(
            f"Expected 37 unique Brick459 Community names, found "
            f"{len(names)} rows and {len(set(names))} unique values"
        )

    samples_by_name = {
        row["name"]: row for row in read_tsv(static_dir / "Sample.tsv")
    }
    existing_communities = {
        row["name"] for row in read_tsv(static_dir / "Community.tsv")
    }
    missing_samples = sorted(set(names) - samples_by_name.keys())
    existing_names = sorted(set(names) & existing_communities)
    if missing_samples or existing_names:
        raise ValueError(
            f"Community preflight failed; missing_samples={missing_samples}, "
            f"already_existing_communities={existing_names}"
        )

    community_rows = [
        {
            "name": name,
            "community_type": COMMUNITY_TYPE,
            "sample": name,
            "parent_community": "null",
            "condition": "null",
            "defined_strains": "null",
            "description": "null",
        }
        for name in names
    ]
    sample_rows = [samples_by_name[name] for name in names]
    return community_rows, sample_rows


def parse_refs(value: str) -> list[tuple[str, str]]:
    return re.findall(r"([A-Za-z_]+):([A-Za-z0-9_-]+)", value)


def build_sampling_replacements(
    source_run: Path, sample_rows: list[dict[str, str]]
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    static_dir = source_run / "coral_export/static_tsv"
    processes = read_tsv(static_dir / "Process.tsv")
    locations_by_id = {
        row["id"]: row["name"] for row in read_tsv(static_dir / "Location.tsv")
    }
    process_by_sample: dict[str, dict[str, str]] = {}
    for process in processes:
        if process["process"] != "Sampling <PROCESS:0000002>":
            continue
        outputs = parse_refs(process["output_objects"])
        for object_type, object_id in outputs:
            if object_type == "Sample":
                if object_id in process_by_sample:
                    raise ValueError(
                        f"Sample {object_id} has multiple Sampling producers"
                    )
                process_by_sample[object_id] = process

    import_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []
    seen_processes: set[str] = set()
    for sample in sample_rows:
        process = process_by_sample.get(sample["id"])
        if process is None:
            raise ValueError(f"No Sampling process produces {sample['id']}")
        if process["id"] in seen_processes:
            raise ValueError(
                f"Sampling process {process['id']} produces multiple target Samples"
            )
        seen_processes.add(process["id"])

        inputs = parse_refs(process["input_objects"])
        outputs = parse_refs(process["output_objects"])
        if len(inputs) != 1 or inputs[0][0] != "Location":
            raise ValueError(
                f"Unexpected Sampling inputs for {process['id']}: {inputs}"
            )
        if outputs != [("Sample", sample["id"])]:
            raise ValueError(
                f"Unexpected Sampling outputs for {process['id']}: {outputs}"
            )
        location_id = inputs[0][1]
        location_name = locations_by_id.get(location_id)
        if location_name is None:
            raise ValueError(f"Missing Location row for {location_id}")
        if sample["location_id"] != location_name:
            raise ValueError(
                f"Sampling Location mismatch for {sample['id']}: "
                f"process={location_name}, sample={sample['location_id']}"
            )

        import_rows.append(
            {
                "process": process["process"],
                "person": process["person"],
                "campaign": process["campaign"],
                "protocol": process["protocol_id"] or "null",
                "date_start": process["date_start"] or "null",
                "date_end": process["date_end"] or "null",
                "input_objects": f"Location: {location_name}",
                "output_objects": (
                    f"Sample: {sample['name']}, Community: {sample['name']}"
                ),
            }
        )
        audit_rows.append(
            {
                "old_process_id": process["id"],
                "process": process["process"],
                "person": process["person"],
                "campaign": process["campaign"],
                "protocol": process["protocol_id"],
                "date_start": process["date_start"],
                "date_end": process["date_end"],
                "location_id": location_id,
                "location_name": location_name,
                "sample_id": sample["id"],
                "sample_name": sample["name"],
                "new_community_name": sample["name"],
            }
        )
    return import_rows, audit_rows


def new_brick_name(old_name: str) -> str:
    suffix = ".ndarray"
    if not old_name.endswith(suffix):
        raise ValueError(f"Expected ndarray name: {old_name}")
    return old_name[: -len(suffix)] + "_v2" + suffix


def rewrite_brick_csv(
    source: Path,
    destination: Path,
    spec: dict[str, Any],
) -> dict[str, int]:
    old_name = spec["name"]
    updated_name = new_brick_name(old_name)
    old_description = spec["description"]
    updated_description = old_description + "_v2"
    line_replacements = {
        f"name,{old_name}".encode(): f"name,{updated_name}".encode(),
        f"description,{old_description}".encode(): (
            f"description,{updated_description}".encode()
        ),
    }
    metadata_counts = {source: 0 for source in line_replacements}
    value_counts = {name: 0 for name in spec["corrections"]}

    with source.open("rb") as src, destination.open("wb") as dst:
        for line in src:
            content = line.rstrip(b"\r\n")
            newline = line[len(content) :]
            if content in line_replacements:
                metadata_counts[content] += 1
                content = line_replacements[content]
            for old_value, (canonical_value, _) in spec["corrections"].items():
                old_field = f"{old_value} <{old_value}>".encode()
                new_field = (
                    f"{canonical_value} <{canonical_value}>".encode()
                )
                count = content.count(old_field)
                if count:
                    value_counts[old_value] += count
                    content = content.replace(old_field, new_field)
            dst.write(content + newline)

    bad_metadata = {
        key.decode(): count
        for key, count in metadata_counts.items()
        if count != 1
    }
    bad_values = {
        old_value: {
            "expected": spec["corrections"][old_value][1],
            "observed": observed,
        }
        for old_value, observed in value_counts.items()
        if observed != spec["corrections"][old_value][1]
    }
    if bad_metadata or bad_values:
        raise ValueError(
            f"Brick rewrite mismatch for {source.name}: "
            f"metadata={bad_metadata}, values={bad_values}"
        )
    return value_counts


def file_contains(path: Path, needle: bytes) -> bool:
    overlap = max(len(needle) - 1, 0)
    tail = b""
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            data = tail + chunk
            if needle in data:
                return True
            tail = data[-overlap:] if overlap else b""
    return False


def build_bricks(
    source_run: Path,
    output: Path,
    taxon_names: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    json_dir = output / "json"
    check_dir = output / "check"
    reports: list[dict[str, Any]] = []
    update_rows: list[dict[str, str]] = []

    target_names = {
        canonical
        for spec in BRICK_SPECS.values()
        for canonical, _ in spec["corrections"].values()
    }
    missing_targets = sorted(target_names - taxon_names)
    if missing_targets:
        raise ValueError(
            f"Canonical Taxon names absent from fresh Taxon.tsv: {missing_targets}"
        )

    for brick_id, spec in BRICK_SPECS.items():
        source_csv = (
            source_run / "coral_export/brick_csv" / f"{brick_id}.csv"
        )
        updated_name = new_brick_name(spec["name"])
        json_path = json_dir / (
            updated_name.removesuffix(".ndarray") + ".json"
        )
        check_path = check_dir / f"{json_path.name}.check"

        with tempfile.TemporaryDirectory(
            prefix=f"{brick_id}_v2_", dir="/tmp"
        ) as tmpdir:
            corrected_csv = Path(tmpdir) / f"{brick_id}_v2.csv"
            counts = rewrite_brick_csv(source_csv, corrected_csv, spec)
            converted = run_java(
                "gov.lbl.enigma.app.ConvertGeneric",
                corrected_csv,
                json_path,
            )
            if converted.returncode != 0:
                raise RuntimeError(
                    f"ConvertGeneric failed for {brick_id}:\n"
                    + (converted.stdout or "")
                    + (converted.stderr or "")
                )

        for old_value, (canonical_value, _) in spec["corrections"].items():
            if file_contains(json_path, old_value.encode()):
                raise ValueError(
                    f"{brick_id} JSON still contains {old_value!r}"
                )
            if not file_contains(json_path, canonical_value.encode()):
                raise ValueError(
                    f"{brick_id} JSON lacks canonical {canonical_value!r}"
                )
        if not file_contains(json_path, f'"name":"{updated_name}"'.encode()):
            raise ValueError(f"{brick_id} JSON has wrong name")
        updated_description = spec["description"] + "_v2"
        if not file_contains(
            json_path, f'"description":"{updated_description}"'.encode()
        ):
            raise ValueError(f"{brick_id} JSON has wrong description")

        checked = run_java("gov.lbl.enigma.app.CheckGeneric", json_path)
        check_output = (checked.stdout or "") + (checked.stderr or "")
        check_path.write_text(check_output, encoding="utf-8")
        if checked.returncode != 0 or "Generic is OK!" not in check_output:
            raise RuntimeError(
                f"CheckGeneric failed for {brick_id}:\n{check_output}"
            )

        reports.append(
            {
                "source_brick": brick_id,
                "source_name": spec["name"],
                "replacement_name": updated_name,
                "source_description": spec["description"],
                "replacement_description": updated_description,
                "corrected_source_cells": sum(counts.values()),
                "correction_counts": counts,
                "source_sha256": sha256(source_csv),
                "json_path": str(json_path.relative_to(output)),
                "json_bytes": json_path.stat().st_size,
                "json_sha256": sha256(json_path),
                "check_path": str(check_path.relative_to(output)),
            }
        )
        update_rows.append(
            {
                "process": UPDATE_PROCESS,
                "person": CURATOR,
                "campaign": spec["campaign"],
                "protocol": "null",
                "date_start": PROCESS_DATE,
                "date_end": PROCESS_DATE,
                "input_objects": f"Generic: {spec['name']}",
                "output_objects": f"Generic: {updated_name}",
            }
        )
    return reports, update_rows


def deletion_script(targets: list[dict[str, str]]) -> str:
    template = r'''/* global ARGUMENTS, print */
"use strict";

const fs = require("fs");
const db = require("@arangodb").db;

const PROCESS_COLLECTION = "SYS_Process";
const INPUT_COLLECTION = "SYS_ProcessInput";
const OUTPUT_COLLECTION = "SYS_ProcessOutput";
const targets = __TARGETS__;
const args = typeof ARGUMENTS === "undefined" ? [] : ARGUMENTS;
const apply = args.indexOf("--apply") !== -1;
const processCollection = db._collection(PROCESS_COLLECTION);
const inputCollection = db._collection(INPUT_COLLECTION);
const outputCollection = db._collection(OUTPUT_COLLECTION);

function fail(message) {
  throw new Error(message);
}

const snapshots = targets.map((target) => {
  const processId = PROCESS_COLLECTION + "/" + target.old_process_id;
  const document = processCollection.document(target.old_process_id);
  if (document.process_term_id !== "PROCESS:0000002") {
    fail("Not a Sampling process: " + processId);
  }
  if (
    document.date_start !== target.date_start ||
    document.date_end !== target.date_end
  ) {
    fail("Sampling date mismatch: " + processId);
  }

  const inputEdges = db._query(
    `FOR edge IN @@collection FILTER edge._to == @id RETURN edge`,
    {"@collection": INPUT_COLLECTION, id: processId}
  ).toArray();
  const outputEdges = db._query(
    `FOR edge IN @@collection FILTER edge._from == @id RETURN edge`,
    {"@collection": OUTPUT_COLLECTION, id: processId}
  ).toArray();
  const expectedInput = "SDT_Location/" + target.location_id;
  const expectedOutput = "SDT_Sample/" + target.sample_id;
  if (
    inputEdges.length !== 1 ||
    inputEdges[0]._from !== expectedInput
  ) {
    fail("Unexpected input edges for " + processId);
  }
  if (
    outputEdges.length !== 1 ||
    outputEdges[0]._to !== expectedOutput
  ) {
    fail("Unexpected output edges for " + processId);
  }
  return {
    target: target,
    document: document,
    input_edges: inputEdges,
    output_edges: outputEdges
  };
});

print("validated Sampling processes: " + snapshots.length);
print("validated input edges: " +
  snapshots.reduce((n, row) => n + row.input_edges.length, 0));
print("validated output edges: " +
  snapshots.reduce((n, row) => n + row.output_edges.length, 0));

if (!apply) {
  print("Dry run only. Re-run with --apply to delete exact old processes.");
} else {
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const backupPath =
    "sampling_process_replacement_backup_" + timestamp + ".json";
  fs.write(backupPath, JSON.stringify(snapshots, null, 2) + "\n");

  snapshots.forEach((row) => {
    row.input_edges.forEach((edge) =>
      inputCollection.remove(edge._key));
    row.output_edges.forEach((edge) =>
      outputCollection.remove(edge._key));
    processCollection.remove(row.document._key);
  });

  snapshots.forEach((row) => {
    const processId =
      PROCESS_COLLECTION + "/" + row.target.old_process_id;
    if (processCollection.exists(row.target.old_process_id)) {
      fail("Process still exists after deletion: " + processId);
    }
    const remainingInputs = db._query(
      `FOR edge IN @@collection FILTER edge._to == @id RETURN 1`,
      {"@collection": INPUT_COLLECTION, id: processId}
    ).toArray().length;
    const remainingOutputs = db._query(
      `FOR edge IN @@collection FILTER edge._from == @id RETURN 1`,
      {"@collection": OUTPUT_COLLECTION, id: processId}
    ).toArray().length;
    if (remainingInputs || remainingOutputs) {
      fail("Process edges remain after deletion: " + processId);
    }
  });
  print("before-state backup: " + backupPath);
  print("deleted and verified Sampling processes: " + snapshots.length);
}
'''
    return template.replace(
        "__TARGETS__",
        json.dumps(targets, ensure_ascii=True, separators=(",", ":")),
    )


def write_helpers(output: Path, brick_reports: list[dict[str, Any]]) -> None:
    community_path = "static/Community_additions_20260724.tsv"
    sampling_path = (
        "process/process_sampling_sso_sediment_community_"
        "replacements_20260724.tsv"
    )
    update_path = "process/process_update_data_taxonomy_v2_20260724.tsv"
    json_paths = [report["json_path"] for report in brick_reports]
    (output / "files_to_import.txt").write_text(
        "\n".join([community_path, *json_paths, sampling_path, update_path])
        + "\n",
        encoding="utf-8",
    )
    commands = [
        "toolx.update_core('Community_additions_20260724.tsv', 'Community')",
        *[
            f"toolx.upload_brick('{Path(path).name}')"
            for path in json_paths
        ],
        "# Then run tools/delete_old_sampling_processes.js with --apply.",
        f"toolx.upload_process('Sampling', '{Path(sampling_path).name}')",
        f"toolx.upload_process('Update Data', '{Path(update_path).name}')",
    ]
    (output / "import_to_coral.py").write_text(
        "\n".join(commands) + "\n", encoding="utf-8"
    )


def write_readme(output: Path, brick_reports: list[dict[str, Any]]) -> None:
    replacements = "\n".join(
        f"- `{row['source_name']}` -> `{row['replacement_name']}` "
        f"({row['corrected_source_cells']} corrected cells)"
        for row in brick_reports
    )
    text = f"""# CORAL Community and taxonomy corrections

This package adds the 37 missing Environmental Communities used by Brick459,
replaces the 37 Sampling processes so each produces both the existing Sample
and the same-named Community, and supersedes four immutable taxonomy bricks.

## Required order

1. Import `static/Community_additions_20260724.tsv` as the CORAL Community
   static type. The file intentionally has no IDs; CORAL assigns them. Run:
   `toolx.update_core('Community_additions_20260724.tsv', 'Community')`.
2. Upload all four JSON bricks listed in `files_to_import.txt`.
3. Run `tools/delete_old_sampling_processes.js` with arangosh without
   arguments. It must validate exactly 37 processes and 74 edges.
4. Re-run that script with `--apply`. It writes a complete before-state backup
   before deleting the exact old Sampling process records and edges.
5. Upload
   `process/process_sampling_sso_sediment_community_replacements_20260724.tsv`
   with `toolx.upload_process('Sampling', ...)`.
6. Upload `process/process_update_data_taxonomy_v2_20260724.tsv` with
   `toolx.upload_process('Update Data', ...)`.
7. Re-poll CORAL before resuming the BERDL sync.

Do not import the replacement Sampling TSV before deleting the old records;
that would create duplicate provenance for the Samples.

## Taxonomy replacements

{replacements}

Every JSON file has a fresh check transcript under `check/` ending in
`Generic is OK!`. `reports/build_summary.json` contains hashes and exact
replacement counts.

## arangosh

```bash
arangosh <connection-options> \\
  --javascript.execute tools/delete_old_sampling_processes.js
arangosh <connection-options> \\
  --javascript.execute tools/delete_old_sampling_processes.js -- --apply
```
"""
    (output / "README.md").write_text(text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    source_run = args.source_run.resolve()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {output}")

    for directory in ("static", "process", "json", "check", "reports", "tools"):
        (output / directory).mkdir(parents=True)

    community_rows, sample_rows = build_community_rows(source_run)
    sampling_rows, sampling_audit = build_sampling_replacements(
        source_run, sample_rows
    )
    write_tsv(
        output / "static/Community_additions_20260724.tsv",
        [
            "name",
            "community_type",
            "sample",
            "parent_community",
            "condition",
            "defined_strains",
            "description",
        ],
        community_rows,
    )
    write_tsv(
        output
        / "process/process_sampling_sso_sediment_community_"
        "replacements_20260724.tsv",
        [
            "process",
            "person",
            "campaign",
            "protocol",
            "date_start",
            "date_end",
            "input_objects",
            "output_objects",
        ],
        sampling_rows,
    )
    write_tsv(
        output / "reports/sampling_process_replacements_20260724.tsv",
        list(sampling_audit[0]),
        sampling_audit,
    )

    deletion_targets = [
        {
            "old_process_id": row["old_process_id"],
            "location_id": row["location_id"],
            "sample_id": row["sample_id"],
            "date_start": row["date_start"],
            "date_end": row["date_end"],
        }
        for row in sampling_audit
    ]
    (output / "tools/delete_old_sampling_processes.js").write_text(
        deletion_script(deletion_targets), encoding="utf-8"
    )

    taxon_names = {
        row["name"]
        for row in read_tsv(
            source_run / "coral_export/static_tsv/Taxon.tsv"
        )
    }
    brick_reports, update_rows = build_bricks(
        source_run, output, taxon_names
    )
    write_tsv(
        output / "process/process_update_data_taxonomy_v2_20260724.tsv",
        [
            "process",
            "person",
            "campaign",
            "protocol",
            "date_start",
            "date_end",
            "input_objects",
            "output_objects",
        ],
        update_rows,
    )
    write_helpers(output, brick_reports)
    write_readme(output, brick_reports)

    summary = {
        "source_run": str(source_run),
        "communities_added": len(community_rows),
        "sampling_processes_replaced": len(sampling_rows),
        "taxonomy_bricks_replaced": len(brick_reports),
        "taxonomy_cells_corrected": sum(
            row["corrected_source_cells"] for row in brick_reports
        ),
        "brick_replacements": brick_reports,
    }
    (output / "reports/build_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
