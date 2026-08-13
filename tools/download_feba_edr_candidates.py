#!/usr/bin/env python3
"""Download only EDR contigs/GFF candidate pairs from a bounded file listing."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file-listings", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--https-proxy", default="http://127.0.0.1:8123")
    return parser.parse_args()


def selected_files(path: Path) -> list[dict[str, Any]]:
    folders: dict[tuple[str, str, str, str], dict[str, dict[str, Any]]] = {}
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            record = json.loads(raw)
            result = record.get("mc_result")
            if not isinstance(result, dict) or result.get("type") != "file":
                continue
            identity = (
                str(record["scope"]),
                str(record["strain"]),
                str(record["version_key"]),
                str(record["prefix"]),
            )
            folders.setdefault(identity, {})[str(result.get("key", ""))] = result

    selected: list[dict[str, Any]] = []
    for (scope, strain, version_key, prefix), files in sorted(folders.items()):
        required = (f"{strain}_contigs.fasta", f"{strain}_Prodigal.gff")
        missing = [name for name in required if name not in files]
        if missing:
            raise ValueError(
                f"Candidate folder {scope}/{strain}/{version_key} is missing {missing}"
            )
        version = version_key.rstrip("/")
        if not version or Path(version).name != version:
            raise ValueError(f"Unsafe candidate version key: {version_key!r}")
        for filename in required:
            if Path(filename).name != filename:
                raise ValueError(f"Unsafe candidate filename: {filename!r}")
            result = files[filename]
            selected.append(
                {
                    "scope": scope,
                    "strain": strain,
                    "version": version,
                    "filename": filename,
                    "source": prefix.rstrip("/") + "/" + filename,
                    "expected_size": int(result["size"]),
                    "etag": str(result.get("etag", "")),
                }
            )
    if not selected:
        raise ValueError("No candidate FASTA/GFF files were selected")
    return selected


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def main() -> int:
    args = parse_args()
    candidates = selected_files(args.file_listings)
    environment = os.environ.copy()
    environment["https_proxy"] = args.https_proxy
    environment["no_proxy"] = "localhost,127.0.0.1"
    completed: list[dict[str, Any]] = []

    for candidate in candidates:
        destination = (
            args.output_dir
            / candidate["scope"]
            / candidate["strain"]
            / candidate["version"]
            / candidate["filename"]
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        reused = destination.is_file() and destination.stat().st_size == candidate["expected_size"]
        if not reused:
            partial = destination.with_name(f".{destination.name}.part")
            if partial.exists():
                partial.unlink()
            result = subprocess.run(
                ["mc", "cp", candidate["source"], str(partial)],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"mc cp failed for {candidate['source']}: {result.stderr[:2000]}"
                )
            if (
                not partial.exists()
                and destination.is_file()
                and destination.stat().st_size == candidate["expected_size"]
            ):
                # A prior/resumed writer may have atomically finalized the same file.
                pass
            elif not partial.is_file() or partial.stat().st_size != candidate["expected_size"]:
                raise ValueError(
                    f"Downloaded size mismatch for {candidate['source']}: "
                    f"expected {candidate['expected_size']}, "
                    f"found {partial.stat().st_size if partial.exists() else 'missing'}"
                )
            else:
                os.replace(partial, destination)
        completed.append(
            {
                **candidate,
                "destination": str(destination.resolve()),
                "sha256": sha256_file(destination),
                "reused_existing": reused,
            }
        )

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source_listing": str(args.file_listings.resolve()),
        "output_dir": str(args.output_dir.resolve()),
        "candidate_versions": len(candidates) // 2,
        "files": len(completed),
        "bytes": sum(row["expected_size"] for row in completed),
        "completed": completed,
    }
    write_json_atomic(args.report, report)
    print(
        json.dumps(
            {key: report[key] for key in ("candidate_versions", "files", "bytes")},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
