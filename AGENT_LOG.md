# Agent Log

This file records the CORAL-to-BERDL work performed in this session. Runtime
exports remain under `sync-coral-to-berdl/exports/` and are intentionally not
tracked by git.

## Session History

### Initial sync and lifecycle correction

- The user requested a CORAL-to-BERDL sync after a new brick became available.
- The first lifecycle pass showed that inferred `update data` provenance could
  require a new CORAL Process record before BERDL should be changed.
- The user specified the required gate:
  - Never emit empty or header-only `process_*.tsv` files.
  - If any non-empty process import file is emitted, stop before BERDL ingest.
  - Tell the user to load the file into CORAL, then re-export CORAL so lifecycle
    classification uses the updated Process table.
- The user loaded `process_update_data_sync-20260603-112146.tsv` into CORAL.
- The sync skill was updated to use this stop-and-repoll behavior.

### Schema publication requirement

- The user required every table addition or removal to trigger regeneration of
  repository `schema/` references, propagation to dependent skills, and a push
  to GitHub.
- The dependent schema consumers in this repository are:
  - `skills/berdl-mcp/references/enigma_coral_schema.md`
  - `skills/enigma-berdl-query/references/enigma_coral_schema.md`
  - `skills/enigma-berdl-query/references/ddt_ndarray_table.md`
  - `skills/enigma-berdl-query/references/sys_ddt_typedef_table.md`

### Brick relationship questions

- The current strain-to-best-genome mapping was investigated.
- `Brick0000521` was identified as the relevant strain/genome-quality brick.
- Its genome relationship is represented by `link_context_genome`, not a
  normalized foreign-key column directly referencing `sdt_genome`.

### Comment and array-context implementation

- The user requested two sync changes before another live sync:
  1. Repair missing BERDL column comments.
  2. Materialize array-level CORAL context as a constant BERDL column only when
     the context is a foreign key to another BERDL table.
- Example requirement: array context term `ME:0000228` with object reference
  `SSO-U3` becomes a constant `sdt_location_name` column referencing
  `sdt_location.sdt_location_name`.
- Comments, instrumentation, scalar measurements, and other non-foreign-key
  context remain only in `ddt_ndarray_metadata`.

Implemented changes:

- `dry_run_tools.py`
  - Improved Spark schema comment parsing and JSON unescaping.
  - Emits structured schema entries using `column`, matching BERDL ingest.
  - Resolves array context against unambiguous foreign-key mappings aggregated
    from `sys_ddt_typedef`.
  - Adds constant context columns to brick TSVs, matching schema fields and
    `sys_ddt_typedef` rows.
  - Reports expansions, skipped context, conflicts, and mapping ambiguity.
  - Runs context expansion only after the lifecycle process-import gate.
  - Includes data, schema, comments, and combined table hashes in manifests.
- `apply_full_import_comments.py`
  - Fixed the concrete missing-comment bug: fallback column comments had been
    applied only to `ddt_ndarray` and `sys_ddt_typedef`.
  - Fallback comments now apply to every enabled table with structured schema
    comments, including static and brick tables.
- `prepare_mini_import.py`
  - Updated schema consumption from the obsolete `name` key to `column`.
- Updated `SKILL.md`, `references/workflow.md`, and
  `references/comment_contract.md` to describe the behavior.

Validation completed before live export:

- Python compilation and skill validation passed.
- `git diff --check` passed.
- Parsed 1,368 historical brick schemas containing 17,304 columns with no
  parse mismatches or blank comments.
- A rich `array_context` fixture expanded the location FK and skipped an
  instrument entry; a second run was idempotent.
- Historical `Brick0001599` expanded `sdt_location_name=SSO-U3` across 5,239
  rows and skipped four non-FK context entries.
- Historical export analysis found 405 bricks with FK-valued context and 415
  prospective columns. `Brick0000075` contains conflicting values for one
  target column and is intentionally reported/skipped.
- A fake Spark fallback test confirmed comments are now applied to static-table
  columns as well as DDT metadata columns.
- The updated repository skill was copied to the installed Codex skill and the
  two copies were verified with `diff -qr`.

### Current live sync

- The user paused brick pulling while updating CORAL.
- After the user confirmed CORAL was updated and refreshed `KBASE_AUTH_TOKEN`,
  a clean run was created at:
  `sync-coral-to-berdl/exports/sync-20260717-174244`.
