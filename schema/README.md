# Schema

This directory stores schema markdown for the ENIGMA CORAL dataset as
published to the BERDL Lakehouse namespace `enigma.coral` (Iceberg). Use
`enigma.coral` as the BERDL MCP `database` value; the former Delta namespace
`enigma_coral` was retired in October 2026.

## What to do

- Generate or refresh the schema markdown:

```bash
python3 skills/sync-coral-to-berdl/scripts/generate_schema_markdown.py \
  --run-dir sync-coral-to-berdl/exports/sync-20261001-151414 \
  --schema-dir schema
```

- Override the output directory:

```bash
python3 skills/sync-coral-to-berdl/scripts/generate_schema_markdown.py \
  --run-dir /path/to/sync-coral-export \
  --schema-dir /path/to/schema
```

The generated files are `ddt_ndarray_table.md`,
`sys_ddt_typedef_table.md`, and `enigma_coral_schema.md` (the file name is
historical; its content documents `enigma.coral`). The sync pipeline's
publish stage regenerates them and copies them into the `berdl-mcp` and
`enigma-berdl-query` skills.
