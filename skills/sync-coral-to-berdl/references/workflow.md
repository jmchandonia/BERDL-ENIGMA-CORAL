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

4. Classify brick lifecycle:
   - read exported `Process.tsv`, brick metadata, and `ddt_ndarray`
   - mark a brick obsolete when it is an input to an explicit `withdraw data` or `update data` process
   - for explicit `update data`, treat output brick(s) as successors when unambiguous
   - for explicit `withdraw data`, set `withdrawn_date` from process end date, or start date if end date is blank
   - infer missing update relationships only when names show clear version/date progression and CORAL does not already contain the lifecycle relationship
   - write inferred update rows to `export/metadata/process_update_data_<run_id>.tsv` for CORAL import/review
   - write `export/reports/brick_lifecycle.tsv` with current, obsolete, explicit, inferred, and review-needed classifications
   - retain obsolete bricks in `ddt_ndarray`, filling `withdrawn_date` and `superceded_by_ddt_ndarray_id` where known
   - exclude obsolete `ddt_brick...` data tables from the generated ingest config
   - compare obsolete brick tables against existing BERDL tables and write `export/reports/obsolete_berdl_tables_to_drop.sql` for reviewed deletion

5. Normalize:
   - standardize table names to target BERDL names
   - validate headers against schema
   - validate row widths with Python `csv`
   - rewrite risky CSV as TSV or Parquet when needed

6. Build manifest:
   - one record per target table
   - content hash and schema/comment hash
   - row count and byte count
   - source file paths and timestamps
   - lifecycle status for brick and DDT metadata tables
   - parser warnings and transformations

7. Diff manifest:
   - `data_changed`
   - `schema_changed`
   - `comments_changed`
   - `unchanged`
   - `missing_from_current_export`
   - `obsolete_excluded`

8. Generate BERDL ingest config:
   - structured `schema`, not `schema_sql`
   - only changed data/schema tables enabled
   - no obsolete `ddt_brick...` tables enabled
   - comment-only tables excluded from data ingest and queued for validation/fallback

9. Run BERDL ingest using the `berdl-ingest` workflow.

10. Validate:
   - row counts
   - schema order and types
   - column comments from ingest `comments_report`
   - table comments where supported
   - obsolete brick tables are absent from the BERDL namespace
   - obsolete bricks remain represented in `ddt_ndarray`

11. Report and archive:
   - save current manifest
   - save sync report
   - record any fallback SQL statements generated or applied
   - record inferred lifecycle process TSVs that need CORAL import or were skipped because CORAL already had explicit provenance