- Preflight found 4.3 TB free on `/scratch`.
- The full static export completed for all 18 typedef types. Notable current
  counts include 93,091 Process rows, 223,704 OTU rows, 20,717 Reads rows, and
  6,705 Genome rows.
- CORAL reports 1,434 current bricks, compared with 1,368 files in the prior
  snapshot.
- The saved BERDL browser session was stale. `berdl-remote login` successfully
  refreshed it from the new KBase token, and a new remote kernel was created.
- The upstream brick downloader is single-threaded. After downloading 107
  current files, it was replaced with a temporary bounded four-worker runner
  that uses the same CORAL authentication and per-brick download functions,
  skips completed non-empty files, retries failures, and verifies catalog
  completeness at exit.

## Critical Process Review

### What is working well

- Runtime snapshots are isolated and reproducible rather than modifying the
  previous run in place.
- The lifecycle gate prevents inferred provenance from racing ahead of CORAL.
- Empty process files are suppressed.
- Array context expansion is deliberately limited to normalized foreign keys.
- Schema comments are structured metadata, validated after import, with a
  fallback path for every enabled table.
- Lifecycle-obsolete bricks remain represented in `ddt_ndarray` while their
  physical brick tables can be excluded or reviewed for removal.

### Gaps and improvements

1. **Changed-table detection is not actually enforced end to end.** The current
   manifest records hashes, but generated configs still enable every current
   table and mark rows `dry_run_not_compared`. Add a manifest-diff command that
   compares tables by logical table name, classifies data/schema/comment-only
   changes, and writes the exact enabled-table list consumed by import.
2. **Schema propagation is documented but not automated.** The schema generator
   writes only repository `schema/`; no script currently copies and verifies
   the references used by `berdl-mcp` and `enigma-berdl-query`. Add one publish
   command that generates, copies, checks `diff`, refreshes installed skill
   copies, and fails if any consumer remains stale.
3. **The full downloader is slow and lacks robust completion metadata.** Move
   bounded concurrency, retry/backoff, atomic temporary writes, a catalog ID
   manifest, and final non-empty-file verification into the maintained skill
   instead of relying on a temporary runner.
4. **Execution is too manual.** Export, conversion, lifecycle checking, manifest
   diff, ingest, comment verification, schema publication, and GitHub push are
   separate commands. Add a resumable orchestrator with explicit checkpoints;
   the lifecycle handoff should remain a hard stop.
5. **Credential checks can be misleading.** `berdl-remote status` checks saved
   cookies, not the newly supplied KBase token. Preflight should run token login
   when credentials changed, then status/spawn, without requiring diagnosis of
   a stale cookie failure.
6. **Schema references should come from verified BERDL state.** Generate final
   references after read-back verification of table lists, schemas, comments,
   and row counts, rather than only from the prepared local config.
7. **Lifecycle inference contains hard-coded bridges and dates.** Keep explicit
   CORAL provenance authoritative, move exceptional inference rules into a
   reviewed data file, and test them independently from export mechanics.
8. **End-to-end regression coverage is missing.** Add a small fixture containing
   a new brick, an obsolete brick, FK and non-FK array context, comment-only
   changes, and a non-empty process handoff; assert exact config, reports, and
   stop behavior.

## Current Status

- Full current CORAL export and conversion: complete (`sync-20260717-174244`).
- Lifecycle classification and process-import gate: complete; no process
  handoff TSV was generated.
- BERDL changed-table ingest and read-back verification: complete.
- Repository and dependent-skill schema publication: complete and byte-verified.
- Commit and GitHub push: pending.

### Manifest-diff enforcement added during review

- Added `select_changed_tables.py` to compare current and prior manifests by
  logical table name and classify ingest, comment-only, unchanged, added,
  lifecycle-obsolete, and removed-from-export tables.
- Added `run_full_import.py --table-file` so the generated
  `ingest/changed_tables.txt` is the explicit upload/import selection while the
  config's existing `enabled` flag retains its lifecycle meaning.
- This avoids treating unchanged disabled-for-import tables as obsolete drops,
  and keeps comment-only changes on the metadata application path.

### Incremental brick conversion added during review

- Added `prepare_brick_tables.py` to hash every current raw CORAL brick against
  the prior raw snapshot.
- Converted data, schema, and both sidecars are copied into the new run only
  when raw bytes are identical and all four prior artifacts are complete.
- Every new or changed raw brick is reconverted with the staged typedef and OBO
  files. The report records raw, converter, typedef, and ontology hashes.
