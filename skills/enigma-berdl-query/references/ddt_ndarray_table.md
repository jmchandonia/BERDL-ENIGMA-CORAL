# Table: enigma_coral.ddt_ndarray

**Description:** Dynamic Data Types (N-Dimensional Arrays)

## Schema

| Column Name | Data Type | Nullable |
|-------------|-----------|----------|
| ddt_ndarray_id | string | Yes |
| ddt_ndarray_name | string | Yes |
| ddt_ndarray_description | string | Yes |
| ddt_ndarray_metadata | string | Yes |
| ddt_ndarray_type_sys_oterm_id | string | Yes |
| ddt_ndarray_type_sys_oterm_name | string | Yes |
| ddt_ndarray_shape | string | Yes |
| ddt_ndarray_dimension_types_sys_oterm_id | string | Yes |
| ddt_ndarray_dimension_types_sys_oterm_name | string | Yes |
| ddt_ndarray_dimension_variable_types_sys_oterm_id | string | Yes |
| ddt_ndarray_dimension_variable_types_sys_oterm_name | string | Yes |
| ddt_ndarray_variable_types_sys_oterm_id | string | Yes |
| ddt_ndarray_variable_types_sys_oterm_name | string | Yes |
| withdrawn_date | string | Yes |
| superceded_by_ddt_ndarray_id | string | Yes |

**Total Rows:** 23

## Data

