#!/usr/bin/env python3
"""Parse the SSO campaign sources into staged TSVs + a manifest for sso_load.py.

Four sources, three load modes (see sso_schema.py):
  * picarro_gas    - Picarro/Firesting CSV -> append + dedup on (epoch_time,
                     instrument).  Two analyzers run concurrently; each row is
                     attributed to one (well-ports by the README port assignment
                     in sso_schema, reference channels by the column signature)
                     and the two rules are cross-checked: a disagreement means a
                     port was moved, so those rows are HELD and reported, never
                     guessed.  Incremental by default: only rows newer than the
                     last loaded epoch are staged (the loader's anti-join is the
                     safety net).
  * field_metadata - 'Field Metadata' sheet -> full refresh (replace all rows).
  * sample_registry- 'Assay Metadata' sheet -> upsert (MERGE) by sdt_sample_name.
  * toc_tn_anions  - every workbook in TOC_TN_Anions_Chakraborty/ -> upsert by
                     sdt_sample_name (the ANIONS registry sample).  All rows are
                     re-staged each run; MERGE makes new rows inserts and edited
                     rows updates, so additions the lab makes are picked up daily.

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
GAS_OVERLAP_S = 2.0  # restage a hair of overlap; the loader dedups on (epoch_time, instrument)
DOC_EXTENSIONS = {".txt", ".md", ".docx", ".doc", ".pdf", ".pptx"}  # documentation, not data


def inventory_sources(source_dir: Path, gas_paths: list[Path], state_dir: Path,
                      extra_known: dict[str, str] | None = None) -> dict:
    """Every file under the fetched campaign folder, classified so the daily
    report can raise ACTION for data files the pipeline does not ingest:

      ingested  the gas CSV(s), Field/Assay Metadata and the TOC/TN/anion
                workbooks (with mtime/size, and whether this run read them)
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
    known.update(extra_known or {})  # e.g. the TOC/TN/anion workbooks actually parsed this run
    read_now = ({p.relative_to(source_dir).as_posix() for p in gas_paths} | {sso.FIELD_FILE, sso.ASSAY_FILE}
                | set(extra_known or {}))
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


def gas_instrument_checks(frame: pd.DataFrame, raw: pd.DataFrame):
    """Attribute every gas row to an analyzer and cross-check the two rules.

    signature  : NH3_dry reported -> A, O2_% reported -> B (per row, from the CSV)
    assignment : well-port -> analyzer from schema.GAS_WELL_INSTRUMENT (the README table)
    Well rows take the assignment, reference rows the signature.  Returns
    (instrument Series, keep mask, checks dict).  Rows are HELD (not staged) when
    the assignment and the signature disagree (a port was moved: edit the
    assignment, then re-stage with --full-gas) or when neither rule applies.
    """
    import numpy as np

    def present(col):
        return raw[col].str.strip() != "" if col in raw else pd.Series(False, index=raw.index)

    by_sig = {serial: present(meta["signature"]) for serial, meta in schema.GAS_INSTRUMENTS.items()}
    sig = pd.Series(None, index=raw.index, dtype=object)
    ambiguous = pd.Series(False, index=raw.index)
    for serial, mask in by_sig.items():
        ambiguous |= mask & sig.notna()
        sig = sig.mask(mask & sig.isna(), serial)
    sig = sig.mask(ambiguous, None)

    is_well = frame["channel_type"] == "well"
    assigned = frame["location"].map(schema.GAS_WELL_INSTRUMENT)
    instrument = pd.Series(np.where(is_well & assigned.notna(), assigned, sig), index=raw.index, dtype=object)

    conflict = is_well & assigned.notna() & sig.notna() & (assigned != sig)
    unattributed = instrument.isna()
    unknown_port = is_well & assigned.isna()
    keep = ~(conflict | unattributed)

    def tally(mask, cols):
        if not mask.any():
            return []
        g = pd.DataFrame({c: v[mask] for c, v in cols.items()}).fillna("").groupby(list(cols)).size()
        return [{**dict(zip(cols, k if isinstance(k, tuple) else (k,))), "rows": int(n)} for k, n in g.items()]

    on_state = pd.to_numeric(frame["multiplexer_on_state"], errors="coerce")
    expected_loc = pd.Series([
        schema.GAS_PORT_LOCATION.get((i, int(o))) if (i is not None and pd.notna(o)) else None
        for i, o in zip(instrument, on_state)], index=raw.index, dtype=object)
    port_map_mismatch = keep & expected_loc.notna() & (expected_loc != frame["location"])

    checks = {
        "conflicts": tally(conflict, {"location": frame["location"], "assigned": assigned, "signature": sig}),
        "unattributed": tally(unattributed & ~conflict, {"location": frame["location"], "channel_type": frame["channel_type"]}),
        "unknown_ports": tally(unknown_port & keep, {"location": frame["location"], "instrument": instrument}),
        "port_map_mismatch": tally(port_map_mismatch, {"instrument": instrument, "multiplexer_on_state": on_state,
                                                       "location": frame["location"], "assigned_location": expected_loc}),
        "rows_held": int((~keep).sum()),
        "rows_by_instrument": {k: int(v) for k, v in instrument[keep].value_counts().items()},
    }
    return instrument, keep, checks


