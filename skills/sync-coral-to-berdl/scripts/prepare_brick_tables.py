#!/usr/bin/env python3
"""Prepare current brick tables, reusing prior artifacts for immutable brick IDs."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import traceback
from pathlib import Path
from typing import Any

from repository_paths import normalize_repository_links_in_tsv


CONVERTER = Path("/h/jmc/src/CORAL/convert/spark-minio/convert_bricks.py")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifacts(run_dir: Path, brick_id: str) -> dict[str, Path]:
    return {
        "data": run_dir / "berdl_upload" / "data" / f"{brick_id}.tsv",
        "schema": run_dir / "berdl_upload" / "schema" / f"{brick_id}_schema.py",
        "ddt_ndarray": run_dir / "metadata" / "brick_sidecars" / f"{brick_id}_ddt_ndarray.tsv",
        "sys_ddt_typedef": run_dir / "metadata" / "brick_sidecars" / f"{brick_id}_sys_ddt_typedef.tsv",
    }


def _copy_atomic(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file() and target.stat().st_size > 0:
        return
    temporary = target.with_name(f".{target.name}.copying")
    temporary.unlink(missing_ok=True)
    try:
        os.link(source, temporary)
    except OSError:
        subprocess.run(
            [
                "cp",
                "--reflink=auto",
                "--preserve=mode,timestamps",
                str(source),
                str(temporary),
            ],
            check=True,
        )
    temporary.replace(target)


def _reuse_artifacts(
    previous_run: Path,
    run_dir: Path,
    brick_id: str,
    normalization_complete: bool = False,
) -> dict[str, int]:
    for name, source in _artifacts(previous_run, brick_id).items():
        _copy_atomic(source, _artifacts(run_dir, brick_id)[name])
    if normalization_complete:
        return {"cells_changed": 0, "replacements": 0}
    return normalize_repository_links_in_tsv(_artifacts(run_dir, brick_id)["data"])


def _previous_raw_hashes(previous_run: Path) -> dict[str, str]:
    report_path = previous_run / "reports" / "brick_preparation.json"
    if not report_path.is_file():
        return {}
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return {
        str(brick_id): str(digest)
        for brick_id, digest in report.get("raw_sha256", {}).items()
    }


def _previous_normalized_bricks(previous_run: Path) -> set[str]:
    report_path = previous_run / "reports" / "brick_preparation.json"
    if not report_path.is_file():
        return set()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    by_brick = report.get("repository_path_normalization", {}).get("by_brick", {})
    return set(by_brick)


def _load_converter():
    spec = importlib.util.spec_from_file_location("coral_convert_bricks", CONVERTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _convert_one(
    raw_path: Path,
    run_dir: Path,
    converter,
    term_map,
    parent_map,
    type_map,
) -> dict[str, Any]:
    brick_id = raw_path.stem
    stage_dir = run_dir / "convert_stage" / brick_id
    stage_dir.mkdir(parents=True, exist_ok=True)
    stage_data = stage_dir / f"{brick_id}.tsv"
    try:
        converter.convert(
            str(raw_path),
            str(stage_data),
            term_map,
            parent_map,
            type_map,
            brick_id,
        )
        normalization = normalize_repository_links_in_tsv(stage_data)
    except Exception:
        return {
            "brick_id": brick_id,
            "status": "failed",
            "error": traceback.format_exc()[-8000:],
        }

    staged = {
        "data": stage_data,
        "schema": stage_dir / f"{brick_id}_schema.py",
        "ddt_ndarray": stage_dir / f"{brick_id}_ddt_ndarray.tsv",
        "sys_ddt_typedef": stage_dir / f"{brick_id}_sys_ddt_typedef.tsv",
    }
    missing = [name for name, path in staged.items() if not path.is_file() or path.stat().st_size == 0]
    if missing:
        return {
            "brick_id": brick_id,
            "status": "failed",
            "missing_artifacts": missing,
        }
    for name, source in staged.items():
        target = _artifacts(run_dir, brick_id)[name]
        target.parent.mkdir(parents=True, exist_ok=True)
        source.replace(target)
    stage_dir.rmdir()
    return {
        "brick_id": brick_id,
        "status": "converted",
        "repository_path_normalization": normalization,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--previous-run-dir", required=True, type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    previous_run = args.previous_run_dir.resolve()
    raw_dir = run_dir / "coral_export" / "brick_csv"
    previous_raw_dir = previous_run / "coral_export" / "brick_csv"
    typedef = run_dir / "coral_export" / "schema" / "typedef.json"
    ontologies = sorted((run_dir / "coral_export" / "ontologies").glob("*.obo"))
    if not typedef.is_file() or not ontologies:
        raise FileNotFoundError("Staged typedef.json and at least one OBO file are required")

    raw_paths = sorted(raw_dir.glob("Brick*.csv"))
    if not raw_paths:
        raise RuntimeError(f"No brick CSV files found in {raw_dir}")

    reused = []
    resumed = []
    reused_normalization = {}
    to_convert = []
    raw_hashes = {}
    previous_hashes = _previous_raw_hashes(previous_run)
    previous_normalized = _previous_normalized_bricks(previous_run)
    for index, raw_path in enumerate(raw_paths, start=1):
        brick_id = raw_path.stem
        previous_raw = previous_raw_dir / raw_path.name
        previous_artifacts = _artifacts(previous_run, brick_id)
        current_artifacts = _artifacts(run_dir, brick_id)
        can_reuse = (
            previous_raw.is_file()
            and all(path.is_file() and path.stat().st_size > 0 for path in previous_artifacts.values())
        )
        if can_reuse:
            raw_hashes[brick_id] = previous_hashes.get(brick_id) or _sha256(previous_raw)
            reused_normalization[brick_id] = _reuse_artifacts(
                previous_run,
                run_dir,
                brick_id,
                normalization_complete=brick_id in previous_normalized,
            )
            reused.append(brick_id)
        elif all(path.is_file() and path.stat().st_size > 0 for path in current_artifacts.values()):
            raw_hashes[brick_id] = _sha256(raw_path)
            reused_normalization[brick_id] = {"cells_changed": 0, "replacements": 0}
            resumed.append(brick_id)
        else:
            raw_hashes[brick_id] = _sha256(raw_path)
            to_convert.append(raw_path)
        if index % 100 == 0:
            print(f"[classify {index}/{len(raw_paths)}] reused={len(reused)} convert={len(to_convert)}", flush=True)

    results = [
        {
            "brick_id": brick_id,
            "status": "converted",
            "resumed": True,
            "repository_path_normalization": {"cells_changed": 0, "replacements": 0},
        }
        for brick_id in resumed
    ]
    if to_convert:
        converter = _load_converter()
        print(f"Loading {len(ontologies)} staged ontology files once for all conversions", flush=True)
        term_map, parent_map = converter.load_multiple_obos([str(path) for path in ontologies])
        type_map = converter.load_typedef(str(typedef))
        for index, path in enumerate(to_convert, start=1):
            row = _convert_one(path, run_dir, converter, term_map, parent_map, type_map)
            results.append(row)
            print(
                f"[convert {index}/{len(to_convert)}] {row['brick_id']} {row['status']}",
                flush=True,
            )

    failures = [row for row in results if row["status"] != "converted"]
    normalization_by_brick = {
        **reused_normalization,
        **{
            row["brick_id"]: row["repository_path_normalization"]
            for row in results
            if row["status"] == "converted"
        },
    }
    normalized_bricks = sorted(
        brick_id
        for brick_id, stats in normalization_by_brick.items()
        if stats["cells_changed"]
    )
    report = {
        "raw_bricks": len(raw_paths),
        "reused": len(reused),
        "resumed": len(resumed),
        "converted": sum(row["status"] == "converted" for row in results),
        "failed": len(failures),
        "reused_bricks": reused,
        "conversion_results": sorted(results, key=lambda row: row["brick_id"]),
        "repository_path_normalization": {
            "bricks_changed": normalized_bricks,
            "cells_changed": sum(stats["cells_changed"] for stats in normalization_by_brick.values()),
            "replacements": sum(stats["replacements"] for stats in normalization_by_brick.values()),
            "by_brick": normalization_by_brick,
        },
        "raw_sha256": raw_hashes,
        "converter": str(CONVERTER),
        "converter_sha256": _sha256(CONVERTER),
        "typedef_sha256": _sha256(typedef),
        "ontology_sha256": {path.name: _sha256(path) for path in ontologies},
    }
    report_path = run_dir / "reports" / "brick_preparation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("raw_bricks", "reused", "converted", "failed")}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