- The converter's 2.4-million-term ontology maps are loaded once and reused for
  all new/changed bricks, avoiding the upstream CLI's repeated ontology parse
  for every file.
- Reused artifacts are ordinary copies rather than hard links because the
  array-context expansion intentionally rewrites current-run data and schema.

### Final comment acceptance criterion

- The user requires the completed run to prove that the missing-comment bug is
  fixed: every table must have a non-empty table comment and every column of
  every table must have a non-empty column comment.
- `verify_full_import.py` now reads metadata back for every table in the target
  namespace, reports blank table/column comments, compares configured comments
  with actual values, writes `reports/full_import_verification.json`, and fails
  the run on any missing or mismatched comment.

### One-time hydrology location-link acceptance criterion

- For this run, the user also requires explicit validation that generated
  hydrology brick tables contain normalized location links.
- After ingest, identify the hydrology bricks from current `ddt_ndarray`
  names/descriptions and the array-context expansion report, then verify for
  every corresponding BERDL table:
  - the explicit location column exists;
  - its column comment declares the intended `sdt_location` foreign key;
  - location values are populated; and
  - every distinct location value resolves to the referenced `sdt_location`
    key.
- Save a per-table report under the current run's `reports/` directory. This is
  a one-time acceptance check and is not being made a mandatory step for every
  future sync.

### One-time reload for the FK transformation change

- The user clarified that every brick whose BERDL structure changes because of
  the new array-context foreign-key behavior must be reloaded even when its raw
  CORAL CSV is unchanged.
- Change selection therefore compares post-transformation data and schema
  hashes. Adding a constant FK column changes both hashes and selects the table
  for this ingest.
- The completed current manifest will become the next baseline, so these tables
  will not be selected again unless raw input, metadata, comments, schema, or
  transformation output changes.

### Obsolete brick-table acceptance criterion

- The user reiterated that bricks made obsolete by current CORAL Process
  provenance must have their physical `ddt_brick...` tables deleted from
  BERDL, while their `ddt_ndarray` rows remain with `withdrawn_date` and/or
  `superceded_by_ddt_ndarray_id` populated.
- This behavior is already documented in the skill guardrails and lifecycle
  workflow. `run_full_import.py` drops lifecycle-disabled brick tables, and
  `verify_full_import.py` fails if an obsolete table remains or its retained
  lifecycle row lacks the required annotation.

## Completed sync-20260717-174244

- Exported all 1,434 CORAL bricks and 93,091 Process rows. Converted 66 new
  bricks and reused 1,368 byte-identical prior conversions.
- Classified 684 current and 750 obsolete bricks. No non-empty lifecycle
  process handoff file was generated. Relative to the prior package, 51 brick
  tables became obsolete and 66 new brick tables became current.
- Expanded or confirmed 464 FK-valued array-context columns across 454 bricks;
  291 currently active affected brick tables were selected for the one-time
  structure reload.
- Imported 320 initially selected tables and dropped all 750 lifecycle-disabled
  brick tables. Two transient Spark authentication failures were recovered by
  bounded reconnect and did not leave failed tables.
- Confirmed the prior missing-comment bug: fallback column comments were gated
  to only `ddt_ndarray` and `sys_ddt_typedef`. Removed that gate, changed repair
  to compare before altering, and repaired one remaining live column comment.
- Final read-back verified all 708 table comments and all 8,959 column comments
  are non-empty and exactly match the generated package. No active table is
  missing, no obsolete brick table remains, and every obsolete brick has a
  retained annotated `ddt_ndarray` row.
- One-time hydrology verification passed all 48 Brick1619-Brick1666 tables:
  237,857 rows, zero blank locations, zero orphan links, and exact FK comments
  referencing `sdt_location.sdt_location_name`.
- Found that `sys_process_input` and `sys_process_output` were previously left
  stale when `sys_process` changed. Added deterministic regeneration and
  imported 103,064 current input links plus 103,588 output links. The new
  19-column schema represents every CORAL object type and includes 753 brick
  input links that the old input schema could not encode.
- Fixed rerun idempotency so regenerated `sys_ddt_typedef` always regains the
  derived context rows even when transformed brick columns already exist.
- Fixed standalone comment/verification scripts to configure the BERDL proxy,
  and added bounded verifier reconnects for transient Spark authentication
  resets.
- Regenerated root `schema/` and refreshed repository and installed copies for
  `berdl-mcp` and `enigma-berdl-query`; all dependent files were byte-identical.
