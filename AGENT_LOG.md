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

## 2026-07-21 Process protocol correction recovery

- The first protocol-correction handoff incorrectly treated the exported
  `protocol_id` TSV header as the only live Arango field. A later cleanup also
  removed that property broadly. A subsequent prefix-based repair was unsafe:
  its prefixes matched valid protocol families beyond the 259 intended rows,
  and pasted replacement values acquired embedded newlines.
- Stopped the BERDL reload after the fresh Process export exposed the damage.
  The pre-damage authority is
  `sync-coral-to-berdl/exports/sync-20260720-172424/coral_export/static_tsv/Process.tsv`:
  93,090 records with well-formed nine-column physical TSV rows.
- Added
  `coral_import/process_protocol_restore_20260721/restore_process_protocols.js`.
  The guarded arangosh script restores `Process.protocol` by exact process ID,
  applies only the four reviewed typo mappings, validates all 51 desired names
  against `SDT_Protocol`, requires the live count to be 93,089, permits only
  missing `Process0068062`, writes a before-state backup, updates differences
  in batches, and verifies zero remaining differences.
- Syntax-checked the script with `node --check`. The restore has not yet been
  executed; the CORAL-to-BERDL run remains paused until the user completes the
  dry run and apply run and a new Process export passes comparison.
- Rebuilt the recovery artifact as a fully self-contained 4,265,260-byte
  arangosh script so it can be copied to another server without the TSV
  snapshot. It embeds all 93,090 exact-ID desired protocol states, including
  nulls, and therefore can detect or remove unexpected protocol assignments as
  well as restore non-null values. SHA-256:
  `f07083a97728fff9c2db18604f1872630a533692a9167503472055efbfb38b7c`.
- Added `tools/build_process_protocol_restore_script.py` and its JavaScript
  template so the standalone artifact can be regenerated deterministically
  from the pre-damage Process and Protocol exports. The generated correction
  counts are 90, 51, 117, and 1 for the four reviewed typo mappings.

## 2026-07-22 Process reload, ontology repair, and relationship audit

- The user ran the exact-ID recovery successfully: 12,004 protocol differences
  were updated and post-write verification found zero remaining differences.
  A fresh CORAL export contained 93,089 Process records and exactly matched the
  pre-damage snapshot plus the four reviewed typo corrections, excluding only
  the intentionally deleted `Process0068062`.
- Fixed the OBO loader to scan only brick `*_sys_oterm_id` values, select one
  canonical ontology row per CURIE, and preserve historic CORAL unit labels for
  stable generated column names. The first corrected `sys_oterm` had 4,329
  unique IDs and restored the five rank terms needed by Bricks 12 and 16.
- Reloaded `sys_oterm`, `sys_process`, `sys_process_input`, and
  `sys_process_output` from run `sync-20260721-170409`. All four imports
  completed. Live read-back found all 711 current tables, none of the 749
  obsolete tables, all four table comments, and all 58 column comments, with no
  missing or mismatched metadata.
- The live foreign-key audit exposed a Spark transport limit: one SQL statement
  containing 1,451 relationships repeatedly ended with `RST_STREAM`, and the
  remote Spark endpoint became unhealthy. Added bounded relationship batches
  and a documented `--local-package` fallback that streams the exact imported
  package once by table. The repository suite now passes 36 tests.
- The corrected staged-package audit checked 1,451 relationships across 359
  source tables. It found nine failures. Eight are CORAL source-data defects:
  Brick364 uses isolate-like values as image links; Bricks454/458/461/478 and
  Brick1600 contain taxon values absent from `sdt_taxon`; Brick510 contains an
  unregistered serialized condition; and one `sdt_community` condition field
  contains an embargo/curation note. The updated process tables have no invalid
  foreign keys.
- The ninth failure, Brick68's `CHEBI:48505`, exposed a remaining importer bug:
  the OBO parser ignored `alt_id`. Added alternate-ID expansion so secondary
  IDs inherit canonical metadata. `CHEBI:48505` is now emitted as ribitol with
  canonical ID `CHEBI:15963`; no unresolved ontology stubs remain.
- Reloaded only `sys_oterm` after the alternate-ID fix. It now has 4,339 unique
  rows. Live read-back verified its table comment and all eight column comments,
  and a scoped staged-package recheck passed all three Brick68 relationships.

## 2026-07-23 Foreign-key correction draft

