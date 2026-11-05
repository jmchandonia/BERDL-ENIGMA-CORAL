# Example brick-like structure: `enigma.sso_staging.picarro_gas`

Revised per user guidance (2026-10-29): **oterm ids and microtype context do
NOT go in variable names**, and are NOT overloaded into column comments.
Instead, data tables use short, readable column names, and a CORAL-style
**`column_typedef` metadata table** (a mirror of `enigma.coral.sys_ddt_typedef`) carries
the structured microtype per measurement column: primary measurement oterm,
molecule (CHEBI), method, context (incl. wet/dry basis), unit + unit oterm.
This is also the lossless blueprint for the end-of-campaign CORAL conversion
(CORAL will regenerate its own long column names from these terms).

Data-table **column comments** stay lightweight, like continuous_monitoring:
`{description, unit}` (+ `type`/`references` for FKs). Nothing more.

## Data table: `picarro_gas` (append + dedup on `epoch_time` + `picarro_serial`)

**Two analyzers (revised 2026-11-04).** Kris's updated `Gas_Data/README.txt`
documents two Picarro G2508s running concurrently — A = `ORNL-EA-031620`,
B = `ORNL-EA-007299` — each with its own Eosense 12-port multiplexer and
Firesting probe. The analyzer serial is **data** (`picarro_serial` column, part
of the dedup key), not microtype context: `column_typedef` keeps the free-text token
`instrument=picarro`, so the derived column names below are unchanged, and at
conversion each analyzer becomes its own brick with the serial as brick-level
instrument context. Which analyzer reports which column:

| column(s) | A `ORNL-EA-031620` | B `ORNL-EA-007299` |
|---|---|---|
| N2O, CO2, CH4 (wet + dry), NH3_ppb, H2O_% | yes | yes |
| `NH3_dry` | **yes** | empty |
| `O2_%`, `O2_dry_%` (internal O2 probe) | empty | **yes** |
| `O2p_%` (Firesting, one probe per system), `TrailerTemp_C` (shared) | yes | yes |

### Measurement columns (DOUBLE) — CORAL-style derived names

Naming follows the **continuous_monitoring precedent** (`build_column_map.py`):
the column name is CORAL's own derivation from the microtype label — NOT a
hand-made name and NOT the oterm ids. Derivation = slugify the label (lowercase;
drop commas; `=`/space/hyphen/punct → `_`), with CORAL's property-name
canonicalization (e.g. label `State=` → `physiochemical_state`). Validated
against the live `enigma.coral` TCD gas columns before load.

**Minimal-context rule (user, 2026-10-29):** a context token goes in the name
ONLY where two columns would otherwise collide in the lakehouse. So `condition`
is kept (wet/dry pairs collide on molecule+unit), `method` is dropped from every
name (too long; lives in `column_typedef`), and `instrument` (ME:0000012, free-text
`picarro`/`firesting`) is added ONLY to the dioxygen trio — the one place two
instruments measure the same molecule+unit. The single-instrument species carry
no instrument token. All oterm ids live in `column_typedef`; the free-text `comment`
property is never used in a name.

| CSV col | Column (CORAL-derived, minimal) | unit (comment) |
|---|---|---|
| `N2O_ppm` | `concentration_molecule_from_list_dinitrogen_oxide_condition_wet_parts_per_million_by_volume` | parts per million by volume |
| `N2O_dry_ppm` | `concentration_molecule_from_list_dinitrogen_oxide_condition_dry_parts_per_million_by_volume` | parts per million by volume |
| `CO2_ppm` | `concentration_molecule_from_list_carbon_dioxide_condition_wet_parts_per_million_by_volume` | parts per million by volume |
| `CO2_dry_ppm` | `concentration_molecule_from_list_carbon_dioxide_condition_dry_parts_per_million_by_volume` | parts per million by volume |
| `CH4_ppm` | `concentration_molecule_from_list_methane_condition_wet_parts_per_million_by_volume` | parts per million by volume |
| `CH4_dry_ppm` | `concentration_molecule_from_list_methane_condition_dry_parts_per_million_by_volume` | parts per million by volume |
| `NH3_ppb` | `concentration_molecule_from_list_ammonia_condition_wet_parts_per_billion` | parts per billion |
| `NH3_dry` | `concentration_molecule_from_list_ammonia_condition_dry_parts_per_billion` | parts per billion |
| `H2O_%` | `concentration_molecule_from_list_water_percent` | percent |
| `O2_%` | `concentration_molecule_from_list_dioxygen_instrument_picarro_condition_wet_percent` | percent |
| `O2_dry_%` | `concentration_molecule_from_list_dioxygen_instrument_picarro_condition_dry_percent` | percent |
| `O2p_%` | `concentration_molecule_from_list_dioxygen_instrument_firesting_percent` | percent |
| `TrailerTemp_C` | `temperature_degree_celsius` | degree Celsius |

The `description` in each column comment = the full microtype label (incl.
instrument + method), e.g. `concentration, molecule from list=dinitrogen oxide,
instrument=picarro, method=cavity ring-down spectroscopy, condition=dry`,
matching how coral/cm populate `description`.

