# BERDL-ENIGMA-CORAL

Tools for querying ENIGMA data from CORAL in BERDL using AI.

## Authentication

You need a KBase account linked to the KBase Lakehouse.  Once you have
one, go to https://hub.berdl.kbase.us/, log in, start a new Jupyter
notebook, click on "Get Credentials" in the upper right corner of the
screen, and download the config file to ~/.berdl/remote-config.yaml.

## Database Access

After doing the above authentication steps, you should also click on
"Request Tenant Access" for any datasets you need access to.

## Output locations

By default, table dumps and the schema markdown are written to the `schema`
directory in this repo. You can override the output directory with
`BERDL_OUTPUT_DIR`.

## Directories

- `tools/`: CLI utilities for querying BERDL and generating outputs.
- `schema/`: Generated schema markdown (and related artifacts).
- `templates/`: NCBI submission spreadsheet templates.
- `duckdb-mcp-server/`: Local DuckDB-backed MCP server implementation.
- `benchmarks/`: Benchmark prompts, answers, and results.
- `skills/`: Codex skills and references.
