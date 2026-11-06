# Ontology update: Robertson soil behavior type ontology and ton per square foot (2026-11-04/05)

## New ontology `robertson_soil_behavior_type.obo` (prefix `SBT`, 27 terms)

- `SBT:0000001 soil behavior type` (under COMO root ME:0000001) > `SBT:0000002 soil behavior type classification`:
  the microtype (`data_type oterm_ref`, valid data variable / dimension / dimension variable / property,
  `xref: ORef:SBT:0000002`, so its values are its descendants).
- `SBT:0000010 Robertson 1986 soil behavior type`: zones 0-12 as `SBT:0000011`-`SBT:0000023`, named
  `<label> (Robertson 1986 zone N)`, with `zone_number` and the USCS group as a RELATED synonym.
- `SBT:0000030 Robertson 1990 normalized soil behavior type`: zones 1-9 as `SBT:0000031`-`SBT:0000039`.
- `.txt` companion in the hand-edited tree format of the other small ontologies.

Registered in the hub's `/home/coral/prod/modules/var/upload_config.json` (entry `sbt`, backup
`upload_config.json.bak-20261105`), in `tools/java/gov/lbl/enigma/app/CheckGenericProduction.java`, in the
sync's `coral_metadata.py` (`CANONICAL_ONTOLOGY_BY_PREFIX["SBT"]`, `FULL_INCLUDE_ONTOLOGIES`) and in the
scratchpad `sync_prep.sh` copy list.

## COMO: `ME:0000518 ton per square foot` (synonym tsf), under `units not in UO` and `UO:0000109`

First use: `coral_import/cpt_physical_20261105` (Fugro CPT profiles; soil behavior type as oterm_ref values).

| File | Before (baseline/) | After (production/) |
| --- | --- | --- |
| context_measurement_ontology.obo | 37240d8e47d24b59c38ffe368b178ce1bd5462e6652885fa071064899b664129 | 2b046c334b7092bd6147f2ad243ee2890a0761441eec57159c85e1dd3265109e |
| context_measurement_ontology.txt | 1531ca9e24f96ccb9eb541f43fed17308f7eb78af332f74f719ba842cec31a92 | b1160df71aaa220f776720454df7efc1859f9b2139855bb9f6d01a3425f3dacc |
| robertson_soil_behavior_type.obo | (new) | 7a6b722f8131e3af26b58e0530bd804a4fd6d152b3f699ecbe37e7ce05c2d011 |
| robertson_soil_behavior_type.txt | (new) | 50223fba260d0cbb18b39157b97f620d1e6df7b672cdef66bbaff0c9954656be |

2026-11-05: installed in `/home/coral/prod/data_import/ontologies/` on stout and coral-enigma (hashes verified on
both), reloaded with `toolx.upload_ontologies()` from `upload_new_data_claude.ipynb` ("Doing ontology: sbt"; only
the three expected aro/UBERON duplicate-index errors); OTerm holds all 27 SBT terms (SBT:0000002 is_microtype,
oterm_ref, valid values parent SBT:0000002) and ME:0000518. Log: `reports/hub_import_log.txt`.
