#!/usr/bin/env python3
"""Parse the SSO campaign sources into staged TSVs + a manifest for sso_load.py.

Four sources, three load modes (see sso_schema.py):
  * picarro_gas    - Picarro/Firesting CSV -> append + dedup on (epoch_time,
                     picarro_serial).  Two analyzers run concurrently; each row is
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
GAS_OVERLAP_S = 2.0  # restage a hair of overlap; the loader dedups on (epoch_time, picarro_serial)
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


def iso_date(value: str) -> str:
    """YYYYMMDD -> YYYY-MM-DD (the CORAL date form); anything else is returned as is."""
    s = (value or "").strip()
    return f"{s[:4]}-{s[4:6]}-{s[6:]}" if len(s) == 8 and s.isdigit() else s


def iso_local(date_iso: str, hms: str) -> str:
    """Date (YYYY-MM-DD) + clock time (HH:MM[:SS]) in America/New_York -> ISO 8601
    with UTC offset at millisecond precision (the CORAL / continuous_monitoring
    form of time_series_datetime).  Empty when either part is missing or malformed."""
    if not date_iso or not hms:
        return ""
    try:
        return datetime.fromisoformat(f"{date_iso}T{hms}").replace(tzinfo=EASTERN).isoformat(timespec="milliseconds")
    except ValueError:
        return ""


def draw_id(date_iso: str, well_port: str, hms: str) -> str:
    """field_metadata key: YYYYMMDD-<well-port>-HHMM of the pump start (CORAL-legal)."""
    return f"{date_iso.replace('-', '')}-{well_port}-{hms[:2]}{hms[3:5]}"


def load_draw_overrides(state_dir: Path) -> dict[str, str]:
    """state/draw_overrides.json: {sdt_sample_name: field_draw_id} for samples whose
    day has several draws of the same well-port (settled with the field team)."""
    path = Path(state_dir) / "draw_overrides.json"
    return json.loads(path.read_text()) if path.exists() else {}


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
    """Attribute every gas row to an analyzer and cross-check the rules.

    export     : the CSV's Picarro column ("System A (...)" / "System B (...)", from
                 2026-11-12), matched by schema.GAS_INSTRUMENTS export_prefix
    signature  : NH3_dry reported -> A, O2_% reported -> B (per row, from the CSV)
    assignment : well-port -> analyzer from schema.GAS_WELL_INSTRUMENT (the README table)
    The export column wins where present; otherwise well rows take the assignment
    and reference rows the signature.  Returns (picarro_serial Series, keep mask,
    checks dict).  Rows are HELD (not staged) when the rules disagree (a port was
    moved: edit the assignment, then re-stage with --full-gas), when the Picarro
    column names an analyzer not in GAS_INSTRUMENTS, when no rule applies, or
    when the row names neither a well-port nor a reference channel.
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

    well_port, ref = frame["well_port"], frame["reference_channel"]
    is_well = well_port.notna()
    channel = well_port.where(is_well, ref)  # the one name a row has, for reporting
    assigned = well_port.map(schema.GAS_WELL_INSTRUMENT)
    inferred = pd.Series(np.where(is_well & assigned.notna(), assigned, sig), index=raw.index, dtype=object)

    # The export's own analyzer column (prefix match), where present.
    export_label = raw["Picarro"].str.strip() if "Picarro" in raw else pd.Series("", index=raw.index)
    exported = pd.Series(None, index=raw.index, dtype=object)
    for s, meta in schema.GAS_INSTRUMENTS.items():
        exported = exported.mask(export_label.str.startswith(meta["export_prefix"]), s)
    unknown_analyzer = (export_label != "") & exported.isna()
    serial = exported.where(exported.notna(), inferred)

    conflict = ((is_well & assigned.notna() & sig.notna() & (assigned != sig))
                | (exported.notna() & sig.notna() & (exported != sig))
                | (exported.notna() & is_well & assigned.notna() & (exported != assigned)))
    no_channel = channel.isna()
    unattributed = serial.isna() | no_channel
    unknown_port = is_well & assigned.isna()
    keep = ~(conflict | unattributed | unknown_analyzer)

    def tally(mask, cols):
        if not mask.any():
            return []
        g = pd.DataFrame({c: v[mask] for c, v in cols.items()}).fillna("").groupby(list(cols)).size()
        return [{**dict(zip(cols, k if isinstance(k, tuple) else (k,))), "rows": int(n)} for k, n in g.items()]

    on_state = pd.to_numeric(frame["multiplexer_on_state"], errors="coerce")
    expected = pd.Series([
        schema.GAS_PORT_CHANNEL.get((i, int(o))) if (i is not None and pd.notna(o)) else None
        for i, o in zip(serial, on_state)], index=raw.index, dtype=object)
    port_map_mismatch = keep & expected.notna() & (expected != channel)

    checks = {
        "conflicts": tally(conflict, {"well_port": well_port, "assigned": assigned, "signature": sig, "exported": exported}),
        "unattributed": tally(unattributed & ~conflict & ~unknown_analyzer, {"channel": channel}),
        "unknown_analyzer": tally(unknown_analyzer, {"picarro": export_label}),
        "unknown_ports": tally(unknown_port & keep, {"well_port": well_port, "picarro_serial": serial}),
        "port_map_mismatch": tally(port_map_mismatch, {"picarro_serial": serial, "multiplexer_on_state": on_state,
                                                       "channel": channel, "assigned_channel": expected}),
        "rows_held": int((~keep).sum()),
        "rows_by_serial": {k: int(v) for k, v in serial[keep].value_counts().items()},
    }
    return serial, keep, checks


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
                    "unknown_analyzer": [], "rows_held": 0, "rows_by_serial": {}}

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
    out["time_series_datetime"] = [t.isoformat(timespec="milliseconds") for t in dt]
    # Firesting DateTime is Eastern wall clock with no offset; give it the row's own
    # offset (the two clocks agree to within 30 s, so this is unambiguous even in
    # the fall-back hour) and the same ISO form as time_series_datetime.
    fs = pd.to_datetime(col("DateTime"), format="%Y-%m-%d %H:%M:%S", errors="coerce")
    offset = pd.Series([t.isoformat()[-6:] for t in dt], index=raw.index)
    out["firesting_datetime"] = np.where(fs.notna(), fs.dt.strftime("%Y-%m-%dT%H:%M:%S.000") + offset, "")
    channel = pd.Series(np.where(port != "", port, (well + "-" + depth).str.strip("-")), index=raw.index, dtype=object)
    channel = channel.mask(channel == "", None)
    out["sdt_location_name"] = np.where(is_ref, None, np.where(is_efpw, well, "SSO-" + well))
    out["well_port"] = channel.where(~is_ref, None)
    out["reference_channel"] = channel.where(is_ref, None)
    out["zone"] = np.where(is_ref | (depth == ""), None, depth)
    for c in schema.GAS_COLUMNS:
        src = c.get("src")
        if c["role"] in ("measurement", "dim") and src and src not in ("TIME", "EPOCH_TIME", "DateTime", "Picarro", "Port", "Depth", "Well"):
            out[c["name"]] = raw[src].values if src in raw else ""
    out["source_file"] = paths[-1].name

    serial, keep, checks = gas_instrument_checks(out, raw)
    out["picarro_serial"] = serial
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


