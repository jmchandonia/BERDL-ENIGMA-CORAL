# Prior RB-TnSeq brick conversion investigation

Date: 2026-08-25

## Conclusion

The full fitness matrices are present in the imported CORAL JSON bricks, but
the CORAL CSV export path mis-encodes them before the local BERDL converter or
Spark sees them. The local converter then turns that already incomplete CSV
into one row per condition, drops the gene dimension, and emits two all-null
duplicate measurement columns. This is not a Spark ingestion truncation.

The immediate trigger is that each fitness JSON contains two `typed_values`
(`fit` and `t`) over the real dimensions `(gene, condition)` but has an empty
`array_context`. It therefore lacks CORAL's `data variables type` context
marker. The condition-metadata control brick includes that marker and exports
correctly.

## Evidence chain

### Stored source is complete

The staged source for `Brick0001693`,
`feba_tnseq_fitness_FW300-N2E2.3.ndarray`, has:

- dimensions `[5133, 388]`;
- 5,133 gene and genome dimension values;
- 388 condition and TnSeq-library dimension values; and
- two numeric arrays of 1,991,604 values each, exactly `5133 * 388`.

All 22 source fitness JSON files passed `CheckGeneric`. Their source manifest
contains 16,292,891 cells and one `fit` and one `t` value per cell.

### CORAL CSV export is already incomplete

`download_coral_bricks.py` sends only `{"format":"CSV"}` to
`/coral/brick/<brick_id>` and writes the returned string without slicing it.
The server route calls `_brick_to_csv`, which runs the legacy Java
`ConvertGeneric.sh`/`ConvertGeneric` path.

For `Brick0001693`, the returned CSV still declares `size,5133,388`, but its
data section contains only 776 rows: indices `1..2` by `1..388`. Those rows are
exactly the first gene's 388 `fit` values followed by the first gene's 388 `t`
values from the complete source JSON. It contains no rows for the other 5,132
genes.

The Java export path calls `ConvertHNDArray.isDCFormat`. That method recognizes
a heterogeneous array only when array context contains `Data Variables Type`.
The fitness JSON has no such context, so the array is passed unchanged to the
legacy CSV writer. The resulting CSV shows that the writer interprets the two
typed data variables as an implicit first dimension even though the actual
first dimension contains 5,133 genes.

### The condition-metadata brick is a positive control

`feba_tnseq_condition_metadata_20260813.json` has one real condition dimension,
50 typed data variables, and this array context:

```text
data variables type = Metadata Data <DA:0000004>
```

Its CORAL CSV export has size `[50, 3846]`, and the local converter correctly
merges the implicit variable dimension into a 3,846-row wide table. By
contrast, every fitness JSON has two typed data variables and an empty array
context; its CSV keeps the declared `[gene, condition]` size but contains only
`2 * condition_count` data rows.

### Local conversion compounds the loss

Because the malformed fitness CSV has no explicit `values` line,
`convert_bricks.py` treats dimension 1 as an implicit measurement-variable
dimension and merges rows on dimensions 2 through N. Two separate dimension-1
metadata blocks cause it to append `fit` and `t` columns twice and overwrite
the first block's index mapping. The result has:

- one row per condition, not one row per `(gene, condition)`;
- no gene or genome column;
- two leading all-null measurement columns;
- two numeric columns containing only the first gene's `fit` and `t`; and
- a derived ndarray shape of `[condition_count]` rather than
  `[gene_count, condition_count]`.

The preparation step accepted these files because it checked only that the
four artifacts existed and were nonempty. The manifest then recorded the
incorrect row counts as the expected counts, and later syncs hard-linked and
reused the immutable converted artifacts without reconsidering their shape.

## Audit of all affected bricks

Every current FEBA fitness brick has the same signature. `raw rows` is the
number returned by CORAL's CSV endpoint; `Lakehouse rows` is the prepared TSV
and current table row count. Every prepared table has six columns and zero
nonblank gene/genome/locus columns.

| Brick | Genes | Conditions | Expected cells | Raw rows | Lakehouse rows | Stored converted shape |
|---|---:|---:|---:|---:|---:|---|
| Brick0001675 | 2,394 | 38 | 90,972 | 76 | 38 | `[38]` |
| Brick0001676 | 2,417 | 199 | 480,983 | 398 | 199 | `[199]` |
| Brick0001677 | 4,346 | 115 | 499,790 | 230 | 115 | `[115]` |
| Brick0001678 | 6,384 | 243 | 1,551,312 | 486 | 243 | `[243]` |
| Brick0001679 | 3,935 | 31 | 121,985 | 62 | 31 | `[31]` |
| Brick0001680 | 4,569 | 12 | 54,828 | 24 | 12 | `[12]` |
| Brick0001681 | 4,472 | 12 | 53,664 | 24 | 12 | `[12]` |
| Brick0001682 | 4,317 | 112 | 483,504 | 224 | 112 | `[112]` |
| Brick0001683 | 3,820 | 377 | 1,440,140 | 754 | 377 | `[377]` |
| Brick0001684 | 4,423 | 185 | 818,255 | 370 | 185 | `[185]` |
| Brick0001685 | 4,601 | 146 | 671,746 | 292 | 146 | `[146]` |
| Brick0001686 | 5,559 | 185 | 1,028,415 | 370 | 185 | `[185]` |
| Brick0001687 | 3,144 | 73 | 229,512 | 146 | 73 | `[73]` |
| Brick0001688 | 3,935 | 196 | 771,260 | 392 | 196 | `[196]` |
| Brick0001689 | 4,350 | 116 | 504,600 | 232 | 116 | `[116]` |
| Brick0001690 | 4,336 | 197 | 854,192 | 394 | 197 | `[197]` |
| Brick0001691 | 5,028 | 307 | 1,543,596 | 614 | 307 | `[307]` |
| Brick0001692 | 5,193 | 198 | 1,028,214 | 396 | 198 | `[198]` |
| Brick0001693 | 5,133 | 388 | 1,991,604 | 776 | 388 | `[388]` |
| Brick0001694 | 2,933 | 515 | 1,510,495 | 1,030 | 515 | `[515]` |
| Brick0001695 | 2,946 | 103 | 303,438 | 206 | 103 | `[103]` |
| Brick0001696 | 2,657 | 98 | 260,386 | 196 | 98 | `[98]` |

