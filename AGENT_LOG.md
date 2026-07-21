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

## 2026-07-20 repository-link normalization investigation

- Traced Brick1618 from the raw CORAL CSV through `prepare_brick_tables.py`
  and the upstream `convert_bricks.py` converter into the BERDL-ready TSV. The
  absolute `/auto/sahara/namib/home/gtl/enigma-data-repository/` prefix is
  preserved at every stage.
- Confirmed that the existing path rewrite is only called while normalizing
  static/system tables in `coral_metadata.py`. A duplicate rewrite in
  `prepare_mini_import.py` also covers brick data, but only in disposable mini
  validation bundles. The full brick conversion path never invokes either.
- Found 24 generated brick TSVs containing the absolute prefix. Twenty-three
  are obsolete and excluded from ingestion; Brick1618 is the sole active
  affected table and was added by `sync-20260717-174244`. Its obsolete
  predecessor Brick521 contains the same unnormalized links.
- Root cause: the normalization was implemented separately for static-table
  and mini-import workflows, while full dynamic brick conversion writes
  extracted values directly. This is a pipeline coverage bug, not a failure to
  match the Brick1618 prefix.

## 2026-07-20 Brick13 representative-sequence investigation

- Inspected published KBase Narrative `145709/1/13`, titled `Data of ENIGMA
  100 Well Survey in Ning et al 2023`. The narrative stores no KBase data
  objects but links its study files through OwnCloud and a public GitHub
  mirror.
- Located `Publication2/Data/100WSc.Rep_Seq.fasta` in the linked `iCAMP1`
  repository and compared it with Brick13 identifiers.
- The FASTA has 28,644 unique sequences, 240-254 bases long. Every FASTA ID is
  present among Brick13's 49,904 legacy OTU IDs, but 21,260 Brick13 IDs are not
  represented in this FASTA.
- Confirmed that the linked `100WSc.OTUtable.csv` contains 91 samples and
  exactly the same 28,644 OTU IDs as the FASTA. These files are therefore a
  matched, filtered study dataset rather than a complete sequence companion
  for Brick13's 212-sample by 49,904-OTU matrix.

## 2026-07-20 taxonomy-brick namespace investigation

- Compared taxonomy Bricks 11, 12, and 16. They share taxonomy column names
  but represent different Zhou datasets and identifier namespaces:
  100WS legacy OTUs, 27WS sequence-hash ASVs, and Core Pilot local OTUs.
- Their `sdt_asv_name` sets are pairwise disjoint, and there are no shared
  `(sdt_asv_name, taxonomic level, taxon)` assignments. A system selecting a
  taxonomy table from column-name compatibility alone can therefore choose a
  structurally compatible but semantically unrelated dataset.
- Recorded the intended dataset pairings: Brick11 taxonomy with Brick13
  counts; Brick12 taxonomy with Brick14 counts and Brick15 sequences; Brick16
  taxonomy with Brick17 and Brick18 counts.
- Brick12 and Brick16 have `withdrawn_date=2026-07-17` and their physical BERDL
  tables are excluded. Current discovery must filter withdrawn ndarray records
  before selecting a taxonomy brick.

## 2026-07-20 repository-link fix and Brick12/16 un-withdraw preparation

- Centralized legacy repository path rewriting in `repository_paths.py` and
  reused it from static-table normalization, mini-import preparation, and full
  brick preparation.
- Full brick preparation now normalizes TSVs after both fresh conversion and
  prior-artifact reuse, before manifest hashing. This makes unchanged raw
  Brick1618 data acquire a changed BERDL data hash on the next sync.
- Added six regression tests covering both legacy prefixes, atomic TSV
  rewriting, unchanged-byte preservation, chunk-boundary detection, fresh
  conversion, and reuse of prior converted artifacts. All tests pass.
- Validated the transformation on a copy of Brick1618: 2,815 cells were
  rewritten and no legacy repository prefixes remained.
- Traced Brick12 and Brick16 withdrawals to `Process0213633` and
  `Process0213634`, respectively. Both are single-input `Withdraw Data
  <PROCESS:0000052>` records with no outputs. No other update/withdraw process
  refers to either brick.
