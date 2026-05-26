# Manifest Schema

The sync manifest is the source of truth for deciding which tables changed.
Store it as JSON under the run directory and copy the completed manifest to
the durable sync location for the next run.

## Top-Level Fields

```json
{
  "manifest_version": 1,
  "generated_at": "ISO-8601 timestamp",
  "tenant": "enigma",
  "dataset": "coral",
  "namespace": "enigma_coral",
  "coral_source": {
    "typedef": "/path/to/typedef.json",
    "obo_dir": "/path/to/ontologies",
    "host": "coral-enigma.lbl.gov"
  },
  "tables": []
}
```

## Table Fields

```json
{
  "table": "sdt_sample",
  "source_kind": "typedef|brick|ddt_metadata|ontology",
  "data_path": "export/data/sdt_sample.tsv",
  "format": "tsv",
  "delimiter": "\t",
  "row_count": 123,
  "byte_count": 4567,
  "schema": [
    {
      "column": "sdt_sample_id",
      "type": "STRING",
      "nullable": true,
      "comment": "{\"description\":\"...\"}"
    }
  ],
  "table_comment": "optional table-level comment",
  "hashes": {
    "data_sha256": "...",
    "schema_sha256": "...",
    "comments_sha256": "...",
    "table_sha256": "..."
  },
  "parser_warnings": [],
  "lifecycle": {
    "status": "current|obsolete|not_applicable|review_needed",
    "source": "explicit_update|explicit_withdraw|inferred_version|inferred_date|none",
    "withdrawn_date": "optional ISO-8601 date",
    "superceded_by_ddt_ndarray_id": "optional successor ddt_ndarray id",
    "process_id": "optional CORAL process id",
    "inferred_process_tsv": "optional export/metadata/process_update_data_<run_id>.tsv"
  },
  "change_status": "new|data_changed|schema_changed|comments_changed|unchanged|missing_from_current_export"
}
```

## Hash Rules

- `data_sha256`: raw bytes of the normalized data file.
- `schema_sha256`: canonical JSON of ordered column names, types, and nullability.
- `comments_sha256`: canonical JSON of ordered column comments plus table comment.
- `table_sha256`: canonical JSON containing the three hashes above plus format settings.

Use sorted object keys and stable separators when hashing JSON-derived content.
Do not include local absolute work paths in table hashes.

## Brick Lifecycle Fields

Use `lifecycle.status = "obsolete"` for a brick table when the source
`ddt_ndarray` row is withdrawn or superseded. Obsolete brick data tables must
not be enabled in the BERDL ingest config, even if their data hash changed.

Use `lifecycle.status = "current"` for brick data tables that may be exposed as
`ddt_brick...` tables in BERDL.

Use `lifecycle.status = "review_needed"` when a brick appears in ambiguous
update/withdraw provenance or when name-based inference finds multiple possible
successors.

For non-brick tables, set `lifecycle.status = "not_applicable"`.

When lifecycle metadata changes only in `ddt_ndarray`, treat `ddt_ndarray` as
changed even if the obsolete brick's own data file is excluded from ingest.