- Expanded the five taxon relationship failures into their complete distinct
  value set. The 2,704 per-table orphan counts collapse to 1,831 unique taxon
  names because many labels occur in multiple taxonomy bricks.
- Created `coral_import/taxon_fk_update_20260723/Taxon_additions.tsv` with
  1,823 unambiguous additions using the CORAL static-type import shape:
  `name` and `ncbi_taxid`, with no caller-assigned Taxon IDs. CORAL assigns
  static-type IDs during import.
- Streamed the staged 408 MB `ncbitaxon.obo` snapshot and keyword-matched
  normalized taxon names against primary names and synonyms. Assigned 985
  unambiguous primary-name and 45 unambiguous synonym mappings; left four
  ambiguous synonyms and 789 unmatched names as `null`.
- Held out eight values that should be corrected in superseding bricks instead:
  four spreadsheet-converted date strings and four capitalization-only
  duplicates of existing Taxon names. Added a provenance TSV covering every
  proposed addition and a review TSV documenting each held-out correction.
- Expanded the three non-taxon failures into review artifacts. Brick364's 94
  Image records are not missing: all are linked by `Process0031771` through
  `Process0031864`, and each brick value differs from the valid Image name only
  by a missing `.tif` extension. Brick510 has one condition that differs from
  `Condition0000685` only by initial capitalization and can be corrected in
  place. Eleven Community records contain the same embargo/curation note in the
  condition field.
- Traced Brick364 to Walian Lab's `DumpIsolateImageData.java` generator and
  protocol `walian-2022-isolate-image`; its companion process generator added
  `.tif` while the brick generator did not. Also noticed that the same source
  generator fills flagellar diameter from `heights` instead of
  `flagellaDiams`, an independent value-generation bug to address when the
  brick is replaced.
- Traced the Community records to `communities_isolates.tsv`, generated by
  `DumpIsolates5.java` from `190919_ENIGMA_Isolates.tsv`. The source embargo
  note was in `Isolation conditions/description` and was treated as a
  condition. All 11 defined strains came from sample `FW305-033116` via
  Chakraborty Lab isolation processes in the Natural Organic Matter campaign
  on 2019-03-20; the Community objects themselves have no direct process links.
- Added a deterministic scratch-local `uv` build script and README. The package
  warns that the live Taxon ID range must be checked immediately before import
  because static CORAL records can be added or deleted between exports.

## 2026-07-23 Brick364 replacement and Community deletion audit

- Audited the 11 malformed FW305 isolate Communities against the complete
  static/process TSV export and all 20 bricks whose generated sidecars declare
  a foreign key to `sdt_community`. The only occurrences are the 11 Community
  definitions themselves; there are no external brick, parent-Community, or
  process references in the 2026-07-21 snapshot.
- Added a reproducible bounded audit and reports under
  `coral_import/brick364_v2_20260723/`. The audit stops after brick dimension
  metadata, avoiding scans of multi-gigabyte value matrices that cannot contain
  Community dimension references.
- Corrected the authoritative
  `/h/jmc/src/java/classes/gov/lbl/enigma/app/DumpIsolateImageData.java` and
  recompiled it. Image object references now include the `.tif` suffix,
  flagellar diameters use `flagellaDiams` instead of cell `heights`, and an
  optional fourth argument supplies immutable version suffixes such as `_v2`.
  A portable copy and patch are included in the package.
- Regenerated the Walian source into the historical raw HNDArray form, converted
  it with `ConvertHNDArray` to CORAL's valid one-dimensional heterogeneous
  representation, and created
  `json/isolate_image_data_221011_v2.json`. `CheckGeneric` ends with
  `Generic is OK!`.
- Compared the v2 brick against the original Brick364 source JSON. All 94 Image
  references now exactly match `Image.tsv`; all 61 non-null source flagellar
  diameters are represented correctly; the original diameter vector exactly
  duplicated cell heights; and no semantic differences remain after accounting
  for the `_v2` name/description and the two intended corrections.
- Added a one-row `Update Data <PROCESS:0000053>` process TSV linking
  `isolate_image_data_221011.hndarray` to
  `isolate_image_data_221011_v2.hndarray`, plus ordered CORAL import helpers.
- Added a self-contained, dry-run-by-default arangosh deletion script for the
  11 malformed Communities. It validates exact IDs and names, checks live
  Community and process-edge references, refuses deletion on any match, and
  writes a before-state backup before an `--apply` deletion.