## Selected repair and staged correction

On 2026-08-25 the project owner selected the CORAL-side repair so the bricks
will export through the same canonical path as other heterogeneous CORAL
bricks. The staged package is:

`coral_import/feba_20260811/fitness_brick_v2_20260825/`

It contains 22 new immutable `_v2.ndarray` bricks. Each adds exactly one array
context property,
`data variables type <ME:0000293> = Gene Knockout Fitness <DA:0000010>`, and
otherwise preserves the scientific payload: data type, two dimensions,
dimension variables, object references, fit values, t values, terms, and
units. The package records a canonical scientific-payload hash for every old
and new pair. All 22 replacements pass `CheckGeneric`, contain 16,292,891 fit
values and 16,292,891 t values, and have one-to-one `Update Data` process rows.

Import the replacement bricks first and validate their CORAL CSV exports before
importing the lifecycle process. Every exported shape must be
`[2, gene_count, condition_count]`, and every converted table must have
`gene_count * condition_count` rows containing both fit and t. The replacement
package was subsequently imported into CORAL and synchronized to BERDL as run
`sync-20260825-113646`; final validation is recorded below.

The generator now enforces the multi-variable array-context marker because
`CheckGeneric` alone does not. The same rule and post-import export-shape gate
are documented in both the repository and live installed versions of the
`coral-ndarray-generation` skill.

## Other repair options considered

### Direct CORAL JSON conversion

Fetch the current immutable brick as JSON and flatten its real dimensions and
typed values directly into a long table with columns for gene, genome,
condition, TnSeq library, `fit`, and `t`. This preserves the existing CORAL
objects and avoids relying on the legacy CSV dialect. The output must have
exactly one row per `(gene, condition)` and retain the original two-dimensional
shape in `ddt_ndarray`.

The locally retained import JSON can be used to develop and test this converter,
but production publication should re-fetch or checksum the current CORAL JSON
so CORAL remains the source of truth.

### CORAL exporter patch

Patch the CORAL CSV export to add/handle an implicit data-variable dimension
when an ndarray has multiple typed data variables over its declared dimensions.
This remains a useful defensive improvement, but it is not required for the
selected replacement-brick repair.

## Required regression gates

Before reloading these tables:

1. Require every typed numeric value array length to equal the product of the
   declared real dimension sizes.
2. Require long-form output row count to equal that same product.
3. Require all declared dimension variables, including gene and condition
   foreign keys, to be present and nonblank.
4. Reject wholly null output columns and shape reduction not explicitly
   requested by the conversion contract.
5. Compare deterministic source/output samples and hashes for both `fit` and
   `t`.
6. Force reconversion and reload of Brick0001675 through Brick0001696. The
   current reuse logic does not invalidate converted artifacts when only the
   converter algorithm changes.
7. Run the benchmark's full 16,292,891-key two-backend equivalence gate before
   marking `rbtnseq_fitness_v1` ready.

## Resolution status (2026-08-25)

CORAL exported all 22 replacements as shape
`[2, gene_count, condition_count]`. Exhaustive raw-CSV and converted-TSV
comparison checked 16,292,891 fit values, 16,292,891 t values, and 189,476
dimension references against the staged source JSON with no differences.

BERDL now contains Brick0001699 through Brick0001720 and no longer contains
the superseded Brick0001675 through Brick0001696 tables. Live verification
found 16,292,891 total rows and zero null rows across the four reference
columns plus fit and t. All row counts and comments match the generated
package, and all 140 scoped foreign-key checks pass.

One additional converter metadata defect was found at the FK gate: the gene
dimension was declared against nonexistent `sdt_gene.sdt_gene_gene_id` even
though its values were correct external gene names. The sync preparation now
normalizes that target to `sdt_gene.sdt_gene_name`; it never targets the
internal `sdt_gene_id`/`Gene00000x` values. Durable evidence is in
`sync-coral-to-berdl/exports/sync-20260825-113646/reports/`:

- `feba_v2_coral_export_validation.json`
- `full_import_verification.json`
- `foreign_key_validation.json`
- `feba_v2_live_validation.json`
- `sync_pipeline_sync-20260825-113646.json`

The conversion incident is resolved. The benchmark's separate two-backend
scientific equivalence gate remains required before declaring the benchmark
itself ready.
