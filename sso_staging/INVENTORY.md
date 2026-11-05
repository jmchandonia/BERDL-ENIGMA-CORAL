# sso_staging — source data inventory

Scan of the Google Drive folder **Sampling Mission Control**
(`12T_UzYcuR43WXO8zJrtlMHqmZt8prFIV`) → `2026 SSO Time Series Field Data/`,
done 2026-10-28. Campaign window: **2026-10-06 → 2026-12-15**, 36 sampling
timepoints (every 2 days), 9 SSO wells × SZ1/SZ2 ports + EFPW02/EFPW03.

## 1. Gas data (Kris) — Picarro + Firesting

`2026 SSO Time Series Field Data/Gas_Data/` (folder created 2026-10-28)

| File | Size | Notes |
|---|---|---|
| `2026_10_28_gas_data.csv` | 207 MB | Cumulative campaign file, data through ~2026-10-28 |
| `README.txt` | 2.9 KB | Column spec + provenance; **updated 2026-10-28 11:33** with the two-analyzer port tables (the 1.6 KB first version had none) |

Produced from the collab notebook `DataCompiler.ipynb`. **Two Picarro G2508
analyzers run concurrently** — A = `ORNL-EA-031620`, B = `ORNL-EA-007299` — each
with its own Eosense 12-port multiplexer (eos-mx) and Firesting FSO2-4 / OXROB3
O2 probe (README; confirmed by Katie and Kris 2026-11-04). One timestamped row
per analyzer cycle step; each multiplexer visits one port at a time, so each row
is tagged with the port being monitored. Near-continuous (Firesting O2 every
30 s; Picarro faster). Delivered as periodic (≈weekly) re-exported cumulative
CSVs named by date.

Columns (from README.txt):

| Column | Meaning | Candidate COMO variable / unit |
|---|---|---|
| `TIME` | field real time (Knoxville, US/Eastern) | datetime |
| `EPOCH_TIME` | unix epoch seconds | datetime |
| `N2O_ppm`, `N2O_dry_ppm` | nitrous oxide (wet / water-corrected) | N2O conc, ppm |
| `CO2_ppm`, `CO2_dry_ppm` | carbon dioxide | CO2 conc, ppm |
| `CH4_ppm`, `CH4_dry_ppm` | methane | CH4 conc, ppm |
| `H2O_%` | water vapor | H2O, percent |
| `NH3_ppb` | ammonia | NH3 conc, ppb |
| `O2_%`, `O2_dry_%` | oxygen (Picarro) | O2 conc, percent |
| `O2p_%` | oxygen (Firesting, in serum bottle, 30 s) | O2 conc, percent |
| `TrailerTemp_C` | trailer temperature (Firesting) | temperature, °C |
| `on_state` | Eosense multiplexer port state | context/dimension |
| `set` | cycle counter | context/dimension |
| `timedelta` | seconds this port has been monitored | context/dimension |
| `DateTime` | Firesting time used to join frames | datetime (join key) |
| `Port` | port id (postprocessed) | dimension |
| `Depth` | port depth (postprocessed) | dimension |
| `Well` | well id (postprocessed) | dimension → sdt_location |

"dry" = Picarro software auto-corrected for water content.

### Gas port analysis (from the 207 MB file, 2026-10-28)

945,384 rows, 2026-10-04 → 2026-10-26, 17 sampling days (~43k rows/day, ~1 Hz).
**Parser alignment (verified 2026-10-30):** the CSV has a **leading unnamed
index column** (header field 1 is blank, data field 1 is a 0-based integer), so
both header and data rows have 23 fields and data field *N* = header name at
field *N*. Read columns by header name, not fixed position. `Port` = full
well-port (`U2-SZ1`), `Depth` = zone (`SZ1`), `Well` = `U2`.

`NH3_dry` IS present in the file header (field 12) and is a **valid dry-basis
ppb** column — the README's prose column list just omits it. Confirmed from data:
NH3 dry/wet ratio = 1.018 (range 1.00–1.04), the same small Picarro water
correction as the other documented dry species (N2O dry/wet = 1.03). Trust the
file header over the README prose list.

