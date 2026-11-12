# Ontology update: soil lime buffer capacity and cation exchange capacity (2026-11-11)

COMO (`context_measurement_ontology.obo/.txt`):

- `ME:0000524 lime buffer capacity` (synonym LBC; unit ME:0000527)
- `ME:0000525 cation exchange capacity` (synonym CEC; unit ME:0000526)
- `ME:0000526 milliequivalent per 100 grams` (meq/100 g), under "units not in UO"
- `ME:0000527 ppm calcium carbonate per pH unit` (ppm CaCO3/pH), under "units not in UO"

First use: `hazen_sediment_chemistry_fwb306_2015` in `coral_import/evo_memory_brick7_20261111`.

`baseline/` holds the files installed before the update, `production/` the files to install on stout and
coral-enigma (`/home/coral/prod/data_import/ontologies/`), followed by `toolx.upload_ontologies()`.

Installed 2026-11-11 on stout and coral-enigma (`/home/coral/prod/data_import/ontologies/`), sha256 obo 317d7d6c…, txt fed71a4e…;
reloaded with `toolx.upload_ontologies()` (three benign UBERON errors only); the four terms verified in `OTerm`. Copied to
`~/src/CORAL/example/enigma/ontologies/`.
