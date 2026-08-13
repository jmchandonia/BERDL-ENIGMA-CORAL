# FEBa CORAL import implementation

This directory is the resume-safe implementation workspace for
`FEBA_CORAL_IMPORT_PLAN.md`. The source review covers the 25 private
`enigma.fitprivate` organisms in `matched_organisms.tsv`, but the approved
import scope is restricted to the 22 ENIGMA isolate strains. Btheta
(`Bacteroides thetaiotaomicron VPI-5482`), Keio (`Escherichia coli BW25113`),
and Putida (`Pseudomonas putida KT2440`) are explicitly excluded as reference
or laboratory strains.

## Current state

Phase 0 source inventory and canonical source fingerprints are complete.
Live CORAL strain validation and the active/withdrawn EDR inventory are
complete for the narrowed 22-strain scope. Exact comparison of 53 historical
candidate versions found no reusable exact assembly/annotation pair. Local
FASTA/GFF exports for all 22 proposed new versions are complete and validated,
and the inspectable production checkout is staged under
`production_checkout_20260812/`. On 2026-08-13 the project owner reported that
all CORAL package static types, bricks, producing processes, and the deferred
N2E2 replacement process were imported. A live post-import audit remains
required before treating those relationships and counts as independently
verified.

The exhaustive annotation-only audit also compared every one of the 53
same-strain EDR GFF files, including active and withdrawn versions. It found
zero exact annotation matches. See
`phase1/live_edr_20260811/edr_all_candidate_annotation_comparison_report.json`.

Generated files under `phase0/`:

- `feba_organism_work_manifest_20260811.tsv`: one row per source organism,
  including source counts, three canonical genome fingerprints, reviewed CORAL
  strain mapping, and resumable workflow status fields;
- `feba_strain_rollup_20260811.tsv`: one row per target CORAL strain;
- `feba_library_crosswalk_20260811.tsv`: all 34 in-scope source library labels, their
  experiment counts, and approved `primers_model` assignments;
- `feba_phase0_metadata_20260811.json`: immutable source identity, output names,
  and reconciled totals.

The approved model decisions are stored in
`config/tnseq_library_model_assignments_20260811.tsv`. The builder requires an
exact one-to-one match between the 34 in-scope assignments and selected source
library labels. Historical assignments for the three excluded organisms remain
in that evidence file but are ignored by the builder. The required scope gate
is `config/feba_enigma_isolate_scope_20260811.tsv`.

## Rebuild Phase 0

```bash
python3 tools/build_feba_phase0_manifest.py \
  --database /scratch/jmc/fitprivate-rbtnseq/source/feba.db \
  --crosswalk /scratch/jmc/fitprivate-rbtnseq/config/matched_organisms.tsv \
  --scope coral_import/feba_20260811/config/feba_enigma_isolate_scope_20260811.tsv \
  --library-models coral_import/feba_20260811/config/tnseq_library_model_assignments_20260811.tsv \
  --output-dir coral_import/feba_20260811/phase0 \
  --run-date 20260811 \
  --database-sha256 6b9e4edce230b2f82bff90242fe9ca46219598905d2eb775ab4f16ea446a1f11
```

The builder rewrites source-derived fields atomically and preserves existing
manual/live progress columns by `fitprivate_orgId`. Canonical fingerprints use
normalized uppercase scaffold sequences and length-framed, deterministically
ordered annotation records.

## Validation completed

- SQLite size: `30,529,265,664` bytes;
- SQLite SHA-256 independently rechecked on 2026-08-11:
  `6b9e4edce230b2f82bff90242fe9ca46219598905d2eb775ab4f16ea446a1f11`;
- 22 organisms and 22 distinct CORAL strains;
- 411 scaffolds and 122,466,056 bases;
- 110,899 source gene rows and 55,261 cross-reference rows;
- 3,846 experiments and 16,292,891 gene-fitness rows;
- 34 distinct `(orgId, mutantLibrary)` pairs, all with a nonblank model;
- all 22 assembly, structural-annotation, and metadata-annotation fingerprints
  are populated and unique.

The source contains undocumented `Gene.type` values beyond the SQLite schema
comment: type 3 is 16S rRNA, type 4 is 5S rRNA, and type 8 is other small RNA.
They are represented as `rRNA`, `rRNA`, and `ncRNA`, respectively. The earlier
review also identified a non-triplet Keio `prfB` feature, but Keio is now
outside the approved import scope.

## Next action

Re-poll CORAL and validate the imported static counts, unique names, foreign
keys, all 23 brick shapes and representative values, producing-process edges,
and the N2E2 replacement edge. Confirm that `tnseq_n2e2.ndarray` is obsolete
in favor of `feba_tnseq_fitness_FW300-N2E2.3.ndarray`. Then perform the scoped
CORAL-to-BERDL sync and foreign-key audit described in
`FEBA_CORAL_IMPORT_PLAN.md`.

The local handoff package already contains `genome_annotations/`, the 22
manifest rows, a four-source active/withdrawn version audit, package checksums,
and a self-contained `genomes_from_feba/` recorder directory. Its default
`genomes_to_record.tsv` lists all 22 genomes and the `evidence/` subdirectory
contains the active/withdrawn manifest snapshots plus the version inventory
and export preflight. Validate the package without external paths with:

```bash
cd coral_import/feba_20260811/production_checkout_20260812
python3 genomes_from_feba/record_feba_genomes_260812.py --check-only
```

The handoff is ignored by Git because it contains about 160 MB of generated
genome files intended for manual inspection and production transfer.

The repository contains the pre-publication EDR evidence, but EDR publication
itself should still be independently verified against production before the
final CORAL/BERDL audit is closed.