21 distinct `Port` values:
- **18 well-ports** = 9 wells (L7–L9, M4–M6, U1–U3) × (SZ1, SZ2). No EFPW.
- **3 QC/reference channels**: `Drierite` (desiccant zero), `Std` (span gas),
  `N2` (nitrogen blank — run only occasionally).

Key facts for the table-shape decision (corrected 2026-11-04; the first pass
read the 1.6 KB README and wrongly concluded "one instrument, time-shared"):
- **Two analyzers, concurrent.** `on_state` = which port is live on *that*
  analyzer's multiplexer; the README port tables (as of 10/04/2026 20:00):

  | port | Picarro A `ORNL-EA-031620` | Picarro B `ORNL-EA-007299` |
  |---|---|---|
  | 1–9 | U2-SZ1, U2-SZ2, M5-SZ1, M5-SZ2, M6-SZ1, M6-SZ2, L9-SZ1, L9-SZ2, L8-SZ2 | U1-SZ1, U1-SZ2, M4-SZ1, M4-SZ2, L7-SZ1, L7-SZ2, U3-SZ1, U3-SZ2, L8-SZ1 |
  | 10 / 11 / 12 | HighSTD / UHPN2 / Air (CSV: `Std` / `N2` / `Drierite`) | same |

- **Column signature identifies the analyzer on every row**: A reports
  `NH3_dry` and never `O2_%`/`O2_dry_%`; B has the internal O2 probe
  (`O2_%`/`O2_dry_%`) and never `NH3_dry`. Verified on the 2026-10-28 file:
  659,190 A rows / 286,194 B rows, no row with both or neither, and every
  well-port's signature matches the README table. (So "O2 came online later /
  NH3_dry only early" was a misreading of two instruments' column sets.)
- **`EPOCH_TIME` is NOT unique**: 945,384 rows, 945,252 distinct epochs (132
  shared by an A row and a B row); (`EPOCH_TIME`, analyzer) is unique.
- **No independent port dropouts.** After the setup day (10-04, partial), every
  well-port reports on every sampling day.
- **Outages are trailer-wide**, e.g. the whole trailer is silent 10-10 → 10-15.
- `TrailerTemp_C` is one shared feed; `O2p_%` is one Firesting probe per system;
  `set` counts separately on each analyzer. `Drierite` = anhydrous calcium
  sulfate desiccant, i.e. the dry-air zero/baseline channel (README calls it
  "Air"); `Std` = span standard; `N2` = UHP nitrogen blank (rare).

→ Decision: **one table** (`picarro_gas`) with an `instrument` column (analyzer
serial) + well/zone/port dimensions + channel-type flag, dedup on
(`epoch_time`, `instrument`); the port assignment is kept as code
(`sso_schema.GAS_PORT_ASSIGNMENT`) and published as `instrument_port`. Open
question for Kris: README port 12 says "Air" while the CSV labels it
`Drierite`; and whether any port has moved since 10/04 20:00.

## 2. Field / sample metadata (Katie)

`2026 SSO Time Series Field Data/Field Metadata.xlsx` (27.9 MB, modified 2026-10-27)

One row per sampling draw. Filled through timepoint 11 (2026-10-26); timepoint
12 (2026-10-28) present but blank; timepoints 13–36 pre-seeded blank to Dec 15.

Field-log columns:

| Column | COMO variable / unit |
|---|---|
| `Field Metadata Timepoint` | context (int) |
| `Date (YYYYMMDD)` | sample date |
| `Well` (e.g. `U1-SZ1`, `EFPW02`) | dimension → sdt_location |
| `Pump Time On`, `Pump Time Off` | clock times (⚠ no AM/PM; afternoon hours written 1:00–6:00) |
| `Pump Rate (L/min)` | flow rate, L/min |
| `Total Volume (L)` | volume, L |
| `In-field pH` | pH |
| `Restek Bag Mass (g)` | mass, g — **gross/as-weighed** bag mass (~95–116 g, bag-dominated; NOT net gas mass, confirmed from data 2026-10-30) |
| `Field Notes` | free text |

## 3. Also new — lab assay results starting to return (not named in this task)

- `Field Metadata` sheet carries a campaign calendar (AquaTROLL calib, Picarro
  install, 12 Sets, assay plan rows: Metagenome/Carbon/N2O, Anions, Nitrite,
  Nitrate/Water isotopes, Enrichments, Metals [hold until 2027], 16S [UGA],
  MAGs [OSU], Cell counts [MSU]).