- Confirmed the lifecycle inference rules classify both ndarray names as
  non-versioned and will not recreate withdrawal candidates after those two
  explicit lifecycle process records are removed from CORAL.
- Refreshed the installed `sync-coral-to-berdl` skill and verified the core
  normalization files are byte-identical to the repository copy.

## 2026-07-20 ENIGMA data-asset bug report review

- Reviewed `ENIGMA_DATA.md` and `DATA_ASSETS.md` against the current
  `sync-20260717-174244` package and generated schema rather than accepting the
  July 14 census as current state.
- Confirmed several reported defects are already fixed: all 708 current tables
  and 8,959 columns passed comment verification; `ddt_brick0001481` has its
  expected FK comments; and normalized `sys_process_input` and
  `sys_process_output` contain 103,064 and 103,588 rows, respectively.
- Confirmed all 282 current bricks with a foreign-key-valued location array
  context have an explicit `sdt_location_name` column; three other current
  bricks carry the same FK as an ordinary variable. No current array-context
  location is missing its materialized column.
- Value-checked taxonomy Bricks 11, 12, and 16 against `sdt_asv`: each resolves
  100% to the parent table. Their ASV sets are mutually disjoint dataset
  namespaces, so the defect is ambiguous companion-table discovery rather than
  invalid ASV foreign keys. CORAL process co-outputs explicitly identify the
  intended sets: 11/13, 12/14/15, 16/17/18, and 1481/1482/1483.
- Identified Brick13's `sdt_sample_name` declaration as a real integrity bug:
  the values include filter labels and therefore do not directly resolve to
  `sdt_sample`, despite being advertised as a foreign key. The source model
  should split base sample object reference from filter context; the sync
  should add FK value validation so this class of error is reported.
- Recommended adding a generated, FK-commented `ddt_ndarray_companion` bridge
  from explicit co-output provenance, plus a foreign-key value-integrity report.
  Cross-tenant weather, GenomeDepot, and FitnessBrowser crosswalks should remain
  separately owned integration tables rather than CORAL-sync heuristics.

## 2026-07-20 Brick13 dimension correction

- Retracted the proposed `ddt_ndarray_companion` bridge after confirming the
  existing normalized process records already make companion bricks
  discoverable. Also recorded that `sdt_sample.timezone` has been corrected at
  the source.
- Traced all 212 first-dimension values in Brick13. Zero are exact
  `sdt_sample_name` values; all 212 are exact `sdt_community_name` values of
  type `Environmental Community`. Those communities link cleanly to 109
  distinct parent samples.
- Verified the complete provenance chain for every dimension value:
  `Sample -> Filter -> Community -> 16S Sequencing -> Reads -> Classify OTUs ->
  Brick13`. All 212 Brick13 input reads resolve to one and only one of the 212
  communities, and every community has a filtering process with a sample input.
- Concluded that Brick13's values are correct but its CORAL first-dimension
  metadata is wrong. Change it from `Environmental Sample <ME:0000100>` /
  `Environmental Sample ID <ME:0000102>` to `Community <ME:0000231>` /
  `Community ID <ME:0000233>`, matching the established Brick14 pattern. The
  next sync should consequently emit `sdt_community_name` and reload Brick13.

## 2026-07-20 Brick13 v2 CORAL import package

- Used `/scratch/jmc/field_automated_measurements` as the reference for JSON
  generation, `CheckGeneric` validation, Update Data TSVs, file manifests, and
  `toolx` upload order.
- Added `tools/build_brick13_v2_coral.py`. It starts from the current raw CORAL
  Brick13 CSV, preserves all dimension and count values, and changes only the
  name, description, and first-dimension metadata before invoking CORAL's
  `ConvertGeneric` Java class.
- Generated `coral_import/brick13_v2_20260720/` with replacement JSON
  `zhou_otu_count_100ws_v2.json`, a one-row Update Data process TSV,
  `files_to_import.txt`, `import_to_coral.py`, a validation transcript, and a
  summary report.
- The JSON name is `zhou_otu_count_100ws_v2.ndarray`; its description follows
  the hydrology convention as `Zhou Lab OTU Counts from 100 Well Survey (v2)`.
  Its SHA-256 is
  `0522cbfb271f30eec11d936063c67e30f0a70358d8f624568cac7bf7c577d8ca`.