def read_gas(paths: list[Path], last_epoch: float | None) -> tuple[pd.DataFrame, dict, float | None, dict]:
    """Vectorized: one row per analyzer cycle step, only rows newer than last_epoch.
    Returns (rows, drift, max_epoch, instrument checks)."""
    import numpy as np

    frames = [pd.read_csv(p, dtype=str, keep_default_na=False) for p in paths]
    raw = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
    actual = {c for c in raw.columns if c and not c.startswith("Unnamed")}
    d = drift(actual, schema.GAS_KNOWN_SOURCE)
    names = [c["name"] for c in staged_columns("picarro_gas")]
    empty_checks = {"conflicts": [], "unattributed": [], "unknown_ports": [], "port_map_mismatch": [],
                    "rows_held": 0, "rows_by_instrument": {}}

    epoch = pd.to_numeric(raw.get("EPOCH_TIME", pd.Series("", index=raw.index)), errors="coerce")
    mask = epoch.notna()
    if last_epoch is not None:
        mask &= epoch > (last_epoch - GAS_OVERLAP_S)
    raw, epoch = raw[mask].copy(), epoch[mask]
    if raw.empty:
        return pd.DataFrame(columns=names), d, last_epoch, empty_checks

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

    instrument, keep, checks = gas_instrument_checks(out, raw)
    out["instrument"] = instrument
    out = out[keep]

    # The state advances past held rows too: once the assignment is fixed they
    # come back with --full-gas (the loader's anti-join makes that safe).
    max_epoch = max(last_epoch if last_epoch is not None else float("-inf"), float(epoch.max()))
    return out.reindex(columns=names), d, max_epoch, checks


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
# toc_tn_anions (Chakraborty result workbooks; every file in the folder)
# ----------------------------------------------------------------------

def _open_workbook(path: Path):
    """openpyxl workbook for an xlsx (with or without extension), else None."""
    import io
    import openpyxl

    if path.suffix.lower() in DOC_EXTENSIONS or path.name.startswith((".", "~$")):
        return None
    try:
        return openpyxl.load_workbook(io.BytesIO(path.read_bytes()), read_only=True, data_only=True)
    except Exception:  # BadZipFile / InvalidFileException / ...: not a workbook
        return None  # (csv, image, ...): left for the source inventory to flag


