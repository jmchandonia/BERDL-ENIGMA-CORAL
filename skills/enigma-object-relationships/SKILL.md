---
name: enigma-object-relationships
description: Find and explain relationships/provenance between ENIGMA objects using tools/walk_provenance.py. Use when asked to trace upstream inputs, producing processes, coassemblies, or object-to-object lineage in the enigma_coral database.
---

# Enigma Object Relationships

## Overview

Use `tools/walk_provenance.py` to load ENIGMA process data once and walk upstream relationships between objects. Prefer this when you need provenance, lineage, or shared-process relationships.

## Quick start (CLI)

- Ensure `KB_AUTH_TOKEN` is set; optionally set `BERDL_BASE_URL` and `BERDL_DATABASE`.
- Discover tables and name mappings:

```bash
python tools/walk_provenance.py --show-tables
```

- Walk provenance:

```bash
python tools/walk_provenance.py --walk-provenance <TABLE> "<NAME>"
```

- Check for coassembly in the lineage:

```bash
python tools/walk_provenance.py --coassembly <TABLE> "<NAME>"
```

- List processes producing an object:

```bash
python tools/walk_provenance.py --list-processes <TABLE> "<NAME>"
```

## Relationship workflow

1. Identify the object type and name; map to the table with `--show-tables`.
2. Use `--walk-provenance` to print upstream inputs and the processes that produced them.
3. For relationships between multiple objects, run the walk for each and compare shared process IDs or shared input tokens.
4. If you need exact rows for validation, use `--raw-output-rows` or `--sys-process`.

## Python usage (reuse cached process data)

```python
from tools.walk_provenance import discover_tables, NameResolver, load_process_cache, walk_provenance_by_name

headers = {"Authorization": f"Bearer {token}"}
discovered_tables = discover_tables(headers)
resolver = NameResolver(headers)
cache = load_process_cache(headers, discovered_tables)

walk_provenance_by_name(resolver, cache.out_lookup, "sdt_sample", "Sample Name")
```

`load_process_cache` stores `sys_process` data in memory, so repeated relationship lookups avoid redundant API calls within the same Python session.
