# Workflow

## Planned Runtime Layout

Default work root:

```text
sync-coral-to-berdl/exports/<run_id>/
├── coral_export/
│   ├── static_tsv/
│   └── brick_csv/
├── berdl_upload/
│   ├── data/
│   └── schema/
├── metadata/
│   └── brick_sidecars/
├── reports/
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
   - `.env` defines `CORAL_TYPEDEF` and `CORAL_ONTOLOGIES`
   - BERDL ingest prerequisites are available

3. Export:
   - stage `typedef.json` under `coral_export/schema/` and
     `berdl_upload/source/data/`
   - stage all OBO source files under `coral_export/ontologies/` and
     `berdl_upload/source/ontologies/`
   - parse staged OBO files into `berdl_upload/data/sys_oterm.tsv`
   - parse staged `typedef.json` into `metadata/table_schemas.json`,
     `metadata/table_comments.json`, `berdl_upload/data/sys_typedef.tsv`,
     and normalized `sdt_*`/`sys_*` static table TSVs
   - static/system typedef tables into TSV
   - dynamic bricks into normalized delimited files
   - DDT metadata tables: `ddt_ndarray` and `sys_ddt_typedef`
   - schema and comment metadata into machine-readable JSON
   - always refresh system/static exports because their rows may be added or deleted
   - fetch the current brick catalog, reuse prior raw CSVs for immutable brick
     IDs still in the catalog, and download only newly added brick IDs

4. Classify brick lifecycle:
   - read exported `Process.tsv`, brick metadata, and `ddt_ndarray`
   - mark a brick obsolete when it is an input to an explicit `withdraw data` or `update data` process
   - for explicit `update data`, treat output brick(s) as successors when unambiguous
   - for explicit `withdraw data`, set `withdrawn_date` from process end date, or start date if end date is blank
   - infer missing update relationships only when names show clear version/date progression and CORAL does not already contain the lifecycle relationship
   - infer HTCP growth lifecycle for bricks 215-343 by comparing HTCP rows with later RELOADS/RELOADS_v2 rows
   - write inferred update rows to `metadata/process_update_data_<run_id>.tsv` for CORAL import/review
   - write inferred withdrawal rows to `metadata/process_withdraw_data_<run_id>.tsv` for CORAL import/review
   - write `reports/brick_lifecycle.tsv` with explicit lifecycle rows plus inference candidates
   - write `reports/brick_lifecycle_with_inference.tsv` with one resolved lifecycle row per brick
   - retain obsolete bricks in `ddt_ndarray`, filling `withdrawn_date` and `superceded_by_ddt_ndarray_id` where known
   - exclude obsolete `ddt_brick...` data tables from the generated ingest config
   - compare obsolete brick tables against existing BERDL tables and write `reports/obsolete_berdl_tables_to_drop.sql` for reviewed deletion

5. Normalize:
   - keep raw server TSV/CSV output separate from BERDL-ready upload files
   - treat brick IDs as immutable; reuse hard-linked converted artifacts for prior
     catalog IDs with complete sidecars and convert every newly added brick with
     `prepare_brick_tables.py`
   - rewrite `https://genomics.lbl.gov/enigma-data/` and
     `/auto/sahara/namib/home/gtl/enigma-data-repository/` in all BERDL-ready
     string cells to the MinIO-relative `enigma-data-repository/` prefix;
     reused artifacts must already be normalized, and a normalization algorithm
     change requires a scoped forced rebuild/reload of affected tables
   - standardize table names to target BERDL names
   - resolve each array-context ontology term against unambiguous
     `sys_ddt_typedef` foreign-key mappings
   - append resolved context values as constant brick columns and add matching
     brick schema comments and `sys_ddt_typedef` variable rows
   - reconcile context data, schema, and typedef artifacts independently so a
     repeated run produces the same transformed package
   - regenerate `sys_process_input` and `sys_process_output` from the current
     `sys_process.input_objects` and `output_objects` arrays, including
     `ddt_ndarray_id` for brick links in either direction
   - leave non-foreign-key context, including comments, instrumentation, and
     scalar measurements, only in `ddt_ndarray_metadata`
   - write `reports/array_context_fk_expansion.tsv` and report ambiguous
     mappings without expanding them
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
   - use `scripts/select_changed_tables.py` to write durable ingest,
     comment-only, unchanged, obsolete, added, and removed table lists
   - write `ingest/changed_tables_with_foreign_keys.txt` for reloaded tables
     whose structured column comments declare a foreign key, plus FK-bearing
     source tables whose declared target table is being reloaded
   - pass the prior ingest config so obsolete-to-current transitions are always
     selected for reload even when table bytes are unchanged
   - optionally compare a live table inventory to restore lifecycle-current
     tables missing from BERDL
   - use an explicit force-reload file only when a changed import strategy
     affects existing table structure or metadata

8. Generate BERDL ingest config:
   - structured `schema`, not `schema_sql`
   - only changed data/schema tables enabled
   - no obsolete `ddt_brick...` tables enabled
   - comment-only tables excluded from data ingest and queued for validation/fallback
   - include `source_files` entries for `typedef.json` and OBO files so the
     BERDL upload step stages them to the run Bronze prefix before ingest

9. Run BERDL ingest using the `berdl-ingest` workflow.
   - pass the generated `ingest/changed_tables.txt` through
     `run_full_import.py --table-file`

10. Validate:
   - row counts
   - schema order and types
   - column comments from ingest `comments_report`
   - non-empty table comments and non-empty column comments for every table
     reloaded or metadata-updated in this run, with expected-versus-read-back
     equality
   - trust the prior completed verification for unchanged tables; reserve a
     full namespace audit for a new baseline or import/comment strategy change
   - fallback column comments for the current reload/comment-update set when
     validation finds missing or mismatched comments; compare first and avoid
     rewriting comments already current
   - table comments where supported
   - obsolete brick tables are absent from the BERDL namespace
   - obsolete bricks remain represented in `ddt_ndarray`
   - when `ingest/changed_tables_with_foreign_keys.txt` is non-empty, invoke
     the `check-berdl-foreign-keys` skill and require all declared relationships
     in those selected source tables to pass
   - skip foreign-key validation for unchanged, unrelated source tables;
     reserve a full namespace audit for deliberate investigation

11. Report and archive:
   - save current manifest
   - save sync report
   - record any fallback SQL statements generated or applied
   - record inferred lifecycle process TSVs that need CORAL import or were skipped because CORAL already had explicit provenance

12. Publish verified schema references:
   - run `scripts/publish_schema_references.py --run-dir <work_dir>` after
     BERDL read-back validation
   - regenerate repository `schema/`
   - copy and verify the schema references used by `berdl-mcp` and
     `enigma-berdl-query`
   - pass `--installed-skills-root ~/.codex/skills` to refresh installed copies
   - commit and push the verified workflow and schema changes
