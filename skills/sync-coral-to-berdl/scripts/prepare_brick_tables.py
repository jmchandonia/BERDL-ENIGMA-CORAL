#!/usr/bin/env python3
"""Prepare current brick tables, reusing only byte-identical prior exports."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import traceback
from pathlib import Path
from typing import Any


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
    temporary = target.with_name(f".{target.name}.copying")
    shutil.copy2(source, temporary)
    temporary.replace(target)


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
    return {"brick_id": brick_id, "status": "converted"}


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
    to_convert = []
    raw_hashes = {}
    for index, raw_path in enumerate(raw_paths, start=1):
        brick_id = raw_path.stem
        current_hash = _sha256(raw_path)
        raw_hashes[brick_id] = current_hash
        previous_raw = previous_raw_dir / raw_path.name
        previous_artifacts = _artifacts(previous_run, brick_id)
        can_reuse = (
            previous_raw.is_file()
            and _sha256(previous_raw) == current_hash
            and all(path.is_file() and path.stat().st_size > 0 for path in previous_artifacts.values())
        )
        if can_reuse:
            for name, source in previous_artifacts.items():
                _copy_atomic(source, _artifacts(run_dir, brick_id)[name])
            reused.append(brick_id)
        else:
            to_convert.append(raw_path)
        if index % 100 == 0:
            print(f"[classify {index}/{len(raw_paths)}] reused={len(reused)} convert={len(to_convert)}", flush=True)

    converter = _load_converter()
    print(f"Loading {len(ontologies)} staged ontology files once for all conversions", flush=True)
    term_map, parent_map = converter.load_multiple_obos([str(path) for path in ontologies])
    type_map = converter.load_typedef(str(typedef))
    results = []
    for index, path in enumerate(to_convert, start=1):
        row = _convert_one(path, run_dir, converter, term_map, parent_map, type_map)
        results.append(row)
        print(
            f"[convert {index}/{len(to_convert)}] {row['brick_id']} {row['status']}",
            flush=True,
        )

    failures = [row for row in results if row["status"] != "converted"]
    report = {
        "raw_bricks": len(raw_paths),
        "reused": len(reused),
        "converted": sum(row["status"] == "converted" for row in results),
        "failed": len(failures),
        "reused_bricks": reused,
        "conversion_results": sorted(results, key=lambda row: row["brick_id"]),
        "raw_sha256": raw_hashes,
        "converter": str(CONVERTER),
        "converter_sha256": _sha256(CONVERTER),
        "typedef_sha256": _sha256(typedef),
        "ontology_sha256": {path.name: _sha256(path) for path in ontologies},
    }
    report_path = run_dir / "reports" / "brick_preparation.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("raw_bricks", "reused", "converted", "failed")}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
