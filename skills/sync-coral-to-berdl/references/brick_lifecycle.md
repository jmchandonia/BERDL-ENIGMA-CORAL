# Brick Lifecycle

Use this reference after CORAL brick download and before BERDL ingest config
generation.

## Explicit CORAL Provenance

A brick is obsolete when its object reference appears in `input_objects` for a
CORAL process whose process name or process type is `withdraw data` or
`update data`, matched case-insensitively.

For `update data` processes:

- input brick objects are obsolete
- output brick objects are successors
- fill `superceded_by_ddt_ndarray_id` when exactly one successor can be mapped
- set `withdrawn_date` from `date_end`, falling back to `date_start`
- if multiple successor bricks are present, flag the row as `review_needed`

For `withdraw data` processes:

- input brick objects are obsolete
- no successor is required
- set `withdrawn_date` from `date_end`, falling back to `date_start`

Do not infer an update relationship when explicit CORAL provenance already
covers the brick pair.

## Name-Based Update Inference

Inference is only for newly available bricks whose lifecycle is not already
clear in CORAL. Write inferred relationships for review/import; do not silently
modify CORAL.

Normalize candidate names by lowercasing, trimming punctuation, collapsing
whitespace, and removing recognized version/date tokens. Only compare bricks in
the same normalized name family.

Version examples:

- `v1`, `v2`, `v03`
- `version 1`, `version 2`
- `_v1`, `-v2`, `(v3)`
- embedded forms such as `_v2_ASV_count` and `_v3_ASV_count`

Infer that the later version supersedes the immediately preceding version in
the same normalized family. For example, `taxonomy v2` supersedes
`taxonomy v1`.

Unversioned names may be treated as implicit `v1` only when a matching
explicit versioned brick exists. For example, `growth_2806.ndarray` may be
paired with `growth_2806_v2.ndarray`, but unversioned-only families must not
produce inferred updates.

Date examples:

- `YYMMDD`: `250102`
- `YYYYMMDD`: `20250102`
- corrected date suffixes such as `240314b`
- separated forms such as `2025-01-02`, `2025_01_02`, or `2025 01 02`

Infer that the later dated brick supersedes the previous dated brick in the
same normalized family. For example, `taxonomy data 260402` supersedes
`taxonomy data 250102`.

When a date has a single-letter suffix, sort the unsuffixed date before the
suffixed correction; for example, `240314` precedes `240314b`.

Some cross-family replacement bridges are accepted when row/key coverage shows
that the later table is the maintained form of the older data. Current manual
bridge:

- `isolate_genome_links_arkin_220902` -> `isolate_sequence_and_quality_arkin_230202`

Flag for review instead of inferring when:

- normalized families mix version and date schemes
- multiple older bricks could be the immediate predecessor
- names differ beyond recognized version/date tokens
- explicit CORAL provenance contradicts the inferred order

## HTCP Growth Lifecycle

For Arkin HTCP growth bricks `Brick0000215` through `Brick0000343`, infer
lifecycle from the later RELOADS imports:

- match HTCP and RELOADS candidates by the name prefix before `_HTCP_` or
  `_RELOADS_`
- compare raw TSV row overlap using time, well, strain, and optical density
- infer an update when the later RELOADS table is a near-exact replacement,
  a clean subset of the HTCP table, or a near match with only small numeric or
  row differences
- infer a withdrawal when no later RELOADS table exists for the prefix, or
  when same-prefix candidates have no meaningful row overlap

For update process rows, use the immediate replacement edge:

```text
HTCP -> RELOADS -> RELOADS_v2
```

For the resolved `ddt_ndarray` lifecycle view, set
`superceded_by_ddt_ndarray_id` directly to the latest known successor, usually
the `RELOADS_v2` brick.

## Inferred Process TSV

Write candidate inferred update rows to:

```text
metadata/process_update_data_<run_id>.tsv
```

Write inferred withdrawal rows to:

```text
metadata/process_withdraw_data_<run_id>.tsv
```

Use the CORAL process-import column shape:

```text
process	person	campaign	protocol	date_start	date_end	input_objects	output_objects
```

The update `process` value should be `Update Data <PROCESS:0000053>`.
Use `Withdraw Data <PROCESS:0000052>` for withdrawals. `person`, `campaign`,
and `protocol` must be valid CORAL import values; use `null` for `protocol`
when no protocol object is available. Object references must use the CORAL
loader form, for example `Generic: old_dataset.ndarray`, not exported BERDL
refs such as `[Brick-0000002:Brick0000001]`.

Each inferred row should also appear in `reports/brick_lifecycle.tsv`.
The resolved review file is `reports/brick_lifecycle_with_inference.tsv`;
it must contain exactly one row per brick, with explicit CORAL provenance
taking precedence over inferred candidates.

## BERDL Exposure Policy

Current bricks can be exposed as `ddt_brick...` tables in the `enigma_coral`
namespace.

Obsolete bricks must not be exposed as `ddt_brick...` tables. Exclude them from
the ingest config. If an obsolete table already exists in BERDL, generate a
reviewed drop statement in:

```text
reports/obsolete_berdl_tables_to_drop.sql
```

Do not drop the table until `ddt_ndarray` includes the obsolete brick with
`withdrawn_date` and, when known, `superceded_by_ddt_ndarray_id`.
