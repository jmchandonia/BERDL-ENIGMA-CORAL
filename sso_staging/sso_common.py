"""Shared configuration and helpers for the enigma.sso_staging pipeline.

Mirrors continuous_monitoring/cm_common.py so the two namespaces deploy side by
side on the dipa EDR and share the proxy chain and credentials.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Deployment lives at <FAM_ROOT>/sso_staging with code/ beside fetch/, staging/,
# state/, logs/ and credentials.env (same layout as continuous_monitoring).
# WORK_ROOT defaults to that absolute path — NOT the code dir — so fetch/state/
# staging resolve identically no matter the CWD; for local dev set SSO_WORK_ROOT.
FAM_ROOT = Path(os.environ.get("SSO_FAM_ROOT", "/data/edr/field_automated_measurements"))

# Working root for code, venv, fetch cache, staged files, state and logs.
WORK_ROOT = Path(os.environ.get("SSO_WORK_ROOT", str(FAM_ROOT / "sso_staging")))
FETCH_DIR = Path(os.environ.get("SSO_FETCH_DIR", str(WORK_ROOT / "fetch")))
STAGING_DIR = WORK_ROOT / "staging"
STATE_DIR = WORK_ROOT / "state"
LOG_DIR = WORK_ROOT / "logs"

NAMESPACE = os.environ.get("SSO_NAMESPACE", "enigma.sso_staging")

# Source files inside the fetched Drive subfolder ("2026 SSO Time Series Field Data").
GAS_GLOB = "Gas_Data/*_gas_data.csv"
FIELD_FILE = "Field Metadata"       # Google-native xlsx, no extension on the mirror
ASSAY_FILE = "Assay Metadata"       # Google-native xlsx, no extension on the mirror
# Chakraborty-lab TOC/TN + ion-chromatography anion results: every workbook in
# this subfolder is read (the lab may re-export under a new dated name or add a
# sheet); rows are keyed by sample so later files/edits update earlier ones.
TOC_DIR = "TOC_TN_Anions_Chakraborty"

IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")       # lakehouse column / table names
SAMPLE_ID_RE = re.compile(r"^[A-Z0-9-]+$")          # CORAL-legal sdt_sample_name / sdt_location_name

QC_CHANNELS = {"Drierite", "Std", "N2"}             # Picarro reference channels (not wells)


# --- SQL helpers (same shapes as cm_load.py) ---

def sql_string(text: str) -> str:
    return "'" + str(text).replace("\\", "\\\\").replace("'", "\\'") + "'"


def quoted(name: str) -> str:
    if not IDENTIFIER.fullmatch(name):
        raise ValueError(f"invalid identifier {name!r}")
    return f"`{name}`"


def full_name(table: str) -> str:
    return ".".join(f"`{part}`" for part in NAMESPACE.split(".")) + "." + quoted(table)


def comment(description: str, **extra) -> str:
    return json.dumps({"description": description, **{k: v for k, v in extra.items() if v is not None}})


# --- location normalization (NAMING.md) ---

def _sdt_from_well(well: str) -> str:
    """Well id -> CORAL sdt_location_name.  EFPW wells verbatim; others 'SSO-<well>'."""
    return well if well.upper().startswith("EFPW") else f"SSO-{well}"


def gas_location(well: str, depth: str, port: str) -> dict:
    """Map a Picarro row's Well/Depth/Port to location fields (the vectorized
    parser in sso_build applies the same rules).  QC/reference channels
    (Drierite/Std/N2) carry no sdt_location and no well_port.
    """
    well = (well or "").strip()
    depth = (depth or "").strip()
    port = (port or "").strip()
    if well in QC_CHANNELS or port in QC_CHANNELS or not well:
        return {"sdt_location_name": None, "well_port": None, "reference_channel": port or well or None, "zone": None}
    return {"sdt_location_name": _sdt_from_well(well), "well_port": port or f"{well}-{depth}".strip("-"),
            "reference_channel": None, "zone": depth or None}


def spreadsheet_location(well_field: str) -> dict:
    """Map a spreadsheet 'Well' value ('U1-SZ1' or 'EFPW02') to location fields.
    `location` in CORAL means sdt_location, so the field label is `well_port`."""
    raw = (well_field or "").strip()
    if raw.upper().startswith("EFPW"):
        return {"sdt_location_name": raw, "well_port": raw, "zone": ""}
    well, _, zone = raw.partition("-")
    return {"sdt_location_name": _sdt_from_well(well), "well_port": raw, "zone": zone}


# --- sample-id normalization (NAMING.md decision A: faithful uppercase) ---

LAB_SAMPLE_ID_RE = re.compile(r"^(?P<well>[A-Za-z0-9]+)(?:-(?P<zone>SZ\d))?-(?P<mmddyy>\d{6})$")


def parse_lab_sample_id(raw: str) -> dict | None:
    """Chakraborty result-sheet ids are '<well>-<zone>-MMDDYY' (L7-SZ1-100626), or
    '<well>-MMDDYY' for zone-less EFPW wells.  Returns well/zone/sample_date
    (YYYYMMDD, 20xx) or None when the id does not have that shape."""
    m = LAB_SAMPLE_ID_RE.fullmatch((raw or "").strip())
    if not m:
        return None
    mm, dd, yy = m["mmddyy"][:2], m["mmddyy"][2:4], m["mmddyy"][4:]
    if not (1 <= int(mm) <= 12 and 1 <= int(dd) <= 31):
        return None
    return {"well": m["well"].upper(), "zone": (m["zone"] or "").upper(), "sample_date": f"20{yy}{mm}{dd}"}


def registry_sample_name(sample_date: str, well: str, zone: str, assay_token: str) -> str:
    """The manifest's CORAL id for a sample: YYYYMMDD-WELL[-ZONE]-ASSAY."""
    return "-".join(p for p in (sample_date, well, zone, assay_token) if p)

def normalize_sample_id(raw: str) -> str:
    """Uppercase the manifest Sample ID.  Date/well/zone are already caps, so this
    just faithfully uppercases the assay token.  Validation is done separately."""
    return (raw or "").strip().upper()


def legal_id(value: str) -> bool:
    return bool(value) and bool(SAMPLE_ID_RE.fullmatch(value))


# --- env / credentials (same contract as cm_common) ---

def load_env_file(path: Path, override: bool = True) -> None:
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if value[:1] == value[-1:] and value[:1] in {'"', "'"}:
            value = value[1:-1]
        if override or key.strip() not in os.environ:
            os.environ[key.strip()] = value


def credentials_file() -> Path:
    return Path(os.environ.get("SSO_CREDENTIALS", str(WORK_ROOT / "credentials.env")))
