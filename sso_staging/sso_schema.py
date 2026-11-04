"""Authoritative schema for the enigma.sso_staging namespace.

Single source of truth for all four data tables, their column names, types and
JSON comments, the per-measurement COMO microtype (recorded in `ddt_brick`), and
the set of source-file columns we know how to map.  The parsers, the loader and
the drift check all read from here, so the lakehouse schema and the review docs
in `examples/*.columns.md` stay in lockstep.

Design rules (locked 2026-10-29/30; see PLAN.md / NAMING.md):
  * Measurement column NAMES are CORAL's own derivation from the microtype label,
    minimal context (a context token appears only to break a lakehouse collision).
  * oterm ids never go in a column name -- they live in `ddt_brick`.
  * method / condition / instrument are free-text string-typed COMO properties,
    so their values are not minted.  The one minted term in the namespace is the
    `liter per minute` unit, added to the COMO ontology as ME:0000517
    (coral_import/ontology_update_20261030_liter_per_minute).
"""

from __future__ import annotations

# --- COMO / ontology ids (verified against live enigma.coral + CORAL ontologies 2026-10-30) ---

VALUE_TYPE = {  # measurement term -> sys_oterm id
    "concentration": "ME:0000129",
    "temperature": "ME:0000123",
    "rate": "ME:0000264",
    "volume": "ME:0000360",
    "mass": "ME:0000135",
    "pH": "ME:0000121",
}

MOLECULE_CHEBI = {
    "dinitrogen oxide": "CHEBI:17045",
    "carbon dioxide": "CHEBI:16526",
    "methane": "CHEBI:16183",
    "ammonia": "CHEBI:16134",
    "water": "CHEBI:15377",
    "dioxygen": "CHEBI:15379",
    # aqueous chemistry (toc_tn_anions); same terms as the 2024 Chakraborty
    # SSO bricks (coral_import/sso_geochemistry_20261009)
    "elemental carbon": "CHEBI:33415",
    "nitrogen atom": "CHEBI:25555",
    "chloride": "CHEBI:17996",
    "sulfate": "CHEBI:16189",
    "nitrate": "CHEBI:17632",
}

UNIT_OTERM = {  # unit label -> sys_oterm id
    "parts per million by volume": "ME:0000348",
    "parts per billion": "UO:0000170",
    "parts per million": "UO:0000169",
    "percent": "UO:0000187",
    "degree Celsius": "UO:0000027",
    "liter": "UO:0000099",
    "gram": "UO:0000021",
    "pH": "UO:0000196",
    "second": "UO:0000010",
    # Minted 2026-10-30 as ME:0000517 under ME:0000294 "units not in UO",
    # is_a UO:0000270 "volumetric flow rate unit" (not stock UO; UO only has
    # microliters per minute).  See coral_import/ontology_update_20261030_*.
    "liter per minute": "ME:0000517",
}

CRDS = [("method", "cavity ring-down spectroscopy")]  # Picarro context fragment


def _meas(name, src, value_type, unit, *, molecule=None, context=(), note=None):
    """Build a measurement column spec (DOUBLE) carrying its COMO microtype."""
    return {
        "name": name,
        "src": src,
        "type": "DOUBLE",
        "role": "measurement",
        "note": note,
        "ddt": {
            "value_type": value_type,
            "value_oterm": VALUE_TYPE[value_type],
            "molecule": molecule,
            "molecule_chebi": MOLECULE_CHEBI.get(molecule) if molecule else None,
            "context": list(context),  # ordered [(property, value), ...], free text
            "unit": unit,
            "unit_oterm": UNIT_OTERM[unit],
        },
    }


def microtype_label(ddt: dict) -> str:
    """CORAL microtype label, e.g.
    'concentration, molecule from list=dinitrogen oxide, instrument=picarro,
     method=cavity ring-down spectroscopy, condition=dry'."""
    parts = [ddt["value_type"]]
    if ddt.get("molecule"):
        parts.append(f"molecule from list={ddt['molecule']}")
    parts += [f"{prop}={val}" for prop, val in ddt["context"]]
    return ", ".join(parts)


