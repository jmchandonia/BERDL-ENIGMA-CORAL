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

Infer that the later version supersedes the immediately preceding version in
the same normalized family. For example, `taxonomy v2` supersedes
`taxonomy v1`.

Date examples:

- `YYMMDD`: `250102`
- `YYYYMMDD`: `20250102`
- separated forms such as `2025-01-02`, `2025_01_02`, or `2025 01 02`

Infer that the later dated brick supersedes the previous dated brick in the
same normalized family. For example, `taxonomy data 260402` supersedes
`taxonomy data 250102`.

Flag for review instead of inferring when:

- normalized families mix version and date schemes
- multiple older bricks could be the immediate predecessor
- names differ beyond recognized version/date tokens
- explicit CORAL provenance contradicts the inferred order

## Inferred Process TSV

Write candidate inferred update rows to:

```text
export/metadata/process_update_data_<run_id>.tsv
```

Use the CORAL `Process.tsv` column shape:

```text
id	process	person	campaign	protocol_id	date_start	date_end	input_objects	output_objects
```

The `process` value should be `update data`. Leave fields blank when the
correct CORAL import value cannot be inferred from the export, and list those
rows in `export/reports/brick_lifecycle_review.tsv`.

Each inferred row should also appear in `export/reports/brick_lifecycle.tsv`
with the inference source, predecessor brick, successor brick, normalized name
family, and confidence/review status.

## BERDL Exposure Policy

Current bricks can be exposed as `ddt_brick...` tables in the `enigma_coral`
namespace.

Obsolete bricks must not be exposed as `ddt_brick...` tables. Exclude them from
the ingest config. If an obsolete table already exists in BERDL, generate a
reviewed drop statement in:

```text
export/reports/obsolete_berdl_tables_to_drop.sql
```

Do not drop the table until `ddt_ndarray` includes the obsolete brick with
`withdrawn_date` and, when known, `superceded_by_ddt_ndarray_id`.
