---
name: sync-coral-to-berdl
description: Export CORAL data into a BERDL-ready local package and sync changed tables into the KBase BERDL Lakehouse using the BERDL ingest workflow. Use when updating enigma_coral or another CORAL-backed BERDL namespace from CORAL typedef/static tables or dynamic data bricks, especially when only changed tables should be imported and table/column comments must be preserved.
---

# Sync CORAL To BERDL

Use this skill to prepare and run a CORAL-to-BERDL sync. It reuses the CORAL
export framework from `/h/jmc/src/CORAL/convert/spark-minio/`, but routes
upload and table creation through BERDL ingest instead of the legacy manual
MinIO copy plus notebook paste workflow.

## Guardrails

- Do not run the actual CORAL export until the user confirms the working disk.
- Default runtime work directory: `sync-coral-to-berdl/exports/<run_id>/`.
- Keep generated TSV/CSV/manifest output out of git.
- Never drop Lakehouse tables just because they disappeared from the current CORAL export; report removals for review.
- Obsolete brick tables are the exception: after explicit CORAL lifecycle
  provenance or reviewed lifecycle inference identifies a brick as withdrawn or
  superseded, exclude its `ddt_brick...` data table from ingest and generate a
  reviewed Lakehouse drop plan if the table already exists.
- Reload a table only when its data/schema changed, it transitioned from
  lifecycle-obsolete to current, it is missing from the live namespace, or an
  explicit import-strategy migration affects it. Apply comment-only changes as
  metadata updates without rewriting table data.
- Use BERDL ingest structured `schema` entries for column comments. Generate manual `ALTER TABLE` SQL only when comment validation shows BERDL ingest did not apply a required comment, or for table-level comments not supported by ingest.
- Expand array-level context into brick columns only when the context term has
  an unambiguous foreign-key mapping in `sys_ddt_typedef`. Keep comments,
  instrumentation, measurements, and other non-foreign-key context only in
  `ddt_ndarray_metadata`.
- Normalize legacy ENIGMA repository URLs and filesystem paths to
  `enigma-data-repository/...` in every BERDL-ready static, system, and dynamic
  brick TSV. Reused immutable artifacts must already contain this normalization;
  when the normalization or another import algorithm changes, force a scoped
  rebuild and reload of every affected brick table.

## Workflow

1. **Preflight**
   - Confirm the target tenant/dataset/namespace and the work directory.
   - Check available disk space before export.
   - Confirm `.env` has `CORAL_TYPEDEF` and `CORAL_ONTOLOGIES`; these are
     the canonical sources for static table schemas/comments and `sys_oterm`.
   - Confirm `KBASE_AUTH_TOKEN`, BERDL ingest prerequisites, and MinIO configuration using the `berdl-ingest` skill workflow.

2. **Export CORAL locally**
   - Use the CORAL scripts as source material:
     - `download_typedef_tsvs.py` for system/static typedef TSV export.
     - `to_spark.py` for schema/comment derivation patterns.
     - `convert_bricks.py` for brick conversion and DDT metadata.
     - `convert_to_berdl_loader.py` for existing BERDL config/comment mapping ideas.
   - Write raw CORAL exports under `<work_dir>/coral_export/`, not inside the skill directory.
   - Always re-export system/static types because records may be added, changed,
     or deleted between runs.
   - Treat an existing brick ID as immutable. Fetch the current brick catalog,
     reuse prior raw CSVs only for IDs still in that catalog, and download full
     brick data only for newly added IDs. Detect brick replacement or withdrawal
     from current Process provenance rather than by expecting an existing brick
     payload to change.

3. **Classify brick lifecycle**
   - After all bricks are downloaded, classify current and obsolete bricks from
     explicit CORAL `withdraw data` and `update data` process provenance.
   - Infer missing `update data` relationships only for brick families with
     clear version/date naming progressions and no existing explicit lifecycle
     provenance.
   - Treat single-letter date suffixes such as `240314b` as corrected versions
     of that date, and recognize embedded version tokens such as
     `_v2_ASV_count`.
   - For HTCP growth bricks 215-343, infer updates to later RELOADS data when
     row overlap supports replacement; infer withdrawals for the remaining
     accepted obsolete HTCP bricks.
   - Write candidate inferred updates to `process_update_data_<run_id>.tsv`
     for CORAL import/review only when at least one row is present.
   - Write candidate inferred withdrawals to
     `process_withdraw_data_<run_id>.tsv` for CORAL import/review only when at
     least one row is present.
   - If any non-empty `process_*_<run_id>.tsv` file is generated, stop the sync
     before BERDL ingest. Tell the user to import the generated process file(s)
     into CORAL, then rerun the CORAL export so the updated `Process` table is
     used for lifecycle classification.
   - Keep obsolete bricks in `ddt_ndarray` with `withdrawn_date` and
     `superceded_by_ddt_ndarray_id` where known, but do not expose obsolete
     bricks as BERDL `ddt_brick...` tables.

