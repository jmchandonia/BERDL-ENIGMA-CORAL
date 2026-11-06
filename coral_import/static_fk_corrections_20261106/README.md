# CORAL static foreign-key correction (2026-11-06)

`SDT_Assembly` `Assembly0000241` (`MT66-resequenced.contigs`, KBase 39899/MT66-resequenced.contigs) has
`strain = "MT66-resequenced"`, a Strain that does not exist. The other copies of the same object
(`Assembly0001356`, `Assembly0002201`) and the Genome counterpart (`Genome0000241`, corrected on
2026-10-01 in `static_fk_corrections_20261001`) use `MT66`. Found by the scoped foreign-key audit of
sync-20261106-140801, which reloaded `sdt_assembly` (CORAL int -> BIGINT schema change).

`01_preflight.aql` (read-only), `02_update_assembly_strain.aql` (guarded, one row), `03_verify.aql`
(read-only), run on the CORAL hub as in October; then re-export the static tables and resume the sync.

2026-11-06: applied with the user's OK through `services.arango_service.find` in a hub session kernel
(recorded in `upload_new_data_claude.ipynb`): `{'id': 'Assembly0000241', 'old_strain': 'MT66-resequenced',
'new_strain': 'MT66'}`; verify: assembly_ok = True, orphan_assembly_rows = 0.
