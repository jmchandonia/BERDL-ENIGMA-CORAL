# Note for the continuous_monitoring session (from the CORAL import session, 2026-11-24)

Five things found while fixing the CORAL monitoring bricks. None has been changed in `enigma.continuous_monitoring` or in
`cm_build.py`; they are yours to decide. Evidence and scripts are named so each can be re-checked.

## 1. WS3 rows from the Area 3 LI-COR export are one hour early during daylight-saving time

- **What:** `licor/area3_2022-2024-2025_05_29_13_27_25_EDT_1.csv` gives its times in Eastern Standard Time (UTC-5) all year and has
  no offset in the time column. `add_licor_exports` parses it as a naive time and `local_naive_from_source(timestamp, None)` treats it
  as local time with daylight saving. Every `hazen_hobo_ws3` row with provenance `licor export` that falls in daylight-saving time is
  stamped one hour early. Winter rows are right. The Area 2 exports print `-0500` on every time and are parsed correctly, so WS1 and
  WS2 are not affected.
- **Evidence:**
  1. Over the export/API overlap (2024-05-22 to 05-31) the export equals the API data when the export time is taken as local time
     minus one hour: mean |dP| 0.0002 inHg and |dT| 0.002 F, against 0.013 inHg and 1.8 F unshifted.
  2. EFPW HydroVu barometric pressure (true UTC) fits WS3 best at a one-hour offset in July-August 2023 (it fits WS1 at zero offset in
     both winter and summer).
  3. The export has readings at 02:00-02:45 on 2023-03-12 and 2024-03-10 and no repeated hour on the autumn dates.
- **Fix:** read that export's times at a fixed UTC-5. Existing rows: add one hour to `hazen_hobo_ws3` rows with provenance
  `licor export` whose stored offset is -04:00 (about 47,000 rows), and drop the four readings that then overlap the first API rows
  (2024-05-22 20:00 to 20:45 EDT). CORAL: replaced by `hazen_hobo_WS3_20220509_20230725_v2` and `hazen_hobo_WS3_20230725_20240522_v2`.

## 2. The 1-minute HydroVu streams at L8, L9, M6 and U3 are not interpolated

- **What:** `cm_build.py` thins these four wells to one reading an hour (the "reading schedule" logic) on the belief that the API
  interpolates between hourly readings. It does not. Against the L8-SZ2 manual VuSitu log of 2025-09-10 the API minute values scatter
  about +/-0.5 uS/cm around the instrument's 10-minute readings and match them at no time offset; over about 4,700 instrument-days the
  minute series is a straight line on 18. The hourly "slope break" the detection keys on is a real jump in the readings, and the
  reading kept is the one at the jump.
- **Evidence:** `coral_import/monitoring_update_20261117/inputs/linearity.py` (scan of every raw file); comparison in AGENT_LOG
  2026-11-19.
- **Open question for the field team:** what the telemetry at those four wells sends each minute (the other wells send one value per
  15 minutes). The user is following this up.
- **CORAL:** the bricks keep one API value every 15 minutes and were left as loaded; item 2 of `CORAL_FIXES_PENDING.md` is withdrawn.

## 3. Conductivity at the sensor's floor

- **What:** 25,662 Aqua TROLL readings have actual conductivity of 0.05-0.07 uS/cm (ultrapure water is 0.055), in 23 CORAL bricks.
  Only 172 readings lie between 0.1 and 5 uS/cm, so the cut is clean. Two patterns: weeks-long spans at one instrument (M4 SZ1
  2025-12-19 to 2026-03-09, U2 SZ1 2025-12-17 to 2026-02-17 and Dec 2024, L7 SZ2 April 2026), and episodes of hours at several wells
  at once (2026-01-10, 2026-01-25/26 and later) during rapid water-level rises, when temperature, pressure, oxygen and pH all behave
  sensibly. The builder's cleaning only nulls negative conductivity.
- **CORAL rule applied:** where actual conductivity < 0.1 uS/cm, blank conductivity and the values computed from it (specific
  conductivity, total dissolved solids, salinity); other sensors untouched.

## 4. Total dissolved solids is parts per thousand, not parts per trillion

- **What:** the instruments' "ppt" is parts per thousand (TDS / specific conductivity = 0.00065 in every brick, i.e. 0.65 mg/L per
  uS/cm in g/L). The builder and the Java map translate "ppt" to parts per trillion, so the column is
  `concentration_phase_solid_physiochemical_state_dissolved_parts_per_trillion`. CORAL: unit corrected in 109 bricks (new column name
  ends `_parts_per_thousand`). The feed's column map was generated from the old CORAL names.

## 5. Smaller items

- **WS3 anemometer:** the last real reading is 2025-03-26 18:30; CORAL now blanks wind speed and gust speed after that reading, the
  feed from 2025-03-27 00:00. Wind direction keeps varying normally and was kept.
- **Deployment depths:** `DEPLOYMENT_DEPTH_BGS_FT` per-well values in the EDR builder are nominal depth below ground plus casing
  stick-up (U2 VSZ 15.51 = 12.50 + 3.01), i.e. depths below top of casing, not below ground.
- **EFPW HydroVu timing** needs no shift (barometric lag test against WS1), so the "unverified" note in `CORAL_FIXES_PENDING.md`
  can be closed. The +4 h for SSO Level TROLL data was re-verified (U2 VSZ HydroVu against U2 VZ manual, best lag +4.0 h, r = 0.97).