def read_field(path: Path) -> tuple[list[dict], dict, list[dict]]:
    """Returns (rows, drift, held).  A draw is keyed by date + well-port + pump start,
    so a row without a pump start time (or a duplicate key) is held and reported."""
    header, records = read_sheet(path, schema.TABLES["field_metadata"]["sheet"])
    d = drift(set(header), schema.FIELD_KNOWN_SOURCE)
    rows, held, seen = [], [], {}
    for rec in records:
        well = cell_to_str(rec.get("Well"))
        date = iso_date(cell_to_str(rec.get("Date (YYYYMMDD)")))
        # Keep only rows with actual field data; skip pre-seeded calendar/blank rows.
        has_data = any(cell_to_str(rec.get(k)) for k in (
            "Pump Time On", "Pump Time Off", "Pump Rate (L/min)", "Total Volume (L)",
            "In-field pH", "In-field Cond (uS/cm)", "Restek Bag Mass (g)", "Field Notes"))
        if not well or not date or not has_data:
            continue
        loc = sso.spreadsheet_location(well)
        on, off = resolve_ampm(rec.get("Pump Time On")), resolve_ampm(rec.get("Pump Time Off"))
        if not iso_local(date, on):
            held.append({"source_sample_id": f"{date} {loc['well_port']}", "normalized": None,
                         "reason": f"field draw without a usable pump start time ({on!r}); the draw cannot be keyed"})
            continue
        key = draw_id(date, loc["well_port"], on)
        if key in seen:
            held.append({"source_sample_id": f"{date} {loc['well_port']}", "normalized": key,
                         "reason": "two field rows with the same date, well-port and pump start"})
            continue
        seen[key] = True
        row = {
            "field_draw_id": key,
            "timepoint": cell_to_str(rec.get("Timepoint")),
            "sdt_location_name": loc["sdt_location_name"],
            "well_port": loc["well_port"],
            "zone": loc["zone"],
            "pump_on_datetime": iso_local(date, on),
            "pump_off_datetime": iso_local(date, off),
            "rate_instrument_pump_liter_per_minute": cell_to_str(rec.get("Pump Rate (L/min)")),
            "volume_liter": cell_to_str(rec.get("Total Volume (L)")),
            "ph_ph": cell_to_str(rec.get("In-field pH")),
            "conductivity_microsiemen_per_centimeter": cell_to_str(rec.get("In-field Cond (uS/cm)")),
            "mass_gram": cell_to_str(rec.get("Restek Bag Mass (g)")),
            "field_notes": cell_to_str(rec.get("Field Notes")),
            "source_file": path.name,
        }
        rows.append(row)
    return rows, d, held


