# enigma.sso_staging — schema + COMO audit (draft for review)

Companion to `INVENTORY.md` (source data) and `NAMING.md` (ID/column rules).
A new BERDL namespace that lands SSO fall-2026 campaign data in CORAL-brick
style, for conversion to CORAL bricks at campaign end (Dec 2026).

## Principles (settled)

- **Append+dedup** (on `epoch_time` + `instrument`) for instrument data that never changes once
  exported (`picarro_gas`); **refresh-from-source** for the spreadsheet-backed
  tables, because sso_staging permits in-place edits when the source sheet
  changes. Mechanism differs by whether a stable key exists: `field_metadata` =
  **full refresh** (shrink-guarded; a timepoint×well can have several draws, so
  no unique key); `sample_registry` = **upsert (MERGE)** on `sdt_sample_name`.
- **CORAL-legal IDs** (`^[A-Z0-9-]+$`, validated, offenders held + reported);
  faithful-uppercase assay tokens; locations `SSO-<well>` with zone as a string.
- **Same BERDL column names / JSON comments / FK targets as coral +
  continuous_monitoring**, so the three namespaces join without translation.
- **Fetch**: daily `rclone copy` of the Drive subfolder into the dipa mirror;
  read from the mirror path.

## COMO audit (checked against schema/sys_ddt_typedef_table.md, 2026-10-28)

Gas-phase concentration microtypes already exist for the GC bricks and reuse
cleanly; only the Picarro *method* + *dry* context and a few field measurements
need minting. **All must be re-verified against live `enigma.coral` before the
first load; any MINT goes through the COMO update path
(`coral_import/ontology_update_20261028/`), not ad-hoc column comments.**

| Source column | Measurement (ME) | Molecule (CHEBI) / context | Unit | Status |
|---|---|---|---|---|
| `N2O_ppm` | concentration ME:0000129 | dinitrogen oxide; Method=CRDS | ppmv ME:0000348 | mol+unit EXIST; **MINT** method |
| `N2O_dry_ppm` | concentration | dinitrogen oxide; Method=CRDS; **water-corrected** | ppmv ME:0000348 | **MINT** method+dry |
| `CO2_ppm` / `CO2_dry_ppm` | concentration | carbon dioxide; CRDS [; dry] | ppmv ME:0000348 | **MINT** method[/dry] |
| `CH4_ppm` / `CH4_dry_ppm` | concentration | methane; CRDS [; dry] | ppmv ME:0000348 | **MINT** method[/dry] |
| `NH3_ppb` / `NH3_dry` | concentration | ammonia; CRDS [; dry] | ppb UO:0000170 | mol+unit EXIST; **MINT** method |
| `H2O_%` | concentration | water; State=gas (vapor); CRDS | percent UO:0000187 | mol+unit EXIST; **MINT** method/state |
| `O2_%` / `O2_dry_%` | concentration | dioxygen; CRDS [; dry] | percent UO:0000187 | mol+unit EXIST; **MINT** method |
| `O2p_%` | concentration | dioxygen; Method=optical (Firesting) | percent UO:0000187 | mol+unit EXIST; **MINT** method |
| `TrailerTemp_C` | temperature UO? | instrument=Firesting/trailer | °C UO:0000027 | EXISTS (add instrument context) |
| `In-field pH` | pH | instrument=pH meter | pH UO:0000196 | **EXISTS** (`pH, instrument=pH meter`) |
| `Pump Rate (L/min)` | volumetric flow rate | — | litre per minute | **MINT** measurement+unit |
| `Total Volume (L)` | volume | pumped/purged | litre | **MINT** measurement+unit |
| `Restek Bag Mass (g)` | mass | (none — mass of collected gas sample) | gram UO:0000021 | **MINT** measurement |

Notes:
- CORAL's existing gas microtypes use `Method=thermal conductivity detector`
  (GC). Picarro is cavity ring-down spectroscopy — a new `Method` enum value;
  "dry" (Picarro water-correction) is a new context. Both are small, pattern-
  following COMO additions.
