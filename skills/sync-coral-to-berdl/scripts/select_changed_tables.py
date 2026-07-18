#!/usr/bin/env python3
"""Compare CORAL sync manifests and select tables requiring BERDL ingest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_lines(path: Path, values: list[str]) -> None:
    path.write_text("".join(f"{value}\n" for value in values), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--previous-manifest", required=True, type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    current_path = run_dir / "manifests" / "current.json"
    config_path = run_dir / "ingest" / "config.dry_run.json"
    current = _load_json(current_path)
    previous = _load_json(args.previous_manifest.resolve())
    config = _load_json(config_path)

    current_by_name = {row["table"]: row for row in current.get("tables", [])}
    previous_by_name = {row["table"]: row for row in previous.get("tables", [])}
    config_by_name = {table["name"]: table for table in config.get("tables", [])}

    ingest = []
    comments_only = []
    unchanged = []
    obsolete_excluded = []
    added = []
    details = []
    for table_name, row in sorted(current_by_name.items()):
        table_config = config_by_name.get(table_name)
        if table_config is not None and not table_config.get("enabled"):
            status = "obsolete_excluded"
            obsolete_excluded.append(table_name)
            changed_parts = []
        else:
            prior = previous_by_name.get(table_name)
            if prior is None:
                status = "added"
                added.append(table_name)
                ingest.append(table_name)
                changed_parts = ["data", "schema", "comments"]
            else:
                changed_parts = [
                    key.removesuffix("_sha256")
                    for key in ("data_sha256", "schema_sha256", "comments_sha256")
                    if row.get("hashes", {}).get(key) != prior.get("hashes", {}).get(key)
                ]
                if "data" in changed_parts or "schema" in changed_parts:
                    status = "ingest"
                    ingest.append(table_name)
                elif "comments" in changed_parts:
                    status = "comments_only"
                    comments_only.append(table_name)
                else:
                    status = "unchanged"
                    unchanged.append(table_name)
        row["change_status"] = status
        row["changed_parts"] = changed_parts
        if table_config is not None:
            table_config["change_status"] = status
            table_config["changed_parts"] = changed_parts
        details.append({
            "table": table_name,
            "status": status,
            "changed_parts": changed_parts,
        })

    removed = sorted(set(previous_by_name) - set(current_by_name))
    ingest = sorted(set(ingest))
    comments_only = sorted(set(comments_only))
    unchanged = sorted(set(unchanged))
    obsolete_excluded = sorted(set(obsolete_excluded))

    ingest_dir = run_dir / "ingest"
    reports_dir = run_dir / "reports"
    _write_lines(ingest_dir / "changed_tables.txt", ingest)
    _write_lines(ingest_dir / "comment_only_tables.txt", comments_only)
    _write_lines(ingest_dir / "unchanged_tables.txt", unchanged)
    _write_lines(ingest_dir / "obsolete_excluded_tables.txt", obsolete_excluded)
    _write_lines(reports_dir / "removed_from_export_tables.txt", removed)

    report = {
        "previous_run_id": previous.get("run_id"),
        "current_run_id": current.get("run_id"),
        "ingest_tables": ingest,
        "comment_only_tables": comments_only,
        "unchanged_tables": unchanged,
        "obsolete_excluded_tables": obsolete_excluded,
        "added_tables": sorted(added),
        "removed_from_export_tables": removed,
        "details": details,
    }
    (reports_dir / "manifest_diff.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    current_path.write_text(json.dumps(current, indent=2), encoding="utf-8")
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(json.dumps({
        "ingest": len(ingest),
        "comments_only": len(comments_only),
        "unchanged": len(unchanged),
        "obsolete_excluded": len(obsolete_excluded),
        "added": len(added),
        "removed_from_export": len(removed),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
