#!/usr/bin/env python3
"""Parse the SSO campaign sources into staged TSVs + a manifest for sso_load.py.

Three sources, three load modes (see sso_schema.py):
  * picarro_gas    - Picarro/Firesting CSV -> append + dedup on epoch_time.
                     Incremental by default: only rows newer than the last loaded
                     epoch are staged (the loader's anti-join is the safety net).
  * field_metadata - 'Field Metadata' sheet -> full refresh (replace all rows).
  * sample_registry- 'Assay Metadata' sheet -> upsert (MERGE) by sdt_sample_name.

Schema drift: any source column we do not recognise is reported in the manifest
(`drift`) and NOT loaded, so a new column added upstream is surfaced for a human
decision instead of being silently dropped or guessed at.  Sample IDs that are
not CORAL-legal after normalization are held back and reported, never rewritten.

    sso_build.py --out STAGE [--mode incremental|backfill]
                 [--gas-file FILE | --all-gas-files] [--full-gas]
                 [--source-dir DIR] [--state DIR]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

import sso_common as sso
import sso_schema as schema

EASTERN = ZoneInfo("America/New_York")
GAS_OVERLAP_S = 2.0  # restage a hair of overlap; the loader dedups on epoch_time
DOC_EXTENSIONS = {".txt", ".md", ".docx", ".doc", ".pdf", ".pptx"}  # documentation, not data


def inventory_sources(source_dir: Path, gas_paths: list[Path], state_dir: Path) -> dict:
    """Every file under the fetched campaign folder, classified so the daily
    report can raise ACTION for data files the pipeline does not ingest:

      ingested  the gas CSV(s) + Field/Assay Metadata (with mtime/size, and
                whether this run actually read them)
      ignored   listed in <state>/ignored_sources.json -- a human decided to skip it.
                An entry is a bare path (ignore always) or {"path", "mtime"}
                (ignore only while the file is unchanged, so a file that later
                gains data resurfaces as ACTION).
      docs      README / docx / pdf ... -- documentation, reported quietly
      unknown   anything else: a new data file or type.  Reported as ACTION on
                every run until it is ingested or added to ignored_sources.json.
    """
    try:
        raw = json.loads((state_dir / "ignored_sources.json").read_text())
    except (FileNotFoundError, ValueError):
        raw = []
    ignored = {}  # path -> mtime it was ignored at (None = ignore regardless)
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, str):
            ignored[item] = None
        elif isinstance(item, dict) and item.get("path"):
            ignored[item["path"]] = item.get("mtime")
    known = {p.relative_to(source_dir).as_posix(): "picarro_gas" for p in source_dir.glob(sso.GAS_GLOB)}
    known[sso.FIELD_FILE] = "field_metadata"
    known[sso.ASSAY_FILE] = "sample_registry"
    read_now = {p.relative_to(source_dir).as_posix() for p in gas_paths} | {sso.FIELD_FILE, sso.ASSAY_FILE}
    out = {"ingested": [], "ignored": [], "docs": [], "unknown": []}
    for p in sorted(source_dir.rglob("*")):
        if not p.is_file() or p.name.startswith((".", "~$")):
            continue
        rel = p.relative_to(source_dir).as_posix()
        st = p.stat()
        entry = {"path": rel, "size": st.st_size,
                 "mtime": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(timespec="seconds")}
        if rel in known:
            entry.update(table=known[rel], read_this_run=rel in read_now)
            out["ingested"].append(entry)
        elif rel in ignored and ignored[rel] in (None, entry["mtime"]):
            out["ignored"].append(entry)
        elif p.suffix.lower() in DOC_EXTENSIONS:
            out["docs"].append(entry)
        else:
            out["unknown"].append(entry)
    return out
BLANK_RUN_EOF = 500  # stop reading a sheet after this many consecutive blank rows

import re

# Spreadsheet placeholders meaning "no value yet", not real data.
PLACEHOLDER_IDS = {"", "-", "--", "---", "NA", "N/A", "TBD", "TBA", "?", "NONE"}
_NOISE_HEADER = re.compile(r"^(unnamed.*|column\s*\d+)$", re.I)


def is_noise_header(name: str) -> bool:
    return not name or bool(_NOISE_HEADER.fullmatch(name.strip()))


def is_placeholder_id(value: str) -> bool:
    v = (value or "").strip()
    return v.upper() in PLACEHOLDER_IDS or set(v) <= {"-"}


def log(msg: str) -> None:
    print(msg, flush=True)


def cell_to_str(value) -> str:
    """Render an openpyxl/pandas cell as a clean string; integral floats lose '.0'."""
    if value is None:
        return ""
    if isinstance(value, float):
        if value != value:  # NaN
            return ""
        if value.is_integer():
            return str(int(value))
        return repr(value)
    if isinstance(value, time):
        return value.strftime("%H:%M:%S")
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value).strip()


def resolve_ampm(value) -> str:
    """Field clock: hours 1-6 are PM (verified from data 2026-10-30; no pre-07:00 draws)."""
    if not isinstance(value, time):
        return cell_to_str(value)
    h = value.hour + 12 if 1 <= value.hour <= 6 else value.hour
    return f"{h:02d}:{value.minute:02d}:{value.second:02d}"


def staged_columns(table: str) -> list[dict]:
    """Columns written to the staged TSV: everything the parser fills (the loader
    adds ingest_run_id and ingested_at)."""
    return [c for c in schema.TABLES[table]["columns"] if c["name"] not in ("ingest_run_id", "ingested_at")]


def drift(actual: set[str], known: set[str]) -> dict:
    actual = {c for c in actual if not is_noise_header(c)}
    return {"new_columns": sorted(actual - known), "missing_columns": sorted(known - actual)}


# ----------------------------------------------------------------------
# picarro_gas
# ----------------------------------------------------------------------

def pick_gas_file(source_dir: Path, gas_file: str | None) -> Path:
    if gas_file:
        p = Path(gas_file)
        return p if p.is_absolute() else source_dir / gas_file
    matches = sorted(source_dir.glob(sso.GAS_GLOB))
    if not matches:
        raise FileNotFoundError(f"no gas CSV matching {sso.GAS_GLOB} under {source_dir}")
    return matches[-1]  # names sort by date; newest last


def read_gas(paths: list[Path], last_epoch: float | None) -> tuple[pd.DataFrame, dict, float | None]:
    """Vectorized: one row per analyzer cycle step, only rows newer than last_epoch."""
    import numpy as np

    frames = [pd.read_csv(p, dtype=str, keep_default_na=False) for p in paths]
    raw = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
    actual = {c for c in raw.columns if c and not c.startswith("Unnamed")}
    d = drift(actual, schema.GAS_KNOWN_SOURCE)
    names = [c["name"] for c in staged_columns("picarro_gas")]

    epoch = pd.to_numeric(raw.get("EPOCH_TIME", pd.Series("", index=raw.index)), errors="coerce")
    mask = epoch.notna()
    if last_epoch is not None:
        mask &= epoch > (last_epoch - GAS_OVERLAP_S)
    raw, epoch = raw[mask].copy(), epoch[mask]
    if raw.empty:
        return pd.DataFrame(columns=names), d, last_epoch

    def col(name):
        return raw[name].str.strip() if name in raw else pd.Series("", index=raw.index)

    well, depth, port = col("Well"), col("Depth"), col("Port")
    is_ref = well.isin(sso.QC_CHANNELS) | port.isin(sso.QC_CHANNELS) | (well == "")
    is_efpw = well.str.upper().str.startswith("EFPW")

    out = pd.DataFrame(index=raw.index)
    out["epoch_time"] = raw["EPOCH_TIME"].values
    # Round to ms so the ISO string matches the source TIME (avoids fp ns artifacts).
    dt = pd.to_datetime((epoch * 1000).round().astype("int64"), unit="ms", utc=True).dt.tz_convert(EASTERN)
    out["time_series_datetime"] = [t.isoformat() for t in dt]
    out["sdt_location_name"] = np.where(is_ref, None, np.where(is_efpw, well, "SSO-" + well))
    out["location"] = np.where(port != "", port, (well + "-" + depth).str.strip("-"))
    out["zone"] = np.where(is_ref, None, depth)
    out["well"] = np.where(is_ref, None, well)
    out["channel_type"] = np.where(is_ref, "reference", "well")
    for c in schema.GAS_COLUMNS:
        src = c.get("src")
        if c["role"] in ("measurement", "dim") and src and src not in ("TIME", "EPOCH_TIME", "Port", "Depth", "Well"):
            out[c["name"]] = raw[src].values if src in raw else ""
    out["provenance"] = f"picarro csv {paths[-1].name}"
    out["source_file"] = paths[-1].name

    max_epoch = max(last_epoch if last_epoch is not None else float("-inf"), float(epoch.max()))
    return out.reindex(columns=names), d, max_epoch


# ----------------------------------------------------------------------
# field_metadata / sample_registry (xlsx sheets)
# ----------------------------------------------------------------------

def read_sheet(path: Path, sheet: str) -> tuple[list[str], list[dict]]:
    import io
    import openpyxl

    # The Drive files are Google-native xlsx mirrored without a .xlsx extension,
    # which openpyxl rejects by name; a bytes handle sidesteps the extension check.
    wb = openpyxl.load_workbook(io.BytesIO(path.read_bytes()), read_only=True, data_only=True)
    ws = wb[sheet]
    it = ws.iter_rows(values_only=True)
    header = [("" if h is None else str(h).strip()) for h in next(it)]
    # These sheets have a phantom used-range out to Excel's ~1.05M-row maximum.
    # Skip fully-blank rows and stop after a long run of them, so we read only the
    # real data instead of a million empty rows.
    records, blank_run = [], 0
    for raw in it:
        if all(c is None for c in raw):
            blank_run += 1
            if blank_run >= BLANK_RUN_EOF:
                break
            continue
        blank_run = 0
        records.append({header[i]: raw[i] for i in range(min(len(header), len(raw))) if header[i]})
    wb.close()
    return [h for h in header if h], records


def read_field(path: Path) -> tuple[list[dict], dict]:
    header, records = read_sheet(path, schema.TABLES["field_metadata"]["sheet"])
    d = drift(set(header), schema.FIELD_KNOWN_SOURCE)
    rows = []
    for rec in records:
        well = cell_to_str(rec.get("Well"))
        date = cell_to_str(rec.get("Date (YYYYMMDD)"))
        # Keep only rows with actual field data; skip pre-seeded calendar/blank rows.
        has_data = any(cell_to_str(rec.get(k)) for k in (
            "Pump Time On", "Pump Time Off", "Pump Rate (L/min)", "Total Volume (L)",
            "In-field pH", "Restek Bag Mass (g)", "Field Notes"))
        if not well or not date or not has_data:
            continue
        loc = sso.spreadsheet_location(well)
        row = {
            "timepoint": cell_to_str(rec.get("Timepoint")),
            "sample_date": date,
            "sdt_location_name": loc["sdt_location_name"],
            "location": loc["location"],
            "zone": loc["zone"],
            "well": loc["well"],
            "pump_time_on": resolve_ampm(rec.get("Pump Time On")),
            "pump_time_off": resolve_ampm(rec.get("Pump Time Off")),
            "rate_instrument_pump_liter_per_minute": cell_to_str(rec.get("Pump Rate (L/min)")),
            "volume_liter": cell_to_str(rec.get("Total Volume (L)")),
            "ph_ph": cell_to_str(rec.get("In-field pH")),
            "mass_gram": cell_to_str(rec.get("Restek Bag Mass (g)")),
            "field_notes": cell_to_str(rec.get("Field Notes")),
            "provenance": f"field metadata {path.name}",
            "source_file": path.name,
        }
        rows.append(row)
    return rows, d


def read_registry(path: Path) -> tuple[list[dict], dict, list[dict]]:
    header, records = read_sheet(path, schema.TABLES["sample_registry"]["sheet"])
    d = drift(set(header), schema.REGISTRY_KNOWN_SOURCE)
    rows, held, seen = [], [], {}
    unassigned = 0
    for rec in records:
        raw_id = cell_to_str(rec.get("Sample ID"))
        if is_placeholder_id(raw_id):  # future slot, not yet assigned a sample id
            unassigned += 1
            continue
        norm = sso.normalize_sample_id(raw_id)
        if not sso.legal_id(norm):
            held.append({"source_sample_id": raw_id, "normalized": norm, "reason": "illegal character for CORAL id"})
            continue
        if norm in seen:
            held.append({"source_sample_id": raw_id, "normalized": norm,
                         "reason": f"duplicate id (also from {seen[norm]!r})"})
            continue
        seen[norm] = raw_id
        well = cell_to_str(rec.get("Well"))
        loc = sso.spreadsheet_location(well)
        assay = cell_to_str(rec.get("Assay"))
        rows.append({
            "sdt_sample_name": norm,
            "source_sample_id": raw_id,
            "timepoint": cell_to_str(rec.get("Timepoint")),
            "sample_date": cell_to_str(rec.get("Date")),
            "sdt_location_name": loc["sdt_location_name"],
            "location": loc["location"],
            "zone": loc["zone"],
            "assay": assay,
            "assay_token": assay.upper(),
            "storage_condition": cell_to_str(rec.get("Storage Condition")),
            "sample_volume": cell_to_str(rec.get("Volume")),
            "container": cell_to_str(rec.get("Container")),
            "responsible_person": cell_to_str(rec.get("Responsible Person")),
            "pi": cell_to_str(rec.get("PI")),
            "ship_date": cell_to_str(rec.get("Ship Date")),
            "tracking_number": cell_to_str(rec.get("Tracking #")),
            "notes": cell_to_str(rec.get("Notes")),
            "provenance": f"assay manifest {path.name}",
            "source_file": path.name,
        })
    return rows, d, held, unassigned


# ----------------------------------------------------------------------

def write_tsv(out: Path, table: str, rows) -> str:
    names = [c["name"] for c in staged_columns(table)]
    if isinstance(rows, pd.DataFrame):
        frame = rows.reindex(columns=names)
    else:
        frame = pd.DataFrame([{n: r.get(n, "") for n in names} for r in rows], columns=names)
    # Empty strings mark nulls in the TSV; None/NaN must render as empty, not 'None'/'nan'.
    frame = frame.astype(object).where(frame.notna(), "").astype(str).replace({"None": "", "nan": ""})
    tsv = f"{table}.tsv"
    frame.to_csv(out / tsv, sep="\t", index=False)
    return tsv


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True, help="staging directory to write")
    ap.add_argument("--mode", choices=["incremental", "backfill"], default="incremental")
    ap.add_argument("--source-dir", type=Path, default=None,
                    help="fetched '2026 SSO Time Series Field Data' dir (default: SSO_FETCH_DIR)")
    ap.add_argument("--state", type=Path, default=sso.STATE_DIR, help="state dir (gas last-epoch)")
    ap.add_argument("--gas-file", default=None, help="load this gas CSV instead of the newest")
    ap.add_argument("--all-gas-files", action="store_true", help="concatenate every gas CSV (dedup handles overlap)")
    ap.add_argument("--full-gas", action="store_true", help="stage all gas rows, ignoring the last-epoch state")
    args = ap.parse_args()

    source_dir = args.source_dir or sso.FETCH_DIR
    args.out.mkdir(parents=True, exist_ok=True)

    last_epoch = None
    gas_state = Path(args.state) / "gas_state.json"
    if not args.full_gas and args.mode == "incremental" and gas_state.exists():
        last_epoch = json.loads(gas_state.read_text()).get("last_epoch")

    manifest = {"mode": args.mode, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "tables": {}, "drift": {}, "held": {}}

    # --- gas ---
    if args.all_gas_files:
        gas_paths = sorted(source_dir.glob(sso.GAS_GLOB))
    else:
        gas_paths = [pick_gas_file(source_dir, args.gas_file)]
    log(f"gas: reading {[p.name for p in gas_paths]} (last_epoch={last_epoch})")
    gas_rows, gas_drift, max_epoch = read_gas(gas_paths, last_epoch)
    tsv = write_tsv(args.out, "picarro_gas", gas_rows)
    manifest["tables"]["picarro_gas"] = {
        "tsv": tsv, "load_mode": "append_dedup", "dedup_key": "epoch_time",
        "rows": len(gas_rows), "description": schema.TABLES["picarro_gas"]["description"],
        "source_files": [p.name for p in gas_paths],
    }
    manifest["drift"]["picarro_gas"] = gas_drift
    if max_epoch is not None:
        (args.out / "gas_state_pending.json").write_text(json.dumps({"last_epoch": max_epoch}) + "\n")
    log(f"gas: staged {len(gas_rows)} rows")

    # --- field metadata ---
    field_path = source_dir / sso.FIELD_FILE
    log(f"field_metadata: reading {field_path.name}")
    field_rows, field_drift = read_field(field_path)
    tsv = write_tsv(args.out, "field_metadata", field_rows)
    manifest["tables"]["field_metadata"] = {
        "tsv": tsv, "load_mode": "full_refresh", "rows": len(field_rows),
        "description": schema.TABLES["field_metadata"]["description"], "source_files": [field_path.name],
    }
    manifest["drift"]["field_metadata"] = field_drift
    log(f"field_metadata: staged {len(field_rows)} rows")

    # --- sample registry ---
    assay_path = source_dir / sso.ASSAY_FILE
    log(f"sample_registry: reading {assay_path.name}")
    reg_rows, reg_drift, held, unassigned = read_registry(assay_path)
    tsv = write_tsv(args.out, "sample_registry", reg_rows)
    manifest["tables"]["sample_registry"] = {
        "tsv": tsv, "load_mode": "upsert", "upsert_key": "sdt_sample_name", "rows": len(reg_rows),
        "unassigned_skipped": unassigned,
        "description": schema.TABLES["sample_registry"]["description"], "source_files": [assay_path.name],
    }
    manifest["drift"]["sample_registry"] = reg_drift
    manifest["held"]["sample_registry"] = held
    log(f"sample_registry: staged {len(reg_rows)} rows, held {len(held)}, unassigned {unassigned}")

    # --- source folder inventory: un-ingested data files become ACTION items ---
    manifest["sources"] = inventory_sources(source_dir, gas_paths, Path(args.state))
    unknown = manifest["sources"]["unknown"]
    if unknown:
        log(f"sources: {len(unknown)} un-ingested data file(s): {[u['path'] for u in unknown]}")

    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # Exit code 3 signals "loaded, but something needs a human" (new/missing columns,
    # held ids, or an un-ingested source file), mirroring cm_build.py's
    # unknown-label convention so run_daily can note it.
    flags = (any(v["new_columns"] or v["missing_columns"] for v in manifest["drift"].values())
             or bool(held) or bool(unknown))
    sys.exit(3 if flags else 0)


if __name__ == "__main__":
    main()
