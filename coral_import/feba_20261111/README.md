# FEBa update 2026-11-11 (fitprivate release 2026-10-21)

Incremental update of the FEBa (fitprivate) data in CORAL, following `FEBA_CORAL_IMPORT_PLAN.md`.
Built by `tools/build_feba_update_coral_import.py`, which compares the snapshot already in CORAL
(`/scratch/jmc/fitprivate-rbtnseq/source/feba.db`, 2026-07-14) with the new one
(`source/feba_20261022.db`, SHA-256 `5985a55b0354cf3fd0a7700763631be0452dd19153503a7b3cf1ae53ef8a1142`)
and stages only what changed. Loaded into production CORAL on 2026-11-11 with the hub scripts
of the `update-enigma-isolates` skill; every run is in the hub notebook `upload_new_data_claude.ipynb`.

## What changed

Scope is 23 ENIGMA isolates (the 22 of August plus Sphingo3); 17 are unchanged and produced nothing.

| fitprivate orgId | Action | CORAL result |
| --- | --- | --- |
| Sphingo3 | new organism | Genome0007818 `GW456-12-10-14-TSB1.4`, 4,967 Genes, TnSeq_Library0000070 (`model_pTGG37_NN1`), Brick0002176, Assay Fitness Process0223428 |
| Brev2 | 38 -> 60 experiments | Brick0001699 -> Brick0002171 (`_v3`) |
| Janthino_FHT05C05 | 12 -> 29, existing values recomputed | Brick0001704 -> Brick0002172 |
| Janthinobacterium_agari | 12 -> 27, existing values recomputed | Brick0001705 -> Brick0002173 |
| MT049 | 112 -> 242 (1 removed), existing values recomputed | Brick0001706 -> Brick0002174 |
| MT058 | 377 -> 490 | Brick0001707 -> Brick0002175 |
| condition metadata | 3,846 -> 4,179 conditions | Brick0001674 -> Brick0002177 (`feba_tnseq_condition_metadata_20261111`) |

334 Condition objects were added. The Condition for the one removed MT049 experiment stays in CORAL
but is no longer referenced by a current brick. Replacements are recorded as one-to-one `Update Data`
processes (Process0223429-0223434).

## New genome

The Sphingo3 assembly is sequence-identical to EDR `GW456-12-10-14-TSB1.1`, but the FEBa annotation
(4,967 features) differs from that version's Prodigal annotation, so under the exact-pair rule a new
version was allocated: `.4` (versions 1-3 active, none withdrawn, checked on niya). The FASTA and GFF
from `tools/export_feba_genome.py` are in `edr_checkout/` and were copied to niya's EDR master
(`genome_processing/GW456-12-10-14-TSB1/assembliesAndAnnotations/GW456-12-10-14-TSB1.4/`) with one
manifest row appended. The dipa copy, the local copy and the MinIO mirror were not updated here.

`Sphingo3_ML4` is `pTGG37_NN1` in the mutant-library mastersheet (direct row).

## Layout

- `config/`: scope, genome names, library models and current brick names given to the builder.
- `coral_package_20261111/`: static TSVs, brick JSON, process TSVs, reports, checksums.
- `hub/`: read-only preflight and verification probes, and the three import stages.
- `reports/`: hub import log and probe outputs.

## Load order used

1. `hub/preflight_feba_update_20261111.py` (read-only): no name collisions; referenced genes,
   conditions and libraries present; replaced bricks current.
2. `hub/import_stage1_static.py`, then `hub/verify_stage1.py`.
3. `hub/import_stage2_bricks.py`, then `hub/verify_bricks.py`.
4. `hub/import_stage3_update_data.py`, then `hub/verify_bricks.py` again.

## Lakehouse sync

Sync `sync-20261111-183230` published the update to `enigma.coral`: 16 tables imported, the six superseded brick
tables dropped, 81 of 81 foreign keys passing. The exported fitness bricks have the full gene-by-condition shape and
match the fitprivate source, and all 4,179 metadata-brick conditions resolve in `enigma.fitprivate.experiment`.

## Still to do

- Replicate the new genome directory and manifest row to dipa, the local EDR copy and MinIO.
