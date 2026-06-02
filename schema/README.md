# Schema

This directory stores schema markdown for the ENIGMA CORAL dataset.

## What to do

- Generate or refresh the schema markdown:

```bash
python3 skills/sync-coral-to-berdl/scripts/generate_schema_markdown.py \
  --run-dir sync-coral-to-berdl/exports/dryrun-20260527-143730 \
  --schema-dir schema
```

- Override the output directory:

```bash
python3 skills/sync-coral-to-berdl/scripts/generate_schema_markdown.py \
  --run-dir /path/to/sync-coral-export \
  --schema-dir /path/to/schema
```

The generated files are `ddt_ndarray_table.md`,
`sys_ddt_typedef_table.md`, and `enigma_coral_schema.md`.