def link_draws(field_rows: list[dict], overrides: dict[str, str]):
    """Returns (resolve, ambiguous): resolve(sample_name, date, well_port) -> field_draw_id
    or "" when no draw is logged yet or several match without an override; the
    ambiguous list collects the unresolved cases for the email."""
    by_key: dict[tuple[str, str], list[str]] = {}
    for r in field_rows:
        by_key.setdefault((r["pump_on_datetime"][:10], r["well_port"]), []).append(r["field_draw_id"])
    known = {r["field_draw_id"] for r in field_rows}
    ambiguous: list[dict] = []

    def resolve(sample_name: str, date_iso: str, well_port: str) -> str:
        if sample_name in overrides:
            if overrides[sample_name] in known:
                return overrides[sample_name]
            ambiguous.append({"sdt_sample_name": sample_name, "candidates": by_key.get((date_iso, well_port), []),
                              "reason": f"draw_overrides.json names {overrides[sample_name]!r}, which is not a logged draw"})
            return ""
        cands = by_key.get((date_iso, well_port), [])
        if len(cands) == 1:
            return cands[0]
        if len(cands) > 1:
            ambiguous.append({"sdt_sample_name": sample_name, "candidates": cands,
                              "reason": "several draws of this well-port that day; add the sample to state/draw_overrides.json"})
        return ""
    return resolve, ambiguous


