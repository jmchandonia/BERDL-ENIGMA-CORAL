---
name: coral-ndarray-generation
description: Generate or review CORAL generic ndarray JSON files, CORAL static-object import TSVs, and CORAL-style BERVO ontologized tabular metadata, focusing on typedef field names, required properties, foreign-key names, reusable ndarray structure, ontology terms, units, references, and validation.
---

# Coral Ndarray Generation

Use this skill when the user wants to generate, update, or review CORAL generic
ndarrays, CORAL static-object import TSVs, or CORAL-style BERVO tabular data.

## Required references

Read `references/model.md` first. When generating or reviewing static-object
TSVs, also read `references/static-imports.md` before editing data.

## Core ndarray workflow

1. Identify the array value being measured and dimensions matching its shape.
2. Classify each dimension variable as numeric, string, `object_ref`, or
   `oterm_ref`.
3. Verify every ontology ID and label in the current OBO files.
4. Give every numeric field a unit.
5. Use only legitimate imported identifiers in ID/reference fields.
6. Validate every JSON with `gov.lbl.enigma.app.CheckGeneric`, overwriting stale
   `.check` files.

## CORAL static-object TSV workflow

- Inspect the current CORAL typedef before generation. The typedef's
  `field_name` is the import header; do not substitute a BERDL/CDM column name,
  generated database column, or intuitive alias.
- Omit the primary-key `id` for additions when CORAL assigns it. Include every
  required non-PK property.
- For a foreign key, use the declared FK property's `field_name` as the header
  and the target object's unique name as its value. Do not put a future
  CORAL-assigned ID into a staged file or brick reference.
- Preserve literal model distinctions. For example, a Gene's unique field can
  be `gene_id` even when another object type uses `name`.
- Before delivery, require an exact header comparison against the typedef,
  reject undeclared columns, reject missing required values, and validate FK
  values against staged or already imported unique names.
- Import static types in dependency order, then stop and re-poll names, counts,
  and foreign keys before importing bricks.

## BERVO CORAL-style tabular generation

- Preserve one logical array per dataset, row dimensions in the data table,
  measured values as data variables, and array constants in
  `ddt_ndarray_metadata`.
- Use BERVO CURIEs such as `BERVO:0000000`, never
  `bervo:BERVO_0000000`. Use UO CURIEs for units.
- Put dimension variables first, grouped by dimension, and keep
  `sys_ddt_typedef` dimension/variable numbers consistent.
- Move values constant across the array to array metadata unless required as
  row keys. Drop wholly empty source columns and encode partial missing values
  as empty fields, not sentinel strings.
- Populate `sys_oterm` with the complete ontology snapshot used for the
  dataset, not only referenced terms.

## CORAL process TSVs

- Use the established schema when present: `process`, `person`, `campaign`,
  `protocol`, `date_start`, `date_end`, `input_objects`, `output_objects`.
- `campaign` is required unless the current schema proves otherwise.
- Format typed ontology values as `Label <CURIE>`.
- Use loader-specific object prefixes, such as `Generic: name.ndarray`.
- Join multiple object references with commas, not semicolons.
- Validate referenced object names against JSON `name` values and current
  imported unique names.

## Guardrails

- Keep ontology labels exactly as they appear in current OBO files.
- Use JSON `null`, not fake terms such as `none`.
- Mirror `object_ref` values into `string_values`.
- Keep CURIEs in `oterm_refs` and original mapped source labels in
  `string_values`.
- Keep stable unique names synchronized across static TSVs, bricks, process
  files, and audit artifacts.
- Preserve timestamp offsets and source null/suppression semantics.
- For single-location time series, keep location in `array_context`; represent
  row-level provenance as a dimension variable.

## Validation

For static TSVs, validate headers and required values against the current
typedef and resolve every FK by unique name. For ndarrays, run `CheckGeneric`
on every JSON. After load, re-poll CORAL and verify counts, names, relationships,
array shapes, and sampled source values.