- `CheckGeneric` passed for a 212-community by 49,904-OTU array with count-unit
  values. The process replaces `zhou_otu_count_100ws.ndarray` with
  `zhou_otu_count_100ws_v2.ndarray` under the 100 Well Survey campaign.

## 2026-07-20 prioritized ENIGMA data-gap review

- Reconciled the new P0/P1/P2 bug report with the current generated schema and
  the earlier Brick13 investigation. The current tenant has BONCAT cell-count
  bricks and active-fraction communities, but no BONCAT-seq or PMA-seq read
  assets identified by the report.
- Confirmed that the externally located `100WSc.Rep_Seq.fasta` is only a
  28,644-OTU study subset of Brick13's 49,904 OTUs. A complete representative
  set must be recovered from the original QIIME output or exact reference
  release; the partial file must not be presented as a complete companion.
- Recommended modeling field material in `sdt_sample` and derived bulk,
  active, viable, filter, treatment, incubation, and well instances in
  `sdt_community`. Sediment depth zone belongs on `sdt_sample`; BONCAT/PMA and
  size-fraction attributes belong on the derived community.
- Recommended a canonical marker-sequence registry keyed by normalized
  sequence hash plus dataset-local membership and evidence-qualified
  relationships. Exact identity, reverse-complement identity, containment,
  alignment similarity, and shared phylogenetic placement must remain distinct;
  different amplicon sequences cannot be asserted to be the same organism.
- Recommended pinning one SILVA release and SEPP reference package for 16S
  placement, while retaining GTDB for genome/MAG taxonomy. Metagenome MAG
  abundance and read-classifier abundance should remain separate evidence
  products even when exposed through a common taxonomic-abundance interface.
- Classified location columns and the full table/column comment backfill as
  resolved in the 2026-07-17 package. Timezone correction, Brick13 v2, restored
  Brick12/16 tables, and repository-link normalization remain pending the next
  CORAL-to-BERDL sync. NO3 validation, hydrograph logger-role labels, the
  enrichment/geochemistry push, FW021 alias curation, and private RB-TnSeq
  ingestion remain open workstreams.

## 2026-07-20 Brick13 representative-sequence recovery audit

- Confirmed that the public Ning OTU table is a rarefied 91-community subset:
  every sample column sums to exactly 10,800 reads. It contains the same 28,644
  identifiers as the public representative FASTA.
- Of the 21,260 Brick13 identifiers missing from that FASTA, 12,510 have no
  counts in the selected 91 communities and 8,750 have raw counts there but
  disappeared during rarefaction. The missing OTUs account for 216,527 reads
  across full Brick13; 81.4% have at most 10 reads and 91.1% at most 20 reads.
- Found no evidence that contamination explains the missing half. Brick11
  contains only 16 missing identifiers labeled `Cyanobacteria/Chloroplast`.
  Smith et al.'s documented alignment/chimera filtering applies to a separate
  26,943-OTU DBC/USEARCH product and cannot annotate Brick13 removals.
- Verified that KBase workspace 26835 has only the narrative and 222 raw-read
  objects; MG-RAST `mgp8190` and `/h/jmc/www/mg-rast` likewise provide raw or
  per-sample pipeline data, not the cross-sample QIIME representative set.
- Inspected the iCAMP repository history and found only the current 28,644-entry
  publication file. The Smith narrative's Joe Zhou original-data Drive folder
  (`0B62rJp3HQTPMbm5lamtFLTlDY1U`) and the Alm cluster folder both return HTTP
  401 and require restored sharing or authenticated access.
- Downloaded and tested the QIIME Greengenes 13_5 97% reference set. It covers
  all 4,244 missing numeric IDs, but is not a valid representative-sequence
  replacement: only 311 of 6,980 published numeric short representatives are
  exact substrings of their corresponding Greengenes references.
- Added
  `coral_import/brick13_v2_20260720/reports/brick13_representative_sequence_audit.md`
  and a missing-ID handoff TSV for recovery and validation.

