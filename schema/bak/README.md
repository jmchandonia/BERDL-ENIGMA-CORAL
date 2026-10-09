# Schema

This directory stores schema markdown for the ENIGMA CORAL dataset.

## What to do

- Generate or refresh the schema markdown:

```bash
uv run python tools/get_schema.py
```

- Override the output directory:

```bash
uv run python tools/get_schema.py --schema-dir /path/to/schema
```

The default output file is `enigma_coral_schema.md`.
