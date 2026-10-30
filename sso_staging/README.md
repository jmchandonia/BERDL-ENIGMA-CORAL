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
| `picarro_gas` | append + dedup on `epoch_time` | `epoch_time` | `Gas_Data/*_gas_data.csv` (Picarro/Firesting) |
| `field_metadata` | **full refresh** (shrink-guarded) | — (multiple draws per timepoint×well) | `Field Metadata` sheet |
| `sample_registry` | **upsert** (MERGE) | `sdt_sample_name` | `Assay Metadata` sheet (manifest) |

Bookkeeping tables (rewritten each run): `ddt_brick` (COMO microtype per
measurement column — the oterm ids live here, never in column names),
`table_metadata`, `ingest_runs`.

Load semantics differ from the neighbours on purpose: continuous_monitoring is
append-only, CORAL is withdraw+replace, **sso_staging may modify rows in place**
when a source spreadsheet is edited — hence full-refresh / upsert for the two
spreadsheet tables.  The gas stream never changes once exported, so it is
append-with-dedup.

## Pipeline

```
sso_fetch.py    rsync the campaign subfolder out of the dipa Google-Drive mirror
                (or `rclone copy` if SSO_RCLONE_REMOTE is set) into fetch/
sso_build.py    parse the three sources -> staged TSVs + manifest.json
sso_load.py     create/append/refresh/upsert into enigma.sso_staging; write
                ddt_brick / table_metadata / ingest_runs; emit load_result.json
combined_report.py  compose ONE email covering cm + sso (see below)
run_daily.sh    orchestrate both namespaces in one tunnel/spawn, send one email
```

### Gas file: "handle both" until Kris's protocol is settled

`sso_build.py` loads the **newest** `*_gas_data.csv` by default and, incrementally,
stages only rows newer than the last loaded `epoch_time` (tracked in
`state/gas_state.json`); the loader's anti-join on `epoch_time` is the dedup
safety net, so re-ingesting a cumulative re-export never duplicates rows.  Flags:
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
