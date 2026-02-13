---
name: enigma-berdl-query
description: Query ENIGMA (enigma_coral) data using the BERDL MCP API with the provided schema references; use when answering questions about ENIGMA tables, brick/ndarray data, or when composing BERDL queries that must adhere strictly to the enigma_coral table/column list.
---

# Enigma BERDL Query

## Overview

Use this skill to answer ENIGMA data questions by composing BERDL MCP API queries against the `enigma_coral` database using only the tables and columns listed in `references/enigma_coral_schema.md`. Do not use any other data source for ENIGMA data.

## Required references

- `references/enigma_coral_schema.md` for the allowed table/column list.
- `references/ddt_ndarray_table.md` and `references/sys_ddt_typedef_table.md` when questions involve bricks/ndarrays (tables named `ddt_brick*`).

## Workflow

1. Load `references/enigma_coral_schema.md` and confirm the tables/columns needed by the request.
2. If the request involves bricks/ndarrays, load `references/ddt_ndarray_table.md` and `references/sys_ddt_typedef_table.md` and identify:
   - the relevant `ddt_ndarray` record(s)
   - the matching `ddt_brick{ID}` table
   - columns and joins from `sys_ddt_typedef`
3. Build BERDL MCP API queries using only the schema-listed tables/columns.
4. Use `/delta/tables/select` for all queries (SQL is not supported).
5. Keep `limit <= 1000` and use `order_by` when paginating.

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
- Use `sys_ddt_typedef` filtered by `ddt_ndarray_id` to map brick columns and join targets.
- Query the brick table `ddt_brick{ID}` using those columns.

## Guardrails

- Only use tables and columns that appear in `references/enigma_coral_schema.md`.
- Do not use any other ENIGMA data sources beyond the BERDL MCP API.
- When unsure about a column, ask for clarification instead of guessing.