- Corrected the deletion script after its first remote dry run showed that
  `quit()` is unavailable in that arangosh execution context. Dry-run and apply
  behavior now use explicit branches, so a dry run exits naturally without
  falling through into deletion; `node --check` passes.

## 2026-07-23 CORAL re-poll after Brick364 replacement

- Created fresh run `sync-coral-to-berdl/exports/sync-20260723-145923` and
  re-exported all 18 system/static tables from CORAL.
- Refreshed the 1,437-brick catalog, reused 1,436 immutable prior raw brick
  files, and downloaded new `Brick0001669`
  (`isolate_image_data_221011_v2.hndarray`).
- Confirmed CORAL `Process0213897` is an explicit
  `Update Data <PROCESS:0000053>` relationship from Brick364 to Brick1669.
  Brick364 is lifecycle-obsolete but remains annotated in `ddt_ndarray`;
  Brick1669 is current.
- Confirmed all 11 malformed Community records are absent. The fresh static
  exports contain 4,643 Communities, 5,490 Taxa, and 93,090 Processes.
- Confirmed lifecycle generation produced no non-empty pending process TSVs.
- Added an exact importer-side correction for Brick510's one lowercase
  `sdt_condition_name`. The mapping is restricted to the complete brick ID,
  column, and source value; it changed one staged cell and the relationship now
  passes. Added focused tests.
- Built the package and selected 10 data/schema tables for ingest:
  `ddt_brick0000510`, `ddt_brick0001669`, `ddt_ndarray`, `sdt_community`,
  `sdt_taxon`, `sys_ddt_typedef`, `sys_oterm`, `sys_process`,
  `sys_process_input`, and `sys_process_output`.
- Ran the required pre-upload local-package foreign-key audit across all
  affected sources. Of 1,475 relationships, 1,470 passed and five failed.
- The remaining failures are taxon aliases in bricks 454, 458, 461, and 478,
  plus Brick459 declaring 37 Sample names as Communities. Details are in
  `reports/remaining_foreign_key_problems.md`.
- Stopped before BERDL upload because the skill requires zero foreign-key
  failures. No Lakehouse tables, repository schema references, dependent skill
  schemas, or GitHub state were changed by this run.
- Documented that bounded value corrections must use exact brick/column/value
  mappings and that a wrong CORAL foreign-key target type requires a
  superseding source brick rather than importer relabeling.

## 2026-07-24 Brick459 Community-model comparison

- Revisited the initial recommendation to replace Brick459 after comparing it
  with every current taxonomic-abundance brick declaring an
  `sdt_community_name` foreign key.
- Confirmed the closely related Zhou Lab ASV-count bricks consistently model
  the abundance dimension as Community. Same-name Sample and Environmental
  Community objects are established: 191 of 405 values in Brick451, all 14 in
  Brick462, 223 of 587 in Bricks464/476, and all 40 in Brick479.
- Confirmed filtered fractions use distinct Community names and `Filter`
  provenance, while same-name environmental Communities link directly through
  `Community.sample_id`. Brick479 provides the closest precedent because all
  40 names equal Sample names and none has a Community-producing process row.
- Revised the correction recommendation: preserve immutable Brick459 and add
  37 missing `Environmental Community <ME:0000326>` records whose names and
  `sample_id` values equal the existing Sample names. No update-data process or
  importer relationship relabeling is needed.

## 2026-07-24 Community and taxonomy CORAL correction package

- Added reproducible builder
  `tools/build_community_taxonomy_corrections.py` and generated
  `coral_import/community_taxonomy_corrections_20260724/` from the fresh
  `sync-20260723-145923` CORAL export.
- Generated 37 ID-free Community additions. Every row is an
  `Environmental Community <ME:0000326>` whose name and `sample_id` both equal
  one of Brick459's existing Sample names.
- Generated 37 replacement Sampling process rows preserving each original
  process term, Hazen Lab person, Subsurface Observatory campaign, dates, and
  Location input while producing both the existing Sample and the new
  same-named Community.
- Generated a self-contained, dry-run-by-default arangosh script embedding the
  exact 37 old Sampling process IDs, expected Sampling term, dates, Location
  input edges, and Sample output edges. It writes a complete backup before
  removing the old process documents and 74 edges.
