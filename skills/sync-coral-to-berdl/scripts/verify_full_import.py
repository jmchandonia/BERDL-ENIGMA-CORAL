#!/usr/bin/env python3
"""Verify a completed CORAL full import in BERDL."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _make_spark(app_name: str):
    from run_full_import import _patch_spark_connect_config_defaults
    from spark_connect_remote.session import create_spark_session

    spark = create_spark_session(
        host_template="metrics.berdl.kbase.us",
        port=443,
        use_ssl=True,
        kbase_token=os.environ["KBASE_AUTH_TOKEN"],
        app_name=app_name,
    )
    _patch_spark_connect_config_defaults(spark)
    return spark


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--namespace", default="enigma_coral")
    args = parser.parse_args()

    config = _load_json(args.run_dir / "ingest" / "config.dry_run.json")
    enabled = {table["name"] for table in config["tables"] if table.get("enabled")}
    disabled = {table["name"] for table in config["tables"] if not table.get("enabled")}

    spark = _make_spark("sync-coral-full-import-verify")
    imported = {
        row.tableName
        for row in spark.sql(f"SHOW TABLES IN {args.namespace}").collect()
        if not row.isTemporary
    }

    missing_enabled = sorted(enabled - imported)
    present_disabled = sorted(disabled & imported)

    ndarray_rows = spark.sql(
        f"""
        SELECT ddt_ndarray_id, withdrawn_date, superceded_by_ddt_ndarray_id
        FROM {args.namespace}.ddt_ndarray
        """
    ).collect()
    ndarray = {row.ddt_ndarray_id: row.asDict() for row in ndarray_rows}

    disabled_brick_ids = {
        "Brick" + table.removeprefix("ddt_brick").zfill(7)
        for table in disabled
        if table.startswith("ddt_brick")
    }
    missing_lifecycle = sorted(
        brick_id
        for brick_id in disabled_brick_ids
        if brick_id not in ndarray
        or (
            not (ndarray[brick_id].get("withdrawn_date") or "").strip()
            and not (ndarray[brick_id].get("superceded_by_ddt_ndarray_id") or "").strip()
        )
    )

    go_terms = spark.sql(
        f"""
        SELECT COUNT(*) AS c
        FROM {args.namespace}.sys_oterm
        WHERE upper(sys_oterm_id) LIKE 'GO:%'
           OR lower(sys_oterm_ontology) LIKE '%gene ontology%'
           OR lower(sys_oterm_ontology) = 'go'
        """
    ).collect()[0].c
    ncbitaxon_terms = spark.sql(
        f"""
        SELECT COUNT(*) AS c
        FROM {args.namespace}.sys_oterm
        WHERE upper(sys_oterm_id) LIKE 'NCBITAXON:%'
           OR lower(sys_oterm_ontology) LIKE '%ncbitaxon%'
           OR lower(sys_oterm_ontology) LIKE '%ncbi taxon%'
        """
    ).collect()[0].c

    sample_ids = ["Brick0000001", "Brick0000215", "Brick0000453", "Brick0000456"]
    samples = {brick_id: ndarray.get(brick_id) for brick_id in sample_ids}

    result = {
        "enabled_tables_expected": len(enabled),
        "enabled_tables_missing": missing_enabled,
        "disabled_tables_expected_absent": len(disabled),
        "disabled_tables_present": present_disabled,
        "disabled_bricks_missing_lifecycle": missing_lifecycle,
        "sample_lifecycle": samples,
        "go_terms": go_terms,
        "ncbitaxon_terms": ncbitaxon_terms,
    }
    print(json.dumps(result, indent=2, default=str))
    return 1 if missing_enabled or present_disabled or missing_lifecycle or go_terms else 0


if __name__ == "__main__":
    raise SystemExit(main())
