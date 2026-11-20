# Ontology update: flow rate (2026-11-17)

COMO (`context_measurement_ontology.obo/.txt`):

- `ME:0000528 flow rate` (volume of fluid per unit time; units under UO:0000270 volumetric flow rate unit, e.g. ME:0000517 liter per minute)

First use: `hazen_pump_log_sso_pump_test_2025` in `coral_import/monitoring_update_20261117` (flow rate, instrument = pump).

`baseline/` holds the files installed before the update, `production/` the files to install on stout and
coral-enigma (`/home/coral/prod/data_import/ontologies/`), followed by `toolx.upload_ontologies()`.