- Generated four immutable taxonomy replacement JSON bricks with `_v2`
  appended to both name and description, correcting 935 cells:
  Brick454 (817), Brick458 (70), Brick461 (19), and Brick478 (29).
- Generated four `Update Data <PROCESS:0000053>` rows connecting each original
  taxonomy brick to its replacement.
- Ran `CheckGeneric` on all four JSON files; every transcript ends with
  `Generic is OK!`. Also converted each original source brick independently,
  applied only the intended metadata and taxon substitutions to that JSON, and
  confirmed byte-for-byte equality with the generated replacement.
- Validated the arangosh helper with `node --check` and recorded hashes,
  correction counts, old process mappings, import order, and remote execution
  instructions in the package reports and README.
- Corrected the Community additions after the first `toolx.update_core` attempt
  rejected export-side fields such as `sample_id`. CORAL static imports require
  the typedef property names `sample`, `parent_community`, `condition`, and
  `defined_strains`; the failed first row was not persisted.
- Added `toolx.update_core('Community_additions_20260724.tsv', 'Community')` as
  the first command in `import_to_coral.py`, dated the Community and sampling
  audit TSV filenames, updated the reproducible builder, and documented the
  `YYYYMMDD` requirement for future correction/addition files in the sync
  skill.

## 2026-07-24 Community/taxonomy sync completion

- Confirmed the corrected Community static import uses CORAL typedef property
  names (`sample`, `parent_community`, `condition`, and `defined_strains`) rather
  than export-side `sample_id`. Confirmed generated Community and process TSVs
  are dated `20260724`.
- Re-polled all 18 CORAL static/system types. The live export contains 4,680
  Communities and 93,094 Processes, matching 37 Community additions, 37
  replacement Sampling records, and four Update Data records.
- Refreshed the immutable brick catalog: 1,441 total bricks, 1,437 reused from
  the prior poll, and four new downloads. Converted `Brick0001670` through
  `Brick0001673`; lifecycle classification found 754 explicit obsolete bricks
  and generated no non-empty process TSVs requiring another CORAL round trip.
- Compared against the last completed BERDL baseline
  `sync-20260721-170409`, not the blocked 2026-07-23 package. Selected 14 table
  reloads: Brick510, Brick1669, Bricks1670-1673, `ddt_ndarray`,
  `sdt_community`, `sdt_taxon`, `sys_ddt_typedef`, `sys_oterm`, `sys_process`,
  `sys_process_input`, and `sys_process_output`.
- Selected and dropped the five newly obsolete live tables for Brick364,
  Brick454, Brick458, Brick461, and Brick478. Their CORAL records remain in
  `ddt_ndarray` with lifecycle annotations; all 754 lifecycle-obsolete brick
  tables are absent from BERDL.
- Added referenced-target key differencing to foreign-key scope selection.
  Reloaded FK-bearing tables are always checked. Unchanged sources are now
  checked only when a reloaded target lost exact referenced keys, or when key
  comparison is unavailable. This reduced this run's audit scope from 369 to
  31 source tables while retaining checks for the 11 deleted Community keys and
  37 deleted Process keys.
- Pre-upload package validation passed 79 of 79 relationships across the 13
  directly reloaded FK-bearing tables. Final live Spark validation passed 150
  of 150 relationships across all 31 direct/deletion-affected source tables,
  with zero orphaned values, duplicate target keys, declaration errors, or type
  failures.
- Uploaded 12 source metadata files and 14 changed table files, then completed
  all 14 BERDL imports. The first Spark attempt stopped before any DDL because
  the JupyterHub server had shut down; resumed cleanly from the completed upload
  report after respawning the server.
- Added a standard PySpark Connect fallback for import, verification, comment
  repair, and foreign-key validation because the maintained public bootstrap
  references private `spark_connect_remote` and `berdl_remote` repositories
  that were unavailable. A live `SELECT 1` probe and the complete sync passed
  through the fallback.
- Verified all 711 lifecycle-current BERDL tables are present and all 754
  obsolete tables are absent. For this run's 14 reloaded tables, every table
  comment and all 146 column comments are non-empty and exactly match the
  generated configuration.
- Fixed schema publication so it obtains exact row counts from
  `manifests/current.json` and reads only five sample rows per table. The old
  implementation unnecessarily rescanned every row of all 711 enabled tables.
