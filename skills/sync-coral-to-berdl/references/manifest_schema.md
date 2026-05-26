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
