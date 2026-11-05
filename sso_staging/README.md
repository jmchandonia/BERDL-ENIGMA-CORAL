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
| `picarro_gas` | append + dedup on (`epoch_time`, `instrument`) | `epoch_time` + `instrument` (analyzer serial) | `Gas_Data/*_gas_data.csv` (two Picarro G2508s + Firesting) |
| `field_metadata` | **full refresh** (shrink-guarded) | — (multiple draws per timepoint×well) | `Field Metadata` sheet |
| `sample_registry` | **upsert** (MERGE) | `sdt_sample_name` | `Assay Metadata` sheet (manifest) |
| `toc_tn_anions` | **upsert** (MERGE) | `sdt_sample_name` (the ANIONS sample) | every workbook in `TOC_TN_Anions_Chakraborty/` (Chakraborty TOC/TN + IC anion results, ppm) |

Bookkeeping tables (rewritten each run): `ddt_brick` (COMO microtype per
measurement column — the oterm ids live here, never in column names),
`instrument_port` (analyzer serial × multiplexer port → well-port, from Kris's
README; see below), `table_metadata`, `ingest_runs`.

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
                ddt_brick / table_metadata / ingest_runs; emit load_result.json
combined_report.py  compose ONE email covering cm + sso (see below)
run_daily.sh    orchestrate both namespaces in one tunnel/spawn, send one email
```

### Gas: two analyzers, one table

Two Picarro G2508 analyzers run concurrently (`Gas_Data/README.txt`, updated
2026-10-28): **A = ORNL-EA-031620** and **B = ORNL-EA-007299**, each with its own
Eosense 12-port multiplexer and Firesting O2 probe, so two rows can share an
`epoch_time`.  Every row carries the analyzer serial in `instrument` and the
dedup key is (`epoch_time`, `instrument`).  Attribution: well-ports use the
README's dated port assignment (`sso_schema.GAS_PORT_ASSIGNMENT`, published as
the `instrument_port` table); reference channels (Std / N2 / Drierite) use the
row's column signature (`NH3_dry` reported = A, `O2_%` reported = B, each
analyzer reports exactly one).  The build cross-checks the two rules on every
row: a well-port whose rows carry the other analyzer's signature means a port
was moved, so those rows are **held** and the email raises GAS PORT MOVED?
(also GAS ROWS UNATTRIBUTED, GAS NEW PORT, GAS PORT MAP).  Edit the assignment
after confirming with Kris, then re-stage with `--full-gas`.  The serial is data,
not microtype context (`ddt_brick` keeps `instrument=picarro`), so at CORAL
conversion each analyzer becomes its own brick with the serial as brick-level
context.  (`sso_migrate_instrument.py` is the one-time 2026-11-04 backfill that
attributed the 945,384 rows loaded before the column existed.)

### Gas file: "handle both" until Kris's protocol is settled

`sso_build.py` loads the **newest** `*_gas_data.csv` by default and, incrementally,
stages only rows newer than the last loaded `epoch_time` (tracked in
`state/gas_state.json`); the loader's anti-join on (`epoch_time`, `instrument`)
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