# --- shared column fragments ---

def _fk_location():
    return {
        "name": "sdt_location_name", "src": None, "type": "STRING", "role": "fk",
        "desc": "environmental sample location ID",
        "references": "enigma.coral.sdt_location.sdt_location_name",
    }


def _bookkeeping():
    return [
        {"name": "provenance", "src": None, "type": "STRING", "role": "book",
         "desc": "data source and source-file date"},
        {"name": "source_file", "src": None, "type": "STRING", "role": "book",
         "desc": "raw source file name the row was built from"},
        {"name": "ingest_run_id", "src": None, "type": "STRING", "role": "fk",
         "desc": "load that wrote the row", "references": "ingest_runs.ingest_run_id"},
        {"name": "ingested_at", "src": None, "type": "TIMESTAMP", "role": "book",
         "desc": "time the row was written (UTC)"},
    ]


# ======================================================================
# picarro_gas  -- append + dedup on epoch_time
# ======================================================================

GAS_COLUMNS = [
    {"name": "time_series_datetime", "src": "TIME", "type": "STRING", "role": "dim",
     "desc": "datetime (ISO 8601 with UTC offset, America/New_York)"},
    {"name": "epoch_time", "src": "EPOCH_TIME", "type": "DOUBLE", "role": "key",
     "desc": "unix epoch seconds; dedup key (one multiplexer port is live at a time)"},

    _meas("concentration_molecule_from_list_dinitrogen_oxide_condition_wet_parts_per_million_by_volume",
          "N2O_ppm", "concentration", "parts per million by volume",
          molecule="dinitrogen oxide", context=[("instrument", "picarro"), *CRDS, ("condition", "wet")]),
    _meas("concentration_molecule_from_list_dinitrogen_oxide_condition_dry_parts_per_million_by_volume",
          "N2O_dry_ppm", "concentration", "parts per million by volume",
          molecule="dinitrogen oxide", context=[("instrument", "picarro"), *CRDS, ("condition", "dry")]),
    _meas("concentration_molecule_from_list_carbon_dioxide_condition_wet_parts_per_million_by_volume",
          "CO2_ppm", "concentration", "parts per million by volume",
          molecule="carbon dioxide", context=[("instrument", "picarro"), *CRDS, ("condition", "wet")]),
    _meas("concentration_molecule_from_list_carbon_dioxide_condition_dry_parts_per_million_by_volume",
          "CO2_dry_ppm", "concentration", "parts per million by volume",
          molecule="carbon dioxide", context=[("instrument", "picarro"), *CRDS, ("condition", "dry")]),
    _meas("concentration_molecule_from_list_methane_condition_wet_parts_per_million_by_volume",
          "CH4_ppm", "concentration", "parts per million by volume",
          molecule="methane", context=[("instrument", "picarro"), *CRDS, ("condition", "wet")]),
    _meas("concentration_molecule_from_list_methane_condition_dry_parts_per_million_by_volume",
          "CH4_dry_ppm", "concentration", "parts per million by volume",
          molecule="methane", context=[("instrument", "picarro"), *CRDS, ("condition", "dry")]),
    _meas("concentration_molecule_from_list_ammonia_condition_wet_parts_per_billion",
          "NH3_ppb", "concentration", "parts per billion",
          molecule="ammonia", context=[("instrument", "picarro"), *CRDS, ("condition", "wet")]),
    _meas("concentration_molecule_from_list_ammonia_condition_dry_parts_per_billion",
          "NH3_dry", "concentration", "parts per billion",
          molecule="ammonia", context=[("instrument", "picarro"), *CRDS, ("condition", "dry")]),
    _meas("concentration_molecule_from_list_water_percent",
          "H2O_%", "concentration", "percent",
          molecule="water", context=[("instrument", "picarro"), *CRDS]),
    _meas("concentration_molecule_from_list_dioxygen_instrument_picarro_condition_wet_percent",
          "O2_%", "concentration", "percent",
          molecule="dioxygen", context=[("instrument", "picarro"), *CRDS, ("condition", "wet")]),
    _meas("concentration_molecule_from_list_dioxygen_instrument_picarro_condition_dry_percent",
          "O2_dry_%", "concentration", "percent",
          molecule="dioxygen", context=[("instrument", "picarro"), *CRDS, ("condition", "dry")]),
    _meas("concentration_molecule_from_list_dioxygen_instrument_firesting_percent",
          "O2p_%", "concentration", "percent",
          molecule="dioxygen", context=[("instrument", "firesting"), ("method", "optical oxygen sensor")]),
    _meas("temperature_degree_celsius",
          "TrailerTemp_C", "temperature", "degree Celsius",
          context=[("instrument", "firesting")]),

    _fk_location(),
    {"name": "location", "src": "Port", "type": "STRING", "role": "dim",
     "desc": "well-port string, e.g. U2-SZ1 (raw Port); QC channel name for reference channels"},
    {"name": "zone", "src": "Depth", "type": "STRING", "role": "dim", "desc": "port zone, SZ1 or SZ2 (raw Depth)"},
    {"name": "well", "src": "Well", "type": "STRING", "role": "dim", "desc": "well id, e.g. U2 (raw Well)"},
    {"name": "channel_type", "src": None, "type": "STRING", "role": "dim",
     "desc": "well (a sampled well-port) or reference (Drierite/Std/N2 QC channel)"},
    {"name": "multiplexer_on_state", "src": "on_state", "type": "INT", "role": "dim",
     "desc": "Eosense multiplexer live-port state"},
    {"name": "cycle_set", "src": "set", "type": "INT", "role": "dim", "desc": "Picarro cycle counter (raw set)"},
    {"name": "port_seconds", "src": "timedelta", "type": "DOUBLE", "role": "dim",
     "desc": "seconds this port had been monitored (raw timedelta)", "unit": "second"},
    {"name": "firesting_datetime", "src": "DateTime", "type": "STRING", "role": "dim",
     "desc": "Firesting time used to join the frames (traceability)"},
    *_bookkeeping(),
]