4. **Build the ingest package**
   - Keep raw server output under `coral_export/static_tsv/` and `coral_export/brick_csv/`.
   - Put BERDL-ready table files under `berdl_upload/data/`, brick schemas under `berdl_upload/schema/`, and intermediate sidecars under `metadata/brick_sidecars/`.
   - Put source metadata files to upload under `berdl_upload/source/`:
     `source/data/typedef.json`, `source/ontologies/*.obo`, and
     `source/upload_manifest.json`.
   - Put reports directly under `reports/` and generated metadata directly under `metadata/`.
   - Produce BERDL ingest config with structured per-column schema maps, not `schema_sql`, so ingest applies column comments.
   - Materialize foreign-key-valued array context as a constant column in the
     brick TSV, with the same foreign-key comment and a corresponding
     `sys_ddt_typedef` variable row. Reconcile those three artifacts
     independently so reruns restore derived typedef rows even when the brick
     column already exists. Report and skip ambiguous mappings.
   - Regenerate `sys_process_input` and `sys_process_output` from the current
     normalized `sys_process` arrays on every run. Emit one process-object link
     per row, use explicit FK columns for every CORAL static object type, and
     map every `Brick-*` reference to `ddt_ndarray_id` in both directions.
   - Use `scripts/download_coral_bricks.py` with the prior complete run to fetch
     the current catalog, copy immutable prior brick CSVs for IDs still present,
     and download only newly added brick IDs.
   - Use `scripts/prepare_brick_tables.py` when a prior complete run is
     available. It hard-links converted artifacts for reused immutable brick
     inputs with complete sidecars and converts every new brick. Atomic
     derived-column rewrites break the current-run link without mutating the
     prior baseline.
   - Prefer TSV or Parquet-compatible output when CSV parsing risk is high.

5. **Detect changed tables**
   - Compute a stable hash per table from data bytes, normalized schema, column comments, table comment, and source metadata.
   - Compare against the prior sync manifest from the previous run or Lakehouse/MinIO.
   - Run `scripts/select_changed_tables.py` with both the prior manifest and
     prior ingest config to compare logical table names and lifecycle enabled
     state, classify data/schema/comment-only changes, and write
     `ingest/changed_tables.txt`.
   - Supply `--force-reload-file` only for tables affected by an import-strategy
     change. Optionally supply a live table inventory with `--live-tables-file`
     so lifecycle-current tables missing from BERDL are restored.
   - Preserve `enabled` as the lifecycle-current flag, and select only changed
     data/schema tables for upload and import through
     `ingest/changed_tables.txt`.
   - Write `ingest/changed_tables_with_foreign_keys.txt` as the intersection of
     the reload set and tables with JSON column comments declaring
     `type: foreign_key`, plus unchanged source tables whose declared target
     table is being reloaded.
   - Treat comment-only changes as a comment sync path, avoiding unnecessary data upload.

6. **Run BERDL ingest**
   - Follow the `berdl-ingest` skill for infrastructure, upload, chunking, ingest, and row-count verification.
   - Use the generated config and metadata files from this skill.
   - Pass `--table-file ingest/changed_tables.txt` to `run_full_import.py` so
     only data/schema-changed tables are uploaded and rewritten. Lifecycle-
     disabled brick tables remain the reviewed obsolete-drop set.

7. **Validate comments**
   - Inspect BERDL ingest `comments_report`.
   - Read table schema metadata back from Spark for every table reloaded or
     metadata-updated in this run. Require a non-empty table comment and a
     non-empty comment for every column, compare configured values with
     read-back values, and fail on missing or mismatched metadata.
   - Trust the prior completed verification for unchanged tables. Run a full
     namespace comment audit only when establishing a baseline or changing the
     comment/import algorithm.
   - If expected comments are missing or mismatched, apply only the required
     `ALTER TABLE ... ALTER COLUMN ... COMMENT` statements after comparing
     current metadata. Apply this repair to every enabled table that has
     structured schema comments in the current reload/comment-update set.
   - Apply table-level comments separately if the target Lakehouse supports them and they are required.

8. **Validate foreign keys when triggered**
   - If `ingest/changed_tables_with_foreign_keys.txt` is non-empty, invoke the
     `check-berdl-foreign-keys` skill after all selected tables are loaded.
   - Fail the sync verification on orphaned non-null values, duplicate target
     keys, missing target tables/columns, malformed declarations, or
     incompatible source/target types.
   - Do not recheck unchanged, unrelated tables and do not run a full namespace
     foreign-key audit during routine syncs.

9. **Report**
   - Write a sync report listing updated, skipped, comment-only, failed, and removed-from-export tables.
   - Include row counts, hashes, comment validation status, and any parser workarounds used.

10. **Publish schema updates**
   - Whenever the sync adds or drops Lakehouse tables, regenerate the
     repository `schema/` reference files from the completed sync package.
   - Copy the updated schema references into every dependent skill that vendors
     the ENIGMA CORAL schema, including `berdl-mcp` and
     `enigma-berdl-query`.
   - Run `scripts/publish_schema_references.py` after BERDL read-back
     verification. It regenerates repository schema markdown, refreshes both
     dependent skills, and fails if copied files differ. Pass
     `--installed-skills-root ~/.codex/skills` to refresh installed copies in
     the same checked operation.
   - Commit and push the sync workflow changes plus schema reference updates to
     GitHub after BERDL verification.

## References

- For the exact staged flow, read `references/workflow.md`.
- For manifest fields and hash inputs, read `references/manifest_schema.md`.
- For BERDL ingest comment behavior and fallback policy, read `references/comment_contract.md`.
- For CSV/TSV parser risk handling, read `references/csv_import_pitfalls.md`.
- For current/obsolete brick classification and inferred update provenance, read `references/brick_lifecycle.md`.