### Dimension / context / bookkeeping columns

| CSV col | Column | type | comment |
|---|---|---|---|
| `TIME` | `time_series_datetime` | STRING | datetime (ISO 8601 with UTC offset, America/New_York, millisecond precision `2026-10-06T14:00:00.000-04:00`, the continuous_monitoring / CORAL form); derived from `EPOCH_TIME`, which equals `TIME` on every row; compare with `to_timestamp()` |
| `EPOCH_TIME` | `epoch_time` | DOUBLE | unix epoch seconds; dedup key together with `picarro_serial` (the two analyzers can share an epoch) |
| `Port` (assignment) / `NH3_dry`, `O2_%` (signature) | `picarro_serial` | STRING | analyzer serial `ORNL-EA-031620` (A) or `ORNL-EA-007299` (B): well-ports per the README port assignment (`sso_schema.GAS_PORT_ASSIGNMENT`), reference channels per the row's column signature (NH3_dry reported = A, O2_% reported = B) |
| `Well` | `sdt_location_name` | STRING | FK → enigma.coral.sdt_location.sdt_location_name; `SSO-<well>`; NULL on reference rows |
| `Port` | `well_port` | STRING | field well-port label `U2-SZ1`; NULL on reference rows. Named `well_port`, not `location`: in CORAL "location" means `sdt_location` |
| `Port` | `reference_channel` | STRING | `Std` (span standard, port 10) / `N2` (UHP N2 blank, 11) / `Drierite` (ambient air dried through a Drierite column, 12 "Air"); NULL on well rows |
| `Depth` | `zone` | STRING | `SZ1`/`SZ2`; NULL on reference rows |
| `on_state` | `multiplexer_on_state` | INT | Eosense multiplexer live-port state, 1-12, per analyzer (`GAS_PORT_ASSIGNMENT` maps it) |
| `set` | `cycle_set` | INT | Picarro cycle counter (counts per analyzer) |
| `timedelta` | `port_seconds` | DOUBLE | seconds this port monitored (unit=second) |
| `DateTime` | `firesting_datetime` | STRING | Firesting clock reading joined onto the row (30 s cadence; Eastern wall clock in the source), same ISO form with the row's offset; traceability of the join |
| — | `provenance` | STRING | `picarro csv` + source file date |
| — | `source_file` | STRING | CSV filename |
| — | `ingest_run_id` | STRING | FK → ingest_runs.ingest_run_id |
| — | `ingested_at` | TIMESTAMP | append time (UTC) |

## Port assignment (code, not a table): `sso_schema.GAS_PORT_ASSIGNMENT`

The README's dated port tables ("as of 10/04/2026 20:00"), kept in the schema
module (versioned in git) and used to attribute `picarro_serial`. Derivable from
the data too: `SELECT DISTINCT picarro_serial, multiplexer_on_state, well_port,
sdt_location_name FROM picarro_gas`.

| port | Picarro A `ORNL-EA-031620` | Picarro B `ORNL-EA-007299` |
|---|---|---|
| 1–9 | U2-SZ1, U2-SZ2, M5-SZ1, M5-SZ2, M6-SZ1, M6-SZ2, L9-SZ1, L9-SZ2, L8-SZ2 | U1-SZ1, U1-SZ2, M4-SZ1, M4-SZ2, L7-SZ1, L7-SZ2, U3-SZ1, U3-SZ2, L8-SZ1 |
| 10 / 11 / 12 | Std (HighSTD) / N2 (UHPN2) / Drierite (Air) | same |

Every build cross-checks the signature against this table. A disagreement on a
well-port (a moved port) HOLDS those rows and raises GAS PORT MOVED? in the
email; a port not in the table raises GAS NEW PORT; an `on_state` whose README
channel differs from the row's `Port` raises GAS PORT MAP. Nothing is guessed.

## Metadata table: `column_typedef` (mirrors `enigma.coral.sys_ddt_typedef`)

One row per brick-bound column of `picarro_gas`, `field_metadata` and
`toc_tn_anions` (not `sample_registry`, which becomes `sdt_sample`, a static
type). Same 15 columns as `sys_ddt_typedef` (`table_name` in place of
`ddt_ndarray_id`; `berdl_column_name`, `berdl_column_data_type` = `variable` /
`dimension_variable`, `scalar_type`, `foreign_key`, `comment` = microtype label,
`unit_sys_oterm_id/name`, `dimension_number`, `dimension_oterm_id/name`,
`variable_number`, `variable_oterm_id/name`, `original_csv_string` in CORAL's
dump format) plus `molecule_sys_oterm_id/name`, `context_metadata` (JSON
`[property, value]` pairs — where the **wet/dry basis** lives, not in the column
name) and `note`. Dimension variables: `time_series_datetime` (time series /
datetime, as Brick0000019), `sdt_location_name` (environmental sample location
/ Environmental Sample Location ID, object_ref FK), and the instrument
bookkeeping columns with NULL terms and a note saying what they become at
conversion. Dimension/variable numbers are provisional. 53 rows today (the two pump datetimes added 2026-11-05).

