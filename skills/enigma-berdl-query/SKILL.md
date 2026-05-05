---
name: enigma-berdl-query
description: Query ENIGMA (enigma_coral) data using the BERDL MCP API with generated schema references; use when answering questions about ENIGMA tables, brick/ndarray data, provenance/object tables, or when composing BERDL queries that must adhere strictly to the current enigma_coral table/column list.
---

# Enigma BERDL Query

## Overview

Use this skill to answer ENIGMA data questions by composing BERDL MCP API queries against the `enigma_coral` database using only the generated schema references bundled with this skill. Do not use any other data source for ENIGMA data.

The schema reference is large. Search it and read only the table sections needed for the request; do not load the whole file into context unless the user explicitly asks for a full schema review.

## Required references

- `references/enigma_coral_schema.md` for the allowed table/column list and sample rows. This is the complete generated schema.
- `references/ddt_ndarray_table.md` for the full `ddt_ndarray` extract when locating arrays/bricks.
- `references/sys_ddt_typedef_table.md` for the full `sys_ddt_typedef` extract when mapping brick columns, dimensions, variables, units, and foreign keys.

## Finding schema details

- List table sections with `rg -n "^## Table:" references/enigma_coral_schema.md`.
- Find a specific table with `rg -n "^## Table: <table>$" references/enigma_coral_schema.md`, then read from that line to the next `## Table:`.
- Search by column or term with `rg -n "<column_or_term>" references/enigma_coral_schema.md`.
- For bricks, search the ndarray and typedef extracts by Brick ID or dataset name, for example `rg -n "Brick0000529|isolate_genbank" references/ddt_ndarray_table.md references/sys_ddt_typedef_table.md`.

## Workflow

1. Locate the relevant table section(s) in `references/enigma_coral_schema.md` and confirm the exact table and column names.
2. If the request involves bricks/ndarrays, inspect `references/ddt_ndarray_table.md` and `references/sys_ddt_typedef_table.md` and identify:
   - the relevant `ddt_ndarray` record(s)
   - the matching `ddt_brickNNNNNNN` table
   - columns, units, dimensions, variables, and joins from `sys_ddt_typedef`
3. Build BERDL MCP API queries using only the schema-listed tables/columns.
4. Use `/delta/tables/select` for all queries (SQL is not supported).
5. Keep `limit <= 1000` and use `order_by` when paginating.
6. Exclude rows with non-null `withdrawn_date` unless the user asks for withdrawn or superseded arrays.

## BERDL MCP API usage (summary)

- Base URL: `https://hub.berdl.kbase.us/apis/mcp`
- Auth: `Authorization: Bearer $KB_AUTH_TOKEN`
- Database: `enigma_coral`

Common endpoints:
- List tables: `POST /delta/databases/tables/list`
- Table schema: `POST /delta/databases/tables/schema`
- Count rows: `POST /delta/tables/count`
- Query (structured): `POST /delta/tables/select`

## Structured query tips

- Use table names as `table_alias` values in `columns` when joins are present.
- Keep filter column names unambiguous across joined tables (filters do not accept table aliases).
- Supported filter operators: `=`, `!=`, `<`, `>`, `<=`, `>=`, `IN`, `NOT IN`, `LIKE`, `NOT LIKE`, `IS NULL`, `IS NOT NULL`, `BETWEEN`.

## Brick (ndarray) guidance

- Use `ddt_ndarray` to identify the brick and its `ddt_ndarray_id`.
- Convert a `ddt_ndarray_id` such as `Brick0000529` to the brick table name `ddt_brick0000529`.
- Use `sys_ddt_typedef` filtered by `ddt_ndarray_id` to map brick columns and join targets.
- Treat brick schemas as heterogeneous. Do not assume that condition, media, growth, sequence, or chemistry columns have the same names across bricks; inspect the specific brick and typedef rows.
- Query the brick table using the exact columns listed for that brick table in `references/enigma_coral_schema.md`.

## Object and provenance tables

- Core object tables use matching `<table>_id` and `<table>_name` columns, for example `sdt_sample`, `sdt_strain`, `sdt_reads`, `sdt_assembly`, `sdt_genome`, `sdt_bin`, `sdt_community`, `sdt_image`, `sdt_tnseq_library`, and `sdt_dubseq_library`.
- `sys_process` contains `input_objects` and `output_objects` arrays.
- `sys_process_input` and `sys_process_output` provide normalized process/object link rows. Use them for exact process-object filters when they are easier than parsing the arrays.
- Prefer the `enigma-object-relationships` skill for upstream lineage, coassembly, and shared-process questions.

## Guardrails

- Only use tables and columns that appear in `references/enigma_coral_schema.md`.
- Do not use any other ENIGMA data sources beyond the BERDL MCP API.
- When unsure about a column, ask for clarification instead of guessing.