## 2026-07-20 Brick13 representative-sequence brick

- Inspected the recovered root-level `rep_seq.fna`. It has 49,904 unique FASTA
  identifiers and exactly covers Brick13's 49,904 OTU IDs, with no missing or
  extra identifiers. All aligned records are 269 columns; ungapped sequences
  are 240-254 bases and contain only A, C, G, T, and N.
- Confirmed that all 28,644 records in the public Ning representative FASTA
  match the recovered file after removing alignment gaps. This resolves the
  prior gap as a publication-subset issue rather than absent source data or a
  documented contamination filter.
- Added `tools/build_brick13_repseq_coral.py`, which validates FASTA/Brick13 ID
  coverage, removes alignment gaps, orders records by Brick13's OTU dimension,
  generates a CORAL Generic JSON, runs `CheckGeneric`, and emits a validation
  summary.
- Generated `coral_import/brick13_repseq_20260720/`. The new brick is
  `zhou_otu_repseq_100ws.ndarray`, described as `Zhou Lab 100 Well Survey OTU
  16S Representative Sequences`, with the same microbial-sequence ontology
  model as Brick15. `CheckGeneric` passed; the JSON SHA-256 is
  `6971dde0fb7d03cfca6a3f11c8b34b5f779d4e54fe6e36566677f52e8c3e8661`.
- Corrected the initial provenance plan after user review: this is not an
  `Import Historic Data` operation. The package contains 212 corrected
  `Classify OTUs <PROCESS:0000031>` rows, each retaining its original reads
  input and recording the count, taxonomy, and representative-sequence bricks
  as three co-outputs, matching the 27 Well Survey pattern.
- Added separate AQL verification and cleanup files. They require all 212 new
  representative-sequence producers before deleting the original two-output
  `Process0013232` through `Process0013443` records and their input/output
  edges; each query is run separately to comply with the ArangoDB editor's
  single top-level query requirement.
- Renamed the prior missing-ID handoff to
  `brick13_previously_missing_recovered_ids.tsv` and updated the audit to state
  that every listed identifier has been recovered.
- Corrected an AQL handoff bug found during CORAL execution: `Brick-0000064`
  is an exported typed-object label, not a live ArangoDB collection. After the
  user supplied the authoritative collection name, updated all five package
  queries and the builder to resolve the new ndarray from `DDT_Brick`. Also
  replaced `LPAD` process-ID construction with the explicit `Process00`
  prefix.

## 2026-07-20 immutable-brick incremental export rule

- User clarified that a CORAL brick ID is immutable: existing brick payloads
  do not change. New brick IDs may be added, and existing bricks may become
  superseded or withdrawn through Process records.
- Static/system type records are not immutable and must be freshly exported on
  every run because rows may be added or deleted.
- Added `download_coral_bricks.py` with current-catalog discovery, immutable
  prior-CSV reuse only for IDs still in the catalog, new-ID downloads, bounded
  request timeouts, retry/backoff, atomic writes, and a completion manifest.
- Updated the sync skill and workflow so Process provenance, not brick payload
  mutation, controls lifecycle classification.

## 2026-07-20 CORAL-to-BERDL sync completion

- Completed run `sync-20260720-172424` from a fresh static/system export and a
  1,436-brick current catalog. Reused 1,434 immutable brick artifacts and
  converted only new Brick1667 and Brick1668. The current Process export has
  93,090 rows.
- The lifecycle gate produced no non-empty `process_*.tsv` handoff file, so the
  BERDL phase proceeded. Lifecycle classification retained all 1,436 records in
  `ddt_ndarray`, with 749 obsolete physical brick tables excluded and dropped.
- Fixed incremental selection to compare the prior ingest config as well as
  table hashes. This correctly selected Brick12 and Brick16 as
  `lifecycle_reactivated`; both physical tables were restored. The final reload
  set was nine tables: Brick12, Brick16, Brick1667, Brick1668, `ddt_ndarray`,
  `sys_ddt_typedef`, `sys_process`, `sys_process_input`, and
  `sys_process_output`.