- Regenerated `schema/` and byte-verified copies in repository and installed
  `berdl-mcp` and `enigma-berdl-query` skills. The query skill therefore
  contains the current table set, including Bricks1669-1673 and excluding the
  five superseded brick tables.

### Critical process review

- Improved foreign-key selection during this run. Reloaded FK-bearing tables
  are still mandatory checks, while unchanged sources are rechecked only when
  an updated target lost referenced keys or a safe key comparison cannot be
  completed. This preserves coverage without repeatedly scanning every large
  brick that points at an append-only static table.
- Improved schema publication during this run. Exact row counts now come from
  the current manifest and schema examples read at most five rows, eliminating
  an accidental full scan of every enabled brick.
- The next reliability improvement should make the comparison baseline an
  explicit successfully imported and verified run. This run selected that
  baseline manually because the most recent generated package was intentionally
  blocked before upload.
- The remote Spark client should gain a supported JupyterHub readiness/spawn
  step that does not depend on private helper repositories. The plain PySpark
  fallback connects correctly once the user server is running, but it does not
  currently start a stopped server.
- Source metadata and ontology uploads are repeated on every import. Content
  addressing or reuse by digest would reduce transfer work while retaining the
  exact source snapshot in each run report.

## 2026-08-10 FW300-N2E2 FEBa genome reconstruction

- Confirmed that `feba.db` contains no `ODPJKPKL_*` identifiers in the N2E2
  `Gene`, `LocusXref`, `GeneFitness`, or `FitByExp_pseudo6_N2E2` records. The
  source organism is `pseudo6_N2E2`; all 6,175 source features use
  `Pf6N2E2_*`, and 5,133 of those loci occur in the fitness tables.
- Retrieved the EDR `FW300-N2E2_Prodigal.gff` for a bounded format comparison.
  Added `tools/export_feba_genome.py`, which exports an organism directly from
  FEBa `ScaffoldSeq`, `Gene`, and `LocusXref` into matching FASTA and GFF3
  files while preserving source identifiers, coordinates, annotations, GC
  fractions, and RefSeq/UniProt cross-references.
- Generated `tnseq_genome_sources/FW300-N2E2_feba/` with a one-scaffold,
  6,919,098 bp FASTA and a GFF3 containing 6,175 genes, 6,094 CDS features, 16
  rRNAs, and 65 tRNAs. The manifest records file sizes and SHA-256 digests.
- Re-read and validated the generated files. The FASTA sequence exactly equals
  the `ScaffoldSeq` value (normalized sequence SHA-256
  `762bb6d15f840efc2dd11e68875f0f6475955701b87f8f2cca6041b917b4916a`);
  all 12,350 GFF rows have valid scaffold coordinates and unique IDs, all
  6,175 child features resolve to gene parents, and no `ODPJKPKL_*` identifier
  appears in the export.

## 2026-08-10 FEBa-to-CORAL project planning

- Read the live active and withdrawn EDR `manifest.tsv` files and established
  that version allocation must use the union of both histories, skip reserved
  `.2`, and verify actual object directories because withdrawn provenance rows
  can mention former active paths.
- Scoped the reviewed import to 25 FEBa organisms, 415 contigs, 139,581,003 bp,
  126,072 source features, 46 mutant libraries, 7,329 experiments, and
  30,756,839 fitness rows, pending confirmation that all 25 reviewed strain
  matches remain in scope.
- Identified two schema-critical namespace collisions: 5,854 FEBa locus IDs are
  reused between selected organisms, while `sdt_gene_name` is globally unique;
  1,132 experiment names are reused across organisms and can represent
  different conditions, while `sdt_condition_name` is globally unique.
- Confirmed FEBa has no primer/barcode field that can populate CORAL's required
  `TnSeq_Library.primers_model`, and that the 25 organisms contain 46 distinct
  `mutantLibrary` values. Per-experiment mapped-read counts cannot be treated as
  library-level metrics without an additional aggregation definition.
- Wrote `FEBA_CORAL_IMPORT_PLAN.md` with gated phases for EDR fingerprinting,
  deduplication and version allocation; paired FASTA/GFF publication; CORAL
  Genome/Gene/Condition/TnSeq Library imports; one fitness brick per strain;
  process provenance; and final BERDL sync and foreign-key validation.