# Gas source headers we know how to handle (anything else => drift/flag).
# The file carries a leading UNNAMED index column (header field 1 blank); the
# parser reads by header name, so the index column is simply ignored.
GAS_KNOWN_SOURCE = {
    "TIME", "EPOCH_TIME", "N2O_ppm", "N2O_dry_ppm", "CO2_ppm", "CO2_dry_ppm",
    "CH4_ppm", "CH4_dry_ppm", "H2O_%", "NH3_ppb", "NH3_dry", "O2_%", "O2_dry_%",
    "on_state", "timedelta", "set", "DateTime", "O2p_%", "TrailerTemp_C",
    "Port", "Depth", "Well",
}

# ======================================================================
# field_metadata  -- full refresh from source (no stable unique key: a
# timepoint x well can have several draws); shrink-guarded.
# ======================================================================

FIELD_COLUMNS = [
    {"name": "timepoint", "src": "Timepoint", "type": "INT", "role": "dim", "desc": "campaign timepoint 1-36"},
    {"name": "sample_date", "src": "Date (YYYYMMDD)", "type": "STRING", "role": "dim", "desc": "sample date, YYYYMMDD"},
    _fk_location(),
    {"name": "location", "src": "Well", "type": "STRING", "role": "dim",
     "desc": "well-port string, e.g. U1-SZ1 (EFPW wells have no zone)"},
    {"name": "zone", "src": None, "type": "STRING", "role": "dim", "desc": "port zone, SZ1 or SZ2; empty for EFPW"},
    {"name": "well", "src": None, "type": "STRING", "role": "dim", "desc": "well id, e.g. U1"},
    {"name": "pump_time_on", "src": "Pump Time On", "type": "STRING", "role": "dim",
     "desc": "pump start HH:MM:SS, AM/PM resolved (field clock hours 1-6 read as PM)"},
    {"name": "pump_time_off", "src": "Pump Time Off", "type": "STRING", "role": "dim",
     "desc": "pump stop HH:MM:SS, AM/PM resolved (field clock hours 1-6 read as PM)"},

    _meas("rate_instrument_pump_liter_per_minute", "Pump Rate (L/min)", "rate", "liter per minute",
          context=[("instrument", "pump")]),
    _meas("volume_liter", "Total Volume (L)", "volume", "liter"),
    _meas("ph_ph", "In-field pH", "pH", "pH"),
    _meas("mass_gram", "Restek Bag Mass (g)", "mass", "gram",
          note="gross as-weighed mass of the Restek gas-sampling bag (includes bag tare; "
               "not net gas mass -- verified from data 2026-10-30, ~95-116 g, bag-dominated)"),

    {"name": "field_notes", "src": "Field Notes", "type": "STRING", "role": "dim", "desc": "field notes, free text"},
    *_bookkeeping(),
]

