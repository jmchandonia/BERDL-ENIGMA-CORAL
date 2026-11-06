# Example brick-like structure: `enigma.sso_staging.field_metadata`

One row per pumped draw, keyed by `field_draw_id`. **Refresh-from-source**, because
the source sheet (Katie's `Field Metadata.xlsx`) is edited in place as the
campaign proceeds. Same conventions as `picarro_gas`: CORAL-derived measurement
column names (minimal context), oterm ids in `column_typedef`, FK columns identical to
coral/continuous_monitoring.

**Load mode = full refresh** (replace all rows each run), NOT upsert-by-key:
verified in the data (2026-10-30) that a single (timepoint, well) can have
**several draws** — e.g. timepoint 1 at U1-SZ1 has two rows (a 15 L draw and a
0.4 L accidental pump).  Since 2026-11-06 each draw has a key, `field_draw_id`
(`20261006-U1-SZ1-0831`: date, well-port, pump start), which `sample_registry`
and the result tables reference; a row without a pump start cannot be keyed and
is held.  Full refresh is kept because the sheet is edited in place. The
loader replaces the table from source each run, guarded by a shrink-check that
refuses to wipe the table if the source suddenly has far fewer rows. The parser
keeps only rows with actual field data (pre-seeded calendar rows are dropped).

## Measurement columns (DOUBLE) — 4 real measurements

Minimal-context rule: no two of these collide on name, so none needs a
*disambiguating* token. Two carry a semantic context token anyway: pump rate
takes `instrument=pump` (bare `rate` is meaningless — the instrument says it is
the pump's flow rate), and pH is left bare (one pH column, instrument dropped
per user 2026-10-30). `instrument` (ME:0000012) is a free-text string property,
so `pump` is not minted.

| Source col | Column (CORAL-derived) | microtype label | unit (oterm) |
|---|---|---|---|
| `Pump Rate (L/min)` | `rate_instrument_pump_liter_per_minute` | rate, instrument=pump | liter per minute (mint — see below) |
| `Total Volume (L)` | `volume_liter` | volume | liter UO:0000099 |
| `In-field pH` | `ph_ph` | pH | pH UO:0000196 |
| `Restek Bag Mass (g)` | `mass_gram` | mass | gram UO:0000021 |

(`ph_ph` is the honest CORAL derivation — measurement label `pH` + unit label
`pH`; it reads oddly but matches how the generator appends the unit. Flag at
CORAL-conversion review if a cleaner column is wanted.)

### `column_typedef` rows (scalar_type = float)

| Source col | value_type (measurement) | instrument | unit | unit oterm |
|---|---|---|---|---|
| Pump Rate (L/min) | rate ME:0000264 | pump | liter per minute | mint under UO:0000270 |
| Total Volume (L) | volume ME:0000360 | — | liter | UO:0000099 |
| In-field pH | pH ME:0000121 | — | pH | UO:0000196 |
| Restek Bag Mass (g) | mass ME:0000135 | — | gram | UO:0000021 |

**Decisions (settled, user 2026-10-30):**
1. **Pump-rate unit — DECIDED: mint `liter per minute`** under `volumetric flow
   rate unit` (UO:0000270), the single mint in the whole namespace (reuse first
   if a live-CORAL check finds it already present). Not `microliters per minute`
   (ugly magnitudes).
2. **Pump-rate microtype — DECIDED: `rate` (ME:0000264) + `instrument=pump`**,
   unit L/min. `instrument` is free-text, no mint; no new `volumetric flow rate`
   measurement term is minted.

**Bag mass — DECIDED from the data (2026-10-30): gross, as-weighed.**
Inspected all 71 recorded values: min 95, median 102, mean 103.2, max 116 g
(stdev 4.25). Gas in a few-liter Restek bag weighs ~1–5 g (air ≈ 1.2 g/L), so a
~100 g value cannot be a *net* gas mass — it is the **gross mass of the Restek
bag as weighed** (bag-dominated; the collected gas is within the bag-to-bag
scatter and not resolvable). So `mass_gram` is modeled as a real `mass` (gram)
measurement but its `description` must say *gross/as-weighed mass of the Restek
gas-sampling bag*, **not** "mass of gas collected." It functions as a sample/QC
provenance weight. Name stays bare (one mass column); qualify only if a second
mass column ever appears. No Kris email needed.

## Dimension / context / bookkeeping columns

| Source col | Column | type | comment |
|---|---|---|---|
| `Date (YYYYMMDD)` + `Well` + `Pump Time On` | `field_draw_id` | STRING | **PK** `YYYYMMDD-<well-port>-HHMM` (`20261006-L7-SZ1-0832`) |
| `Field Metadata Timepoint` | `timepoint` | INT | campaign timepoint 1–36 |
| `Well` | `sdt_location_name` | STRING | FK → enigma.coral.sdt_location; `SSO-<well>`; EFPW verbatim |
| `Well` | `well_port` | STRING | field well-port label `U1-SZ1`; EFPW has no zone (`EFPW02`).  Not `location`, which means `sdt_location` in CORAL |
| `Well` | `zone` | STRING | `SZ1`/`SZ2`; empty for EFPW |
| `Date (YYYYMMDD)` + `Pump Time On` | `pump_on_datetime` | STRING | pump start as an instant (AM/PM resolved: field hours 1–6 → PM): ISO 8601 with UTC offset, America/New_York, millisecond precision (`2026-10-06T08:31:00.000-04:00`); its date part is the sample date; comparable with `time_series_datetime` in `picarro_gas` and continuous_monitoring via `to_timestamp()` |
| `Date (YYYYMMDD)` + `Pump Time Off` | `pump_off_datetime` | STRING | pump stop, same form |
| `Field Notes` | `field_notes` | STRING | free text |
| — | `source_file` / `ingest_run_id` / `ingested_at` | | bookkeeping (FK on ingest_run_id) |

Note: `pump_on_datetime` / `pump_off_datetime` carry the COMO `datetime` term
(ME:0000180) in `column_typedef` and are the pump window on the shared timeline;
`pump_off_datetime` is the approximate sampling time of every sample linked to
the draw.  The raw clock-time columns were dropped 2026-11-06 (fully contained
in the datetimes).
