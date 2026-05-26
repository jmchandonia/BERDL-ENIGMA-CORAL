# Comment Contract

## BERDL Ingest Behavior

The installed `data_lakehouse_ingest` package supports column comments when a
table config uses structured `schema` entries:

```json
{
  "name": "sdt_sample",
  "schema": [
    {
      "column": "sdt_sample_id",
      "type": "STRING",
      "nullable": true,
      "comment": "{\"description\":\"Primary key\"}"
    }
  ]
}
```

The package does not apply comments from `schema_sql`. Always generate
structured `schema` for this sync.

Observed installed package behavior:

- `data_lakehouse_ingest.utils.delta_comments.apply_comments_from_table_schema`
  applies column comments with:
  `ALTER TABLE <table> ALTER COLUMN <column> COMMENT '<escaped comment>'`
- `process_table()` calls this helper when structured schema comment metadata is present.
- Results are returned in each table report as `comments_report`.

## Table-Level Comments

No table-level comment support was found in the installed ingest package.
Treat table comments separately:

1. Include expected table comments in the manifest.
2. Validate whether the target table has the expected table comment.
3. Generate fallback SQL only for missing or mismatched table comments.

## Fallback Policy

Do not generate broad repair SQL by default. Generate only the statements
needed after validation:

- missing column comment
- failed column comment in `comments_report`
- missing or mismatched table comment

When generating SQL, escape single quotes by doubling them. Quote column names
with backticks.