FIELD_KNOWN_SOURCE = {
    "Timepoint", "Date (YYYYMMDD)", "Well", "Pump Time On", "Pump Time Off",
    "Pump Rate (L/min)", "Total Volume (L)", "In-field pH", "Restek Bag Mass (g)", "Field Notes",
}

# ======================================================================
# sample_registry  -- upsert (MERGE) by sdt_sample_name; no COMO measurements.
# ======================================================================

REGISTRY_COLUMNS = [
    {"name": "sdt_sample_name", "src": "Sample ID", "type": "STRING", "role": "pk_fk",
     "desc": "environmental sample ID; normalized CORAL id (assay token uppercased), validated ^[A-Z0-9-]+$",
     "references": "enigma.coral.sdt_sample.sdt_sample_name"},
    {"name": "source_sample_id", "src": "Sample ID", "type": "STRING", "role": "dim",
     "desc": "verbatim manifest Sample ID (traceability)"},
    {"name": "timepoint", "src": "Timepoint", "type": "INT", "role": "dim", "desc": "campaign timepoint 1-36"},
    {"name": "sample_date", "src": "Date", "type": "STRING", "role": "dim", "desc": "sample date, YYYYMMDD"},
    _fk_location(),
    {"name": "location", "src": "Well", "type": "STRING", "role": "dim", "desc": "well-port string, e.g. U1-SZ1"},
    {"name": "zone", "src": None, "type": "STRING", "role": "dim", "desc": "port zone, SZ1 or SZ2; empty for EFPW"},
    {"name": "assay", "src": "Assay", "type": "STRING", "role": "dim", "desc": "raw manifest assay label, e.g. Anions, NitrateIso"},
    {"name": "assay_token", "src": None, "type": "STRING", "role": "dim", "desc": "uppercased assay token used in the id, e.g. ANIONS"},
    {"name": "storage_condition", "src": "Storage Condition", "type": "STRING", "role": "dim", "desc": "e.g. '4C, acidified', '-80C'"},
    {"name": "sample_volume", "src": "Volume", "type": "STRING", "role": "dim", "desc": "planned sample volume as recorded, e.g. '30 mL' (registry attribute, not a measurement)"},
    {"name": "container", "src": "Container", "type": "STRING", "role": "dim", "desc": "container as recorded, e.g. '30 mL VOA vial', 'Restek Bags'"},
    {"name": "responsible_person", "src": "Responsible Person", "type": "STRING", "role": "dim", "desc": "person responsible for the sample"},
    {"name": "pi", "src": "PI", "type": "STRING", "role": "dim", "desc": "principal investigator"},
    {"name": "ship_date", "src": "Ship Date", "type": "STRING", "role": "dim", "desc": "ship date, YYYYMMDD, or empty"},
    {"name": "tracking_number", "src": "Tracking #", "type": "STRING", "role": "dim", "desc": "shipment tracking number, or empty"},
    {"name": "notes", "src": "Notes", "type": "STRING", "role": "dim", "desc": "manifest notes, free text"},
    *_bookkeeping(),
]

