"""Shared configuration for the enigma.continuous_monitoring pipeline."""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Root of the ENIGMA Data Repository copy of field_automated_measurements.
# On dipa this is local disk; on stout it is the NFS mount of the same tree.
FAM_ROOT = Path(os.environ.get("CM_FAM_ROOT", "/data/edr/field_automated_measurements"))
# Working root for code, venv, fetch cache, staged TSVs, state and logs.
# sync_niya.sh excludes its credentials, venv and vendored packages.
WORK_ROOT = Path(os.environ.get("CM_WORK_ROOT", str(FAM_ROOT / "continuous_monitoring")))

FETCH_DIR = WORK_ROOT / "fetch"
STAGING_DIR = WORK_ROOT / "staging"
STATE_DIR = WORK_ROOT / "state"
LOG_DIR = WORK_ROOT / "logs"

NAMESPACE = os.environ.get("CM_NAMESPACE", "enigma.continuous_monitoring")
COLUMN_MAP = HERE / "column_map.json"
CORRECTIONS = HERE / "corrections.json"

TIMESTAMP_COLUMN = "time_series_datetime"
LOCATION_COLUMN = "sdt_location_name"
PROVENANCE_COLUMN = "provenance"
SOURCE_COLUMN = "source_file"
RUN_COLUMN = "ingest_run_id"

FAMILY_PREFIX = {
    "aquatroll600": "hazen_aquatroll600",
    "leveltroll500": "hazen_leveltroll500",
    "weather": "hazen_hobo",
}

IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")


def builder_module():
    """Import tools/build_continuous_monitoring_coral.py from the EDR tree."""
    tools = str(FAM_ROOT / "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    return importlib.import_module("build_continuous_monitoring_coral")


def table_name(family: str, location: str, zone: str) -> str:
    parts = [FAMILY_PREFIX[family], location] + ([zone] if zone else [])
    name = re.sub(r"[^a-z0-9]+", "_", "_".join(parts).lower()).strip("_")
    if not IDENTIFIER.fullmatch(name):
        raise ValueError(f"bad table name {name!r}")
    return name


def load_column_map() -> dict:
    return json.loads(COLUMN_MAP.read_text())


def load_corrections() -> dict:
    return json.loads(CORRECTIONS.read_text())


def load_env_file(path: Path, override: bool = True) -> None:
    """Load KEY=VALUE lines into os.environ.

    By default the file wins over inherited values: a login shell may export
    an older KBASE_AUTH_TOKEN than the one in credentials.env.
    """
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
    return Path(os.environ.get("CM_CREDENTIALS", str(WORK_ROOT / "credentials.env")))
