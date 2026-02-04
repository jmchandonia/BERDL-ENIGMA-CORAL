# DuckDB MCP Server

Local MCP-style REST service backed by DuckDB for the ENIGMA CORAL dataset.

## What is here

- `src/`: FastAPI application exposing BERDL-compatible endpoints.
- `deploy/`: Systemd deployment instructions and unit file.
- `pyproject.toml`: Python project configuration.

## How to run locally

```bash
cd duckdb-mcp-server
uv sync
uv run python -m src.main
```

Swagger/OpenAPI UI is available at `/docs` (or `/apis/mcp/docs` if mounted under `/apis/mcp`).
The exposed database name is `enigma_coral`.

## How to deploy

See `duckdb-mcp-server/deploy/README.md` for systemd setup instructions.

## Data source

The DuckDB file is produced from ENIGMA tables. The current recipe for building it
lives in the `https://github.com/realmarcin/linkml-coral` repository.
