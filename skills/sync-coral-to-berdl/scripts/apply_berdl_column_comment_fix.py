#!/usr/bin/env python3
"""Apply corrected BERDL column wording to imported CORAL metadata tables."""

from __future__ import annotations

import json
import os
import sys

from run_full_import import _patch_spark_connect_config_defaults, _sql_string


def main() -> int:
    sys.path.insert(0, "/h/jmc/src/BERIL-research-observatory/scripts")
    import ingest_lib  # noqa: F401
    from spark_connect_remote import create_spark_session

    spark = create_spark_session(
        host_template="metrics.berdl.kbase.us",
        port=443,
        use_ssl=True,
        kbase_token=os.environ["KBASE_AUTH_TOKEN"],
        app_name="sync-coral-berdl-column-comment-fix",
    )
    _patch_spark_connect_config_defaults(spark)
    updates = [
        ("enigma_coral.sys_ddt_typedef", "berdl_column_name", {"description": "BERDL column name"}),
        (
            "enigma_coral.sys_ddt_typedef",
            "berdl_column_data_type",
            {"description": "BERDL column data type, variable or dimension_variable"},
        ),
        (
            "enigma_coral.sys_typedef",
            "cdm_column_name",
            {"description": "BERDL column name derived from the CORAL field"},
        ),
    ]
    for table, column, comment in updates:
        spark.sql(
            f"ALTER TABLE {table} ALTER COLUMN `{column}` "
            f"COMMENT '{_sql_string(json.dumps(comment))}'"
        )
    print(json.dumps({"updated": len(updates)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
