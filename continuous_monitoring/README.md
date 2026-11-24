# enigma.continuous_monitoring

A daily, append-only lakehouse copy of the ENIGMA Hazen continuous-monitoring
data (Aqua TROLL 600, Level TROLL 500 and HOBO/LI-COR weather). It is built
from the API-derived data in the EDR `field_automated_measurements` tree,
using the same cleaning as the CORAL continuous-monitoring bricks.

How it differs from the CORAL bricks:

- **API data is always used.** HydroVu and LI-COR API data are never
  suppressed in favour of manually downloaded files. Manually curated VuSitu
  logs, pump-test downloads and the pre-2020 ENIGMA spreadsheets are not
  included. The LI-COR CSV exports are included; where an export and the
  LI-COR API cover the same timestamp, the API value is kept.
- **One table per location and zone, appended daily.** Tables are named like
  `hazen_aquatroll600_sso_l7_sz1`, `hazen_leveltroll500_sso_u2_vz` and
  `hazen_hobo_ws3`. Existing rows are never replaced. A row is appended only
  if its `time_series_datetime` is not already in the table.

## Tables

| Table | Contents |
|---|---|
| `hazen_<family>_<location>[_<zone>]` | Brick-style columns: `time_series_datetime`, the measurement columns (same names, types and JSON comments as the enigma.coral brick columns), and `sdt_location_name`, which references `enigma.coral.sdt_location`. Also `provenance`, `source_file`, `ingest_run_id` and `ingested_at`. |
| `table_metadata` | One row per data table: instrument, zone, deployment depth (below the top of the well casing, as the field team measures it; the SSO casings stick up above ground), processing notes (nitrate units, timestamp/depth corrections), first and last timestamps, row count. Rewritten each run. |
| `ingest_runs` | One row per load: mode, times, status, rows staged and appended, details. |

## Processing

`cm_build.py` imports `tools/build_continuous_monitoring_coral.py` from the
EDR tree and applies its cleaning to each raw file:

- header normalisation;
- sentinel and implausible-value nulling;
- nitrate sentinels nulled. Unlike the Oct 9 bricks, nitrate is NOT converted from nitrate-N: the instrument values are already nitrate, and existing rows were corrected on 2026-10-19 by `fix_nitrate_20261019.py`;
- dropping HydroVu sparse and extreme-temperature rows.

These corrections differ from the bricks and are listed in
`field_automated_measurements/CORAL_FIXES_PENDING.md`:

- **+4 h on every HydroVu SSO timestamp,** Aqua TROLL SZ and Level TROLL
  VZ/VSZ alike. This was verified against manual VuSitu logs
  (`analysis/lag_test.py`). The 2022–23 EFPW HydroVu data is not shifted:
  a barometric-pressure lag test against the WS1 weather station (CORAL
  monitoring update, 2026-11-24) shows its clock is right.
- **The SZ depth relabel** to ground surface → water surface.
- **LI-COR export times are fixed Eastern Standard Time.** HOBOlink exports
  print the station's standard time all year (`-0500` on every Area 2 and
  Background A row, summer included). The Area 3 export prints no offset; its
  times are the same fixed UTC-5 and are read with that offset
  (`EXPORT_NAIVE_OFFSET`), then stored as local time like everything else.
  Until 2026-11-24 they were read as DST-aware local time, which stamped every
  summer WS3 export reading one hour early and dropped the 02:00–02:45
  readings of the two spring-forward mornings; `fix_ws3_export_20261124.py`
  rebuilt those rows from a `cm_build.py --mode backfill --exports-only`
  staging (ingest run `ws3-export-est-20261124`).
- **Real reading times for interpolated HydroVu streams.** At SSO-L8, L9, M6
  and U3, HydroVu returns a 1-minute series interpolated between real
  readings, usually hourly at a fixed minute for each instrument. Slope breaks
  (|second difference| ≥ 10× the median) are counted per 6-hour window. The
  interval (60/30/20/15/10/5 min) and minute that best concentrate them give
  the reading schedule, and only those timestamps are kept.
  - The saved schedule is kept while it still explains a window. A dated
    history in `state/reading_schedule.json` makes reprocessing a day give
    the same rows.
  - Instruments whose values barely change, such as Level TROLL pressure,
    borrow the hourly minute of another instrument in the same well.
  - If nothing is detectable, the bricks' 15-minute phase rule is used.
  - The bricks instead keep one arbitrary 15-minute phase per day, which is
    mostly interpolated values.
