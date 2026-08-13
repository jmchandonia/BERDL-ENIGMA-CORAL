# CORAL Generic Ndarray Model

## Minimal shape

A CORAL generic ndarray normally contains `name`, `description`, `data_type`,
`array_context`, `dim_context`, typed dimension variables, and measured array
values. Dimensions must match the actual array shape.

## Value typing

### `object_ref`

Use for a concrete imported object. Put the stable unique name in
`object_refs` and mirror it in `string_values`. Do not use a future
CORAL-assigned primary key.

### `oterm_ref`

Use for ontology terms. Put CURIEs in `oterm_refs` and the original mapped
source labels in `string_values`.

### Numeric values

Every numeric variable must have an explicit unit, including dimensionless
scales when an appropriate UO term exists.

## Context and dimensions

- Keep array-wide constants in `array_context`.
- For single-location time series, keep location at array level.
- For shared depth, store depth once at array level. For mixed depths, describe
  the channel/screen distinction without inventing an ambiguous bare depth.
- Make depth reference endpoints explicit.
- Keep row-level provenance aligned as a dimension variable.
- Preserve timestamp timezone offsets and DST-distinguishable observations.

## Common pitfalls

- Using stale ontology labels.
- Omitting numeric units.
- Failing to mirror `object_ref` values.
- Filling ID fields with unregistered source strings.
- Reusing stale `.check` files.
- Using BERDL/CDM aliases as CORAL static-import headers. Static TSVs require
  the typedef's literal `field_name`; these names may differ from generated
  database columns and from intuitive names.
- Treating the auto-assigned primary-key `id` as a value that must be staged.

## Validation

Run `gov.lbl.enigma.app.CheckGeneric` after generation and overwrite `.check`
files after any JSON or filename change. Independently validate static TSVs
against the current typedef as described in `static-imports.md`.
