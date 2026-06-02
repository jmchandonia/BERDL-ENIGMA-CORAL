#!/usr/bin/env python3
"""Verify sys_ddt_typedef excludes withdrawn/superceded bricks in BERDL."""

from __future__ import annotations

import json
import os
import sys

from run_full_import import _patch_spark_connect_config_defaults


def main() -> int:
    sys.path.insert(0, "/h/jmc/src/BERIL-research-observatory/scripts")
    import ingest_lib  # noqa: F401
    from spark_connect_remote import create_spark_session

    spark = create_spark_session(
        host_template="metrics.berdl.kbase.us",
        port=443,
        use_ssl=True,
        kbase_token=os.environ["KBASE_AUTH_TOKEN"],
        app_name="sync-coral-sys-ddt-typedef-filter-verify",
    )
    _patch_spark_connect_config_defaults(spark)
    total = spark.sql("SELECT COUNT(*) AS c FROM enigma_coral.sys_ddt_typedef").collect()[0].c
    obsolete = spark.sql(
        """
        SELECT COUNT(*) AS c
        FROM enigma_coral.sys_ddt_typedef t
        JOIN enigma_coral.ddt_ndarray n
          ON t.ddt_ndarray_id = n.ddt_ndarray_id
        WHERE coalesce(n.withdrawn_date, '') <> ''
           OR coalesce(n.superceded_by_ddt_ndarray_id, '') <> ''
        """
    ).collect()[0].c
    comments = spark.sql("DESCRIBE TABLE EXTENDED enigma_coral.sys_ddt_typedef").collect()
    comment_map = {
        row.col_name: row.comment
        for row in comments
        if row.col_name in {"berdl_column_name", "berdl_column_data_type"}
    }
    result = {
        "total_rows": total,
        "rows_for_withdrawn_or_superceded_bricks": obsolete,
        "comments": comment_map,
    }
    print(json.dumps(result, indent=2))
    return 0 if total == 8270 and obsolete == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