- Corrected the source scope after the user required both public and private
  RB-TnSeq data. Queried live `kescience.fitnessbrowser.organism` (48 rows),
  `enigma.fitprivate.organism` (25 rows), and `enigma.coral.sdt_strain` (3,154
  rows). Exact current-name/full-organism matching yielded 11 public matches and
  25 private matches with no ambiguity; all 11 public matches overlap the
  private set, leaving 25 unique CORAL strains represented by 36
  source-organism datasets.
- Reviewed all 37 unmatched public organisms for normalized or substring
  candidates in `sdt_strain`; none had a defensible current-strain match. The
  scope therefore has 14 private-only organisms, 11 dual-source organisms, and
  no public-only organism.
- Verified that both result sources matter. The 11 matched public
  `fitbyexp_*` tables contain 10,264,888 rows, while their private counterparts
  contain 23,526,981 rows; every pair has a different row count. Updated the
  plan to compare genomes, genes, experiments, libraries, and exact
  `(locusId, expName, fit, t)` rows, deduplicate only identical records, retain
  both source provenances, and stop rather than silently prefer one source when
  same-key values conflict.

## 2026-08-10 public/private N2E2 comparison

- Compared live public `kescience.fitnessbrowser` and private
  `enigma.fitprivate` data for `pseudo6_N2E2`. Both sources contain the exact
  same 6,919,098 bp scaffold sequence (SHA-256
  `762bb6d15f840efc2dd11e68875f0f6475955701b87f8f2cca6041b917b4916a`)
  and the same 6,175 source gene features, including coordinates, types,
  strands, names, descriptions, and GC values.
- The public result has 188 experiments and 965,004 fitness rows; private has
  388 experiments and 1,991,604 rows. Both use the same 5,133 fitness loci.
  All 188 public experiments occur in private, and all 965,004 shared
  `(expName, locusId)` rows have numerically identical `fit` and `t` values.
- The 200 private-only experiments add 99 `ML5`, 92 `ML5b`, 7 `ML5c`, and 2
  `ML5a` experiments. By experiment group these comprise 109 stress, 43 carbon
  source, 18 LB, 12 nitrogen source, 9 denitrifying, 7 resistance, and 2
  anaerobic experiments.
- Semantically normalized metadata for the 188 shared experiments is identical
  except for publication provenance: public supplies `pubId` for every shared
  experiment (`Price18` 178, `Price21b` 6, `Price17` 4), while private leaves
  `pubId` blank. The import should deduplicate shared measurements, retain the
  200 private-only experiments, and preserve the public publication links.

## 2026-08-10 private-only source decision

- The user selected `enigma.fitprivate` as the sole import source for all 25
  matched ENIGMA strains. Public `kescience.fitnessbrowser` organisms and
  measurements will be ignored even when they overlap private organisms.
- Updated `FEBA_CORAL_IMPORT_PLAN.md` to remove the 11-organism cross-source
  reconciliation gate, scope the work manifest and genome fingerprints to 25
  private organisms, generate bricks only from private fitness data, and record
  only private source provenance.
- This intentionally omits public-only publication metadata. For N2E2, that
  means the `Price18`, `Price21b`, and `Price17` `pubId` annotations will not be
  carried into CORAL unless separately requested.

## 2026-08-10 FEBa identifier collision examples

- Rechecked the 25 selected private organisms directly against the immutable
  `feba.db`. All 5,854 reused gene locus IDs are generic `GFF<number>` names
  shared by `Phaga5` and `PseudoFW215-L2`; they identify different coordinates
  and functions. Examples include `GFF1` (phenylacetate-CoA ligase versus
  tyrosyl-tRNA ligase), `GFF100` (hypothetical protein versus CreB), and
  `GFF1369` (p-aminobenzoyl-glutamate cleavage subunit A versus OccM).
- Rechecked all 1,132 experiment names used by more than one selected organism.
  Every reused `expName` has multiple condition signatures when comparing
  description, media, temperature, pH, vessel, atmosphere, shaking, and all
  treatment/concentration fields. For example, `set1IT012` denotes sodium
  pyruvate for N2E2, D-xylose for Keio, and 200 mM sodium nitrate stress for
  Cup4G11; `set1IT081` includes anaerobic L-rhamnose for Btheta, aerobic glycine
  nitrogen source for Keio, and anaerobic potassium dichromate stress for
  MT049.
