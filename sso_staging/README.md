# enigma.sso_staging

A BERDL lakehouse namespace that lands the **SSO fall-2026 sampling campaign**
(Oct 6 – Dec 15, 36 timepoints) in CORAL-brick style, built to convert into real
CORAL bricks at campaign end.  Modeled on `../continuous_monitoring`: daily
fetch → build → load, with email reporting on dipa.

See `PLAN.md` (schema + COMO audit), `NAMING.md` (CORAL-legal id/column rules),
`INVENTORY.md` (sources + parser notes) and `examples/*.columns.md` (the reviewed
per-table brick structures).  `sso_schema.py` is the authoritative schema.

## Tables

| Table | Load mode | Key | Source |
|---|---|---|---|
| `picarro_gas` | append + dedup on (`epoch_time`, `picarro_serial`) | `epoch_time` + `picarro_serial` | `Gas_Data/*_gas_data.csv` (two Picarro G2508s + Firesting) |
| `field_metadata` | **full refresh** (shrink-guarded) | `field_draw_id` (one pumped draw: date + well-port + pump start) | `Field Metadata` sheet |
| `sample_registry` | **upsert** (MERGE) | `sdt_sample_name`; FK `field_draw_id` | `Assay Metadata` sheet (manifest) |
| `toc_tn_anions` | **upsert** (MERGE) | `sdt_sample_name` (the ANIONS sample); FKs `sdt_location_name`, `field_draw_id` | every workbook in `TOC_TN_Anions_Chakraborty/` (Chakraborty TOC/TN + IC anion results, ppm) |

Bookkeeping tables (rewritten each run): `column_typedef` (the
`enigma.coral.sys_ddt_typedef` rows these tables become: one row per
brick-bound column with its COMO terms, unit, FK and CORAL dump string — the
oterm ids live here, never in column names), `table_metadata`, `ingest_runs`.

Naming: `location` means `sdt_location` in CORAL and continuous_monitoring, so
the field team's well-port label (`U2-SZ1`) is **`well_port`** everywhere here
and the CORAL key is always **`sdt_location_name`** (`SSO-U2`); `zone` (SZ1/SZ2)
is the only other location-ish column.  Picarro reference rows carry
`reference_channel` (Std / N2 / Drierite) and a NULL `well_port`.

Time: every datetime column in both namespaces (`time_series_datetime` here and
in continuous_monitoring, `firesting_datetime`, `pump_on_datetime` /
`pump_off_datetime`) is an ISO 8601 string with the Eastern UTC offset at
millisecond precision, `2026-10-06T14:00:00.000-04:00`, the form the CORAL
bricks use; `picarro_gas.epoch_time` is the same instant as unix seconds.
Compare them with `to_timestamp()` (then `date_trunc` / `window` to align
cadences; `unix_timestamp(to_timestamp(x))` equals `epoch_time`), never as
strings: `01:45:00-04:00` sorts after `01:15:00-05:00` in the fall-back hour.
`sample_date` is `YYYY-MM-DD`, the CORAL date form.
(`sso_migrate_20261105_datetimes.py` is the one-time normalization.)

### Joining the tables

Every sample links to the pumped draw it came from.  `field_metadata` is keyed
by `field_draw_id` (`20261006-L7-SZ1-0832`: date, well-port, pump start);
`sample_registry` and every result table carry it as a foreign key, filled at
build time by sample date + well-port.  A day with several draws of one
well-port leaves the key NULL and raises SAMPLE DRAW AMBIGUOUS in the email
until `state/draw_overrides.json` (`{"<sdt_sample_name>": "<field_draw_id>"}`)
records which draw filled which sample.  The approximate sampling time is the
draw's `pump_off_datetime`:

```sql
SELECT t.sdt_sample_name, f.pump_off_datetime AS approx_sample_datetime, t.*
FROM enigma.sso_staging.toc_tn_anions t
JOIN enigma.sso_staging.field_metadata f ON f.field_draw_id = t.field_draw_id
```

Result tables carry only their keys (`sdt_sample_name`, `sdt_location_name`,
`field_draw_id`) and measurements; timepoint, date, well-port, zone and the
sample's storage come from `sample_registry` by `sdt_sample_name`.  Redundancy
review 2026-11-06: columns derivable from another column or table were dropped
(`assay_token`, the verbatim ids, `provenance`, the raw pump clock times);
`well_port` and `timepoint` stay deliberately (CORAL's SSO bricks carry the
well-port label as a dimension variable, and the timepoint survives a schedule
slip).  `sso_migrate_20261106_links.py` is the one-time migration.

Load semantics differ from the neighbours on purpose: continuous_monitoring is
append-only, CORAL is withdraw+replace, **sso_staging may modify rows in place**
when a source spreadsheet is edited — hence full-refresh / upsert for the two
spreadsheet tables.  The gas stream never changes once exported, so it is
append-with-dedup.

## Pipeline

```
sso_fetch.py    rsync the campaign subfolder out of the dipa Google-Drive mirror
                (or `rclone copy` if SSO_RCLONE_REMOTE is set) into fetch/
sso_build.py    parse the four sources -> staged TSVs + manifest.json
sso_load.py     create/append/refresh/upsert into enigma.sso_staging; write
                column_typedef / table_metadata / ingest_runs; emit load_result.json
combined_report.py  compose ONE email covering cm + sso (see below)
run_daily.sh    orchestrate both namespaces in one tunnel/spawn, send one email
```

### Gas: two analyzers, one table

