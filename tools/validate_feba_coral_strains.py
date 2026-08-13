#!/usr/bin/env python3
"""Revalidate the selected FEBa strain mappings against live ENIGMA CORAL."""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests


DEFAULT_BASE_URL = "https://hub.berdl.kbase.us/apis/mcp"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organism-manifest", required=True, type=Path)
    parser.add_argument("--phase0-metadata", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--database", default="enigma_coral")
    parser.add_argument(
        "--https-proxy",
        default=None,
        help="HTTPS proxy URL, normally http://127.0.0.1:8123 off-cluster",
    )
    parser.add_argument("--timeout", type=int, default=120)
    return parser.parse_args()


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError(f"TSV has no header: {path}")
        return list(reader.fieldnames), [dict(row) for row in reader]


def write_tsv_atomic(path: Path, columns: list[str], rows: Iterable[dict[str, str]]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def compare_live_rows(
    manifest_rows: list[dict[str, str]], live_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_name: dict[str, list[dict[str, Any]]] = {}
    for row in live_rows:
        by_name.setdefault(str(row.get("sdt_strain_name", "")), []).append(row)

    results = []
    for manifest_row in manifest_rows:
        expected_name = manifest_row["sdt_strain_name"]
        expected_id = manifest_row["sdt_strain_id"]
        matches = by_name.get(expected_name, [])
        if len(matches) == 0:
            status = "missing"
            actual_ids: list[str] = []
        elif len(matches) > 1:
            status = "ambiguous"
            actual_ids = sorted(str(row.get("sdt_strain_id", "")) for row in matches)
        else:
            actual_ids = [str(matches[0].get("sdt_strain_id", ""))]
            status = "verified" if actual_ids[0] == expected_id else "id_mismatch"
        results.append(
            {
                "fitprivate_orgId": manifest_row["fitprivate_orgId"],
                "expected_sdt_strain_id": expected_id,
                "sdt_strain_name": expected_name,
                "actual_sdt_strain_ids": actual_ids,
                "status": status,
            }
        )
    return results


def post_select(
    *,
    args: argparse.Namespace,
    token: str,
    table: str,
    columns: list[str],
    filters: list[dict[str, Any]],
    order_column: str,
) -> list[dict[str, Any]]:
    payload = {
        "database": args.database,
        "table": table,
        "columns": [{"column": column} for column in columns],
        "filters": filters,
        "order_by": [{"column": order_column, "direction": "ASC"}],
        "limit": 1000,
        "offset": 0,
    }
    response = requests.post(
        f"{args.base_url.rstrip('/')}/delta/tables/select",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        proxies={"https": args.https_proxy} if args.https_proxy else None,
        timeout=args.timeout,
    )
    if not response.ok:
        raise RuntimeError(
            f"BERDL {table} select failed with HTTP {response.status_code}: "
            f"{response.text[:2000]}"
        )
    body = response.json()
    rows = body.get("data") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        raise ValueError(f"Unexpected BERDL {table} response: {json.dumps(body)[:500]}")
    return rows


def main() -> int:
    args = parse_args()
    token = os.environ.get("KB_AUTH_TOKEN") or os.environ.get("KBASE_AUTH_TOKEN")
    if not token:
        raise SystemExit("KB_AUTH_TOKEN or KBASE_AUTH_TOKEN is not set")
    columns, manifest_rows = read_tsv(args.organism_manifest)
    required = {
        "fitprivate_orgId",
        "sdt_strain_id",
        "sdt_strain_name",
        "coral_match_live_status",
        "coral_match_live_checked_at",
    }
    missing = required - set(columns)
    if missing:
        raise SystemExit(f"Organism manifest is missing columns: {sorted(missing)}")
    names = [row["sdt_strain_name"] for row in manifest_rows]
    if not names or len(names) != len(set(names)):
        raise SystemExit("Organism manifest must contain nonempty unique strain names")

    filters = [
        {"column": "sdt_strain_name", "operator": "IN", "values": names}
    ]
    live_rows = post_select(
        args=args,
        token=token,
        table="sdt_strain",
        columns=["sdt_strain_id", "sdt_strain_name", "sdt_genome_name"],
        filters=filters,
        order_column="sdt_strain_name",
    )
    live_genomes = post_select(
        args=args,
        token=token,
        table="sdt_genome",
        columns=[
            "sdt_genome_id",
            "sdt_genome_name",
            "sdt_strain_name",
            "n_contigs_count_unit",
            "n_features_count_unit",
            "link",
        ],
        filters=filters,
        order_column="sdt_genome_name",
    )

    checked_at = datetime.now(timezone.utc).isoformat()
    comparisons = compare_live_rows(manifest_rows, live_rows)
    status_by_org = {row["fitprivate_orgId"]: row["status"] for row in comparisons}
    for row in manifest_rows:
        row["coral_match_live_status"] = status_by_org[row["fitprivate_orgId"]]
        row["coral_match_live_checked_at"] = checked_at
    write_tsv_atomic(args.organism_manifest, columns, manifest_rows)

    failures = [row for row in comparisons if row["status"] != "verified"]
    report = {
        "checked_at": checked_at,
        "database": args.database,
        "table": "sdt_strain",
        "requested_names": len(names),
        "returned_rows": len(live_rows),
        "returned_genomes": len(live_genomes),
        "verified": len(comparisons) - len(failures),
        "failures": failures,
        "comparisons": comparisons,
        "live_genomes": live_genomes,
    }
    write_json_atomic(args.report, report)

    metadata = json.loads(args.phase0_metadata.read_text())
    metadata["live_coral_validation"] = "complete" if not failures else "failed"
    metadata["live_coral_validation_checked_at"] = checked_at
    metadata["live_coral_validation_report"] = str(args.report.resolve())
    write_json_atomic(args.phase0_metadata, metadata)
    print(json.dumps({key: report[key] for key in ("verified", "returned_rows")}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