REGISTRY_KNOWN_SOURCE = {
    "Timepoint", "Date", "Well", "Assay", "Sample ID", "Storage Condition",
    "Volume", "Notes", "Container", "Responsible Person", "PI", "Ship Date", "Tracking #",
}

# ======================================================================
# toc_tn_anions  -- upsert (MERGE) by sdt_sample_name: Chakraborty-lab TOC/TN
# and ion-chromatography anion results on the campaign's ANIONS samples (the
# lab's 0.2 um syringe-filtered, 4C vial).  Microtypes match the lab's 2024 SSO
# bricks (chakraborty_toc_tn_* / chakraborty_ic_anions_*): TOC = elemental
# carbon, organic=1 (the organic token stays in the name because coral's
# `..._elemental_carbon_parts_per_million` is TOTAL carbon); TN = nitrogen atom;
# anions as the ion; all parts per million as the lab reports them.
# ======================================================================

TOC_COLUMNS = [
    # Declared as a foreign key (like coral's brick tables), not a primary key:
    # the results attach to a registry sample; one-row-per-sample is enforced by
    # the upsert, and the FK checker can validate it against sample_registry.
    {"name": "sdt_sample_name", "src": "SampleID", "type": "STRING", "role": "fk",
     "desc": "environmental sample ID of the ANIONS sample the results belong to "
             "(YYYYMMDD-WELL-ZONE-ANIONS, derived from the lab id <well>-<zone>-MMDDYY); upsert key",
     "references": "sample_registry.sdt_sample_name"},
    {"name": "source_sample_id", "src": "SampleID", "type": "STRING", "role": "dim",
     "desc": "verbatim lab sample id, e.g. L7-SZ1-100626 (traceability)"},
    {"name": "timepoint", "src": None, "type": "INT", "role": "dim",
     "desc": "campaign timepoint 1-36 (from the sample registry)"},
    {"name": "sample_date", "src": "Date Sampled", "type": "STRING", "role": "dim", "desc": "sample date, YYYYMMDD"},
    _fk_location(),
    {"name": "location", "src": "Well", "type": "STRING", "role": "dim", "desc": "well-port string, e.g. L7-SZ1"},
    {"name": "zone", "src": "Zone", "type": "STRING", "role": "dim", "desc": "port zone, SZ1 or SZ2; empty for EFPW"},
    {"name": "well", "src": "Well", "type": "STRING", "role": "dim", "desc": "well id, e.g. L7"},
    {"name": "preservation", "src": "Preservation", "type": "STRING", "role": "dim",
     "desc": "sample preservation as recorded by the lab, e.g. '0.2um syringe filter'"},
    {"name": "storage_condition", "src": "Storage", "type": "STRING", "role": "dim",
     "desc": "sample storage as recorded by the lab, e.g. '4C'"},
    {"name": "analysis_order", "src": "ORDER", "type": "INT", "role": "dim",
     "desc": "lab run order of the sample (raw ORDER)"},

    _meas("concentration_molecule_from_list_elemental_carbon_organic_1_parts_per_million",
          "TOC_ppm", "concentration", "parts per million",
          molecule="elemental carbon", context=[("organic", "1")],
          note="total organic carbon of the 0.2 um filtered sample, as reported by the lab"),
    _meas("concentration_molecule_from_list_nitrogen_atom_parts_per_million",
          "TN_ppm", "concentration", "parts per million", molecule="nitrogen atom",
          note="total nitrogen of the 0.2 um filtered sample, as reported by the lab"),
    _meas("concentration_molecule_from_list_chloride_parts_per_million",
          "Chloride_ppm", "concentration", "parts per million", molecule="chloride"),
    _meas("concentration_molecule_from_list_sulfate_parts_per_million",
          "Sulfate_ppm", "concentration", "parts per million", molecule="sulfate"),
    _meas("concentration_molecule_from_list_nitrate_parts_per_million",
          "Nitrate_ppm", "concentration", "parts per million", molecule="nitrate",
          note="reported as the nitrate ion (NO3-)"),
    *_bookkeeping(),
]

