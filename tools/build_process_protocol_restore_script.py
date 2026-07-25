#!/usr/bin/env python3
"""Build a self-contained arangosh Process.protocol restoration script."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REPLACEMENTS = {
    "arkin-plasmidsaurus-2023": "arkin-2023-plasmidsaurus",
    "chandonia-2019-trimmomatic2": "chandonia-2019-trimmomatic-2",
    "illumina-hiseq-4000-pe": "illumina-hiseq-4000-150pe",
    "nielsen-2019-bin-refinemen": "nielsen-2019-bin-refinement",
}
PLACEHOLDER = "__PROCESS_PROTOCOL_PATCHES_JSON__"


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--process", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    process_rows = read_tsv(args.process)
    protocol_rows = read_tsv(args.protocol)
    protocol_names = {row["name"] for row in protocol_rows}

    patches: list[dict[str, str | None]] = []
    seen: set[str] = set()
    replacement_counts = {source: 0 for source in REPLACEMENTS}
    for row in process_rows:
        process_id = row["id"]
        if process_id in seen:
            raise ValueError(f"duplicate process ID: {process_id}")
        seen.add(process_id)
        source_protocol = row["protocol_id"] or None
        if source_protocol in REPLACEMENTS:
            replacement_counts[source_protocol] += 1
            desired_protocol = REPLACEMENTS[source_protocol]
        else:
            desired_protocol = source_protocol
        patches.append({"id": process_id, "protocol": desired_protocol})

    desired_names = {
        patch["protocol"] for patch in patches if patch["protocol"] is not None
    }
    missing_protocols = sorted(desired_names - protocol_names)
    if missing_protocols:
        raise ValueError(
            f"desired protocols missing from Protocol.tsv: {missing_protocols}"
        )

    template = args.template.read_text(encoding="utf-8")
    if template.count(PLACEHOLDER) != 1:
        raise ValueError(f"template must contain exactly one {PLACEHOLDER}")
    payload = json.dumps(patches, ensure_ascii=True, separators=(",", ":"))
    output = template.replace(PLACEHOLDER, payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8")

    print(
        json.dumps(
            {
                "output": str(args.output),
                "processes": len(patches),
                "non_empty_protocols": sum(
                    patch["protocol"] is not None for patch in patches
                ),
                "distinct_protocols": len(desired_names),
                "replacement_counts": replacement_counts,
                "bytes": args.output.stat().st_size,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
