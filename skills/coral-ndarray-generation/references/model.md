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
- When `typed_values` contains more than one measured variable, mark the array
  as heterogeneous with exactly one array-context scalar property:

  ```json
  {
    "value_type": {
      "term_name": "data variables type",
      "oterm_ref": "ME:0000293",
      "oterm_name": "data variables type"
    },
    "value": {
      "scalar_type": "oterm_ref",
      "oterm_ref": "<the ndarray data_type CURIE>"
    }
  }
  ```

  CORAL uses this marker to add the leading data-variable axis during CSV
  export. Its value must match the top-level `data_type.oterm_ref`.
- For single-location time series, keep location at array level.
- For shared depth, store depth once at array level. For mixed depths, describe
  the channel/screen distinction without inventing an ambiguous bare depth.
- Make depth reference endpoints explicit.
- Keep row-level provenance aligned as a dimension variable.
- Preserve timestamp timezone offsets and DST-distinguishable observations.

## Compound microtypes

A variable's primary term (its `value_type`) is the thing actually measured or
computed; the context terms that follow only qualify it. A statistic is
therefore primary, and its context says what it is a statistic of:

- Standard deviation of a concentration: `standard deviation <ME:0000149>`;
  `measurement <ME:0000120>` = `concentration <ME:0000129>`, in the
  concentration's unit; not `concentration` with `statistic` = `standard
  deviation`.
- Coefficient of variation of AODC cell counts: `coefficient of variation
  <ME:0000358>`; `measurement` = `count <ME:0000126>`; `category` = `cell`.
- Mean cells per microscope field: `average <ME:0000147>`; `measurement` =
  `count`; `category` = `cell`.

Always name the measured quantity for `standard deviation`, `average`,
`coefficient of variation` and other statistics; a bare statistic with only a
unit is ambiguous. The `measurement` context takes any term under
`measurement <ME:0000120>` as its value (concentration, count, ion intensity,
...). Older bricks such as `adams_metals_27ws` used the reverse order
(`concentration`; `statistic` = `standard deviation`); do not copy it.

Use a specific microtype rather than a near miss: retention time is not
`time series`, and an observed m/z is not `mass` or `exact mass` (a property of
a reference compound). When no term fits, propose a new ontology term rather
than overloading `description` or `comment`.

## Common pitfalls

- Using stale ontology labels.
- Omitting numeric units.
- Making a qualifier the primary term, such as `concentration` with
  `statistic` = `standard deviation` instead of `standard deviation` with
  `measurement` = `concentration`.
- Failing to mirror `object_ref` values.
- Filling ID fields with unregistered source strings.
- Reusing stale `.check` files.
- Using BERDL/CDM aliases as CORAL static-import headers. Static TSVs require
  the typedef's literal `field_name`; these names may differ from generated
  database columns and from intuitive names.
- Treating the auto-assigned primary-key `id` as a value that must be staged.
- Omitting `data variables type <ME:0000293>` from a multi-variable ndarray.
  `CheckGeneric` can still pass, but CORAL may export only the declared
  dimensions and collapse or lose values from the implicit variable axis.

## Validation

Run `gov.lbl.enigma.app.CheckGeneric` after generation and overwrite `.check`
files after any JSON or filename change. For heterogeneous arrays, separately
verify that the exported shape begins with the number of measured variables.
Independently validate static TSVs against the current typedef as described in
`static-imports.md`.
