#!/usr/bin/env python3
"""List files inside only the bounded EDR genome-version candidate folders."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version-listings", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--https-proxy", default="http://127.0.0.1:8123")
    return parser.parse_args()


def candidate_folders(path: Path) -> list[dict[str, str]]:
    folders: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            record = json.loads(raw)
            result = record.get("mc_result")
            if not isinstance(result, dict) or result.get("type") != "folder":
                continue
            key = str(result.get("key") or "")
            if not key:
                continue
            folders.append(
                {
                    "scope": str(record["scope"]),
                    "strain": str(record["strain"]),
                    "version_key": key,
                    "prefix": str(record["prefix"]).rstrip("/") + "/" + key,
                }
            )
    return folders


def main() -> int:
    args = parse_args()
    folders = candidate_folders(args.version_listings)
    environment = os.environ.copy()
    environment["https_proxy"] = args.https_proxy
    environment["no_proxy"] = "localhost,127.0.0.1"
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for folder in folders:
        result = subprocess.run(
            ["mc", "ls", "--json", folder["prefix"]],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        for raw in result.stdout.splitlines():
            if raw.strip():
                records.append({**folder, "mc_result": json.loads(raw)})
        if result.returncode != 0:
            failures.append(
                {
                    **folder,
                    "returncode": result.returncode,
                    "stderr": result.stderr.strip()[:1000],
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(f".{args.output.name}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    os.replace(temporary, args.output)

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "candidate_folders": len(folders),
        "file_records": len(records),
        "failures": failures,
    }
    report_temporary = args.report.with_name(f".{args.report.name}.tmp")
    report_temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    os.replace(report_temporary, args.report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
