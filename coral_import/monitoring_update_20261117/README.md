# Monitoring update (built 2026-11-17 to 11-19, loaded 2026-11-19)

Built by `tools/build_monitoring_update_coral_import.py`; 134 bricks, CORAL Brick0002349 to Brick0002482. The JSON files are
not committed (334 MB); rebuild them with the builder (it needs the scratch inputs named at its top: the feed's backfill
output for the weather bricks and the hub's stored copies of the bricks being replaced).

Ontology: `coral_import/ontology_update_20261117_flow_rate` (COMO `ME:0000528 flow rate`), installed on stout and
coral-enigma and reloaded before the load.

## New bricks (9)

| brick | content |
|---|---|
| `hazen_leveltroll400_DP06_20190728_20191206` | the one 2019 Level TROLL log that was an .xlsx; 18,942 readings, like its 17 siblings (water temperature, pressure, depth to water below top of casing) |
| `hazen_pump_log_sso_pump_test_2025` | Pump Log sheet of the 2025 pump test: cumulative liters pumped and flow rate (instrument = pump), 242 readings at nine ports; two typing errors corrected from the neighbouring rows |
| `hazen_hobo_WS3_20220509_20230725` | WS3 rainfall only (the station recorded nothing else until 2023-07-25), from the Area 3 LI-COR export |
| `hazen_hobo_WS3_20230725_20240522` | WS3 full station record up to the first LI-COR API brick; soil water as recorded, including negatives |
| `hazen_hobo_WS2_20190622_20190723` | WS2 after Brick0000046 ends ("Background Site A" columns of the Area 2 export); battery-only rows dropped |
| `hazen_aquatroll600_EFPW01_*` (3) | HydroVu export 2022-08 to 2023-08, split at gaps over 5 days; nitrate as recorded with a comment that it drifts upward and is unreliable from about spring 2023 |
| `hazen_aquatroll600_EFPW05_20230301_20230509` | direct download; the export says Central time but the clock is Eastern (barometric comparison with WS1) |

## Replacements (125), each with an Update Data process

| group | bricks | change |
|---|---|---|
| HydroVu Level TROLL VZ/VSZ | 5 | every timestamp 4 hours later, all rows kept; U1 and U2 VSZ depth relabelled to ground surface to water surface |
| WS3 anemometer | 3 | wind speed and gust speed blank after the last real reading (2025-03-26 18:30); wind direction kept (the vane still works) |
| Total dissolved solids unit | 109 | parts per thousand, not parts per trillion (TDS / specific conductivity = 0.00065 in every brick) |
| Conductivity at the sensor floor | 17 of the 109, plus 6 more | conductivity, specific conductivity, TDS and salinity blank where conductivity < 0.1 uS/cm (25,662 readings in 23 bricks; many during rapid water-level rises) |
| 2018-19 weather pressure unit | 2 | the variable labelled mmHg holds inHg |

## Decided against

- CORAL_FIXES_PENDING item 2 ("interpolated" HydroVu streams at L8, L9, M6, U3) is withdrawn: the API minute series there is not
  an interpolation of the instrument log, so the 19 Aqua TROLL bricks stay as loaded.
- Item 3 (corrections in the EDR builder) and the deployment-depth labels wait for the next manual bricks.
- Not loaded: the EFPW01 direct download (one reading, in air) and the raw April 2024 pump-test TROLL logs (readme says not to use them).

## Checks recorded

- EFPW HydroVu timing needs no shift: barometric pressure against the WS1 station, best at 0 h (EFPW03 r = 0.96, EFPW01 r = 0.75).
- Level TROLL +4 h re-verified: U2 VSZ (HydroVu) against U2 VZ (manual), best at +4.0 h (r = 0.97, 0.39 unshifted).
- Manual Level TROLL depth labels are all correct (depth against pressure head, brick by brick).

## Inputs kept here

`inputs/` holds the small inputs the builder read from its scratch directory (`SCRATCH` at the top of the builder): the list of
current monitoring bricks (`cur_bricks.json`), the bricks with the wrong TDS unit (`tds_check.json`) and with floor conductivity
readings (`cond_floor.json`), and the two analysis scripts (`linearity.py`: how linear each raw HydroVu minute series is;
`lagtest.py`: barometric lag test of the EFPW logs). The large inputs are not kept: `cmout/` is the output of
`continuous_monitoring/cm_build.py --mode backfill --no-state --holdback-minutes 0` (used only for the WS2/WS3 export bricks),
and `stored/` holds the hub's `data_store` copies of the bricks replaced or used as templates.
