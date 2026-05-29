# BERDL-ENIGMA-CORAL

Tools for querying ENIGMA data from CORAL in BERDL using AI.

## Authentication

You need a KBase account linked to the KBase Lakehouse.

To get current BERDL credentials:

1. Go to https://hub.berdl.kbase.us/ and log in.
2. Start a new Jupyter notebook.
3. Click **Get Credentials** in the upper right corner of the screen.
4. Download the config file to `~/.berdl/remote-config.yaml`.

Command-line BERDL tools in this repo should use `berdl-remote` with
`~/.berdl/remote-config.yaml` rather than stale tokens copied into a local
`.env` file. If you downloaded the file somewhere else first, import it with:

```bash
berdl-remote configure -f /path/to/remote-config.yaml
```

If the config expires or BERDL reports invalid credentials, repeat the steps
above to download a fresh config.

You also need to get a KBASE_AUTH_TOKEN and put it in a .env
file, e.g.,

```
KB_AUTH_TOKEN=....
```

When you're logged in to BERDL, and in a Jupyter notebook, run:
BERDLSettings().KBASE_AUTH_TOKEN and paste the token that comes back
(without quotes) into your .env file.

## Database Access

After doing the authentication steps, click **Request Tenant Access** for any
datasets you need access to.

## Output Locations

By default, table dumps and the schema markdown are written to the `schema`
directory in this repo. You can override the output directory with
`BERDL_OUTPUT_DIR`.

## Table Loading

If using the skill to load tables, put in your .env file the location
of the CORAL typedef.json file and the directory where your obo files with
microtypes, units, etc are located.

```
CORAL_TYPEDEF=/path/to/typedef.json
CORAL_ONTOLOGIES=/path/to_obo_files_directory/
```


## Directories

- `tools/`: CLI utilities for querying BERDL and generating outputs.
- `schema/`: Generated schema markdown (and related artifacts).
- `templates/`: NCBI submission spreadsheet templates.
- `duckdb-mcp-server/`: Local DuckDB-backed MCP server implementation.
- `benchmarks/`: Benchmark prompts, answers, and results.
- `skills/`: Codex skills and references.