- Resolved the naming policy: qualify `Gene.gene_id` values as
  `<genome-identifier>:<FEBa-locusId>` and condition names as
  `<strain-name>:<expName>`. Pipe characters must not be used to compose
  identifiers. The gene qualifier is the version-specific CORAL `Genome.name`
  unique key, not the strain name or auto-assigned internal `Genome000...` ID.
- Audited the current exported CORAL `typedef.json`, backend validation code,
  and all static `name` values from the 2026-07-24 snapshot. Every static UPK,
  including `Gene.gene_id`, is unconstrained required unique text with no
  character regex or length limit. Live names already contain spaces, hyphens,
  underscores, periods, slashes, equals signs, semicolons, parentheses, commas,
  plus signs, percent signs, apostrophes, brackets, a degree symbol, and one
  colon; no control characters or edge whitespace were present.
- Added import-level restrictions stronger than CORAL's schema: a non-empty,
  globally unique identifier with one colon as the qualifier; no pipes,
  control characters, or edge whitespace; and a stop if either source
  component already contains a colon. Current FEBa `locusId` and `expName`
  values have zero colons, pipes, edge whitespace, tabs, or newlines.

## 2026-08-10 TnSeq library model investigation

- Audited the immutable private `/scratch/jmc/fitprivate-rbtnseq/source/feba.db`
  schema and confirmed it stores only `Experiment.mutantLibrary`; it contains
  no primer, transposon, delivery-vector, plasmid, or library-construction
  field, and private `pubId` values are blank.
- Enumerated all 46 raw `mutantLibrary` strings and their `timeZeroSet` values.
  Many strings are case, suffix, display-name, or collaborating-site variants
  of one apparent base-library lineage per organism. Shared `timeZeroSet`
  prefixes do not prove that these are the same physical pool, so the import
  plan continues to preserve all 46 CORAL library records.
- Parsed Price et al. 2018 Supplementary Table S20 and its plasmid notes. It
  resolves the selected Acidovorax, Cupriavidus, N1B4, N2C3, N2E2, N2E3, and
  GW456-L13 libraries to mariner vector pKMW3 and the Keio library to Tn5
  vector pKMW7.
- Parsed the open-access Magic Pools article XML. Table 1 resolves Brev2_ML6
  to pTGG39_NN1 and Pedo557_ML3 to pTGG43_NN2. Reviewed the Btheta methods,
  which resolve Btheta_ML6 to pTGG46_NN1, and Putida sources, which resolve
  Putida_ML5 to pKMW3.
- Found that the FW104-10B01 publication confirms a DNA-barcoded mariner
  delivery vector but does not publish its plasmid name. No exact model was
  found in source data or public pages for the remaining 12 newer/private
  physical libraries.
- Created `tnseq_library_model_evidence_20260810.tsv` with all 46 raw labels,
  their apparent base-library lineages, model/transposon evidence, URLs, and
  confidence. Twelve base lineages have exact models, one has only a
  transposon-class assignment, and twelve labels remain unresolved. Model
  inheritance for suffix/site variants remains an inference to confirm.
- Identified a legacy CORAL metadata error: `pseudo6_N2E2_ML5` is a mariner
  pKMW3 library, not pKMW7. Updated the plan to correct the static
  `TnSeq_Library.primers_model` value before reuse; immutable brick data remain
  unchanged.

## 2026-08-13 CORAL import handoff

- Corrected the static import headers to use literal CORAL typedef field names:
  `Genome.strain`, `Gene.gene_id`, `Gene.genome`, and
  `TnSeq_Library.genome`.
- Added generator preflight checks that reject undeclared headers and blank,
  `null`, or `nan` required properties; the focused FEBa suite passes 30 tests.
- Rebuilt and checksum-validated the 22-isolate package with 22 genomes,
  110,899 genes, 3,846 conditions, 34 TnSeq libraries, 22 fitness bricks, and
  one shared experiment-metadata brick.
- Added the deferred N2E2 `Update Data` process to `files_to_import.txt` and a
  runnable `import_n2e2_obsoletion_to_coral.py` helper.
- The project owner reports all package files imported into CORAL. Live
  post-import verification remains the next gate; specifically confirm the
  static and brick counts, object references, producing processes, and the
  obsolete/replacement relationship from `tnseq_n2e2.ndarray` to
  `feba_tnseq_fitness_FW300-N2E2.3.ndarray`.
