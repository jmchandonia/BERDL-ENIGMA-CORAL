# Monitoring update 2026-11-24

Built by `tools/build_monitoring_update2_coral_import.py` (it reuses the helpers and scratch inputs of
`tools/build_monitoring_update_coral_import.py`). Loaded 2026-11-24 as Brick0002483 to Brick0002487. JSON not committed.

| brick | CORAL ID | content |
|---|---|---|
| `hazen_aquatroll600_EFPW03_20230401_20230509` | Brick0002483 | direct download of the EFPW03 Aqua TROLL 600, 5,434 readings every 10 minutes; adds nitrate, and the five weeks after the HydroVu record stops |
| `hazen_aquatroll600_EFPW06_20230118_20230509` | Brick0002484 | direct download of the EFPW06 Aqua TROLL 600 (installed 2023-01-18), 15,970 readings; nitrate rises slowly from 2.0 to 3.8 mg/L, stored as recorded |
| `hazen_aquatroll600_EFPW03_20221221_20230401_v2` | Brick0002485 | Brick0001232 (HydroVu) ending where the download begins (190 half-hourly readings dropped) |
| `hazen_hobo_WS3_20220509_20230725_v2` | Brick0002486 | Brick0002351 with the export's times read as Eastern Standard Time |
| `hazen_hobo_WS3_20230725_20240522_v2` | Brick0002487 | Brick0002352 likewise; four readings shorter, ending before the API data |

Clocks:

- EFPW03 download: Central, as the export says; confirmed against the HydroVu brick over their four shared days (water pressure
  within 0.002 psi at the same instant, against 0.006 one hour either way).
- EFPW05 download (loaded 2026-11-19): labelled Central but Eastern; re-checked against WS1 barometric pressure separately for the
  standard-time and daylight-time parts (lag -1.0 h in both).
- EFPW06 download: Eastern, as labelled; no barometer and no overlapping data, so not checkable.
- WS3 (Area 3 LI-COR export): Eastern Standard Time all year. The export matches the LI-COR API data of 2024-05-22..31 exactly at
  local time minus one hour, HydroVu barometric pressure fits it at a one-hour offset in July-August 2023, and it has no skipped or
  repeated hour at the clock changes. The Area 2 exports (WS1, WS2) carry an explicit -0500 and were read correctly.

The same WS3 error is in `enigma.continuous_monitoring`; see `continuous_monitoring/RELAY_NOTE_20261124.md`.