| ddt_ndarray_id | ddt_ndarray_name | ddt_ndarray_description | ddt_ndarray_metadata | ddt_ndarray_type_sys_oterm_id | ddt_ndarray_type_sys_oterm_name | ddt_ndarray_shape | ddt_ndarray_dimension_types_sys_oterm_id | ddt_ndarray_dimension_types_sys_oterm_name | ddt_ndarray_dimension_variable_types_sys_oterm_id | ddt_ndarray_dimension_variable_types_sys_oterm_name | ddt_ndarray_variable_types_sys_oterm_id | ddt_ndarray_variable_types_sys_oterm_name | withdrawn_date | superceded_by_ddt_ndarray_id |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Brick0000010 | adams_metals_100ws.ndarray | Adams Lab Metals Measurements for 100 Well Survey | [] | DA:0000005 | Chemical Measurement | [209, 52, 3, 3] | "[""DA:0000042"" |  ""ME:0000027"" |  ""ME:0000037"" |  ""ME:0000005""]" | "[""Environmental Sample"" |  ""molecule"" |  ""physiochemical state"" |  ""replicate series""]" |
| Brick0000072 | adams_metals_corepilot_271.ndarray | Adams Lab Metals Measurements from Core Pilot | [] | DA:0000005 | Chemical Measurement | [3, 2, 9, 35] | "[""ME:0000037"" |  ""ME:0000146"" |  ""ME:0000100"" |  ""ME:0000027""]" | "[""physiochemical state"" |  ""statistic"" |  ""environmental sample"" |  ""molecule""]" |
| Brick0000073 | adams_metals_corepilot_106.ndarray | Adams Lab Metals Measurements from Core Pilot | [] | DA:0000005 | Chemical Measurement | [3, 2, 18, 33] | "[""ME:0000037"" |  ""ME:0000146"" |  ""ME:0000100"" |  ""ME:0000027""]" | "[""physiochemical state"" |  ""statistic"" |  ""environmental sample"" |  ""molecule""]" |
| Brick0000080 | adams_metals_27ws.hndarray | Adams Lab Metals Measurements from 27 Well Survey | "[[""Instrument <ME:0000012>"" |  ""Nebulizer |  Concentric Quartz; Torch |  Quartz; Cones |  Pt""] |  [""Method <ME:0000007>"" |  ""Samples are diluted 1.2x for final acid conc of 2% HNO3.  Tubes were rinsed thoroughly after receiving them from ORNL due shipping contamination.""] |  [""Comment <ME:0000011>"" |  ""Inorganic Ventures 71A and 71B standards where used plus individual standards of Al |  Mg |  K |  Ca |
| Brick0000452 | zhou_lab_100ws_spring19_corepilot_27ws_cpt_ASV_16S.ndarray | Zhou Lab 100WS Spring19 CorePilot 27WS CPT ASV 16S Sequences | [] | DA:0000064 | Microbial Sequence | [113741] | "[""ME:0000184""]" | "[""ASV""]" | "[[""ME:0000222""]]" | "[[""ASV ID""]]" | "[""ME:0000282""]" | "[""sequence""]" | NULL | NULL |
| Brick0000454 | zhou_lab_100ws_spring19_corepilot_27ws_cpt_ASV_taxonomy.ndarray | Zhou Lab 100WS Spring19 CorePilot 27WS CPT ASV Taxonomy | "[[""Method <ME:0000007>"" |  ""silva-138-nb-classifier""]]" | DA:0000067 | Taxonomic Assignment | [111830, 6] | "[""ME:0000184"" |  ""ME:0000090""]" | "[""ASV"" |  ""taxonomic level""]" | "[[""ME:0000222""] |  [""ME:0000090""]]" | "[[""ASV ID""] |
| Brick0000457 | zhou_lab_sso_sediment_ASV_16S.ndarray | Zhou Lab SSO Sediment ASV 16S Sequences | [] | DA:0000064 | Microbial Sequence | [23458] | "[""ME:0000184""]" | "[""ASV""]" | "[[""ME:0000222""]]" | "[[""ASV ID""]]" | "[""ME:0000282""]" | "[""sequence""]" | NULL | NULL |
| Brick0000458 | zhou_lab_sso_sediment_ASV_taxonomy.ndarray | Zhou Lab SSO Sediment ASV Taxonomy | "[[""Method <ME:0000007>"" |  ""silva-138.1-nb-classifier""]]" | DA:0000067 | Taxonomic Assignment | [23458, 7] | "[""ME:0000184"" |  ""ME:0000090""]" | "[""ASV"" |  ""taxonomic level""]" | "[[""ME:0000222""] |  [""ME:0000090""]]" | "[[""ASV ID""] |
| Brick0000459 | zhou_lab_sso_sediment_ASV_count.ndarray | Zhou Lab SSO Sediment ASV Counts | [] | DA:0000028 | Taxonomic Abundance | [23458, 37] | "[""ME:0000184"" |  ""ME:0000231""]" | "[""ASV"" |  ""community""]" | "[[""ME:0000222""] |  [""ME:0000233""]]" | "[[""ASV ID""] |  [""community ID""]]" |
| Brick0000460 | zhou_lab_sso_pump_test_ASV_16S.ndarray | Zhou Lab SSO Pump Test ASV 16S Sequences | [] | DA:0000064 | Microbial Sequence | [9432] | "[""ME:0000184""]" | "[""ASV""]" | "[[""ME:0000222""]]" | "[[""ASV ID""]]" | "[""ME:0000282""]" | "[""sequence""]" | NULL | NULL |
| Brick0000461 | zhou_lab_sso_pump_test_ASV_taxonomy.ndarray | Zhou Lab SSO Pump Test ASV Taxonomy | "[[""Method <ME:0000007>"" |  ""silva-138.1-nb-classifier""]]" | DA:0000067 | Taxonomic Assignment | [9432, 7] | "[""ME:0000184"" |  ""ME:0000090""]" | "[""ASV"" |  ""taxonomic level""]" | "[[""ME:0000222""] |  [""ME:0000090""]]" | "[[""ASV ID""] |
| Brick0000462 | zhou_lab_sso_pump_test_ASV_count.ndarray | Zhou Lab SSO Pump Test ASV Counts | [] | DA:0000028 | Taxonomic Abundance | [9432, 14] | "[""ME:0000184"" |  ""ME:0000231""]" | "[""ASV"" |  ""community""]" | "[[""ME:0000222""] |  [""ME:0000233""]]" | "[[""ASV ID""] |  [""community ID""]]" |
| Brick0000476 | zhou_lab_100ws_spring19_corepilot_27ws_cpt_unnormalized_ASV_count.ndarray | Zhou Lab 100WS Spring19 CorePilot 27WS CPT unnormalized ASV Counts | [] | DA:0000028 | Taxonomic Abundance | [111830, 587, 2] | "[""ME:0000184"" |  ""ME:0000231"" |  ""ME:0000005""]" | "[""ASV"" |  ""community"" |  ""replicate series""]" | "[[""ME:0000222""] |  [""ME:0000233""] |
| Brick0000477 | zhou_lab_sso_pilot_time_series_ASV_16S.ndarray | Zhou Lab SSO Pilot Time Series ASV 16S Sequences | [] | DA:0000064 | Microbial Sequence | [9398] | "[""ME:0000184""]" | "[""ASV""]" | "[[""ME:0000222""]]" | "[[""ASV ID""]]" | "[""ME:0000282""]" | "[""sequence""]" | NULL | NULL |
| Brick0000478 | zhou_lab_sso_pilot_time_series_ASV_taxonomy.ndarray | Zhou Lab SSO Pilot Time Series ASV Taxonomy | "[[""Method <ME:0000007>"" |  ""silva-138.1-nb-classifier""]]" | DA:0000067 | Taxonomic Assignment | [9398, 7] | "[""ME:0000184"" |  ""ME:0000090""]" | "[""ASV"" |  ""taxonomic level""]" | "[[""ME:0000222""] |  [""ME:0000090""]]" | "[[""ASV ID""] |
| Brick0000479 | zhou_lab_sso_pilot_time_series_ASV_count.ndarray | Zhou Lab SSO Pilot Time Series ASV Counts | [] | DA:0000028 | Taxonomic Abundance | [9398, 40] | "[""ME:0000184"" |  ""ME:0000231""]" | "[""ASV"" |  ""community""]" | "[[""ME:0000222""] |  [""ME:0000233""]]" | "[[""ASV ID""] |  [""community ID""]]" |
| Brick0000510 | isolation_conditions_251112.hndarray | Isolation conditions for each ENIGMA isolate strain, as of 2025-11-12 | [] | DA:0000033 | Map | [3151] | "[""ME:0000042""]" | "[""strain""]" | "[[""ME:0000044""]]" | "[[""strain ID""]]" | "[""ME:0000200"" |  ""ME:0000202"" |  ""ME:0000102"" |  ""ME:0000009"" |
| Brick0000517 | isolate_environment_map_260108.hndarray | ENIGMA isolate strains mapped to Shotgun Metagenomic Samples as of 2026-01-08 | [] | DA:0000018 | Microbial Abundance | [61, 852] | "[""ME:0000100"" |  ""ME:0000042""]" | "[""environmental sample"" |  ""strain""]" | "[[""ME:0000102""] |  [""ME:0000044"" |  ""ME:0000246""]]" | "[[""environmental sample ID""] |
| Brick0000520 | isolate_16S_sanger_260121.ndarray | Isolate 16S Sequences from Sanger sequencing, as of 2026-01-21 | [] | DA:0000064 | Microbial Sequence | [3070, 2] | "[""ME:0000042"" |  ""ME:0000189""]" | "[""strain"" |  ""sequence type""]" | "[[""ME:0000044""] |  [""ME:0000189"" |  ""ME:0000186""]]" | "[[""strain ID""] |
| Brick0000521 | isolate_sequence_and_quality_arkin_260129.hndarray | Links to ENIGMA isolate sequence data and quality assessment on Arkin Lab servers, as of 2026-01-29 | [] | DA:0000064 | Microbial Sequence | [1499] | "[""ME:0000042""]" | "[""strain""]" | "[[""ME:0000044""]]" | "[[""strain ID""]]" | "[""ME:0000203"" |  ""ME:0000203"" |  ""ME:0000126"" |  ""ME:0000126"" |
| Brick0000522 | isolate_classification_gtdb_260129.ndarray | GTDB-Tk classification of each ENIGMA isolate strain with a genome, as of 2026-01-29 | "[[""method <ME:0000007>"" |  ""GTDB-Tk classifier""]]" | DA:0000067 | Taxonomic Assignment | [1328, 7] | "[""ME:0000042"" |  ""ME:0000090""]" | "[""strain"" |  ""taxonomic level""]" | "[[""ME:0000044"" |  ""ME:0000431""] |  [""ME:0000090""]]" |
| Brick0000525 | isolate_genbank_links_260211.hndarray | GenBank links for ENIGMA isolate strains, as of 2026-02-11 | [] | DA:0000064 | Microbial Sequence | [390] | "[""ME:0000042""]" | "[""strain""]" | "[[""ME:0000044""]]" | "[[""strain ID""]]" | "[""ME:0000333"" |  ""ME:0000333"" |  ""ME:0000203"" |  ""ME:0000043"" |
| Brick0000526 | isolate_publication_260211.ndarray | Publications of ENIGMA isolate strains, as of 2026-02-11 | [] | DA:0000017 | Microbial Assay | [635] | "[""ME:0000042""]" | "[""strain""]" | "[[""ME:0000044""]]" | "[[""strain ID""]]" | "[""ME:0000433""]" | "[""PubMed ID""]" | NULL | NULL |
