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
   - Structured builder: `POST /delta/tables/select` (safer; preferred).
   - Raw SQL: `POST /delta/tables/query` (include `ORDER BY` when paginating).
6. **Sample data**: `POST /delta/tables/sample` with `{"database": "enigma_coral", "table": "...", "limit": 10}`.
7. **Count rows**: `POST /delta/tables/count` with `{"database": "enigma_coral", "table": "..."}`.

## Query guidance

- Prefer `select` for safety and clarity (supports joins, filters, aggregations, pagination).
- If using `query`, always add `ORDER BY` when `offset > 0` to avoid duplicate/missing rows.
- Keep `limit <= 1000` (API constraint).

## When to load references

- For request/response schemas, supported operators, and pagination details, load:
  - `references/berdl_mcp_openapi.json`
