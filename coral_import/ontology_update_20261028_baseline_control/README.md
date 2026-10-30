# Ontology update: baseline control, ME:0000516 (2026-10-28)

New child of `control` (ME:0000283), beside negative, positive, low and high control:

- name: baseline control; string microtype like its siblings
- def: Material or system measured before a treatment, incubation or deployment begins, and used as
  the reference state against which changes are assessed; it is not subtracted as a background. Use
  for reference material that is not itself a sample or community on the experiment's time axis.
- synonyms: starting material control (EXACT), background control (RELATED), time-zero reference (RELATED)

First use: the starting sediment of the 2019 bug traps (`coral_import/27ws_bug_traps_20261027`).

| File | Before (baseline/) | After (production/) |
| --- | --- | --- |
| context_measurement_ontology.obo | 75f9ed58cc6c9158368c2226aa40be6f0812b40898cd191379c55130d57ec77f | 25e81da58d7123d2e4d00b421984807531393402a4d66fd9b1f6bd2ed78076ac |
| context_measurement_ontology.txt | 193ff72d25a17438ce1e41167266ab8926b745dbd579c4dcdc90d57e96e27a87 | 49278cb92f7dad7aef3a713b4f044b6581ce2a8b0334e24fcf4bb9790ee7944f |

2026-10-28: installed on stout and coral-enigma (hashes verified on both), reloaded with
`toolx.upload_ontologies()` from `upload_new_data_claude.ipynb`; OTerm has ME:0000516. Only the three
expected aro/UBERON duplicate-index errors. Log: `reports/hub_import_log.txt`.