- Verified 711 lifecycle-current tables exist, all 749 obsolete tables are
  absent, and every obsolete brick has withdrawal or supersession annotation.
  Scoped read-back verification passed for all nine reloaded tables: nine of
  nine table comments and all 94 column comments are non-empty and exactly
  match configured values.
- Verified Brick1668 has 49,904 rows, 49,904 distinct ASVs, and no null IDs or
  sequences; ungapped sequences are 240-254 bases. Brick1667 has 10,579,648
  rows, 212 communities, 49,904 ASVs, and no null community/ASV keys. All 212
  `Classify OTUs` processes link to Brick1668.
- Verified Brick13 is withdrawn on 2026-07-20 and superseded by Brick1667;
  Brick12, Brick16, Brick1667, and Brick1668 are current. Brick13's physical
  table is absent while its `ddt_ndarray` record remains.
- Updated the workflow contract so unchanged tables inherit prior verification.
  A table is reloaded only for data/schema change, obsolete-to-current
  transition, missing live state, or an explicit scoped import-strategy
  migration. Comment verification follows the actual reload/metadata-update
  set; full namespace audits are reserved for baselines or algorithm changes.
- Improved preparation with immutable-ID reuse, atomic hard links, resumable
  artifact detection, prior manifest hash reuse, and a normalization fallback
  for legacy baselines that cannot prove repository-path normalization.
- Added selector regression coverage for lifecycle reactivation, forced
  strategy reloads, missing-live recovery, and unchanged tables. All 10 sync
  tests pass.
- Regenerated the three repository `schema/` references and copied/verified
  eight dependent references across source and installed `berdl-mcp` and
  `enigma-berdl-query` skills.
- Refreshed the installed `sync-coral-to-berdl` skill from the verified
  repository copy and confirmed the installed directory has no differences.

## 2026-07-21 BERDL foreign-key validation skill

- Added the independent `check-berdl-foreign-keys` skill. It reads structured
  JSON column comments with `type: foreign_key`, validates the declared live
  BERDL relationship, and writes bounded JSON/TSV reports. Checks cover missing
  tables/columns, incompatible types, orphaned non-null values, duplicate
  referenced keys, and malformed serialized collections. Native Spark arrays
  and one- or two-level JSON arrays stored in string columns are exploded to
  scalar keys before comparison.
- Integrated a conditional sync handoff. `select_changed_tables.py` now writes
  `ingest/changed_tables_with_foreign_keys.txt` for reloaded FK-bearing source
  tables and for unchanged FK-bearing sources whose target table was reloaded.
  An empty file skips the live check; unchanged unrelated tables are not
  audited during routine syncs.
- Reworked the first live implementation after per-relationship Spark actions
  proved too slow. The final validator batches source coverage, target
  uniqueness, duplicate samples, and serialized-collection parsing. Added 14
  validator/selector tests; the repository suite now passes 24 tests.
- Ran the new gate against the nine tables reloaded in
  `sync-20260720-172424`: 60 declared relationships across nine source tables
  and 27 total live tables. Forty-six passed and 14 failed; all three serialized
  collection relationships parsed successfully and had no orphan values.
- The stable failure set identifies four source problems:
  `sys_oterm.sys_oterm_id` has 244 duplicate values/335 extra rows because the
  same imported ontology IDs are emitted from multiple source OBOs; Bricks 12
  and 16 use five taxonomic-rank terms present in the staged measurement OBO but
  absent from `sys_oterm`; 259 process rows use four protocol names absent from
  `sdt_protocol`; and one process output references absent `Strain0002998`.
  Reports are in the run's `reports/foreign_key_validation.{json,tsv}`.
- Confirmed the missing taxonomic-rank terms expose an existing exporter bug:
  `collect_referenced_terms()` excludes brick TSVs, so terms used only as brick
  data values are omitted. The duplicate ontology keys expose a separate
  `write_sys_oterm()` issue: it emits every included ID once per ontology file
  rather than selecting one authoritative row per CURIE. These data-generation
  fixes are intentionally left as follow-up work because the new gate correctly
  stops on the current live integrity failures.
- Installed `check-berdl-foreign-keys` and refreshed the installed
  `sync-coral-to-berdl` skill under `~/.codex/skills`; recursive diffs against
  the repository source are empty.