- **DECIDED (user, 2026-10-28): proper measurements.** Pump rate, volume, and
  bag mass are minted as real COMO measurements (flow rate / volume / mass with
  UO units), not CORAL's legacy free-text `comment` microtypes
  (`comment, Description=… Volume Collected mL`, ME:0000011). Follow-up noted:
  consider back-filling older CORAL bricks that stored these as comments to use
  the new microtypes — contingent on whether that older data is worth computing
  on.
- **Container is NOT a COMO microtype** and is not minted. Verified against the
  authoritative 504-term ME ontology (`coral_import/ontology_update_20261028/
  production/context_measurement_ontology.obo`): the only container-like term is
  `culture vessel` (ME:0000486), for culturing, not field grab containers. The
  Restek bag (and VOA vial, falcon tube, cryovial, HPLC vial, serum bottle…) is
  a **property of the sample**, recorded as the descriptive `container` STRING
  in `sample_registry` — matching CORAL's existing free-text container handling.
  Only the collected-gas **mass** is a measurement; the bag-mass microtype
  carries no container context.
- Measurement **column names** follow continuous_monitoring's generated
  snake_case scheme, e.g.
  `concentration_molecule_from_list_dinitrogen_oxide_method_crds_parts_per_million_by_volume`,
  with JSON comment `{description, unit, unit_sys_oterm_id}`.

## Table: `picarro_gas`  (append + dedup on `epoch_time` + `instrument`)

