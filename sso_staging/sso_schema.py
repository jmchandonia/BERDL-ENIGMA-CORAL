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
  * Two Picarro G2508 analyzers run concurrently (A = ORNL-EA-031620, B =
    ORNL-EA-007299; Gas_Data/README.txt, 2026-10-28), each with its own Eosense
    12-port multiplexer and Firesting O2 probe.  The analyzer serial is DATA
    (`picarro_gas.instrument`, part of the dedup key), not microtype context:
    the context keeps the free-text token `instrument=picarro`, so the derived
    column names are unchanged, and at CORAL conversion each analyzer becomes
    its own brick with the serial as brick-level instrument context.
  * `location` means sdt_location (SSO-U2) in CORAL and continuous_monitoring,
    so the field team's well-port string (U2-SZ1) is `well_port`, never
    `location`; the CORAL key is always `sdt_location_name`.
  * `column_typedef` mirrors enigma.coral.sys_ddt_typedef (one row per
    brick-bound column, variables and dimension variables) so conversion is a
    copy with the brick id filled in.  TYPEDEF below assigns every dimension
    column of a brick-bound table to a dimension and (where one exists) a COMO
    term; a NULL term is the conversion to-do list, not an omission.
"""

from __future__ import annotations

import json

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

# context property terms, for column_typedef.original_csv_string (CORAL dump format)
PROPERTY_OTERM = {
    "instrument": "ME:0000012", "method": "ME:0000007", "condition": "ME:0000006", "organic": "ME:0000346",
}
MOLECULE_FROM_LIST = ("molecule from list", "ME:0000381")

# dimension / dimension-variable terms used by column_typedef (the same ones the
# Hazen time-series bricks and the 2024 Chakraborty SSO bricks carry)
DIM_OTERM = {
    "time series": "ME:0000004",
    "environmental sample location": "ME:0000099",
    "environmental sample": "ME:0000100",
}
VAR_OTERM = {
    "datetime": "ME:0000180",
    "Environmental Sample Location ID": "ME:0000228",
    "environmental sample ID": "ME:0000102",
    "date": "ME:0000009",
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
        {"name": "source_file", "src": None, "type": "STRING", "role": "book",
         "desc": "source file the row was built from (workbook name, plus the sheet in brackets when a "
                 "folder of workbooks is read)"},
        {"name": "ingest_run_id", "src": None, "type": "STRING", "role": "fk",
         "desc": "load that wrote the row", "references": "ingest_runs.ingest_run_id"},
        {"name": "ingested_at", "src": None, "type": "TIMESTAMP", "role": "book",
         "desc": "time the row was written (UTC)"},
    ]


# ======================================================================
# picarro_gas  -- append + dedup on (epoch_time, instrument)
# ======================================================================

# The two analyzers and the per-row column signature that tells them apart
# (verified on the 2026-10-28 export: every row reports exactly one of the two).
GAS_INSTRUMENTS = {
    "ORNL-EA-031620": {"label": "A", "model": "Picarro G2508", "signature": "NH3_dry",
                       "note": "reports NH3_dry; no internal O2 probe (O2_% / O2_dry_% empty)"},
    "ORNL-EA-007299": {"label": "B", "model": "Picarro G2508", "signature": "O2_%",
                       "note": "internal O2 probe (O2_% / O2_dry_%); NH3_dry empty"},
}

# Multiplexer port assignments from Gas_Data/README.txt ("as of 10/04/2026 20:00").
# Reference ports carry the README's label and the name the CSV's Port column
# uses for the same channel (10 HighSTD = Std, 11 UHPN2 = N2, 12 Air = ambient
# air dried through a Drierite column = Drierite).  This is the attribution
# table for picarro_gas.picarro_serial; it lives here (versioned) and in the
# docs, not in the lakehouse.  A port move or a new port is an ACTION in the
# daily email (sso_build cross-checks every row's signature against it); edit
# here, then re-stage with sso_build.py --full-gas.
GAS_PORT_VALID_FROM = "2026-10-04T20:00:00-04:00"
GAS_PORT_SOURCE = "Gas_Data/README.txt (updated 2026-10-28)"
_REF_PORTS = [(10, "HighSTD", "Std"), (11, "UHPN2", "N2"), (12, "Air", "Drierite")]
_WELL_PORTS = {
    "ORNL-EA-031620": ["U2-SZ1", "U2-SZ2", "M5-SZ1", "M5-SZ2", "M6-SZ1", "M6-SZ2", "L9-SZ1", "L9-SZ2", "L8-SZ2"],
    "ORNL-EA-007299": ["U1-SZ1", "U1-SZ2", "M4-SZ1", "M4-SZ2", "L7-SZ1", "L7-SZ2", "U3-SZ1", "U3-SZ2", "L8-SZ1"],
}
GAS_PORT_ASSIGNMENT = [
    {"picarro_serial": serial, "picarro_label": GAS_INSTRUMENTS[serial]["label"], "multiplexer_on_state": on_state,
     "well_port": well_port, "reference_channel": reference_channel, "readme_label": readme_label,
     "valid_from": GAS_PORT_VALID_FROM, "source_file": GAS_PORT_SOURCE}
    for serial in GAS_INSTRUMENTS
    for on_state, readme_label, well_port, reference_channel in (
        [(i + 1, wp, wp, None) for i, wp in enumerate(_WELL_PORTS[serial])]
        + [(n, rl, None, ch) for n, rl, ch in _REF_PORTS])
]
# well-port -> analyzer serial (reference channels exist on both, so they are not here)
GAS_WELL_INSTRUMENT = {a["well_port"]: a["picarro_serial"] for a in GAS_PORT_ASSIGNMENT if a["well_port"]}
# (serial, multiplexer port) -> well-port or reference channel, for the on_state cross-check
GAS_PORT_CHANNEL = {(a["picarro_serial"], a["multiplexer_on_state"]): a["well_port"] or a["reference_channel"]
                    for a in GAS_PORT_ASSIGNMENT}

GAS_COLUMNS = [
    {"name": "time_series_datetime", "src": "TIME", "type": "STRING", "role": "dim",
     "desc": "datetime (ISO 8601 with UTC offset, America/New_York, millisecond precision, e.g. "
             "2026-10-06T14:00:00.000-04:00, the same form as continuous_monitoring and the CORAL bricks); "
             "the same instant as epoch_time; compare with to_timestamp(), not as strings"},
    {"name": "epoch_time", "src": "EPOCH_TIME", "type": "DOUBLE", "role": "key",
     "desc": "unix epoch seconds; dedup key together with instrument (the two analyzers run "
             "concurrently and can report the same epoch)"},
    {"name": "picarro_serial", "src": "Port (assignment) / NH3_dry, O2_% (signature)", "type": "STRING", "role": "key",
     "desc": "Picarro G2508 analyzer serial that produced the row: ORNL-EA-031620 (Picarro A) or "
             "ORNL-EA-007299 (Picarro B).  Well-ports per the dated port assignment in sso_schema.py "
             "(Gas_Data/README.txt); reference channels per the row's column signature "
             "(NH3_dry reported = A, O2_% reported = B).  Part of the dedup key"},

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
          molecule="ammonia", context=[("instrument", "picarro"), *CRDS, ("condition", "dry")],
          note="reported only by analyzer A (ORNL-EA-031620); empty on analyzer B rows"),
    _meas("concentration_molecule_from_list_water_percent",
          "H2O_%", "concentration", "percent",
          molecule="water", context=[("instrument", "picarro"), *CRDS]),
    _meas("concentration_molecule_from_list_dioxygen_instrument_picarro_condition_wet_percent",
          "O2_%", "concentration", "percent",
          molecule="dioxygen", context=[("instrument", "picarro"), *CRDS, ("condition", "wet")],
          note="internal O2 probe of analyzer B (ORNL-EA-007299) only; empty on analyzer A rows"),
    _meas("concentration_molecule_from_list_dioxygen_instrument_picarro_condition_dry_percent",
          "O2_dry_%", "concentration", "percent",
          molecule="dioxygen", context=[("instrument", "picarro"), *CRDS, ("condition", "dry")],
          note="internal O2 probe of analyzer B (ORNL-EA-007299) only; empty on analyzer A rows"),
    _meas("concentration_molecule_from_list_dioxygen_instrument_firesting_percent",
          "O2p_%", "concentration", "percent",
          molecule="dioxygen", context=[("instrument", "firesting"), ("method", "optical oxygen sensor")],
          note="Firesting FSO2-4 meter, OXROB3 probe in the serum bottle of each analyzer's system (one probe per analyzer)"),
    _meas("temperature_degree_celsius",
          "TrailerTemp_C", "temperature", "degree Celsius",
          context=[("instrument", "firesting")]),

    _fk_location(),
    {"name": "well_port", "src": "Port", "type": "STRING", "role": "dim",
     "desc": "sampled well-port as the field team writes it, e.g. U2-SZ1 (raw Port); NULL on reference-channel rows"},
    {"name": "reference_channel", "src": "Port", "type": "STRING", "role": "dim",
     "desc": "QC channel on reference rows: Std (span standard, multiplexer port 10), N2 (UHP nitrogen blank, 11), "
             "Drierite (ambient air dried through a Drierite column, 12); NULL on well-port rows"},
    {"name": "zone", "src": "Depth", "type": "STRING", "role": "dim", "desc": "sampling zone of the well-port, SZ1 or SZ2 (raw Depth)"},
    {"name": "multiplexer_on_state", "src": "on_state", "type": "INT", "role": "dim",
     "desc": "Eosense multiplexer live-port state, 1-12; each analyzer has its own multiplexer "
             "(port -> well-port table in sso_schema.py, from Gas_Data/README.txt)"},
    {"name": "cycle_set", "src": "set", "type": "INT", "role": "dim", "desc": "Picarro cycle counter (raw set); counts separately on each analyzer"},
    {"name": "port_seconds", "src": "timedelta", "type": "DOUBLE", "role": "dim",
     "desc": "seconds this port had been monitored (raw timedelta)", "unit": "second"},
    {"name": "firesting_datetime", "src": "DateTime", "type": "STRING", "role": "dim",
     "desc": "Firesting clock reading joined onto the row (30 s cadence), as ISO 8601 with the row's UTC "
             "offset (the source DateTime is Eastern wall clock); traceability of the join only"},
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

def _fk_draw(desc: str) -> dict:
    return {"name": "field_draw_id", "src": None, "type": "STRING", "role": "fk", "desc": desc,
            "references": "field_metadata.field_draw_id"}


FIELD_COLUMNS = [
    {"name": "field_draw_id", "src": "Date (YYYYMMDD) + Well + Pump Time On", "type": "STRING", "role": "pk",
     "desc": "the pumped draw: YYYYMMDD-<well-port>-HHMM of the pump start in America/New_York, e.g. "
             "20261006-L7-SZ1-0832 (CORAL-legal id; the join key from sample_registry and the result tables)"},
    {"name": "timepoint", "src": "Timepoint", "type": "INT", "role": "dim", "desc": "campaign timepoint 1-36"},
    _fk_location(),
    {"name": "well_port", "src": "Well", "type": "STRING", "role": "dim",
     "desc": "sampled well-port as the field team writes it, e.g. U1-SZ1 (EFPW wells have no zone: EFPW02)"},
    {"name": "zone", "src": "Well", "type": "STRING", "role": "dim", "desc": "sampling zone, SZ1 or SZ2; NULL for EFPW (from Well)"},
    {"name": "pump_on_datetime", "src": "Date (YYYYMMDD) + Pump Time On", "type": "STRING", "role": "dim",
     "desc": "pump start as a datetime (ISO 8601 with UTC offset, America/New_York, millisecond precision), "
             "the sheet's date + clock time with AM/PM resolved (field clock hours 1-6 read as PM); the "
             "sample date is its date part; comparable with time_series_datetime in picarro_gas and "
             "continuous_monitoring via to_timestamp()"},
    {"name": "pump_off_datetime", "src": "Date (YYYYMMDD) + Pump Time Off", "type": "STRING", "role": "dim",
     "desc": "pump stop as a datetime (ISO 8601 with UTC offset, America/New_York, millisecond precision), "
             "same derivation as pump_on_datetime; the closest proxy for when the draw's samples were "
             "filled"},

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
    {"name": "timepoint", "src": "Timepoint", "type": "INT", "role": "dim", "desc": "campaign timepoint 1-36"},
    {"name": "sample_date", "src": "Date", "type": "STRING", "role": "dim",
     "desc": "sample date, YYYY-MM-DD (CORAL date form; the manifest writes YYYYMMDD, which the sample id keeps); "
             "the collection instant is the linked draw's pump window (field_draw_id)"},
    _fk_location(),
    {"name": "well_port", "src": "Well", "type": "STRING", "role": "dim", "desc": "sampled well-port as the field team writes it, e.g. U1-SZ1 (EFPW02 for the EFPW wells)"},
    {"name": "zone", "src": "Well", "type": "STRING", "role": "dim", "desc": "sampling zone, SZ1 or SZ2; NULL for EFPW (from Well)"},
    _fk_draw("the field_metadata draw the sample was taken from, matched by sample date + well-port "
             "(or state/draw_overrides.json when a day has several draws of the same well-port); NULL until "
             "the field sheet logs the draw, or while the match is ambiguous (reported as an ACTION)"),
    {"name": "assay", "src": "Assay", "type": "STRING", "role": "dim",
     "desc": "manifest assay label, e.g. Anions, NitrateIso (uppercased, it is the last segment of sdt_sample_name)"},
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
    _fk_location(),
    _fk_draw("the draw the sample came from, copied from the sample's registry row; join to field_metadata "
             "for the pump window (pump_off_datetime is the approximate sampling time)"),
    {"name": "preservation", "src": "Preservation", "type": "STRING", "role": "dim",
     "desc": "sample preservation as recorded by the lab, e.g. '0.2um syringe filter'"},
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
        "dedup_key": ["epoch_time", "picarro_serial"],
        "brick": True,
        "sheet": None,  # CSV
        "columns": GAS_COLUMNS,
        "known_source": GAS_KNOWN_SOURCE,
        "description": "Gas monitoring by two Picarro G2508 CRDS analyzers (A ORNL-EA-031620, B ORNL-EA-007299), "
                       "each with its own Eosense 12-port multiplexer and Firesting O2 probe; one row per analyzer "
                       "cycle step, tagged with the analyzer serial and the live well-port",
    },
    "field_metadata": {
        "load_mode": "full_refresh",
        "brick": True,
        "sheet": "Field Metadata",
        "columns": FIELD_COLUMNS,
        "known_source": FIELD_KNOWN_SOURCE,
        "description": "Per-draw field log keyed by field_draw_id (one pumped draw of a well-port): pump "
                       "window, rate, volume, in-field pH, Restek bag mass; refreshed in full from the source sheet",
    },
    "sample_registry": {
        "load_mode": "upsert",
        "upsert_key": "sdt_sample_name",
        "brick": False,  # becomes sdt_sample rows (a static type), not a brick: no column_typedef rows
        "sheet": "Assay Metadata",
        "columns": REGISTRY_COLUMNS,
        "known_source": REGISTRY_KNOWN_SOURCE,
        "description": "Assay sample manifest; one row per physical sample (the staged form of "
                       "CORAL sdt_sample), upserted by sdt_sample_name, linked to its draw by field_draw_id",
    },
    "toc_tn_anions": {
        "load_mode": "upsert",
        "upsert_key": "sdt_sample_name",
        "brick": True,
        "sheet": None,  # every workbook/sheet in the folder with the known header
        "columns": TOC_COLUMNS,
        "known_source": TOC_KNOWN_SOURCE,
        "description": "Chakraborty lab TOC/TN and ion-chromatography anion (chloride, sulfate, "
                       "nitrate) results, ppm, one row per ANIONS sample; upserted by sdt_sample_name "
                       "from every workbook in the TOC_TN_Anions_Chakraborty source folder; sample context "
                       "via sample_registry, sampling time via field_metadata",
    },
}


# ======================================================================
# column_typedef  -- the sys_ddt_typedef rows these tables become.
# Every non-measurement, non-bookkeeping column of a brick-bound table must be
# assigned here (import fails otherwise), to a dimension and, where a COMO term
# exists, a dimension-variable term.  A column with no term keeps a note saying
# what it becomes at conversion.  Dimension / variable numbers are provisional.
# ======================================================================

TYPEDEF = {
    "picarro_gas": {
        "time_series_datetime": {"dim": "time series", "var": "datetime"},
        "epoch_time": {"dim": "time series", "note": "unix-epoch form of time_series_datetime; dropped at conversion"},
        "picarro_serial": {"dim": "time series", "note": "becomes brick-level context instrument <ME:0000012> "
                           "(one brick per analyzer) at conversion"},
        "sdt_location_name": {"dim": "environmental sample location", "var": "Environmental Sample Location ID"},
        "well_port": {"dim": "environmental sample location", "note": "field label <well>-<zone>; redundant with "
                      "sdt_location_name + zone at conversion"},
        "zone": {"dim": "environmental sample location", "note": "SZ1/SZ2 sampling zone of the well; no COMO term yet "
                 "(the 2024 SSO bricks carry it inside the sample id)"},
        "reference_channel": {"dim": "time series", "note": "QC channel (Std/N2/Drierite); reference rows become a "
                              "separate QC brick or are dropped at conversion"},
        "multiplexer_on_state": {"dim": "time series", "note": "Eosense multiplexer port; instrument bookkeeping, dropped at conversion"},
        "cycle_set": {"dim": "time series", "note": "Picarro cycle counter; instrument bookkeeping, dropped at conversion"},
        "port_seconds": {"dim": "time series", "note": "seconds on port; instrument bookkeeping, dropped at conversion"},
        "firesting_datetime": {"dim": "time series", "note": "Firesting join timestamp; traceability only, dropped at conversion"},
    },
    "field_metadata": {
        "field_draw_id": {"dim": "time series", "note": "staging key of the draw; dropped at conversion (the draw is "
                          "identified by sdt_location_name + pump_on_datetime)"},
        "timepoint": {"dim": "time series", "note": "campaign timepoint 1-36; no COMO term yet (candidate: brick-level context)"},
        "sdt_location_name": {"dim": "environmental sample location", "var": "Environmental Sample Location ID"},
        "well_port": {"dim": "environmental sample location", "note": "field label; redundant with sdt_location_name + zone"},
        "zone": {"dim": "environmental sample location", "note": "SZ1/SZ2 sampling zone; no COMO term yet"},
        "pump_on_datetime": {"dim": "time series", "var": "datetime", "note": "pump start"},
        "pump_off_datetime": {"dim": "time series", "var": "datetime", "note": "pump stop"},
        "field_notes": {"dim": "time series", "note": "free text; becomes the brick's comment context or is dropped"},
    },
    "toc_tn_anions": {
        "sdt_sample_name": {"dim": "environmental sample", "var": "environmental sample ID"},
        "sdt_location_name": {"dim": "environmental sample location", "var": "Environmental Sample Location ID"},
        "field_draw_id": {"dim": "environmental sample", "note": "link to the draw; at conversion the sample's datetime "
                          "context (pump_off_datetime) or dropped"},
        "preservation": {"dim": "environmental sample", "note": "sample attribute; becomes brick-level context at conversion"},
        "analysis_order": {"dim": "environmental sample", "note": "lab run order; dropped at conversion"},
    },
}

# Mirrors enigma.coral.sys_ddt_typedef (same names, comments and STRING types),
# with table_name in place of ddt_ndarray_id and four additions at the end.
COLUMN_TYPEDEF_COLUMNS = {
    "table_name": {"description": "staging table that becomes the brick (ddt_ndarray_id is assigned at CORAL conversion)"},
    "berdl_column_name": {"description": "BERDL column name"},
    "berdl_column_data_type": {"description": "BERDL column data type, variable or dimension_variable"},
    "scalar_type": {"description": "Scalar type"},
    "foreign_key": {"description": "Foreign key reference"},
    "comment": {"description": "Column comment (the CORAL microtype label)"},
    "unit_sys_oterm_id": {"description": "Unit, ontology term CURIE", "type": "foreign_key",
                          "references": "enigma.coral.sys_oterm.sys_oterm_id"},
    "unit_sys_oterm_name": {"description": "Unit"},
    "dimension_number": {"description": "Dimension number, starting at 1, for dimension variables (provisional until CORAL conversion)"},
    "dimension_oterm_id": {"description": "Dimension data type, ontology term CURIE", "type": "foreign_key",
                           "references": "enigma.coral.sys_oterm.sys_oterm_id"},
    "dimension_oterm_name": {"description": "Dimension data type"},
    "variable_number": {"description": "Variable number within a dimension, numbered starting at 1 (provisional until CORAL conversion)"},
    "variable_oterm_id": {"description": "Dimension variable data type, ontology term CURIE", "type": "foreign_key",
                          "references": "enigma.coral.sys_oterm.sys_oterm_id"},
    "variable_oterm_name": {"description": "Dimension variable data type"},
    "original_csv_string": {"description": "Representation of this variable in CORAL's data-dump CSV format, generated from the microtype"},
    # additions (sys_ddt_typedef folds these into comment / original_csv_string)
    "molecule_sys_oterm_id": {"description": "molecule, ontology term CURIE (CHEBI), for concentration variables",
                              "type": "foreign_key", "references": "enigma.coral.sys_oterm.sys_oterm_id"},
    "molecule_sys_oterm_name": {"description": "molecule name"},
    "context_metadata": {"description": "JSON list of [property, value] context pairs (free-text method/condition/instrument)"},
    "note": {"description": "human note: what the column becomes at conversion, instrument caveats"},
}

_SCALAR = {"DOUBLE": "float", "INT": "int", "STRING": "string", "TIMESTAMP": "string"}


def _oterm_token(name: str, oterm_id: str | None) -> str:
    return f"{name} <{oterm_id}>" if oterm_id else name


def measurement_csv_string(n: int, ddt: dict) -> str:
    """CORAL dump format, e.g.
    '1,concentration <ME:0000129>,molecule from list <ME:0000381>,methane <CHEBI:16183>,
     instrument <ME:0000012>,picarro,...,parts per million by volume <ME:0000348>'."""
    parts = [str(n), _oterm_token(ddt["value_type"], ddt["value_oterm"])]
    if ddt.get("molecule"):
        parts += [_oterm_token(*MOLECULE_FROM_LIST), _oterm_token(ddt["molecule"], ddt["molecule_chebi"])]
    for prop, val in ddt["context"]:
        parts += [_oterm_token(prop, PROPERTY_OTERM.get(prop)), str(val)]
    parts.append(_oterm_token(ddt["unit"], ddt["unit_oterm"]))
    return ",".join(parts)


