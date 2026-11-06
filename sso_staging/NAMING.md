# sso_staging → CORAL naming compliance

The plan is to convert `enigma.sso_staging` into CORAL bricks at the end of the
fall-2026 campaign, so all IDs must be CORAL-legal from the start. Rules below
are from the coral-ndarray-generation skill and the `coral_import/` SSO
precedents (confirmed 2026-10-28).

## Sample IDs — `sdt_sample_name` (static-import TSV header `name`)

- **Regex: `^[A-Z0-9-]+$`** — capital letters, digits, dashes only. No
  lowercase, underscores, spaces, periods.
- **Convention for this campaign (new time series = date-first):**
  `YYYYMMDD-WELL-ZONE-ASSAY`, optional filter suffix `-F01` / `-F8`.
  (Pre-2025 campaigns used `WELL-ZONE-YYYYMMDD-ASSAY`; live one-off/2025+ data
  uses date-first, e.g. `20250922-U2-SZ2-AODC`.)
- Unique; never an assigned-ID pattern (`Brick0000001`); use the field team's
  recorded name verbatim when it is regex-legal, only construct when none
  exists, and report any constructed ID.

The manifest IDs (`20261006-U1-SZ1-Anions`) are already date-first and only need
the **assay token uppercased** → `20261006-U1-SZ1-ANIONS`.

### Assay-token vocabulary — DECISION: (A) faithful uppercase (user, 2026-10-28)
Keep the field team's own assay tokens, just uppercased: `Anions`→`ANIONS`,
`CellCount`→`CELLCOUNT`, `NitrateIso`→`NITRATEISO`, etc. This is what the CORAL
rules prefer (use the recorded name when regex-legal) and is reversible; a
vocabulary map to prior-campaign tokens (AODC/ICTOC/NH3NO2…) is deferred to the
CORAL-conversion step, when the assays return and each correspondence can be
confirmed.

### ID validation (required, enforced on ingest)
Every `name` (sample and location) is validated against `^[A-Z0-9-]+$` **after**
the known normalization (uppercasing + location mapping). The only transforms
applied are uppercasing and the well-port→`SSO-<well>` mapping; nothing else is
silently rewritten. Any ID still containing an illegal character — underscore,
space, period, slash, etc. — is **held back and reported** (not silently
mangled, not dropped without notice), the same way continuous_monitoring holds
tables with unknown measurement labels. The validator also checks uniqueness of
`sdt_sample_name` within the batch.

## Location IDs — `sdt_location_name` (TSV header `name`)

- Location = **well only**, `SSO-<WELL>` — **no zone, no underscore**:
  `SSO-U1`, `SSO-U2`, `SSO-U3`, `SSO-M4`, `SSO-M5`, `SSO-M6`,
  `SSO-L7`, `SSO-L8`, `SSO-L9`.
- EFPW wells verbatim, **no** `SSO-` prefix, zeros kept: `EFPW02`, `EFPW03`.
  (TODO: confirm EFPW02/EFPW03 are registered `sdt_location`, or stage additions.)
- The port/zone (`SZ1`/`SZ2`) is **not** in the location — it is carried as the
  separate `zone` column, and the field team's label `U1-SZ1` as `well_port`.
  The word `location` is never used for it: in CORAL and continuous_monitoring
  "location" means `sdt_location` (renamed 2026-11-05).

## Mapping applied on ingest (all three staging tables)

| Source | CORAL location FK | zone/port string |
|---|---|---|
| `U1-SZ1` | `SSO-U1` | `U1-SZ1` |
| `M4-SZ2` | `SSO-M4` | `M4-SZ2` |
| `L7-SZ1` | `SSO-L7` | `L7-SZ1` |
| `EFPW02` (no zone) | `EFPW02` | `EFPW02` |
| gas `Well=U2`,`Depth=SZ1` | `SSO-U2` | `U2-SZ1` |
| gas QC `Drierite`/`Std`/`N2` | (none) | channel flag = reference |

Each table keeps the raw source string too, for traceability.

## Column / variable naming — match coral + continuous_monitoring (user, 2026-10-28)

Goal: an agent (or a human) can join `enigma.sso_staging` to
`enigma.continuous_monitoring` and `enigma.coral` without a translation layer.
So sso_staging reuses the **same BERDL column names, JSON column comments, and
foreign-key conventions** as those namespaces:

- **Foreign keys** use the CORAL static-object name columns and point at CORAL:
  - `sdt_location_name` STRING — comment
    `{"description":"environmental sample location ID","type":"foreign_key","references":"enigma.coral.sdt_location.sdt_location_name"}`
  - `sdt_sample_name` STRING — comment
    `{"description":"environmental sample ID","type":"foreign_key","references":"enigma.coral.sdt_sample.sdt_sample_name"}`
    (sample_registry is keyed on this; field_metadata / gas can carry it too
    once a draw's samples are registered.)
  - `ingest_run_id` STRING — `{"type":"foreign_key","references":"ingest_runs.ingest_run_id"}`
- **Timestamps**: every datetime column (`time_series_datetime`, `firesting_datetime`,
  `pump_on_datetime` / `pump_off_datetime`) is STRING, ISO 8601 with the Eastern UTC
  offset at millisecond precision — `2026-10-06T14:00:00.000-04:00` — identical to
  continuous_monitoring and the CORAL bricks; compare with `to_timestamp()`, never as
  strings (the fall-back hour mis-sorts).  Dates (`sample_date`) are `YYYY-MM-DD`, the
  CORAL `date` form; the `YYYYMMDD` form survives only inside sample ids.
- **Measurement columns** use the CORAL brick column scheme: snake_case name
  built from the COMO measurement label + unit (as in
  `continuous_monitoring/column_map.json`), with a JSON comment carrying
  `description`, `unit`, and the unit's `unit_sys_oterm_id` (ME:/UO: term).
  Gas species (N2O/CO2/CH4/NH3/H2O/O2 concentrations, wet & dry) and the field
  variables (pump rate, volume, in-field pH, bag mass) are mapped to existing
  COMO microtypes where they exist; any missing microtype/unit is **minted in
  COMO and recorded** (cf. `coral_import/ontology_update_20261028/`), not
  invented ad hoc in the column comment.
- **Bookkeeping columns** mirror continuous_monitoring: `source_file`,
  `ingest_run_id`, `ingested_at` (no `provenance`: here it was always a fixed
  label + `source_file`), plus `table_metadata` and `ingest_runs` tables.
- **Draw key**: `field_draw_id` = `YYYYMMDD-<well-port>-HHMM` of the pump start
  (CORAL-legal), primary key of `field_metadata`, foreign key in `sample_registry`
  and every result table.  Result tables carry keys + measurements only.
- **Dimension/context strings** (zone/port `U1-SZ1`, multiplexer `on_state`,
  cycle `set`, QC `reference_channel`) are plain STRING columns with descriptive
  comments, following the CORAL "context variable" style.
