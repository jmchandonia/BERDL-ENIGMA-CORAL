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
- Default runtime work directory: `sync-coral-to-berdl/exports/<tenant>_<dataset>/<run_id>/`.
- Keep generated TSV/CSV/manifest output out of git.
- Never drop Lakehouse tables just because they disappeared from the current CORAL export; report removals for review.
- Only import tables whose data, schema, or comments changed.
- Use BERDL ingest structured `schema` entries for column comments. Generate manual `ALTER TABLE` SQL only when comment validation shows BERDL ingest did not apply a required comment, or for table-level comments not supported by ingest.

## Workflow

1. **Preflight**
   - Confirm the target tenant/dataset/namespace and the work directory.
   - Check available disk space before export.
   - Confirm `KBASE_AUTH_TOKEN`, BERDL ingest prerequisites, and MinIO configuration using the `berdl-ingest` skill workflow.

2. **Export CORAL locally**
   - Use the CORAL scripts as source material:
     - `download_typedef_tsvs.py` for system/static typedef TSV export.
     - `to_spark.py` for schema/comment derivation patterns.
     - `convert_bricks.py` for brick conversion and DDT metadata.
     - `convert_to_berdl_loader.py` for existing BERDL config/comment mapping ideas.
   - Write exports under `<work_dir>/export/`, not inside the skill directory.

3. **Build the ingest package**
   - Normalize files into `export/data/`, `export/schema/`, `export/metadata/`, and `export/reports/`.
   - Produce BERDL ingest config with structured per-column schema maps, not `schema_sql`, so ingest applies column comments.
   - Prefer TSV or Parquet-compatible output when CSV parsing risk is high.

4. **Detect changed tables**
   - Compute a stable hash per table from data bytes, normalized schema, column comments, table comment, and source metadata.
   - Compare against the prior sync manifest from the previous run or Lakehouse/MinIO.
   - Enable only changed data tables in the generated BERDL ingest config.
   - Treat comment-only changes as a comment sync path, avoiding unnecessary data upload.

5. **Run BERDL ingest**
   - Follow the `berdl-ingest` skill for infrastructure, upload, chunking, ingest, and row-count verification.
   - Use the generated config and metadata files from this skill.

6. **Validate comments**
   - Inspect BERDL ingest `comments_report`.
   - Read table schema metadata back from Spark.
   - If expected comments are missing, generate a fallback SQL file with only the missing `ALTER TABLE ... ALTER COLUMN ... COMMENT` statements.
   - Apply table-level comments separately if the target Lakehouse supports them and they are required.

7. **Report**
   - Write a sync report listing updated, skipped, comment-only, failed, and removed-from-export tables.
   - Include row counts, hashes, comment validation status, and any parser workarounds used.

## References

- For the exact staged flow, read `references/workflow.md`.
- For manifest fields and hash inputs, read `references/manifest_schema.md`.
- For BERDL ingest comment behavior and fallback policy, read `references/comment_contract.md`.
- For CSV/TSV parser risk handling, read `references/csv_import_pitfalls.md`.
