# Ontology update: `liter per minute` flow-rate unit (2026-10-30)

Adds one term to the ENIGMA context measurement ontology (COMO) so the SSO
fall-2026 pump flow-rate column in `enigma.sso_staging.field_metadata`
(`rate_instrument_pump_liter_per_minute`, microtype `rate` + `instrument=pump`)
has a real unit term instead of a null oterm id.

| New term | |
| --- | --- |
| id | `ME:0000517` (next free; live max was `ME:0000516` `baseline control`) |
| name | `liter per minute` |
| synonyms | `litre per minute` (EXACT), `L/min` (EXACT) |
| is_a | `ME:0000294` (`units not in UO`) and `UO:0000270` (`volumetric flow rate unit`) |

Modeled exactly on `parts per million by volume` (`ME:0000348`): a leaf unit
under `units not in UO`, cross-linked to its UO class. No `property_value`
lines — unit leaves carry none (cf. ppmv, `nanogram per liter`). UO already has
`microliters per minute`; `liter per minute` was chosen over it to avoid ugly
magnitudes (field pump rates are ~0.1–15 L/min).

## Baseline → production

`baseline/` is a verbatim copy of the live stout prod ontology
(`/home/coral/prod/data_import/ontologies/context_measurement_ontology.{obo,txt}`,
mtime 2026-10-28, which already includes `time elapsed` dimension flags and
`baseline control`). `production/` adds the one term to both files.

| File | baseline sha256 | production sha256 |
| --- | --- | --- |
| context_measurement_ontology.obo | 25e81da58d7123d2e4d00b421984807531393402a4d66fd9b1f6bd2ed78076ac | 37240d8e47d24b59c38ffe368b178ce1bd5462e6652885fa071064899b664129 |
| context_measurement_ontology.txt | 49278cb92f7dad7aef3a713b4f044b6581ce2a8b0334e24fcf4bb9790ee7944f | 1531ca9e24f96ccb9eb541f43fed17308f7eb78af332f74f719ba842cec31a92 |

ME term count: 505 → 506.

## Install (shared-system steps)

1. **Hub OTerm** (durable source of truth; `sys_oterm` on the lakehouse is
   regenerated from it):
   - copy `production/context_measurement_ontology.{obo,txt}` to
     `/home/coral/prod/data_import/ontologies/` on stout **and** on
     coral-enigma.jmcnet (verify hashes);
   - run `toolx.upload_ontologies()` from the record notebook
     `upload_new_data_claude.ipynb` on the coral-enigma hub (config skips the
     large ontologies). Confirm `OTerm` has `ME:0000517`. The three expected
     `cannot index term` UBERON/aro warnings are benign.
2. **Lakehouse**: re-export CORAL and sync the `sys_oterm` table into
   `enigma.coral` via `sync-coral-to-berdl` (the exporter pulls in the
   `UO:0000270` parent automatically). Confirm `ME:0000517` and `UO:0000270`
   are in `enigma.coral.sys_oterm`.

After install, `sso_schema.py` carries `UO`/`ME` id `ME:0000517` for
`liter per minute` (no longer null).
