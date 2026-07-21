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


def _foreign_key_targets(table: dict[str, Any]) -> tuple[bool, set[str]]:
    declared = False
    targets: set[str] = set()
    for coldef in table.get("schema") or []:
        comment = coldef.get("comment")
        if isinstance(comment, str):
            try:
                comment = json.loads(comment)
            except json.JSONDecodeError:
                declared = declared or "foreign_key" in comment
                continue
        if isinstance(comment, dict) and comment.get("type") == "foreign_key":
            declared = True
            reference = comment.get("references")
            if isinstance(reference, str):
                reference = reference.removeprefix("[").removesuffix("]")
                if reference.count(".") == 1:
                    targets.add(reference.split(".", 1)[0])
    return declared, targets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--previous-manifest", required=True, type=Path)
    parser.add_argument("--previous-config", type=Path)
    parser.add_argument("--force-reload-file", type=Path)
    parser.add_argument("--live-tables-file", type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    current_path = run_dir / "manifests" / "current.json"
    config_path = run_dir / "ingest" / "config.dry_run.json"
    current = _load_json(current_path)
    previous = _load_json(args.previous_manifest.resolve())
    config = _load_json(config_path)
    previous_config = (
        _load_json(args.previous_config.resolve()) if args.previous_config else {}
    )
    force_reload = set(
        args.force_reload_file.read_text(encoding="utf-8").split()
    ) if args.force_reload_file else set()
    live_tables = set(
        args.live_tables_file.read_text(encoding="utf-8").split()
    ) if args.live_tables_file else None

    current_by_name = {row["table"]: row for row in current.get("tables", [])}
    previous_by_name = {row["table"]: row for row in previous.get("tables", [])}
    config_by_name = {table["name"]: table for table in config.get("tables", [])}
    previous_config_by_name = {
        table["name"]: table for table in previous_config.get("tables", [])
    }

    ingest = []
    comments_only = []
    unchanged = []
    obsolete_excluded = []
    added = []
    reactivated = []
    forced = []
    missing_live = []
    details = []
    for table_name, row in sorted(current_by_name.items()):
        table_config = config_by_name.get(table_name)
        if table_config is not None and not table_config.get("enabled"):
            status = "obsolete_excluded"
            obsolete_excluded.append(table_name)
            changed_parts = []
        else:
            prior = previous_by_name.get(table_name)
            prior_table_config = previous_config_by_name.get(table_name)
            if table_name in force_reload:
                status = "strategy_reload"
                forced.append(table_name)
                ingest.append(table_name)
                changed_parts = ["import_strategy"]
            elif prior_table_config is not None and not prior_table_config.get("enabled"):
                status = "lifecycle_reactivated"
                reactivated.append(table_name)
                ingest.append(table_name)
                changed_parts = ["lifecycle"]
            elif live_tables is not None and table_name not in live_tables:
                status = "missing_live_reload"
                missing_live.append(table_name)
                ingest.append(table_name)
                changed_parts = ["missing_live_table"]
            elif prior is None:
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
    direct_foreign_key_tables = []
    target_impacted_foreign_key_tables = []
    for table_name, table_config in config_by_name.items():
        if not table_config.get("enabled"):
            continue
        has_foreign_key, targets = _foreign_key_targets(table_config)
        if not has_foreign_key:
            continue
        if table_name in ingest:
            direct_foreign_key_tables.append(table_name)
        elif targets & set(ingest):
            target_impacted_foreign_key_tables.append(table_name)
    foreign_key_tables = sorted(set(
        direct_foreign_key_tables + target_impacted_foreign_key_tables
    ))

    ingest_dir = run_dir / "ingest"
    reports_dir = run_dir / "reports"
    _write_lines(ingest_dir / "changed_tables.txt", ingest)
    _write_lines(
        ingest_dir / "changed_tables_with_foreign_keys.txt",
        foreign_key_tables,
    )
    _write_lines(ingest_dir / "comment_only_tables.txt", comments_only)
    _write_lines(ingest_dir / "unchanged_tables.txt", unchanged)
    _write_lines(ingest_dir / "obsolete_excluded_tables.txt", obsolete_excluded)
    _write_lines(reports_dir / "removed_from_export_tables.txt", removed)

    report = {
        "previous_run_id": previous.get("run_id"),
        "current_run_id": current.get("run_id"),
        "ingest_tables": ingest,
        "foreign_key_check_tables": foreign_key_tables,
        "direct_foreign_key_check_tables": sorted(direct_foreign_key_tables),
        "target_impacted_foreign_key_check_tables": sorted(
            target_impacted_foreign_key_tables
        ),
        "comment_only_tables": comments_only,
        "unchanged_tables": unchanged,
        "obsolete_excluded_tables": obsolete_excluded,
        "added_tables": sorted(added),
        "reactivated_tables": sorted(reactivated),
        "forced_reload_tables": sorted(forced),
        "missing_live_reload_tables": sorted(missing_live),
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
        "foreign_key_check": len(foreign_key_tables),
        "comments_only": len(comments_only),
        "unchanged": len(unchanged),
        "obsolete_excluded": len(obsolete_excluded),
        "added": len(added),
        "reactivated": len(reactivated),
        "forced_reload": len(forced),
        "missing_live_reload": len(missing_live),
        "removed_from_export": len(removed),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
