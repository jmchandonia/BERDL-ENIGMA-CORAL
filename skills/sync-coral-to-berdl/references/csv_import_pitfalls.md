# CSV And TSV Import Pitfalls

CORAL exports may contain commas, tabs, quotes, embedded line breaks, JSON-like
array strings, and long free-text fields. Treat delimited data as structured
CSV/TSV, never as split-on-delimiter text.

## Validation

For every exported delimited file:

- parse with Python `csv.reader`
- verify the header is unique and matches the target schema
- verify every row has the same number of fields as the header
- count records through the parser, not by raw newline count when multiline
  fields are possible
- record parser warnings in the table manifest

## Format Preference

- Prefer TSV for static/system tables unless values contain many tabs or
  embedded newlines.
- Prefer Parquet for tables with known parser-sensitive values when feasible.
- Use CSV only when required by an upstream CORAL brick conversion path.

## BERDL Ingest Config

For CSV/TSV, set explicit defaults. Use structured `schema` to avoid inference.

```json
{
  "csv": {
    "header": true,
    "delimiter": "\t",
    "inferSchema": false,
    "quote": "\"",
    "escape": "\"",
    "multiLine": true
  }
}
```

If a KBase import path mishandles valid quoted CSV, rewrite that table to TSV
or Parquet before ingest and document the transformation in the manifest.
