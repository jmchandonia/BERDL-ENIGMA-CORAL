# Ontology update: time elapsed as a dimension variable (2026-10-28)

`time elapsed` (ME:0000122) gains `is_valid_dimension` and `is_valid_dimension_variable`, like its
sibling `time since sample collection` (ME:0000515), so in-situ deployment lengths (the 2019 bug
traps, `coral_import/27ws_bug_traps_20261027`) can be recorded as time elapsed rather than
`time since inoculation`, which describes cultures. In the `.txt` hierarchy the line gains the
`*` dimension-variable marker. No terms are added.

| File | Before (baseline/) | After (production/) |
| --- | --- | --- |
| context_measurement_ontology.obo | 2a254f15b1835d4a4300cb68c1037fa001251b117ccfc916772a686f1593da79 | 75f9ed58cc6c9158368c2226aa40be6f0812b40898cd191379c55130d57ec77f |
| context_measurement_ontology.txt | 4934eb6bcf548b9a011abab1244efd79035d5b3c3027e29e6c0389a0294f571b | 193ff72d25a17438ce1e41167266ab8926b745dbd579c4dcdc90d57e96e27a87 |

Installed on stout (`/home/coral/prod/data_import/ontologies/`) 2026-10-28, hashes verified.
Still to do: copy the two files to coral-enigma.jmcnet's ontologies directory and reload the
ontology there.

2026-10-28: copied to coral-enigma.jmcnet (hashes verified) and reloaded with
`toolx.upload_ontologies()` from the record notebook `upload_new_data_claude.ipynb` (config skips
the large ontologies). OTerm now has ME:0000122 is_dimension/is_dimension_variable = true. Three
expected `cannot index term` errors: UBERON terms bundled in aro that already exist from envo.
Log: `reports/hub_import_log.txt`.