def typedef_rows() -> list[dict]:
    """One row per brick-bound column (variables first, then dimension variables
    in TYPEDEF order), shaped like sys_ddt_typedef."""
    rows = []
    for table, spec in TABLES.items():
        if not spec.get("brick"):
            continue
        cols = {c["name"]: c for c in spec["columns"]}
        book = {c["name"] for c in _bookkeeping()}
        dims = list(dict.fromkeys(v["dim"] for v in TYPEDEF.get(table, {}).values()))
        expected = [n for n, c in cols.items() if c["role"] != "measurement" and n not in book]
        missing = [n for n in expected if n not in TYPEDEF.get(table, {})]
        if missing:
            raise ValueError(f"TYPEDEF[{table!r}] lacks {missing}")
        for n, col in enumerate(measurement_columns(table), 1):
            d = col["ddt"]
            rows.append({
                "table_name": table, "berdl_column_name": col["name"], "berdl_column_data_type": "variable",
                "scalar_type": "float", "foreign_key": None, "comment": microtype_label(d),
                "unit_sys_oterm_id": d["unit_oterm"], "unit_sys_oterm_name": d["unit"],
                "dimension_number": None, "dimension_oterm_id": None, "dimension_oterm_name": None,
                "variable_number": str(n), "variable_oterm_id": d["value_oterm"], "variable_oterm_name": d["value_type"],
                "original_csv_string": measurement_csv_string(n, d),
                "molecule_sys_oterm_id": d["molecule_chebi"], "molecule_sys_oterm_name": d["molecule"],
                "context_metadata": json.dumps(d["context"]), "note": col.get("note"),
            })
        counter = {dim: 0 for dim in dims}
        for name in expected:
            td, col = TYPEDEF[table][name], cols[name]
            dim, var = td["dim"], td.get("var")
            counter[dim] += 1
            dim_no, var_no = dims.index(dim) + 1, counter[dim]
            fk = col.get("references") if col["role"] in ("fk", "pk_fk") else None
            rows.append({
                "table_name": table, "berdl_column_name": name, "berdl_column_data_type": "dimension_variable",
                "scalar_type": "object_ref" if fk else _SCALAR[col["type"]], "foreign_key": fk,
                "comment": var or col["desc"], "unit_sys_oterm_id": None, "unit_sys_oterm_name": col.get("unit"),
                "dimension_number": str(dim_no), "dimension_oterm_id": DIM_OTERM[dim], "dimension_oterm_name": dim,
                "variable_number": str(var_no), "variable_oterm_id": VAR_OTERM[var] if var else None,
                "variable_oterm_name": var,
                "original_csv_string": (f"dmeta,{dim_no + 1},{_oterm_token(dim, DIM_OTERM[dim])},"
                                        f"{_oterm_token(var, VAR_OTERM[var])}") if var else None,
                "molecule_sys_oterm_id": None, "molecule_sys_oterm_name": None, "context_metadata": None,
                "note": td.get("note"),
            })
    return rows


