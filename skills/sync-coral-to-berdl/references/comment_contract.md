# Comment Contract

## Supported BERDL Ingest Behavior

The installed KBase `data_lakehouse_ingest` package supports table and column
comments when a
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
- A table config's `comment` is applied by `apply_table_comment()`.
- Results are returned in each table report as `table_comment_report` and
  `column_comments_report`.
- Despite the historical helper module name `delta_comments`, the supported
  ingest path writes canonical Iceberg tables with catalog-driven
  `writeTo(...).createOrReplace()` and applies these comments to that table.

## Table-Level Comments

Pass the generated `table_comment` value as the supported table config's
`comment` property. Then:

1. Include the expected table comment in the manifest.
2. Inspect `table_comment_report`.
3. Read the table comment back from `DESCRIBE TABLE EXTENDED`.
4. Generate fallback SQL only if the reported or read-back value is missing or
   mismatched.

Run the same read-back comparison separately for canonical Iceberg
`enigma.coral` and transitional Delta `enigma_coral`; a comment present in one
provider does not prove it is present in the other.

## Fallback Policy

Do not generate broad repair SQL by default. Generate only the statements
needed after validation:

- missing column comment
- failed column comment in `column_comments_report`
- missing or mismatched table comment

When generating SQL, escape single quotes by doubling them. Quote column names
with backticks.

The fallback comment application must iterate over structured schema entries
for every enabled table. Do not restrict it to `ddt_ndarray` and
`sys_ddt_typedef`; that leaves static-table and brick-table comments missing.
