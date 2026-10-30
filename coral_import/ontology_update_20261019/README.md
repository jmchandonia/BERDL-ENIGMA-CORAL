# Ontology update ME:0000513 to ME:0000515 (2026-10-19)

Three new terms in `context_measurement_ontology`, needed by the Fields Lab biomass
production brick of the batch C2 package (`coral_import/spring2019_batch_c2_20261019`):

| ID | Name | Type | Parent | Units |
| --- | --- | --- | --- | --- |
| ME:0000513 | nanogram per milliliter per day (synonym ng/mL/day) | unit | units not in UO; UO:0000280 rate unit | |
| ME:0000514 | biomass production rate (related synonym heterotrophic production) | float | rate | nanogram per milliliter per day |
| ME:0000515 | time since sample collection | float | measurement | time units |

UO has nanogram per milliliter but no per-day rate unit. The existing `rate` term
(ME:0000264) is not a valid dimension variable, and every data variable of a
heterogeneous brick must be one, so the rate is a new microtype under `rate`.
The existing `activity` term (ME:0000143) is boolean. `time since sample collection`
is the dimension of incubations started 24 h and 48 h after collection; `time since
inoculation` (ME:0000081) means time after inoculating a culture, and `time elapsed`
(ME:0000122) is not a valid dimension variable.

`production/` holds the edited `context_measurement_ontology.obo` (3 added stanzas)
and `.txt` (6 added lines); `baseline/` holds the live files as of 2026-10-19, which
already include ME:0000506-ME:0000512; `TERMS.tsv` lists the terms with definitions.
Every brick of the batch C2 package passes CheckGeneric against a staged copy of the
production ontology directory with this update applied.

Install (run as the owner of `/home/coral/prod/data_import/ontologies`):

```bash
coral_import/ontology_update_20261019/install_me0000513_0000515.sh
```

The script checks the pre-install hashes, keeps copies of the replaced files in
`baseline/`, installs the two files, verifies their hashes and the new IDs, and runs
the production CheckGeneric on all 7 package bricks. Import the batch C2 package after it.
