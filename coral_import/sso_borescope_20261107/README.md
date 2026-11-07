# CORAL import package: SSO colloidal borescope 2024 (20261107)

Built by `tools/build_sso_borescope_coral_import.py`; needs the COMO update `coral_import/ontology_update_20261107_borescope`
(velocity ME:0000519, azimuth ME:0000520, micrometer per second ME:0000521) installed and reloaded first.

| Brick | Shape | Variables |
| --- | --- | --- |
| hazen_colloidal_borescope_flow_vectors_sso_2024 | 39 measurements | flow azimuth/velocity, 5 statistics each, tracked particles |
| hazen_colloidal_borescope_particle_tracks_sso_2024 | 52036 readings | azimuth, velocity, particles in frame |

Protocol `hazen-colloidal-borescope-sso-2024`; one Assay Environment process (Hazen Lab, Subsurface Observatory, 2024-01-31 to 2024-02-26).
Workbook discrepancies (resolved from the software summaries): 20240205_M4-SZ2-24: workbook says 'No colloids seen' but the log has 1161 readings and the summary a flow vector 335.48/116.93; the summary values are used; 20240226_M5-SZ1-24: workbook vector/speed 191.27/556.84 = the summary's average direction/speed; flow vector used here 321.65/65.84; 20240226_M5-SZ2-26: workbook vector/speed 131.16/197.46 = the summary's average direction/speed; flow vector used here 57.61/73.06; 20240226_M5-SZ2-27: workbook vector/speed 184.04/412.55 = the summary's average direction/speed; flow vector used here 5.32/16.2; 20240226_M5-SZ3-30: workbook vector/speed 214.77/167.89 = the summary's average direction/speed; flow vector used here 234.32/99.19; 20240226_M5-SZ3-31: workbook vector/speed 216.13/180.02 = the summary's average direction/speed; flow vector used here 324.31/72.96; 20240226_M5-SZ3-32: workbook vector/speed 168.72/177.06 = the summary's average direction/speed; flow vector used here 150.98/54.29; 20240226_M5-SZ3-33: workbook vector/speed 167.23/719.26 = the summary's average direction/speed; flow vector used here 102.21/29.15; 20240226_M5-SZ3-35: workbook vector/speed 185.55/174.61 = the summary's average direction/speed; flow vector used here 164.98/38.2; 20240226_M5-SZ3-36: workbook vector/speed 184.41/155.61 = the summary's average direction/speed; flow vector used here 160.15/31.87; 20240205_L9-SZ2-26 log 3266 lines, summary 3265 data points; 20240208_M5-SZ1-18 log 418 lines, summary 415 data points; 20240208_M5-SZ2-24 log 2084 lines, summary 2080 data points; 20240209_M5-SZ3-30 log 159 lines, summary 155 data points; 20240209_M5-SZ3-31 log 1351 lines, summary 1350 data points; 20240209_M5-SZ3-32 log 173 lines, summary 170 data points; 20240209_M5-SZ3-34 log 1126 lines, summary 1124 data points; 20240209_M5-SZ3-36 log 129 lines, summary 125 data points; 20240226_M5-SZ2-26 log 5588 lines, summary 4096 data points

## Loaded 2026-11-07

Brick0002164 (`hazen_colloidal_borescope_flow_vectors_sso_2024`, 39 rows), Brick0002165
(`hazen_colloidal_borescope_particle_tracks_sso_2024`, 52,036 rows), Protocol0000075, Process0223319 (inputs
Location0000588/592/594 = SSO-L9/M4/M5). COMO reloaded on the hub first. Recorded in `upload_new_data_claude.ipynb`.
