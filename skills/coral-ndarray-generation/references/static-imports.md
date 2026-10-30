# CORAL Static-Object Import TSVs

## Source of truth

Use the current CORAL typedef, preferably from the live CORAL application or a
fresh `sys_typedef` export. Determine for each property:

- `field_name`: literal header accepted by the entity loader;
- required/optional status;
- primary-key and unique-key status;
- foreign-key target type and target unique property;
- scalar/list type and validator constraints.

Do not derive import headers from BERDL table columns, `cdm_column_name`,
generated schema names, or an older package.

## Addition contract

For a new object TSV:

1. Omit an auto-assigned primary-key `id`.
2. Include every required non-PK property.
3. Use each property's exact `field_name` as the header.
4. For FKs, write the target object's stable unique name, not its assigned ID.
5. Include optional properties only when the current loader accepts their
   missing-value representation.
6. Validate exact headers and every required cell before delivery.
7. Resolve all FK values against previously imported or same-package objects.

## Current ENIGMA example

This mapping reflects the typedef checked for the 2026-08-13 FEBa package and
must be rechecked if the schema changes:

| Type | Addition headers | Required non-PK fields |
| --- | --- | --- |
| `Genome` | `name`, `strain`, `n_contigs`, `n_features`, `link` | `name`, `n_contigs`, `n_features`, `link` |
| `Gene` | `gene_id`, `genome`, `aliases`, `contig_number`, `strand`, `start`, `stop`, `function` | `gene_id`, `genome`, `contig_number`, `strand`, `start`, `stop` |
| `Condition` | `name` | `name` |
| `TnSeq_Library` | `name`, `genome`, `primers_model`, `n_mapped_reads`, `n_barcodes`, `n_usable_barcodes`, `n_insertion_locations`, `hit_rate_essential`, `hit_rate_other` | `name`, `genome`, `primers_model` |

The consequential distinctions are:

- Genome uses `strain`, not `strain_id`.
- Gene uses `gene_id`, not `name`.
- Gene and TnSeq Library use `genome`, not `genome_id`.

## Sample names

ENIGMA sample names may contain only capital letters, digits and dashes
(`^[A-Z0-9-]+$`): no lower-case letters, underscores, spaces, periods or other
punctuation. Convert source labels accordingly (`L7_SZ2` becomes `L7-SZ2`,
`Metals` becomes `METALS`). About 95 legacy samples from before this rule
(for example `FW106-11-13-12 timepoint 2`) break it; do not rename them, and
do not copy their style.

Never invent a sample identifier silently. When the field team's sample sheet
(for example the Hazen Lab metadata workbooks) gives the sample a name, use that
name verbatim as long as it matches `^[A-Z0-9-]+$`, even if it follows a different
convention from neighboring datasets; map lab-internal IDs (sequencing or
analysis IDs) to it rather than inventing one. Ask the user before recording
those internal IDs in CORAL names, descriptions or brick comments; by default
leave them out, since they confuse users, but there may be a reason to keep them. Only when no recorded name exists,
build one from facts and the prevailing convention for that sample type, and
report the choice for approval.

Two SSO conventions coexist. Campaign samples since 2023 (initial well
characterization, 2024 pump test, 2024 pilot time series) use
`WELL-ZONE-YYYYMMDD-ASSAY`, one sample per assay bottle
(`U2-SZ1-20240313-METALS1`, `L7-SZ1-20240909-ICTOC`, `U1-SZ1-20240909-NH3NO2`).
One-off samplings and the 2025 pump test 2 onward use the field sheet's
date-first names (`20240529-M5-SZ2-F8`, `20250922-U2-SZ2-AODC`). Filtered
fractions append the filter code (`...-F01`, `...-F8`) in both.

## Preflight

- Header list exactly equals the approved typedef-field list.
- No undeclared property appears.
- Every required non-PK cell is nonblank and is not `null`/`nan`.
- Sample names match `^[A-Z0-9-]+$`.
- Unique-name columns have no duplicates within the TSV or collisions with
  unintended live objects.
- Every FK value resolves by target unique name.
- Assigned-ID patterns such as `Gene0000001` do not appear in staged additions
  or brick references.
- Static files import in dependency order; after each phase, re-poll CORAL and
  verify counts, names, and FKs before loading dependent bricks.

## Diagnosing loader errors

- `undeclared property`: the header is not a typedef `field_name`.
- `required property ... absent`: a required header is missing or was supplied
  under an alias.
- `KeyError` naming a property: the loader expected that literal typedef field
  for unique-key lookup or validation.

Do not address these by adding both alias variants. Replace the wrong header
with the current typedef field name and rerun the full preflight.