def iter_toc_sheets(folder: Path):
    """Yield (path, sheet_title, header, records) for every worksheet in every
    workbook under the folder whose header has the TOC/TN result columns.
    Files are visited oldest-modified first so a newer export wins on MERGE."""
    if not folder.is_dir():
        return
    for path in sorted((p for p in folder.rglob("*") if p.is_file()), key=lambda p: (p.stat().st_mtime, p.name)):
        wb = _open_workbook(path)
        if wb is None:
            continue
        for ws in wb.worksheets:
            it = ws.iter_rows(values_only=True)
            first = next(it, None)
            if first is None:
                continue
            header = [("" if h is None else str(h).strip()) for h in first]
            if not schema.TOC_REQUIRED_SOURCE <= set(header):
                continue
            records, blank_run = [], 0
            for raw in it:
                if all(c is None for c in raw):
                    blank_run += 1
                    if blank_run >= BLANK_RUN_EOF:
                        break
                    continue
                blank_run = 0
                records.append({header[i]: raw[i] for i in range(min(len(header), len(raw))) if header[i]})
            yield path, ws.title, [h for h in header if h], records
        wb.close()


def read_toc(source_dir: Path, registry: dict[str, dict]) -> tuple[list[dict], dict, list[dict], dict[str, str]]:
    """Parse the TOC/TN/anion workbooks.  Each lab id '<well>-<zone>-MMDDYY' is
    mapped to the registry's ANIONS sample (YYYYMMDD-WELL-ZONE-ANIONS); the
    timepoint comes from that registry row.  Rows whose id is malformed,
    contradicts the sheet's own Well/Zone/Date columns, is not in the sample
    registry, or repeats within one file are held and reported.  The same id in
    a later (newer-mtime) file supersedes the earlier one.

    Returns (rows, drift, held, {relative path: table} for every file parsed)."""
    folder = source_dir / sso.TOC_DIR
    by_id: dict[str, dict] = {}
    held, parsed, actual_headers = [], {}, set()
    for path, title, header, records in iter_toc_sheets(folder):
        rel = path.relative_to(source_dir).as_posix()
        parsed[rel] = "toc_tn_anions"
        actual_headers |= set(header)
        seen_in_file: dict[str, str] = {}
        for rec in records:
            raw_id = cell_to_str(rec.get("SampleID"))
            if is_placeholder_id(raw_id):
                continue
            parts = sso.parse_lab_sample_id(raw_id)
            if parts is None:
                held.append({"source_sample_id": raw_id, "normalized": None, "source_file": path.name,
                             "reason": "lab id is not <well>-<zone>-MMDDYY"})
                continue
            sheet_well = cell_to_str(rec.get("Well")).upper()
            sheet_zone = cell_to_str(rec.get("Zone")).upper()
            sheet_date = cell_to_str(rec.get("Date Sampled")).zfill(6)
            sheet_date = f"20{sheet_date[4:6]}{sheet_date[:2]}{sheet_date[2:4]}" if len(sheet_date) == 6 and sheet_date.isdigit() else sheet_date
            mismatch = [k for k, a, b in (("Well", sheet_well, parts["well"]), ("Zone", sheet_zone, parts["zone"]),
                                          ("Date Sampled", sheet_date, parts["sample_date"])) if a and a != b]
            if mismatch:
                held.append({"source_sample_id": raw_id, "normalized": None, "source_file": path.name,
                             "reason": f"id disagrees with the sheet's {', '.join(mismatch)} column(s)"})
                continue
            norm = sso.registry_sample_name(parts["sample_date"], parts["well"], parts["zone"], "ANIONS")
            if not sso.legal_id(norm):
                held.append({"source_sample_id": raw_id, "normalized": norm, "source_file": path.name,
                             "reason": "illegal character for CORAL id"})
                continue
            if norm in seen_in_file:
                held.append({"source_sample_id": raw_id, "normalized": norm, "source_file": path.name,
                             "reason": f"duplicate id within {path.name} (also from {seen_in_file[norm]!r})"})
                continue
            seen_in_file[norm] = raw_id
            reg = registry.get(norm)
            if reg is None:
                held.append({"source_sample_id": raw_id, "normalized": norm, "source_file": path.name,
                             "reason": "no ANIONS sample with this id in the Assay Metadata manifest"})
                continue
            loc = sso.spreadsheet_location(f"{parts['well']}-{parts['zone']}" if parts["zone"] else parts["well"])
            row = {
                "sdt_sample_name": norm,
                "source_sample_id": raw_id,
                "timepoint": reg.get("timepoint", ""),
                "sample_date": parts["sample_date"],
                "sdt_location_name": loc["sdt_location_name"],
                "location": loc["location"],
                "zone": loc["zone"],
                "well": loc["well"],
                "preservation": cell_to_str(rec.get("Preservation")),
                "storage_condition": cell_to_str(rec.get("Storage")),
                "analysis_order": cell_to_str(rec.get("ORDER")),
                "provenance": f"chakraborty toc/tn/anions {path.name} [{title}]",
                "source_file": path.name,
            }
            for c in schema.TOC_COLUMNS:
                if c["role"] == "measurement":
                    row[c["name"]] = cell_to_str(rec.get(c["src"]))
            by_id[norm] = row  # later file wins
    d = drift(actual_headers, schema.TOC_KNOWN_SOURCE) if parsed else {"new_columns": [], "missing_columns": []}
    return list(by_id.values()), d, held, parsed


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
    gas_rows, gas_drift, max_epoch, gas_checks = read_gas(gas_paths, last_epoch)
    tsv = write_tsv(args.out, "picarro_gas", gas_rows)
    manifest["tables"]["picarro_gas"] = {
        "tsv": tsv, "load_mode": "append_dedup", "dedup_key": schema.TABLES["picarro_gas"]["dedup_key"],
        "rows": len(gas_rows), "description": schema.TABLES["picarro_gas"]["description"],
        "source_files": [p.name for p in gas_paths],
    }
    manifest["drift"]["picarro_gas"] = gas_drift
    manifest["gas_checks"] = gas_checks
    if max_epoch is not None:
        (args.out / "gas_state_pending.json").write_text(json.dumps({"last_epoch": max_epoch}) + "\n")
    log(f"gas: staged {len(gas_rows)} rows {gas_checks['rows_by_instrument']}, held {gas_checks['rows_held']}")
    for kind in ("conflicts", "unattributed", "unknown_ports", "port_map_mismatch"):
        if gas_checks[kind]:
            log(f"gas: {kind}: {gas_checks[kind]}")

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

    # --- TOC/TN/anion results (every workbook in the lab's folder) ---
    log(f"toc_tn_anions: reading {sso.TOC_DIR}/")
    registry_index = {r["sdt_sample_name"]: r for r in reg_rows}
    toc_rows, toc_drift, toc_held, toc_files = read_toc(source_dir, registry_index)
    tsv = write_tsv(args.out, "toc_tn_anions", toc_rows)
    manifest["tables"]["toc_tn_anions"] = {
        "tsv": tsv, "load_mode": "upsert", "upsert_key": "sdt_sample_name", "rows": len(toc_rows),
        "description": schema.TABLES["toc_tn_anions"]["description"],
        "source_files": [Path(f).name for f in toc_files],
    }
    manifest["drift"]["toc_tn_anions"] = toc_drift
    manifest["held"]["toc_tn_anions"] = toc_held
    held = held + toc_held
    log(f"toc_tn_anions: staged {len(toc_rows)} rows from {len(toc_files)} file(s), held {len(toc_held)}")

    # --- source folder inventory: un-ingested data files become ACTION items ---
    manifest["sources"] = inventory_sources(source_dir, gas_paths, Path(args.state), toc_files)
    unknown = manifest["sources"]["unknown"]
    if unknown:
        log(f"sources: {len(unknown)} un-ingested data file(s): {[u['path'] for u in unknown]}")

    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # Exit code 3 signals "loaded, but something needs a human" (new/missing columns,
    # held ids, or an un-ingested source file), mirroring cm_build.py's
    # unknown-label convention so run_daily can note it.
    gas_flags = any(gas_checks[k] for k in ("conflicts", "unattributed", "unknown_ports", "port_map_mismatch"))
    flags = (any(v["new_columns"] or v["missing_columns"] for v in manifest["drift"].values())
             or bool(held) or bool(unknown) or gas_flags)
    sys.exit(3 if flags else 0)


if __name__ == "__main__":
    main()
