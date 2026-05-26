# Workflow

## Planned Runtime Layout

Default work root:

```text
sync-coral-to-berdl/exports/<tenant>_<dataset>/<run_id>/
├── export/
│   ├── data/
│   ├── schema/
│   ├── metadata/
│   └── reports/
├── ingest/
│   ├── config.json
│   └── enabled_tables.txt
├── manifests/
│   ├── current.json
│   └── previous.json
└── logs/
```

The work root is intentionally outside `skills/` and is ignored by git.
Allow `--work-dir` to override it, especially when the user wants a large
scratch disk.

## Step Sequence

1. Confirm destination:
   - tenant
   - dataset
   - namespace
   - work directory
   - mode, normally `overwrite` for changed CORAL snapshot tables

2. Check local environment:
   - work directory exists or can be created
   - enough free space for exported TSV/CSV/Parquet plus manifests
   - CORAL source paths exist
   - BERDL ingest prerequisites are available

3. Export:
   - static/system typedef tables into TSV
   - dynamic bricks into normalized delimited files
   - DDT metadata tables: `ddt_ndarray` and `sys_ddt_typedef`
   - schema and comment metadata into machine-readable JSON

4. Normalize:
   - standardize table names to target BERDL names
   - validate headers against schema
   - validate row widths with Python `csv`
   - rewrite risky CSV as TSV or Parquet when needed

5. Build manifest:
   - one record per target table
   - content hash and schema/comment hash
   - row count and byte count
   - source file paths and timestamps
   - parser warnings and transformations

6. Diff manifest:
   - `data_changed`
   - `schema_changed`
   - `comments_changed`
   - `unchanged`
   - `missing_from_current_export`

7. Generate BERDL ingest config:
   - structured `schema`, not `schema_sql`
   - only changed data/schema tables enabled
   - comment-only tables excluded from data ingest and queued for validation/fallback

8. Run BERDL ingest using the `berdl-ingest` workflow.

9. Validate:
   - row counts
   - schema order and types
   - column comments from ingest `comments_report`
   - table comments where supported

10. Report and archive:
   - save current manifest
   - save sync report
   - record any fallback SQL statements generated or applied
