# Skills Manifest

This manifest summarizes the Codex skills available in this repo.

## Skills

- name: berdl-mcp
  description: Use the BERDL MCP API to discover databases/tables, inspect schemas, and query Delta Lake data (including enigma_coral).
  path: skills/berdl-mcp/SKILL.md
  references:
    - skills/berdl-mcp/references/enigma_coral_schema.md
    - skills/berdl-mcp/references/berdl_mcp_openapi.json

- name: enigma-berdl-query
  description: Query ENIGMA (coral_enigma) data using the BERDL MCP API with the provided schema references; use when answering questions about ENIGMA tables, brick/ndarray data, or when composing BERDL queries that must adhere strictly to the coral_enigma table/column list.
  path: skills/enigma-berdl-query/SKILL.md
  references:
    - skills/enigma-berdl-query/references/enigma_coral_schema.md
    - skills/enigma-berdl-query/references/ddt_ndarray_table.md
    - skills/enigma-berdl-query/references/sys_ddt_typedef_table.md

- name: enigma-object-relationships
  description: Find and explain relationships/provenance between ENIGMA objects using tools/walk_provenance.py. Use when asked to trace upstream inputs, producing processes, coassemblies, or object-to-object lineage in the enigma_coral database.
  path: skills/enigma-object-relationships/SKILL.md
  tools:
    - skills/enigma-object-relationships/tools/walk_provenance.py
