# EVO injection (Memory campaign), FWB-306 sediment chemistry, and the Brick0000007 replacement (2026-11-11)

Built by `tools/build_evo_memory_brick7_coral_import.py`; decisions and evidence in `coral_import/EVO_MEMORY_PLAN_20261111.md`;
ontology terms in `coral_import/ontology_update_20261111_sediment`.

Loaded on the CORAL hub 2026-11-11 (record: `upload_new_data_claude.ipynb`):

| Brick | ID | Shape |
| --- | --- | --- |
| hazen_field_post100ws_v2 (supersedes Brick0000007) | Brick0002178 | 257 samples x 43 variables |
| hazen_sediment_extractable_fwb306_2015 | Brick0002179 | 8 x 2 x 20 |
| hazen_sediment_soil_properties_fwb306_2015 | Brick0002180 | 8 x 2, 10 variables |
| hazen_geochemistry_evo_injection_2017 | Brick0002181 | 58 samples x 23 variables |
| zhou_lab_evo_injection_2009_2017_zOTU_16S | Brick0002182 | 10,216 |
| zhou_lab_evo_injection_2009_2017_zOTU_count | Brick0002183 | 10,216 x 136 |
| zhou_lab_evo_injection_2009_2017_zOTU_taxonomy | Brick0002184 | 10,216 x 7 |

Static records added: 76 Samples, 136 Communities, 169 Reads, 2,086 OTUs, 58 Taxa, 2 Protocols. Processes: 76 Sampling,
136 Filter, 169 16S Sequencing, 1 Classify OTUs, 2 Assay Geochemistry, 1 Update Data.

Sample moves (`hub/apply_sample_moves.py`): the 14 samples at GP01-30 and GP03-29 moved to GP01-18 and GP03-19 (location,
depth, Sampling process input and its edge); the twelve 2017-2018 EVO samples renamed `GP01-30-*` -> `GP01-18-*`,
`GP03-29-*` -> `GP03-19-*`.

Lesson from the load: renaming a static object also needs its `SYS_ObjectTypeID` entry (`upk_id`) updated, or CORAL cannot
resolve the new name. The first run missed this, so 18 Filter processes failed; the index was fixed with
`hub/apply_sample_name_index.py` and those 18 were loaded from `process/process_filter_evo_remaining_20261111.tsv`. The
template `tools/templates/evo_sample_moves_hub.py.tmpl` now updates the index as part of the move.

Follow-up: the isolate bricks still carry GP01-30 / GP03-29 for strains isolated from `GP01-033115` and `GP03-033115`
until the next isolate update.