- **The value ranges listed in `corrections.json`**: `null_ranges` (the dead WS3
  anemometer after its last real reading at 2025-03-26 18:30; every L8-SZ1 channel from 2026-10-11, a failing
  sonde whose stray readings passed the generic filters) and `offset_ranges` (a constant added to the
  value: L9-SZ2 depth to water +4.07 ft from 2026-09-24, the sonde's
  post-service calibration error, until it is recalibrated).  `start` and
  `end` are local dates, or local date-times when a cut falls within a day.
  Each entry's reason is written into the table's `table_metadata` notes.  Rows loaded
  before an entry existed are corrected once by the matching `fix_*.py`
  script (`fix_nitrate_20261019.py`, `fix_offset_20261111.py --all`, which
  applies every entry that has an `id` and is not yet recorded),
  which records itself in `ingest_runs` and is a no-op afterwards;
  `run_daily.sh` runs them non-fatally before each load.
- **Out-of-water readings** (`corrections.json` `out_of_water`, applied by
  `cm_out_of_water.py` to the live tables after every load, not at stage
  time, because the decision needs whole days and the loader appends partial
  days).  Year-round rule, re-evaluated over the last `window_days` (21) local
  days each run; every action is idempotent and only nulls more:
  - a depth to water at or below `zero_depth_ft` (0.1 ft) means no water above
    the pressure sensor (the water table never came within 0.33 ft of the
    surface here, even at a storm peak) → depth nulled, row kept;
  - a temperature outside `water_temperature_c` (8–25 °C; groundwater is
    14–21 °C, 10.6 °C after winter storms at L7, 22.6 °C at the 99th
    percentile) is air, a shed or a bucket → temperature nulled, row kept;
  - a sonde-day on which at least `air_day_share` (half) of the readings are
    outside the temperature band, or at least half have no depth while the
    temperature swings more than `air_day_temperature_range_c` (2 °C; water
    never does), is a day the sonde spent out of the well → every channel of
    those readings nulled, and the daily report raises CM OUT OF WATER.

  Oxygen, conductivity and water-level swings are deliberately not signals:
  every big storm (2024-11-14, 2025-10-28, the L7/M4 winter events) raises
  oxygen to saturation, halves the conductivity and moves the water table
  4–10 ft in several of these fracture-fed wells at once.  A sonde sitting in
  a bucket at room temperature, or hanging dry inside the casing in winter, is
  invisible to its own channels: use `null_ranges` when the field team reports
  such an episode.  Known episodes: M4-SZ1 2025-10-23..11-03 (indoors), M4-SZ2
  2026-06-09..15 (above the water), M6-SZ2 and L7-SZ1 2025-08-20..21 (lying in
  the shade, depth 0.00).  History was processed once
  (`--since 2024-01-01 --record-id out-of-water-20261119`); the earlier 25 °C
  rule (`air-readings-20261111`) had blanked 1,717 rows, of which
  `restore_air_rows_20261119.py` restored the non-temperature channels of 89
  that were temperature-sensor faults (M5-SZ1 Sept 2026 spikes to 150 °C
  between normal readings; M4-SZ2's first hot readings on 2026-06-06/07).
- **Sentinels and fault rows.** `corrections.json` `sentinels` nulls a value the
  instrument emits instead of a reading (pH exactly 0, conductivity below 1 µS/cm
  from a dry or failed cell, ORP below -10,000 mV), keeping the row; `null_rows` drops whole rows of one instrument while a
  named channel shows its fault state (U2-SZ1 from 2026-10-14: conductivity
  below 100 µS/cm marks the sonde's default-output state).  Both are applied
  once to history by the fix script.

`column_map.json` maps measurement labels to brick column names. It is
generated by `build_column_map.py`, which pairs the brick TSVs with the
`sys_ddt_typedef` rows in `enigma.coral`. If a label is not in the map, its
table is held back and the run reports it.

Partial days:

- `cm_fetch.py` fetches through the current time.
- Rows from the last hour are held back until the next run.
- For the interpolated streams, a complete 6-hour window gives the same
  schedule in a partial or a full-day fetch. The trailing incomplete window
  uses the saved schedule only if its data does not contradict it; otherwise
  its rows wait for a later run.
- In a September 2026 simulation, about 0.1–0.5% of partial-day rows at these
  four sites were not chosen by the later full-day pass. These are hours just
  before a genuine schedule change.
- Days in the last 14 days that are missing, failed, empty or incomplete
  are re-fetched on every run.

## Layout on dipa (`/data/edr/field_automated_measurements/continuous_monitoring`)

| Path | Contents |
|---|---|
| `code/` | This directory, deployed with rsync. |
| `.venv/` | uv venv. Create it with `setup_venv.sh`. `vendor/` holds the BERDL client packages copied from stout, because their GitHub repositories are no longer public. |
| `~/.keychain/dipa-sh` | Agent for the bastion tunnel. `~/.cshrc` starts keychain on interactive logins and cron uses that agent; after a dipa reboot, log in once to unlock `~/.ssh/id_rsa`. |
| `credentials.env` | `KBASE_AUTH_TOKEN`, `HYDROVU_CLIENT_ID`, `HYDROVU_CLIENT_SECRET`, `LICOR_API_TOKEN`. Mode 600; never committed. |
| `fetch/` | Raw API JSON, named by the day it contains. |
| `staging/<run>/` | Staged TSVs and `manifest.json` per run. Pruned after 30 days. |
| `state/` | `fetch_state.json` and `build_state.json`. |
| `logs/` | Per-run logs. Pruned after 90 days. |

`sync_niya.sh` rsyncs the whole `field_automated_measurements` tree to niya;
it excludes `continuous_monitoring/credentials.env`, `.venv/` and `vendor/`.

## Running

```sh
B=/data/edr/field_automated_measurements/continuous_monitoring
# daily (cron on dipa at 06:30); prints nothing unless something failed or needs attention
$B/code/run_daily.sh

# backfill: build everything from the EDR archive, LI-COR exports and fetch cache,
# then load it through the same proxy chain and commit its reading schedules
cd $B/code && ../.venv/bin/python cm_build.py --mode backfill --no-state --holdback-minutes 0 --out ../staging/backfill
$B/code/run_daily.sh --load-only $B/staging/backfill

# compare staged tables with the active API-derived CORAL bricks (run on stout)
python3 compare_with_bricks.py --staging /mnt/net/dipa.jmcnet$B/staging/backfill --out compare.json

# maintenance: run one code/ script through the proxy chain, under the daily lock
$B/code/run_daily.sh --exec fix_offset_20261111.py --all --dry-run
$B/code/run_daily.sh --exec cm_load.py --staging /any --sync-comments --comments-only
```

The first load was on 2026-10-16: 42 tables and 1,471,200 rows (ingest run
`20261017T013807Z`).

`run_monthly_coral.sh` is the monthly CORAL conversion (`update_monthly.sh`).
It moved from the stout crontab to dipa on 2026-10-16.

## Column comments and comment drift (2026-11-04)

Measurement column comments carry `source_label` (the normalized label the
pipeline and the CORAL bricks key on, e.g. `air pressure, PSI`) and
`source_headers` (the raw HydroVu/HOBO/LI-COR headers the builder's translation
map folds into it).  These come from `column_map.json` and the builder, never
from a live file.  A header the translation map does not know holds the whole
table back in `cm_build.py` and is raised in the daily email as
CM NEW SOURCE LABEL.  The daily load never rewrites comments: it reports any
difference between the live comments and the loader's as CM COMMENT DRIFT; after
review, apply with `cm_load.py --staging /any --sync-comments --comments-only`.
