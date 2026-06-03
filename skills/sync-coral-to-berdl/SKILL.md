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
- Only import tables whose data, schema, or comments changed.
- Use BERDL ingest structured `schema` entries for column comments. Generate manual `ALTER TABLE` SQL only when comment validation shows BERDL ingest did not apply a required comment, or for table-level comments not supported by ingest.

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
   - Prefer TSV or Parquet-compatible output when CSV parsing risk is high.

5. **Detect changed tables**
   - Compute a stable hash per table from data bytes, normalized schema, column comments, table comment, and source metadata.
   - Compare against the prior sync manifest from the previous run or Lakehouse/MinIO.
   - Enable only changed data tables in the generated BERDL ingest config.
   - Treat comment-only changes as a comment sync path, avoiding unnecessary data upload.

6. **Run BERDL ingest**
   - Follow the `berdl-ingest` skill for infrastructure, upload, chunking, ingest, and row-count verification.
   - Use the generated config and metadata files from this skill.

7. **Validate comments**
   - Inspect BERDL ingest `comments_report`.
   - Read table schema metadata back from Spark.
   - If expected comments are missing, generate a fallback SQL file with only the missing `ALTER TABLE ... ALTER COLUMN ... COMMENT` statements.
   - Apply table-level comments separately if the target Lakehouse supports them and they are required.

8. **Report**
   - Write a sync report listing updated, skipped, comment-only, failed, and removed-from-export tables.
   - Include row counts, hashes, comment validation status, and any parser workarounds used.

9. **Publish schema updates**
   - Whenever the sync adds or drops Lakehouse tables, regenerate the
     repository `schema/` reference files from the completed sync package.
   - Copy the updated schema references into every dependent skill that vendors
     the ENIGMA CORAL schema, including `berdl-mcp` and
     `enigma-berdl-query`.
   - Commit and push the sync workflow changes plus schema reference updates to
     GitHub after BERDL verification.

## References

- For the exact staged flow, read `references/workflow.md`.
- For manifest fields and hash inputs, read `references/manifest_schema.md`.
- For BERDL ingest comment behavior and fallback policy, read `references/comment_contract.md`.
- For CSV/TSV parser risk handling, read `references/csv_import_pitfalls.md`.
- For current/obsolete brick classification and inferred update provenance, read `references/brick_lifecycle.md`.