Two Picarro G2508 analyzers run concurrently (`Gas_Data/README.txt`, updated
2026-10-28): **A = ORNL-EA-031620** and **B = ORNL-EA-007299**, each with its own
Eosense 12-port multiplexer and Firesting O2 probe, so two rows can share an
`epoch_time`.  Every row carries the analyzer serial in `picarro_serial` and the
dedup key is (`epoch_time`, `picarro_serial`).  Attribution: well-ports use the
README's dated port assignment (`sso_schema.GAS_PORT_ASSIGNMENT`, versioned in
git, not a lakehouse table); reference channels (Std / N2 / Drierite) use the
row's column signature (`NH3_dry` reported = A, `O2_%` reported = B, each
analyzer reports exactly one).  The build cross-checks the two rules on every
row: a well-port whose rows carry the other analyzer's signature means a port
was moved, so those rows are **held** and the email raises GAS PORT MOVED?
(also GAS ROWS UNATTRIBUTED, GAS NEW PORT, GAS PORT MAP).  Edit the assignment
after confirming with Kris, then re-stage with `--full-gas`.  The serial is data,
not microtype context (`column_typedef` keeps `instrument=picarro`), so at CORAL
conversion each analyzer becomes its own brick with the serial as brick-level
context.  (`sso_migrate_instrument.py` is the one-time 2026-11-04 backfill that
attributed the 945,384 rows loaded before the column existed;
`sso_migrate_20261105_names.py` the one-time rename to `well_port` /
`picarro_serial` / `reference_channel` and the drop of `well`, `channel_type`,
`ddt_brick`, `instrument_port`.)

### Gas file: "handle both" until Kris's protocol is settled

`sso_build.py` loads the **newest** `*_gas_data.csv` by default and, incrementally,
stages only rows newer than the last loaded `epoch_time` (tracked in
`state/gas_state.json`); the loader's anti-join on (`epoch_time`, `picarro_serial`)
is the dedup safety net, so re-ingesting a cumulative re-export never duplicates
rows.  Flags:
`--gas-file FILE` (a specific file), `--all-gas-files` (concatenate every CSV),
`--full-gas` (ignore the last-epoch state and stage everything, e.g. a backfill).
Whichever way Kris ends up delivering the exports, these cover it.

### Schema drift (new columns)

Any source column `sso_build.py` does not recognise is reported in the manifest
`drift` block and in the daily email ("NEW SOURCE COLUMNS — decide how to
handle") and is **not** loaded — a new upstream column is surfaced for a decision
instead of being guessed at or silently dropped.  Likewise, sample IDs that are
not CORAL-legal after normalization (or duplicates) are **held** and reported,
never rewritten; manifest placeholder ids (`--`, blank, `NA`, …) are skipped as
"unassigned" (future slots), not held.

### Assay results: the TOC/TN/anion folder

`toc_tn_anions` is the first assay-result table.  `sso_build.py` reads **every**
workbook (and every sheet with the expected header) in the campaign folder's
`TOC_TN_Anions_Chakraborty/` subfolder, maps each lab id (`L7-SZ1-100626`) to
the registry's `20261006-L7-SZ1-ANIONS` sample, and re-stages all rows each run;
the MERGE inserts new samples and updates edited ones, and a newer workbook
wins for the same sample.  Ids that do not resolve to a registry sample are held
and reported.  Anything in the folder that is not a workbook with that header
is left to the source inventory, which raises it as an ACTION item.

### Column comments record the source header; changes are alerts, not auto-edits

Every column's JSON comment carries `source_column`, the source-file header it
is parsed from (`TOC_ppm`, `Pump Time On`, ...).  The value comes from
`sso_schema.py`, never from the live file.  If a source header changes,
`sso_build.py` reports it as NEW/MISSING COLUMN (an ACTION in the email) and
nothing in the lakehouse changes until the schema is edited by hand.  Likewise
the daily load never rewrites comments or alters a table: it compares the live
comments with the schema and raises COMMENT DRIFT as an ACTION, and if the live
table lacks a column the schema defines it skips that table and raises TABLE
LACKS COLUMN.  After review, apply them with

```
sso_load.py --staging /any --sync-comments --comments-only
sso_load.py --staging /any --add-columns          # then backfill the new column
```

(continuous_monitoring works the same way: `source_label` + `source_headers`
in its comments, CM COMMENT DRIFT / CM NEW SOURCE LABEL in the email,
`cm_load.py --sync-comments --comments-only` to apply.)

## One combined daily email

The requirement is a single email per day covering **both** loads.  `run_daily.sh`
opens one SSH tunnel + JupyterHub spawn, loads continuous_monitoring then
sso_staging through it, and calls `combined_report.py`, which reuses cm_report
for the continuous_monitoring section (including its stateful silent-instrument
diff via `CM_CODE_DIR`) and `sso_report` for the sso section.  This replaces the
per-namespace cron entry; each namespace's own `run_daily.sh` still works for
manual runs and backfills.

Cron (dipa), replacing the standalone continuous_monitoring entry:

```
# daily combined lakehouse load (cm + sso)
17 7 * * *  /data/edr/field_automated_measurements/sso_staging/code/run_daily.sh
```

## Build-time COMO check (before first load)

Re-verify the ids in `sso_schema.py` against **live** `enigma.coral` and resolve
the single mint — the `liter per minute` unit (reuse if already present under
`volumetric flow rate unit` UO:0000270, else mint).  Everything else reuses
existing terms (free-text method/condition/instrument are not minted).

## Setup on dipa

```
./setup_venv.sh                      # uv venv + vendored spark_connect_remote/berdl_remote
cp credentials.env.example credentials.env   # set KBASE_AUTH_TOKEN
./run_daily.sh                       # or wire into cron as above
```