TOC_KNOWN_SOURCE = {
    "ORDER", "SampleID", "Preservation", "Storage", "Date Sampled", "Well", "Zone",
    "TOC_ppm", "TN_ppm", "Chloride_ppm", "Sulfate_ppm", "Nitrate_ppm",
}
# Headers that identify a workbook sheet as this layout (anything else in the
# folder is left to the source inventory to flag).
TOC_REQUIRED_SOURCE = {"SampleID", "TOC_ppm", "TN_ppm"}

# ======================================================================

TABLES = {
    "picarro_gas": {
        "load_mode": "append_dedup",
        "dedup_key": "epoch_time",
        "sheet": None,  # CSV
        "columns": GAS_COLUMNS,
        "known_source": GAS_KNOWN_SOURCE,
        "description": "Picarro CRDS + Eosense multiplexer + Firesting O2 gas monitoring; "
                       "one row per analyzer cycle step, tagged with the live well-port",
    },
    "field_metadata": {
        "load_mode": "full_refresh",
        "sheet": "Field Metadata",
        "columns": FIELD_COLUMNS,
        "known_source": FIELD_KNOWN_SOURCE,
        "description": "Per-draw field log (timepoint x well-port): pump times/rate/volume, "
                       "in-field pH, Restek bag mass; refreshed in full from the source sheet",
    },
    "sample_registry": {
        "load_mode": "upsert",
        "upsert_key": "sdt_sample_name",
        "sheet": "Assay Metadata",
        "columns": REGISTRY_COLUMNS,
        "known_source": REGISTRY_KNOWN_SOURCE,
        "description": "Assay sample manifest; one row per physical sample (the staged form of "
                       "CORAL sdt_sample), upserted by sdt_sample_name",
    },
    "toc_tn_anions": {
        "load_mode": "upsert",
        "upsert_key": "sdt_sample_name",
        "sheet": None,  # every workbook/sheet in the folder with the known header
        "columns": TOC_COLUMNS,
        "known_source": TOC_KNOWN_SOURCE,
        "description": "Chakraborty lab TOC/TN and ion-chromatography anion (chloride, sulfate, "
                       "nitrate) results, ppm, one row per ANIONS sample; upserted by sdt_sample_name "
                       "from every workbook in the TOC_TN_Anions_Chakraborty source folder",
    },
}


def measurement_columns(table: str) -> list[dict]:
    return [c for c in TABLES[table]["columns"] if c["role"] == "measurement"]


def column_comment_fields(col: dict) -> dict:
    """The JSON-comment payload for a column (matches continuous_monitoring style)."""
    if col["role"] == "measurement":
        ddt = col["ddt"]
        out = {"description": microtype_label(ddt), "unit": ddt["unit"]}
        if ddt["unit_oterm"]:
            out["unit_sys_oterm_id"] = ddt["unit_oterm"]
        if col.get("note"):
            out["note"] = col["note"]
        return out
    out = {"description": col["desc"]}
    if col.get("unit"):
        out["unit"] = col["unit"]
    if col["role"] in ("fk", "pk_fk"):
        out["type"] = "foreign_key" if col["role"] == "fk" else "primary_key"
        if col.get("references"):
            out["references"] = col["references"]
    return out