Two Picarro G2508 analyzers run concurrently (A = ORNL-EA-031620, B =
ORNL-EA-007299; learned 2026-11-04 from Kris's updated README), so `epoch_time`
alone is not unique.  The serial is data, not microtype context.

| Column | Type | Comment / role |
|---|---|---|
| `time_series_datetime` | STRING | field time, ISO 8601 + offset (America/New_York); from `TIME` |
| `epoch_time` | DOUBLE | unix epoch s (dedup key with `instrument`); from `EPOCH_TIME` |
| `instrument` | STRING | analyzer serial `ORNL-EA-031620` (A) / `ORNL-EA-007299` (B); well-ports from the README port assignment (`instrument_port`), reference channels from the NH3_dry / O2_% column signature |
| gas measurement columns | DOUBLE | the 11 species columns above, COMO-named + commented |
| `sdt_location_name` | STRING | FK → enigma.coral.sdt_location; `SSO-<well>` (NULL for QC channels) |
| `location` | STRING | CORAL port string, e.g. `U2-SZ1` (raw `Port`) |
| `zone` | STRING | `SZ1`/`SZ2` (raw `Depth`) |
| `well` | STRING | `U2` (raw `Well`) |
| `channel_type` | STRING | `well` or `reference` (Drierite/Std/N2) |
| `multiplexer_on_state` | INT | raw `on_state` (1-12, per analyzer; `instrument_port` maps it) |
| `cycle_set` | INT | raw `set` (counts per analyzer) |
| `port_seconds` | DOUBLE | raw `timedelta` (s this port monitored) |
| `firesting_datetime` | STRING | raw `DateTime` (join key), kept for traceability |
| `provenance` | STRING | `picarro csv` + source file date |
| `source_file` | STRING | CSV filename |
| `ingest_run_id` | STRING | FK → ingest_runs.ingest_run_id |
| `ingested_at` | TIMESTAMP | append time (UTC) |

## Table: `field_metadata`  (full refresh from source; shrink-guarded)

| Column | Type | Role |
|---|---|---|
| `timepoint` | INT | campaign timepoint 1–36 |
| `sample_date` | STRING | `YYYYMMDD` (raw `Date`) |
| `sdt_location_name` | STRING | FK; `SSO-<well>` (EFPW verbatim) |
| `location` | STRING | port string `U1-SZ1` |
| `zone` | STRING | `SZ1`/`SZ2` (empty for EFPW) |
| `pump_time_on` / `pump_time_off` | STRING | datetimes after AM/PM resolution (field hours 1–6 → PM) |
| `rate_instrument_pump_liter_per_minute` | DOUBLE | COMO rate, instrument=pump; unit `liter per minute` (MINT, only mint in namespace) |
| `volume_liter` | DOUBLE | COMO volume (EXISTS; liter UO:0000099) |
| `ph_ph` | DOUBLE | COMO pH (EXISTS; UO:0000196); instrument dropped from name |
| `mass_gram` | DOUBLE | COMO mass (EXISTS; gram UO:0000021) — collected-gas sample mass |
| `field_notes` | STRING | free text |
| `provenance`/`source_file`/`ingest_run_id`/`ingested_at` | | bookkeeping |

## Table: `sample_registry`  (refresh-from-source; key = sdt_sample_name)

| Column | Type | Role |
|---|---|---|
| `sdt_sample_name` | STRING | FK → enigma.coral.sdt_sample; normalized CORAL ID `YYYYMMDD-WELL-ZONE-ASSAY` |
| `source_sample_id` | STRING | raw manifest Sample ID (traceability) |
| `timepoint` | INT | |
| `sample_date` | STRING | `YYYYMMDD` |
| `sdt_location_name` | STRING | FK; `SSO-<well>` |
| `location` | STRING | port string |
| `zone` | STRING | |
| `assay` | STRING | raw manifest assay label |
| `assay_token` | STRING | uppercased token used in the ID |
| `storage_condition` | STRING | |
| `volume` | STRING | as recorded (e.g. `30 mL`) |
| `container` | STRING | |
| `responsible_person` | STRING | |
| `pi` | STRING | |
| `ship_date` | STRING | |
| `tracking_number` | STRING | |
| `provenance`/`source_file`/`ingest_run_id`/`ingested_at` | | bookkeeping |

(Assay **results** are NOT modeled yet — none exist. When a result file lands,
results attach to `sample_registry` by `sdt_sample_name`.)

## Table: `toc_tn_anions`  (upsert; key = sdt_sample_name) — added 2026-11-04

First assay-result table: Chakraborty TOC/TN + IC anions (ppm) on the ANIONS
samples; see `examples/toc_tn_anions.columns.md` for columns, microtypes and the
held/drift rules.  Microtypes reuse the lab's 2024 SSO bricks (no minting).

## Bookkeeping tables (as in continuous_monitoring)

- `table_metadata` — one row per data table: source, row count, first/last
  timestamp or timepoint, processing notes. Rewritten each run.
- `ingest_runs` — one row per load: mode, times, status, rows staged/appended/
  upserted, details.

## Open items before build

1. **Build-time only:** re-verify the COMO terms (CHEBI molecule ids, ME/UO unit
   ids) against **live** enigma.coral at load, and resolve the single MINT —
   the `liter per minute` unit (reuse if already live, else mint under
   UO:0000270). Everything else reuses existing terms (free-text method/
   condition/instrument). The `sdt_location` names are already verified (item 3).
2. ~~Volume/rate/mass: proper measurements vs CORAL comment-style~~ — DECIDED
   (user, 2026-10-28): proper measurements. Pump rate = `rate, instrument=pump`
   + `liter per minute`; volume = `volume`/liter; bag mass = `mass`/gram.
   Follow-up: possibly retrofit older comment-style bricks later.
3. ~~Confirm `EFPW02`/`EFPW03` exist as `sdt_location`~~ — DONE (2026-10-30):
   verified in the 2026-10-29 coral sync, spelled `EFPW02`/`EFPW03` exactly
   (zero-padded, no prefix); all nine `SSO-*` wells present too.
4. ~~AM/PM resolution for pump times~~ — DONE (2026-10-30): rule "field clock
   hours 1–6 → PM (+12), 7–12 as-written" validated against the data — turns all
   27 impossible negative durations into 0 and matches volume÷rate to ~12% median
   error. Earliest genuine AM draw is 7:00; no pre-07:00 draws.
5. `sdt_sample_name` for `picarro_gas`/`field_metadata`: leave NULL (keyed on
   location + time/timepoint), attach sample IDs only in `sample_registry`.
6. ~~`NH3_dry` unit / bag mass net-vs-gross~~ — DONE (2026-10-30): `NH3_dry` is
   dry-basis **ppb** (dry/wet = 1.018, normal water correction); bag mass is
   **gross/as-weighed** (~102 g, bag-dominated), not net gas mass. See INVENTORY.

**Parser note (gas CSV):** leading unnamed index column → read by header name,
not fixed position; `NH3_dry` is in the header though the README prose omits it.
