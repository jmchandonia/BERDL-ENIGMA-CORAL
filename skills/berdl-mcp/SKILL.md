---
name: berdl-mcp
description: Use the BERDL MCP API to discover databases/tables, inspect schemas, and query Delta Lake data (including enigma_coral).
---

# BERDL MCP API

Use this skill when interacting with the BERDL MCP API to explore or query CORAL data in the `enigma_coral` database.

## Quick start

- Base URL: `https://hub.berdl.kbase.us/apis/mcp`
- Auth: `Authorization: Bearer $KB_AUTH_TOKEN`
- Default database for CORAL work: `enigma_coral`

## Workflow

1. **Confirm service health** (optional): `GET /health`.
2. **List databases**: `POST /delta/databases/list` with `{"use_hms": true, "filter_by_namespace": true}`.
3. **List tables in a database**: `POST /delta/databases/tables/list` with `{"database": "enigma_coral", "use_hms": true}`.
4. **Get table schema**: `POST /delta/databases/tables/schema` with `{"database": "enigma_coral", "table": "..."}`.
5. **Query data**:
   - Use the structured builder only: `POST /delta/tables/select`.
   - Do not use SQL syntax or `/delta/tables/query` (not supported in this environment).
6. **Sample data**: `POST /delta/tables/sample` with `{"database": "enigma_coral", "table": "...", "limit": 10}`.
7. **Count rows**: `POST /delta/tables/count` with `{"database": "enigma_coral", "table": "..."}`.

## Query guidance

- Use `select` for joins, filters, aggregations, and pagination.
- Use table names as `table_alias` values in `columns` when joins are present.
- Keep filter column names unambiguous across joined tables (filters do not accept table aliases).
- Keep `limit <= 1000` (API constraint).

## When to load references

- For CORAL schema details, load:
  - `references/enigma_coral_schema.md`
- For request/response schemas, supported operators, and pagination details, load:
  - `references/berdl_mcp_openapi.json` (if available in the project using this skill)