All context values below are FREE-TEXT on string-typed properties (method
ME:0000007, condition ME:0000006 — both `data_type=string`), so **nothing here
is minted**. Wet/dry basis = `condition=wet` / `condition=dry` (user, 2026-10-29).
CHEBI ids are CORAL's own (verified in schema dumps); molecule label follows
CORAL (`dinitrogen oxide`, not nitrous oxide).

Measurement (`variable`) rows — one per measurement column (scalar_type = float for all).
Keyed by CSV source here for readability; the stored `column` value is the
CORAL-derived name from the measurement table above.

| CSV source | value_type (measurement) | molecule (CHEBI) | instrument | method | condition | unit | unit oterm | note |
|---|---|---|---|---|---|---|---|---|
| N2O_ppm | concentration ME:0000129 | dinitrogen oxide CHEBI:17045 | picarro | cavity ring-down spectroscopy | wet | parts per million by volume | ME:0000348 |
| N2O_dry_ppm | concentration ME:0000129 | dinitrogen oxide CHEBI:17045 | picarro | cavity ring-down spectroscopy | dry | parts per million by volume | ME:0000348 |
| CO2_ppm | concentration ME:0000129 | carbon dioxide CHEBI:16526 | picarro | cavity ring-down spectroscopy | wet | parts per million by volume | ME:0000348 |
| CO2_dry_ppm | concentration ME:0000129 | carbon dioxide CHEBI:16526 | picarro | cavity ring-down spectroscopy | dry | parts per million by volume | ME:0000348 |
| CH4_ppm | concentration ME:0000129 | methane CHEBI:16183 | picarro | cavity ring-down spectroscopy | wet | parts per million by volume | ME:0000348 |
| CH4_dry_ppm | concentration ME:0000129 | methane CHEBI:16183 | picarro | cavity ring-down spectroscopy | dry | parts per million by volume | ME:0000348 |
| NH3_ppb | concentration ME:0000129 | ammonia CHEBI:16134 | picarro | cavity ring-down spectroscopy | wet | parts per billion | UO:0000170 |
| NH3_dry | concentration ME:0000129 | ammonia CHEBI:16134 | picarro | cavity ring-down spectroscopy | dry | parts per billion | UO:0000170 | note: analyzer A only |
| H2O_% | concentration ME:0000129 | water CHEBI:15377 | picarro | cavity ring-down spectroscopy | — | percent | UO:0000187 |
| O2_% | concentration ME:0000129 | dioxygen CHEBI:15379 | picarro | cavity ring-down spectroscopy | wet | percent | UO:0000187 | note: analyzer B's internal O2 probe only |
| O2_dry_% | concentration ME:0000129 | dioxygen CHEBI:15379 | picarro | cavity ring-down spectroscopy | dry | percent | UO:0000187 | note: analyzer B's internal O2 probe only |
| O2p_% | concentration ME:0000129 | dioxygen CHEBI:15379 | firesting | optical oxygen sensor | — | percent | UO:0000187 | note: Firesting FSO2-4 meter, OXROB3 probe, one per analyzer |
| TrailerTemp_C | temperature ME:0000123 | — | firesting | — | — | degree Celsius | UO:0000027 |

(Superseded 2026-11-05: the earlier `ddt_brick` table, which mirrored
`ddt_ndarray` and carried a per-column `withdrawn_date`, was replaced by
`column_typedef` above. `withdrawn_date` is a brick-level field in CORAL and is
not kept per column.)

(CHEBI ids above are the standard ones — nitrous oxide CHEBI:17045, dioxygen
CHEBI:15379 — to be re-verified against the live CORAL `sys_oterm`/molecule set
before load.)

## MINT list surfaced by this table — effectively empty

`method` (ME:0000007) and `relative` (ME:0000020) are `data_type=string`
properties, so their values are FREE TEXT, not registered terms (confirmed in
`context_measurement_ontology.obo`; this is why `Method=thermal conductivity
detector` works with no such term). Therefore:

- **CRDS method** — free-text `method` value. **No mint.**
- **optical oxygen sensor** (Firesting) — free-text `method` value. **No mint.**
- **wet/dry basis** — `condition=wet` / `condition=dry` (free text, user choice
  2026-10-29). **No mint.** (Ruled out `context` ME:0000001 — it is `oterm_ref`,
  would need minting; `physiochemical state=dry` — already means dry *weight* of
  solids, Brick0000049, collision; `phase` — both are gas phase.)
- concentration/temperature measurements and ppmv/ppb/percent/°C units: exist.

Only possible mint anywhere in sso_staging (and it is in `field_metadata`, not
here): the **`liter per minute`** unit for pump rate — UO has the category
`volumetric flow rate unit` (UO:0000270) and `microliters per minute`
(UO:0000271) but `liter per minute` was not found in the synced UO. Resolve at
build time against live CORAL: reuse if present, else express pump rate in an
existing unit, else mint the one unit. (`rate` ME:0000264, `volume` ME:0000360,
`mass` ME:0000135, `liter` UO:0000099, `gram` UO:0000021 all exist.)
