---
name: enigma-object-relationships
description: Find and explain relationships/provenance between ENIGMA objects using tools/walk_provenance.py. Use when asked to trace upstream inputs, producing processes, coassemblies, normalized process/object links, or object-to-object lineage in the enigma_coral database.
---

# Enigma Object Relationships

## Overview

Use `tools/walk_provenance.py` (bundled with this skill) to load ENIGMA process data once and walk upstream relationships between objects. Prefer this when you need provenance, lineage, coassembly, or shared-process relationships.

The current ENIGMA schema represents provenance in `sys_process` with `input_objects` and `output_objects` arrays, and also exposes normalized link tables `sys_process_input` and `sys_process_output`. The walker uses `sys_process` for lineage and has raw-output inspection for `sys_process_output`.

## Quick start (CLI)

- Ensure `KB_AUTH_TOKEN` is set; optionally set `BERDL_BASE_URL` and `BERDL_DATABASE`.
- Discover tables and name mappings:

```bash
python skills/enigma-object-relationships/tools/walk_provenance.py --show-tables
```

- Walk provenance from an object name or object ID:

```bash
python skills/enigma-object-relationships/tools/walk_provenance.py --walk-provenance <TABLE> "<NAME_OR_ID>"
```

- Check for coassembly in the lineage:

```bash
python skills/enigma-object-relationships/tools/walk_provenance.py --coassembly <TABLE> "<NAME_OR_ID>"
```

- List processes producing an object:

```bash
python skills/enigma-object-relationships/tools/walk_provenance.py --list-processes <TABLE> "<NAME_OR_ID>"
```

## Relationship workflow

1. Identify the object type and name or ID; map to the table with `--show-tables`.
2. Use `--walk-provenance` to print upstream inputs and the processes that produced them.
3. For relationships between multiple objects, run the walk for each and compare shared process IDs or shared input tokens.
4. If you need exact rows for validation, use `--raw-output-rows` or `--sys-process`.

Current object tables with `<table>_id` and `<table>_name` mappings include `ddt_ndarray`, `sdt_sample`, `sdt_strain`, `sdt_reads`, `sdt_assembly`, `sdt_genome`, `sdt_bin`, `sdt_community`, `sdt_image`, `sdt_tnseq_library`, and `sdt_dubseq_library`. Use `ddt_ndarray` for Brick objects; for example, Brick ID `Brick0000529` is the `ddt_ndarray_id` for table `ddt_brick0000529`.

## Python usage (reuse cached process data)

```python
from skills.enigma-object-relationships.tools.walk_provenance import discover_tables, NameResolver, load_process_cache, walk_provenance_by_name

headers = {"Authorization": f"Bearer {token}"}
discovered_tables = discover_tables(headers)
resolver = NameResolver(headers)
cache = load_process_cache(headers, discovered_tables)

walk_provenance_by_name(resolver, cache.out_lookup, "sdt_sample", "Sample Name")
```

`load_process_cache` stores `sys_process` data in memory, so repeated relationship lookups avoid redundant API calls within the same Python session.
