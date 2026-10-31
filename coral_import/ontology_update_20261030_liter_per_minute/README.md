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
2. **Lakehouse**: no immediate action, and a plain re-sync would be a no-op for
   this term. `enigma.coral.sys_oterm` (table comment "Ontology terms used in
   CORAL") is built by `sync-coral-to-berdl` from CURIEs that appear in
   `enigma.coral` `*_sys_oterm_id` columns only — it is a reference-derived
   projection, not the full ontology (e.g. the parent `UO:0000270` is not in it
   today). `ME:0000517` is not referenced by any `enigma.coral` object yet, so
   it enters `sys_oterm` automatically at the first sync *after* a CORAL object
   uses it — i.e. the Dec-2026 sso_staging -> CORAL brick conversion. Until then
   the durable record is the hub OTerm (step 1).
   - `enigma.sso_staging.ddt_brick` does not depend on this: it stores the unit
     id **and** name inline (`unit_sys_oterm_id` / `unit_sys_oterm_name`, no FK),
     so it is self-describing.
   - If the term must be visible in `enigma.coral.sys_oterm` before conversion,
     force-ingest two rows (`ME:0000517` + its parent `UO:0000270`) — but a
     later full sync rebuilds `sys_oterm` from references and drops unreferenced
     rows, so this is a temporary patch, not durable.

After install, `sso_schema.py` carries `ME:0000517` for `liter per minute`
(no longer null) in the sso_staging `ddt_brick`.