def measurement_columns(table: str) -> list[dict]:
    return [c for c in TABLES[table]["columns"] if c["role"] == "measurement"]


def column_comment_fields(col: dict) -> dict:
    """The JSON-comment payload for a column (matches continuous_monitoring style).
    `source_column` names the source-file header the column is parsed from, so
    the lakehouse records the mapping; the header is taken from THIS schema,
    never from the live file -- a changed header is reported as drift by
    sso_build (NEW/MISSING COLUMN), and the comment changes only when this
    file is edited and the loader is run with --sync-comments."""
    if col["role"] == "measurement":
        ddt = col["ddt"]
        out = {"description": microtype_label(ddt), "unit": ddt["unit"]}
        if ddt["unit_oterm"]:
            out["unit_sys_oterm_id"] = ddt["unit_oterm"]
        if col.get("note"):
            out["note"] = col["note"]
        if col.get("src"):
            out["source_column"] = col["src"]  # the source-file header this column is parsed from
        return out
    out = {"description": col["desc"]}
    if col.get("unit"):
        out["unit"] = col["unit"]
    if col["role"] in ("fk", "pk_fk", "pk"):
        out["type"] = "foreign_key" if col["role"] == "fk" else "primary_key"
        if col.get("references"):
            out["references"] = col["references"]
    if col.get("src"):
        out["source_column"] = col["src"]
    return out
