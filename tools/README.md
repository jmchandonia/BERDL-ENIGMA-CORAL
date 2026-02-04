# Tools

Python CLI tools for querying BERDL/ENIGMA data and generating exports.

## What is here

- `get_schema.py`: Fetch schema metadata and render markdown.
- `get_table.py`: Export a table to markdown.
- `walk_provenance.py`: Trace object provenance and list related processes.
- `generate_ncbi_submission.py`: Build NCBI submission spreadsheets and staging assets.
- `list_databases.py`: List BERDL MCP databases.

## Common usage

```bash
uv run python tools/list_databases.py
uv run python tools/get_schema.py
uv run python tools/get_table.py sdt_genome
```

## Options

- `--base-url` overrides the MCP server base URL (defaults to BERDL).
- `--schema-dir` overrides where schema markdown is read/written.

All tools require `KB_AUTH_TOKEN` in the environment if you use BERDL.