def read_registry(path: Path, resolve_draw) -> tuple[list[dict], dict, list[dict], int]:
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
        date = iso_date(cell_to_str(rec.get("Date")))
        rows.append({
            "sdt_sample_name": norm,
            "timepoint": cell_to_str(rec.get("Timepoint")),
            "sample_date": date,
            "sdt_location_name": loc["sdt_location_name"],
            "well_port": loc["well_port"],
            "zone": loc["zone"],
            "field_draw_id": resolve_draw(norm, date, loc["well_port"]),
            "assay": assay,
            "storage_condition": cell_to_str(rec.get("Storage Condition")),
            "sample_volume": cell_to_str(rec.get("Volume")),
            "container": cell_to_str(rec.get("Container")),
            "responsible_person": cell_to_str(rec.get("Responsible Person")),
            "pi": cell_to_str(rec.get("PI")),
            "ship_date": cell_to_str(rec.get("Ship Date")),
            "tracking_number": cell_to_str(rec.get("Tracking #")),
            "notes": cell_to_str(rec.get("Notes")),
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
            row = {
                "sdt_sample_name": norm,
                "sdt_location_name": reg["sdt_location_name"],
                "field_draw_id": reg.get("field_draw_id", ""),
                "preservation": cell_to_str(rec.get("Preservation")),
                "analysis_order": cell_to_str(rec.get("ORDER")),
                "source_file": f"{path.name} [{title}]",
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
    log(f"gas: staged {len(gas_rows)} rows {gas_checks['rows_by_serial']}, held {gas_checks['rows_held']}")
    for kind in ("conflicts", "unattributed", "unknown_ports", "port_map_mismatch", "unknown_analyzer"):
        if gas_checks[kind]:
            log(f"gas: {kind}: {gas_checks[kind]}")

    # --- field metadata ---
    field_path = source_dir / sso.FIELD_FILE
    log(f"field_metadata: reading {field_path.name}")
    field_rows, field_drift, field_held = read_field(field_path)
    tsv = write_tsv(args.out, "field_metadata", field_rows)
    manifest["tables"]["field_metadata"] = {
        "tsv": tsv, "load_mode": "full_refresh", "rows": len(field_rows),
        "description": schema.TABLES["field_metadata"]["description"], "source_files": [field_path.name],
    }
    manifest["drift"]["field_metadata"] = field_drift
    manifest["held"]["field_metadata"] = field_held
    log(f"field_metadata: staged {len(field_rows)} rows, held {len(field_held)}")
    resolve_draw, ambiguous = link_draws(field_rows, load_draw_overrides(args.state))

    # --- sample registry ---
    assay_path = source_dir / sso.ASSAY_FILE
    log(f"sample_registry: reading {assay_path.name}")
    reg_rows, reg_drift, held, unassigned = read_registry(assay_path, resolve_draw)
    tsv = write_tsv(args.out, "sample_registry", reg_rows)
    manifest["tables"]["sample_registry"] = {
        "tsv": tsv, "load_mode": "upsert", "upsert_key": "sdt_sample_name", "rows": len(reg_rows),
        "unassigned_skipped": unassigned,
        "description": schema.TABLES["sample_registry"]["description"], "source_files": [assay_path.name],
    }
    manifest["drift"]["sample_registry"] = reg_drift
    manifest["held"]["sample_registry"] = held
    manifest["draw_ambiguous"] = ambiguous
    linked = sum(1 for r in reg_rows if r["field_draw_id"])
    log(f"sample_registry: staged {len(reg_rows)} rows, held {len(held)}, unassigned {unassigned}, "
        f"linked to a draw {linked}, ambiguous {len(ambiguous)}")
    held = field_held + held

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
    gas_flags = any(gas_checks[k] for k in ("conflicts", "unattributed", "unknown_ports", "port_map_mismatch", "unknown_analyzer"))
    flags = (any(v["new_columns"] or v["missing_columns"] for v in manifest["drift"].values())
             or bool(held) or bool(unknown) or gas_flags or bool(ambiguous))
    sys.exit(3 if flags else 0)


if __name__ == "__main__":
    main()