- `Assay Metadata` (native Google Sheet, modified 2026-10-27) — the assay plan.
- `Assay Metadata_anions_TOC_TN.xlsx` (31 MB, created 2026-10-26) — **first
  returning lab results** (anions / TOC / TN). The connector flattened only the
  plan-calendar sheet; result values live on tabs it did not surface.

Per the 2026-10-26 split decision these discrete assays were slated for CORAL.
Open question below: do they also stage here, or wait for CORAL?

### Assay workbook contents (read from the xlsx, 2026-10-28)

`Assay Metadata_anions_TOC_TN.xlsx` has 3 sheets — **no anion/TOC/TN results**:
- `Schedule` — the orange plan calendar (cadence below).
- `Assays` — the assay plan (one row per assay type: counts, volume, container,
  responsible person, PI, shipment columns — most marked **ship 2027**).
- `Assay Metadata` — a **sample manifest**: one row per (Timepoint, Date, Well,
  Assay) → Sample ID (e.g. `20261006-U1-SZ1-Anions`), storage, volume,
  container, responsible person, PI, ship date, tracking #.

The only measured values present anywhere are **in-field pH** (Notes column,
same as the field log). No concentration columns. → **We have a plan + a sample
registry, not results.** Results arrive later (biweekly shipments; mostly 2027).

### Cadence (from the orange `Schedule` calendar)

| Calendar row | Cadence |
|---|---|
| Sampling Timepoint | every 2 days, Oct 6 → Dec 15 (36 timepoints) |
| Metagenome/Carbon/N2O; N2O/Anions/Nitrite/Nitrate+Water iso | every 6 days (12 timepoints) |
| AquaTROLL calibration; Picarro install | setup window Sep 21 → Oct 5 |
| Shipping (Anions/Metals) | biweekly: Oct 21, Nov 4, Nov 18, Dec 2, Dec 16 |
| Anions / Metals (ship/result markers) | biweekly: Oct 22, Nov 5, Nov 19, Dec 3, Dec 17 |
| Enrichment sampling | one-off Nov 13/16 |

So the live data updates every ~2 days (field) / ~weekly (gas re-export);
assay **results** are a future, irregular, per-assay stream (weeks → 2027).

### sso_staging load semantics (user, 2026-10-28)

Unlike continuous_monitoring (append-only, never changes) and CORAL
(withdraw + replace whole bricks), **sso_staging may modify rows in place** when
the source spreadsheet changes. Archiving old values is not required here. So
spreadsheet-backed tables (field metadata, sample registry) are **refreshed from
source each run** (upsert/replace by key), while the gas stream stays
append-with-dedup (instrument data that doesn't change once exported).

## 4. Lab assay results — TOC/TN/anions (Chakraborty), added 2026-11-04

`TOC_TN_Anions_Chakraborty/SSO_timeseries_102626` (Google Sheet, mirrored as
`.xlsx`): Mingfei Chen's results sheet, copied there 2026-11-04 from Katie's
legacy My-Drive `2026_SSO_Fall_Time Series/TOC/TN/ANION_Chakraborty` folder (the
lab was asked to update only the team-drive copy).  One sheet, 12 columns:
`ORDER, SampleID, Preservation, Storage, Date Sampled, Well, Zone, TOC_ppm,
TN_ppm, Chloride_ppm, Sulfate_ppm, Nitrate_ppm`; 144 rows = 18 well-zones
(L7/L8/L9/M4/M5/M6/U1/U2/U3 × SZ1/SZ2) × timepoints 1–8 (Oct 6–20).  `SampleID`
is the lab's `<well>-<zone>-MMDDYY`, `Date Sampled` a numeric `MMDDYY`; all ids
consistent with their Well/Zone/Date columns and all map to existing
`...-ANIONS` registry samples.  No blanks or zeros.  Staged as `toc_tn_anions`
(see `examples/toc_tn_anions.columns.md`).

## Narrative / model files (not data to ingest)

`SSO Model Brief — 21 October 2026.pptx`, `PFLOTRANS-AI_BRIEF_oct21_2026`
(+ .pdf), `REPORT.md` (229 KB), `PFLOTRANS-AI_SSO_report_v3.2.pdf`, `figures/`.
