# Ontology update ME:0000506 to ME:0000512 (2026-10-16)

Seven new terms in `context_measurement_ontology` for LC-MS metabolomics feature
tables, needed by the batch C1 package (`coral_import/spring2019_batch_c1_20261016`):

| ID | Name | Type | Parent | Units |
| --- | --- | --- | --- | --- |
| ME:0000506 | retention time | float | measurement | time units |
| ME:0000507 | m/z (synonym mass-to-charge ratio) | float | measurement | dimensionless unit |
| ME:0000508 | spectral library compound name | string | molecule | |
| ME:0000509 | spectral library match ID | string | chemical context | |
| ME:0000510 | spectral match score | float | measurement | dimensionless unit |
| ME:0000511 | adduct | string | chemical context | |
| ME:0000512 | MS1 feature area (synonym peak area) | float | measurement | dimensionless unit |

`production/` holds the edited `context_measurement_ontology.obo` (7 added stanzas)
and `.txt` (8 added lines, including the m/z alias); `baseline/` holds the live files as of 2026-10-16;
`TERMS.tsv` lists the terms with definitions. Every brick of the batch C1 package
passes CheckGeneric against a staged copy of the production ontology directory with
this update applied.

Install (run as the owner of `/home/coral/prod/data_import/ontologies`):

```bash
coral_import/ontology_update_20261016/install_me0000506_0000512.sh
```

The script checks the pre-install hashes, keeps copies of the replaced files in
`baseline/`, installs the two files, verifies their hashes and the new IDs, and runs
the production CheckGeneric on all 14 package bricks. As with the ME:0000505 install
(2026-09-08), the install is this file copy; import the batch C1 package after it.

Retention time, m/z and MS1 feature area follow the PSI-MS controlled vocabulary and carry OBO cross-references to it (`xref: MS:1000894`, `MS:1000040`, `MS:1001844`). PSI-MS and IUPAC deprecate the name mass-to-charge ratio (kept as a related synonym) and the unit thomson, so m/z is dimensionless. The CORAL loader reads only `Ref:` and `ORef:` xrefs as reference types, so these external xrefs do not change how the terms are typed. The other four terms have no PSI-MS equivalent (PSI-MS MS:1000353 adduct ion names an ion, not adduct notation).
