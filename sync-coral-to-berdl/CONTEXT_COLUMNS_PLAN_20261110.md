# Plan: stop materializing campaign and personnel context as Lakehouse columns (2026-11-10)

**Decision (user, 2026-11-10).** A brick column should exist only for a dimension variable or a variable. Since
2026-07-17 the sync (`dry_run_tools.expand_array_context_foreign_keys`) has also copied foreign-key-valued array
context into constant columns. That stays for context that links a brick to an object (`sdt_location_name` for the
single-location sonde and weather series, `sdt_strain_name`, `carbon_source_sys_oterm_id`) and stops for ENIGMA
Campaign and ENIGMA Labs and Personnel, which describe the whole brick, are recorded on the producing process, and
remain readable in `ddt_ndarray.ddt_ndarray_metadata`.

**Code (staged, not yet run against the Lakehouse).** `skills/sync-coral-to-berdl/scripts/dry_run_tools.py`:
campaign and personnel context is never expanded; previously added columns are dropped from reused brick TSVs and
schemas (atomic rewrite, so the prior run's hard-linked files are untouched) together with their derived
`sys_ddt_typedef` rows; a brick that declares these as a real variable keeps them (Brick0002146). SKILL.md updated.
Tested on copies of Brick0002164 (columns removed), Brick0002146 (kept) and Brick0000019 (location kept): row counts
unchanged, idempotent on rerun.

**Scope.** 101 current brick tables lose one or two constant columns (94 both, 5 personnel only, 2 campaign
only); `sys_ddt_typedef` loses 195 derived rows. No data values are lost: every value is the same in every row of its
table and is kept in `ddt_ndarray_metadata`.

**Redundancy check against the producing process** (`sys_process` via `sys_process_output`): campaign agrees for all
96 bricks that carry it. Personnel agrees for 85 of 99; for the 14 below the producing process names someone
else, usually because the current brick is a corrected version whose producing process is the update-data step, so
the lab is on the original version's process and in the metadata row. The three 27-well bug-trap reactor bricks
are different: their only producing process is 16S Sequencing by Ying Fu, with no Classify OTUs step, so Yupeng Fan,
who did the ASV analysis, is recorded only in the array context. Adding the missing Classify OTUs process would close
that gap; it is not required for this change.

| Brick | Name | Personnel in array context | Producing process |
| --- | --- | --- | --- |
| Brick0001920 | adams_metals_sso_pump_test_2024_v2.hndarray | Farris Poole | Update Data by John-Marc Chandonia |
| Brick0001921 | adams_metals_sso_pilot_time_series_2024_v2.hndarray | Farris Poole | Update Data by John-Marc Chandonia |
| Brick0001922 | adams_metals_sso_initial_well_characterization_2023_v2.hndarray | Farris Poole | Update Data by John-Marc Chandonia |
| Brick0001923 | adams_metals_sso_sediment_cores_2023_v2.hndarray | Farris Poole | Update Data by John-Marc Chandonia |
| Brick0001924 | hazen_aodc_sso_pump_test_2024_v2.hndarray | Terry Hazen | Update Data by John-Marc Chandonia |
| Brick0001925 | hazen_aodc_sso_initial_well_characterization_2023_v2.hndarray | Terry Hazen | Update Data by John-Marc Chandonia |
| Brick0001926 | northen_metabolomics_sso_sediment_2023_c18_pos_v2.hndarray | Suzanne Kosina | Update Data by John-Marc Chandonia |
| Brick0001927 | northen_metabolomics_sso_sediment_2023_c18_neg_v2.hndarray | Suzanne Kosina | Update Data by John-Marc Chandonia |
| Brick0001928 | northen_metabolomics_sso_sediment_2023_hilic_pos_v2.hndarray | Suzanne Kosina | Update Data by John-Marc Chandonia |
| Brick0001929 | northen_metabolomics_sso_sediment_2023_hilic_neg_v2.hndarray | Suzanne Kosina | Update Data by John-Marc Chandonia |
| Brick0002090 | hazen_field_sso_initial_well_characterization_2023_v2.hndarray | Hazen Lab | Update Data by John-Marc Chandonia |
| Brick0002142 | zhou_lab_27ws_bug_trap_reactor_2020_ASV_16S.ndarray | Yupeng Fan | 16S Sequencing by Ying Fu |
| Brick0002143 | zhou_lab_27ws_bug_trap_reactor_2020_ASV_count.ndarray | Yupeng Fan | 16S Sequencing by Ying Fu |
| Brick0002144 | zhou_lab_27ws_bug_trap_reactor_2020_ASV_taxonomy.ndarray | Yupeng Fan | 16S Sequencing by Ying Fu |

**Apply.** In the next CORAL-to-Lakehouse sync (planned together with the 2017 Pilot Core ITS and GeoChip package):
the changed-table selection picks up the 101 brick tables and `sys_ddt_typedef` by data and schema hash; they
are reloaded, comments verified, and foreign keys checked as usual. Afterwards: confirm no table other than
Brick0002146 has either column, and the schema reference files are republished without them.

**Rollback.** Revert the dry_run_tools.py change and rerun the sync; the columns and typedef rows are re-derived.

## Affected brick tables

| Brick | Name | Columns removed |
| --- | --- | --- |
| Brick0000050 | corepilot_pm_106.hndarray | campaign, personnel |
| Brick0000051 | corepilot_pm_271.hndarray | campaign, personnel |
| Brick0000052 | corepilot_aodc_core_soil.hndarray | campaign, personnel |
| Brick0000053 | corepilot_aodc_core_water.hndarray | campaign, personnel |
| Brick0000054 | corepilot_aodc_nitrate_water.hndarray | campaign, personnel |
| Brick0000064 | corepilot_DAPI_271.hndarray | campaign, personnel |
| Brick0000065 | corepilot_DAPI_106.hndarray | campaign, personnel |
| Brick0000066 | corepilot_BONCAT_271.hndarray | campaign, personnel |
| Brick0000067 | corepilot_BONCAT_106.hndarray | campaign, personnel |
| Brick0001898 | chakraborty_ic_anions_sso_pump_test_2024.hndarray | personnel |
| Brick0001899 | chakraborty_toc_tn_sso_pump_test_2024.hndarray | personnel |
| Brick0001900 | chakraborty_ic_anions_sso_pilot_time_series_2024.hndarray | personnel |
| Brick0001901 | stahl_nitrate_isotopes_sso_pump_test_2024.hndarray | personnel |
| Brick0001907 | baliga_ammonium_nitrite_sso_pilot_time_series_2024.hndarray | personnel |
| Brick0001908 | hazen_aodc_raw_sso_pump_test_2024.hndarray | campaign, personnel |
| Brick0001910 | hazen_aodc_raw_sso_initial_well_characterization_2023.hndarray | campaign, personnel |
| Brick0001916 | adams_metals_spring2019_integrated_sampling.hndarray | campaign, personnel |
| Brick0001917 | chakraborty_c_n_spring2019_integrated_sampling.hndarray | campaign, personnel |
| Brick0001918 | hazen_aodc_raw_spring2019_integrated_sampling.hndarray | campaign, personnel |
| Brick0001919 | hazen_aodc_spring2019_integrated_sampling.hndarray | campaign, personnel |
| Brick0001920 | adams_metals_sso_pump_test_2024_v2.hndarray | campaign, personnel |
| Brick0001921 | adams_metals_sso_pilot_time_series_2024_v2.hndarray | campaign, personnel |
| Brick0001922 | adams_metals_sso_initial_well_characterization_2023_v2.hndarray | campaign, personnel |
| Brick0001923 | adams_metals_sso_sediment_cores_2023_v2.hndarray | campaign, personnel |
| Brick0001924 | hazen_aodc_sso_pump_test_2024_v2.hndarray | campaign, personnel |
| Brick0001925 | hazen_aodc_sso_initial_well_characterization_2023_v2.hndarray | campaign, personnel |
| Brick0001926 | northen_metabolomics_sso_sediment_2023_c18_pos_v2.hndarray | campaign, personnel |
| Brick0001927 | northen_metabolomics_sso_sediment_2023_c18_neg_v2.hndarray | campaign, personnel |
| Brick0001928 | northen_metabolomics_sso_sediment_2023_hilic_pos_v2.hndarray | campaign, personnel |
| Brick0001929 | northen_metabolomics_sso_sediment_2023_hilic_neg_v2.hndarray | campaign, personnel |
| Brick0002084 | elias_ferrozine_iron_spring2019_integrated_sampling.hndarray | campaign, personnel |
| Brick0002085 | fields_cell_counts_spring2019_integrated_sampling.hndarray | campaign, personnel |
| Brick0002086 | fields_biomass_production_spring2019_integrated_sampling.hndarray | campaign, personnel |
| Brick0002087 | fields_water_isotopes_spring2019_integrated_sampling.hndarray | campaign, personnel |
| Brick0002088 | stahl_ammonia_oxidation_isotopes_spring2019_integrated_sampling.hndarray | campaign, personnel |
| Brick0002089 | hazen_field_spring2019_integrated_sampling.hndarray | campaign, personnel |
| Brick0002090 | hazen_field_sso_initial_well_characterization_2023_v2.hndarray | campaign, personnel |
| Brick0002091 | pumptest_2025_field_measurements_v2.hndarray | campaign |
| Brick0002092 | oneoff_260609_sample_metadata_v2.hndarray | campaign |
| Brick0002093 | hazen_manual_dtw_sso_2024.hndarray | campaign, personnel |
| Brick0002094 | hazen_manual_dtw_sso_pump_test_2024.hndarray | campaign, personnel |
| Brick0002095 | hazen_temphion_SSO-L8_SZ1_20260217_20260309.hndarray | campaign, personnel |
| Brick0002096 | hazen_temphion_SSO-L8_SZ2_20260217_20260309.hndarray | campaign, personnel |
| Brick0002097 | hazen_temphion_SSO-L9_SZ1_20260217_20260309.hndarray | campaign, personnel |
| Brick0002098 | hazen_temphion_SSO-L9_SZ2_20260217_20260309.hndarray | campaign, personnel |
| Brick0002099 | hazen_temphion_SSO-M5_SZ1_20260217_20260309.hndarray | campaign, personnel |
| Brick0002100 | hazen_temphion_SSO-M5_SZ2_20260217_20260309.hndarray | campaign, personnel |
| Brick0002101 | hazen_temphion_SSO-M6_SZ1_20260217_20260309.hndarray | campaign, personnel |
| Brick0002102 | hazen_temphion_SSO-M6_SZ2_20260217_20260309.hndarray | campaign, personnel |
| Brick0002103 | hazen_temphion_SSO-U2_SZ1_20260217_20260309.hndarray | campaign, personnel |
| Brick0002104 | hazen_temphion_SSO-U2_SZ2_20260217_20260309.hndarray | campaign, personnel |
| Brick0002105 | hazen_temphion_SSO-U3_SZ1_20260217_20260309.hndarray | campaign, personnel |
| Brick0002106 | hazen_temphion_SSO-U3_SZ2_20260217_20260309.hndarray | campaign, personnel |
| Brick0002107 | hazen_temphion_SSO-L7_SZ1_20260309_20260316.hndarray | campaign, personnel |
| Brick0002108 | hazen_temphion_SSO-L7_SZ2_20260309_20260316.hndarray | campaign, personnel |
| Brick0002109 | hazen_temphion_SSO-L8_SZ1_20260309_20260316.hndarray | campaign, personnel |
| Brick0002110 | hazen_temphion_SSO-L8_SZ2_20260309_20260316.hndarray | campaign, personnel |
| Brick0002111 | hazen_temphion_SSO-L9_SZ1_20260309_20260317.hndarray | campaign, personnel |
| Brick0002112 | hazen_temphion_SSO-L9_SZ2_20260309_20260317.hndarray | campaign, personnel |
| Brick0002113 | hazen_temphion_SSO-M4_SZ1_20260309_20260316.hndarray | campaign, personnel |
| Brick0002114 | hazen_temphion_SSO-M4_SZ2_20260309_20260316.hndarray | campaign, personnel |
| Brick0002115 | hazen_temphion_SSO-M5_SZ1_20260309_20260316.hndarray | campaign, personnel |
| Brick0002116 | hazen_temphion_SSO-M5_SZ2_20260309_20260316.hndarray | campaign, personnel |
| Brick0002117 | hazen_temphion_SSO-M5_SZ3_20260309_20260316.hndarray | campaign, personnel |
| Brick0002118 | hazen_temphion_SSO-M6_SZ1_20260309_20260317.hndarray | campaign, personnel |
| Brick0002119 | hazen_temphion_SSO-L7_SZ1_20260409_20260511.hndarray | campaign, personnel |
| Brick0002120 | hazen_temphion_SSO-L8_SZ1_20260409_20260511.hndarray | campaign, personnel |
| Brick0002121 | hazen_temphion_SSO-L8_SZ2_20260409_20260511.hndarray | campaign, personnel |
| Brick0002122 | hazen_temphion_SSO-L9_SZ1_20260409_20260511.hndarray | campaign, personnel |
| Brick0002123 | hazen_temphion_SSO-L9_SZ2_20260409_20260511.hndarray | campaign, personnel |
| Brick0002124 | hazen_temphion_SSO-M4_SZ1_20260409_20260511.hndarray | campaign, personnel |
| Brick0002125 | hazen_temphion_SSO-M5_SZ1_20260409_20260511.hndarray | campaign, personnel |
| Brick0002126 | hazen_temphion_SSO-M5_SZ3_20260409_20260511.hndarray | campaign, personnel |
| Brick0002127 | hazen_temphion_SSO-M5_VSZ_20260409_20260511.hndarray | campaign, personnel |
| Brick0002128 | hazen_temphion_SSO-M6_SZ1_20260409_20260511.hndarray | campaign, personnel |
| Brick0002129 | hazen_temphion_SSO-M6_SZ2_20260409_20260511.hndarray | campaign, personnel |
| Brick0002130 | zhou_lab_sso_oneoff_colloids_2024_ASV_16S.ndarray | campaign, personnel |
| Brick0002131 | zhou_lab_sso_oneoff_colloids_2024_ASV_count.ndarray | campaign, personnel |
| Brick0002132 | zhou_lab_sso_oneoff_colloids_2024_ASV_taxonomy.ndarray | campaign, personnel |
| Brick0002133 | zhou_lab_sso_oneoff_ftp6_2024_ASV_16S.ndarray | campaign, personnel |
| Brick0002134 | zhou_lab_sso_oneoff_ftp6_2024_ASV_count.ndarray | campaign, personnel |
| Brick0002135 | zhou_lab_sso_oneoff_ftp6_2024_ASV_taxonomy.ndarray | campaign, personnel |
| Brick0002136 | zhou_lab_sso_oneoff_ftp7_2024_ASV_16S.ndarray | campaign, personnel |
| Brick0002137 | zhou_lab_sso_oneoff_ftp7_2024_ASV_count.ndarray | campaign, personnel |
| Brick0002138 | zhou_lab_sso_oneoff_ftp7_2024_ASV_taxonomy.ndarray | campaign, personnel |
| Brick0002139 | zhou_lab_27ws_bug_trap_2019_ASV_16S.ndarray | campaign, personnel |
| Brick0002140 | zhou_lab_27ws_bug_trap_2019_ASV_count.ndarray | campaign, personnel |
| Brick0002141 | zhou_lab_27ws_bug_trap_2019_ASV_taxonomy.ndarray | campaign, personnel |
| Brick0002142 | zhou_lab_27ws_bug_trap_reactor_2020_ASV_16S.ndarray | campaign, personnel |
| Brick0002143 | zhou_lab_27ws_bug_trap_reactor_2020_ASV_count.ndarray | campaign, personnel |
| Brick0002144 | zhou_lab_27ws_bug_trap_reactor_2020_ASV_taxonomy.ndarray | campaign, personnel |
| Brick0002145 | adams_metals_27ws_bug_trap_2019.hndarray | campaign, personnel |
| Brick0002157 | hazen_aodc_cpt_sediment_2020.hndarray | campaign, personnel |
| Brick0002158 | hazen_aodc_raw_cpt_sediment_2020.ndarray | campaign, personnel |
| Brick0002159 | chakraborty_doc_cpt_sediment_2020.hndarray | campaign, personnel |
| Brick0002160 | hazen_fugro_cpt_profiles_area3_2020.hndarray | campaign, personnel |
| Brick0002161 | hazen_fugro_cpt_soundings_area3_2020.hndarray | campaign, personnel |
| Brick0002162 | hazen_manual_water_level_area3_cpt_2020.hndarray | campaign, personnel |
| Brick0002163 | walian_em_groundwater_counts_spring2019.hndarray | campaign, personnel |
| Brick0002164 | hazen_colloidal_borescope_flow_vectors_sso_2024.hndarray | campaign, personnel |
| Brick0002165 | hazen_colloidal_borescope_particle_tracks_sso_2024.hndarray | campaign, personnel |
