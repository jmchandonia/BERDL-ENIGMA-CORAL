#!/usr/bin/env python3
"""Build the CORAL import package for the 2020 cone penetrometer (CPT) physical data, FRC Area 3.

* `hazen_fugro_cpt_profiles_area3_2020`: the 94 Fugro piezocone soundings (13-27 October 2020), one
  row per 2 cm reading: tip resistance, sleeve friction, u2 pore pressure (tsf) and the Robertson 1986
  soil behavior type, from Fugro's per-bore CSV exports (`CPT_Oct2020_Fugro_Data/CPT-*.csv`).
* `hazen_fugro_cpt_soundings_area3_2020`: one row per sounding: start time, cone serial number,
  depth reached and ground elevation (Location sheet of `CPT_full_data.xlsx`).
* `hazen_manual_water_level_area3_cpt_2020`: 74 manual depth-to-water readings from the top of casing
  (`Water Level Master 20201020.xlsx`, AREA 3 folder), 15 and 20 October 2020.

Static additions: Location CPT65 (probe bore beside CPT65S) and seven FRC Area 3 wells read in the
water-level survey (FW-025, FW-122, FW-131, FW-132, FW-130-40, FW-130-44, FW-133); two Protocols.
Ontology: the new `robertson_soil_behavior_type.obo` and COMO ME:0000518 (ton per square foot), from
`coral_import/ontology_update_20261104_cpt/production/`, must be installed and reloaded first.

The `ProbeData` sheet of CPT_full_data.xlsx is NOT used: it holds every reading twice (two metre
roundings of the same foot depth). Fugro's friction ratio column is not stored: it is
round(sleeve friction / tip resistance * 100, 2), clipped at 10.0 (95 readings).

Run with the BERIL venv python (openpyxl):
    python tools/build_cpt_physical_coral_import.py
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_sso_batch_ab_coral_import as ab  # noqa: E402
from build_sso_batch_ab_coral_import import T, NAMES, brick, comment, ctx, float_var, oterm_value, sval, typed, write_process  # noqa: E402

REPO = ab.REPO
TEAM = ab.DRIVE
RELEASE = "20261105"
TAG = f"cpt_physical_{RELEASE}"
OUT = REPO / f"coral_import/{TAG}"
EXPORT = REPO / "sync-coral-to-berdl/exports/sync-20261103-153558/coral_export/static_tsv"
WELL_BRICK = REPO / "sync-coral-to-berdl/exports/sync-20261103-153558/berdl_upload/data/Brick0001698.tsv"
STAGED = Path("/tmp/claude-1000/-scratch-jmc-BERDL-ENIGMA-CORAL/e08931f7-7c7d-4424-a1ff-a5f1bad88ee0/scratchpad/stagedval")
ONT_PATCH = REPO / "coral_import/ontology_update_20261104_cpt/production"
CPT = TEAM / "2020_Cone Penetrometer Sampling"
RAW_DIR = CPT / "CPT_Oct2020_Fugro_Data"
RESTORED = CPT / "2024_0418_Putt's Restored CPT Data from TCH Hard Drive"
FULL = CPT / "CPT Metadata FINAL/CPT_full_data.xlsx"
WL = RESTORED / "2020 CPT Fugro/AREA 3/Water Level Master 20201020.xlsx"
WL_RENAMED = CPT / "Manuscript/Jupyter notebooks/data_cpt/Water Level Master 20201020_name_change.xlsx"
GE = REPO / "All_Wells_ConstructionData_GoogleEarthTags.xlsx"
CAMPAIGN = "Cone Penetrometer Survey <ENIGMA:0000165>"
PERSON = "Hazen Lab <ENIGMA:0000066>"
OFFSET = "-04:00"  # EDT: October 2020 is before the 2020-11-01 change
FT_PER_M = 1 / 0.3048
PROTO_CPT = "fugro-piezocone-cpt-frc-area3-2020"
PROTO_WL = "manual-water-level-tape-frc-area3-2020"

T.update({
    "physical measurement": "DA:0000002", "Cone Penetrometer Survey": "ENIGMA:0000165", "datetime": "ME:0000180",
    "foot": "ME:0000310", "top": "ME:0000311", "bottom": "ME:0000312", "pressure": "ME:0000181",
    "water pressure": "ME:0000315", "elevation": "ME:0000220", "ton per square foot": "ME:0000518",
    "soil behavior type classification": "SBT:0000002",
})
SBT_ZONE_TERM = {z: f"SBT:{11 + z:07d}" for z in range(13)}
# Fugro's label and USCS group for each Robertson 1986 zone, as printed in the CSV exports.
SBT_TABLE = {
    0: ("<out of range>", ""), 1: ("Sensitive Fine-Grained", "OL-CH"), 2: ("Organic Material", "OL-OH"), 3: ("Clay", "CH"),
    4: ("Silty clay to clay", "CL-CH"), 5: ("Clayey Silt to Silty Clay", "MH-CL"), 6: ("Sandy Silt to Clayey Silt", "ML-MH"),
    7: ("Silty Sand to Sandy Silt", "SM-ML"), 8: ("Sand to Silty Sand", "SM-SP"), 9: ("Sand", "SW-SP"),
    10: ("Gravelly Sand to Sand", "SW-GW"), 11: ("Very Stiff Fine Grained (*)", "CH-CL"), 12: ("Sand to Clayey Sand (*)", "SC-SM"),
}
CONE_MODEL = "Fugro CP15 piezocone, CF75PB7SN2-P1E1 (CF25PB7SN2-P1E1 for serial 2111)"
# Putt's port renames (Water Level Master 20201020_name_change.xlsx), checked against that file below.
WL_RENAME = {"FW107-tall": "FW107-43", "FW107-short": "FW107-48", "FW108-1": "FW108-35", "FW113-2": "FW113-32",
             "FW113-3": "FW113-38", "FW130-1": "FW130-40", "FW130-2": "FW130-44", "FW130-3": "FW130-50"}
WL_PORT_PARENT = {"FW133-1": "FW133", "FW133-2": "FW133", "FW134-1": "FW134", "FW134-2": "FW134", "FW134-3": "FW134"}
WL_PHANTOM = {"FW114-57", "FW114-short"}  # FW-114 is a 20 ft single-port well; no Area 3 well has a 57 ft port
NEW_WELLS = ["FW025", "FW122", "FW131", "FW132", "FW130-40", "FW130-44", "FW133"]  # coordinates from the Google Earth sheet


def rel(p: Path) -> str:
    return f"ENIGMA team Google Drive {p.relative_to(TEAM)}"


def stage_validator() -> None:
    """CheckGenericStaged reads STAGED/ont; ab.load_ontology_names reads STAGED/names. Both get the patched COMO and the SBT ontology."""
    for d in ("names", "ont"):
        for f in ("context_measurement_ontology.obo", "robertson_soil_behavior_type.obo"):
            (STAGED / d / f).write_bytes((ONT_PATCH / f).read_bytes())
    ab.ONTOLOGIES = STAGED / "names"
    cp = (STAGED / "classpath.txt").read_text().strip()

    def run(json_path):
        proc = subprocess.run(["java", "-Xmx8g", "-cp", cp, "gov.lbl.enigma.app.CheckGenericStaged", str(json_path)], capture_output=True, text=True)
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0 and "Generic is OK!" in out, out
    ab.run_checkgeneric = run


def coral_name(fugro: str) -> str:
    """CPT-01 -> CPT1, CPT-25A -> CPT25A, CPT10SED -> CPT10S (CORAL's names)."""
    m = re.match(r"CPT-?0*(\d+)([A-Z]*?)(SED)?$", fugro.strip().upper())
    if not m:
        raise ValueError(f"unexpected bore name {fugro!r}")
    return f"CPT{m.group(1)}{m.group(2)}{'S' if m.group(3) else ''}"


def bore_key(name: str):
    m = re.match(r"CPT(\d+)([A-Z]*)$", name)
    return (int(m.group(1)), m.group(2))


def loc_ref(names: list[str]) -> dict:
    return {"value_type": ab.term("environmental sample location ID"), "values": {"scalar_type": "object_ref", "object_refs": names, "string_values": names}}


# ----------------------------------------------------------------------------
# Fugro soundings
# ----------------------------------------------------------------------------

def read_fugro() -> dict[str, dict]:
    """One record per bore: header fields and readings (depth ft, tip, friction, pore pressure, ratio, zone, label, USCS)."""
    files = {}
    for p in sorted(RAW_DIR.glob("CPT-*.csv")) + sorted(RESTORED.rglob("CPT-*.csv")):
        files.setdefault(p.name, p)  # the Oct 2020 export folder wins; the restored tree repeats it
    bores = {}
    for name, p in sorted(files.items()):
        hdr, rows = {}, []
        with p.open(encoding="latin-1") as h:
            for line in h:
                parts = [x.strip() for x in line.rstrip("\r\n").split(",")]
                if not parts or not parts[0]:
                    continue
                if parts[0].startswith("CPT Number"):
                    hdr["number"] = parts[1]
                elif parts[0].startswith("Test Date and Time"):
                    hdr["datetime"] = dt.datetime.strptime(parts[1], "%d-%b-%Y %H:%M:%S")
                elif parts[0].startswith("Cone Number"):
                    hdr["cone"] = parts[1]
                elif parts[0].startswith("Operator"):
                    hdr["operator"] = parts[0].split(None, 1)[1]
                elif parts[0] == "Depth":
                    hdr["columns"] = parts
                elif parts[0] == "(feet)":
                    hdr["units"] = parts
                elif parts[0][0].isdigit():
                    if len(parts) < 7:
                        raise ValueError(f"{p.name}: short data row {parts}")
                    rows.append((float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]), int(parts[5]),
                                 parts[6], parts[7] if len(parts) > 7 else ""))
        if hdr.get("columns") != ["Depth", "Tip", "Friction", "Pore Pressure", "Ratio", "SBT", "Soil Behavior Type", "U.S.C.S."]:
            raise ValueError(f"{p.name}: unexpected columns {hdr.get('columns')}")
        if hdr.get("units")[:5] != ["(feet)", "(tsf)", "(tsf)", "(tsf)", "(%)"]:
            raise ValueError(f"{p.name}: unexpected units {hdr.get('units')}")
        if hdr["number"] != p.stem or hdr.get("operator") != "Bobby Brandt":
            raise ValueError(f"{p.name}: header mismatch {hdr}")
        bores[hdr["number"]] = {"path": p, "rows": rows, **hdr}
    return bores


def check_fugro(bores: dict) -> dict:
    stats = Counter()
    for b, rec in bores.items():
        rows = rec["rows"]
        for i, r in enumerate(rows):
            depth, tip, fr, pore, ratio, zone, label, uscs = r
            if SBT_TABLE[zone] != (label, uscs):
                raise ValueError(f"{b}: zone {zone} labelled {label!r}/{uscs!r}")
            if i and depth <= rows[i - 1][0]:
                raise ValueError(f"{b}: depth not increasing at {depth}")
            calc = fr / tip * 100 if tip else 0.0
            if abs(round(calc, 2) - ratio) <= 0.011:
                stats["ratio_identity"] += 1
            elif ratio == 10.0 and calc > 10:
                stats["ratio_capped"] += 1
            else:
                raise ValueError(f"{b}: friction ratio {ratio} != {calc:.2f} at {depth} ft")
            stats["readings"] += 1
            stats[f"zone_{zone}"] += 1
            stats["negative_u2"] += pore < 0
    return dict(stats)


def location_sheet() -> dict[str, dict]:
    ws = openpyxl.load_workbook(FULL, read_only=True, data_only=True)["Location"]
    rows = [r for r in ws.iter_rows(values_only=True) if r and r[0] and str(r[0]).startswith("CPT")]
    hdr = next(ws.iter_rows(values_only=True, max_row=1))
    if [str(c).strip() for c in hdr[1:7]] != ["Easting", "Northing", "Elevation_AMSL", "dd_lon", "dd_lat", "TotalDepth_M"]:
        raise ValueError(f"Location sheet header changed: {hdr[:7]}")
    return {str(r[0]).strip(): {"elevation_m": float(r[3]), "lon": float(r[4]), "lat": float(r[5]), "total_depth_m": float(r[6])} for r in rows}


def fugro_context(bores: dict, extra: list[dict]) -> list[dict]:
    n_files = len(bores)
    return [
        ctx("ENIGMA campaign", oterm_value("Cone Penetrometer Survey")), ctx("personnel", oterm_value("Hazen Lab")),
        ctx("instrument", sval(CONE_MODEL)),
        comment(f"Source: {rel(RAW_DIR)}/CPT-NN.csv, Fugro's per-bore exports ({n_files} files; CPT crew operator Bobby Brandt, job 04.00168068), "
                "plus the Location sheet of CPT Metadata FINAL/CPT_full_data.xlsx for ground elevations"),
    ] + extra


def build_profiles(bores: dict, locations: set[str]) -> tuple[dict, list[str]]:
    order = sorted(bores, key=lambda b: bore_key(coral_name(b)))
    locs, depths, tips, frs, pores, zones, labels = [], [], [], [], [], [], []
    for b in order:
        name = coral_name(b)
        for depth, tip, fr, pore, ratio, zone, label, uscs in bores[b]["rows"]:
            locs.append(name); depths.append(depth); tips.append(tip); frs.append(fr); pores.append(pore)
            zones.append(SBT_ZONE_TERM[zone]); labels.append(label)
    dim = {"data_type": ab.term("depth"), "size": len(locs), "typed_values": [
        loc_ref(locs),
        float_var("depth", "foot", [ctx("top", sval("ground surface"))], depths)]}
    variables = [
        float_var("pressure", "ton per square foot", [ctx("method", sval("CPT tip resistance"))], tips),
        float_var("pressure", "ton per square foot", [ctx("method", sval("CPT sleeve friction"))], frs),
        float_var("water pressure", "ton per square foot", [ctx("method", sval("CPT piezocone u2")), ctx("relative", sval("atmospheric pressure"))], pores),
        {"value_type": ab.term("soil behavior type classification"), "values": {"scalar_type": "oterm_ref", "oterm_refs": zones, "string_values": labels}},
    ]
    zone_table = "; ".join(f"{z} = {SBT_TABLE[z][0].replace(' (*)', '')}" + (f" ({SBT_TABLE[z][1]})" if SBT_TABLE[z][1] else "") for z in range(13))
    array_context = fugro_context(bores, [
        comment("Variables: cone tip resistance q_c and sleeve friction f_s (tons per square foot, as exported); u2 pore pressure at the shoulder filter behind "
                "the tip, a gauge pressure zeroed to atmospheric at the surface, so negative values (58% of readings, floor about -1 atm) mean suction above the "
                "water table or a dilatant response in dense sand and stiff or cemented fine-grained soil; Robertson et al. (1986) soil behavior type zone as an "
                "ontology term, with Fugro's label as the string value"),
        comment(f"Robertson 1986 zones with Fugro's labels and USCS groups: {zone_table}; zones 11 and 12 are overconsolidated or cemented; zone 0 is Fugro's "
                "'out of range' (no classification) and is kept as its own term, not null"),
        comment("Fugro's friction ratio column is not stored: in every reading it equals round(f_s / q_c * 100, 2), clipped at 10.0 in 95 readings; "
                "the ProbeData sheet of CPT_full_data.xlsx was not used because it lists each reading twice under two metre roundings"),
        comment("Readings every 2 cm (0.065 ft); depth is the cone tip depth below ground surface in feet; bores have 46 to 445 readings on their own depth "
                "vectors, hence one row per reading with the bore as a dimension variable. Per-bore start time, cone serial, depth reached and ground "
                "elevation are in hazen_fugro_cpt_soundings_area3_2020"),
    ])
    obj = brick("hazen_fugro_cpt_profiles_area3_2020",
                "Fugro piezocone penetration test profiles at 94 CPT bores in FRC Area 3, 13-27 October 2020: cone tip resistance, sleeve friction, u2 pore pressure "
                "and Robertson 1986 soil behavior type at each 2 cm push interval, from Fugro's per-bore CSV exports in native units (feet, tons per square foot)",
                "physical measurement", array_context, [dim], variables)
    return obj, sorted(set(locs), key=bore_key)


def build_soundings(bores: dict, sheet: dict) -> dict:
    order = sorted(bores, key=lambda b: bore_key(coral_name(b)))
    locs, times, serials, depths, elevs = [], [], [], [], []
    for b in order:
        rec = bores[b]; name = coral_name(b)
        last_ft = rec["rows"][-1][0]
        sh = sheet[b]
        if abs(sh["total_depth_m"] * FT_PER_M - last_ft) > 0.07:  # 2 cm
            raise ValueError(f"{b}: sheet total depth {sh['total_depth_m']} m != last reading {last_ft} ft")
        serial = rec["cone"].split()[-1]
        if not serial.isdigit() or not rec["cone"].startswith("CP15-CF"):
            raise ValueError(f"{b}: unexpected cone {rec['cone']!r}")
        locs.append(name); times.append(f"{rec['datetime']:%Y-%m-%dT%H:%M:%S}{OFFSET}"); serials.append(serial)
        depths.append(last_ft); elevs.append(sh["elevation_m"])
    dim = {"data_type": ab.term("environmental sample location"), "size": len(locs), "typed_values": [loc_ref(locs)]}
    variables = [
        typed("datetime", "string", times, None, []),
        typed("instrument", "string", serials, None, [ctx("category", sval("serial number"))]),
        float_var("depth", "foot", [ctx("top", sval("ground surface")), ctx("bottom", sval("end of sounding"))], depths),
        float_var("elevation", "meter", [ctx("relative", sval("mean sea level"))], elevs),
    ]
    cones = Counter(serials)
    array_context = fugro_context(bores, [
        comment("Variables: start of the push from the Fugro file header (local time, UTC-4); cone serial number (the model is the instrument context: "
                + ", ".join(f"serial {s} on {n} bores" for s, n in sorted(cones.items())) + "); depth reached = last reading of the profile "
                "(matches TotalDepth_M of the Location sheet within 2 cm for every bore); ground surface elevation above mean sea level from the Location "
                "sheet (Elevation_AMSL), whose survey source the sheet does not state"),
        comment("The sheet's UTM easting/northing are not stored (datum given only as a code); CORAL Location latitude/longitude come from the same sheet"),
    ])
    return brick("hazen_fugro_cpt_soundings_area3_2020",
                 "Per-bore summary of the 94 Fugro piezocone soundings in FRC Area 3, 13-27 October 2020: start time, cone serial number, depth reached and "
                 "ground-surface elevation; companion to hazen_fugro_cpt_profiles_area3_2020",
                 "physical measurement", array_context, [dim], variables)


# ----------------------------------------------------------------------------
# Manual water levels
# ----------------------------------------------------------------------------

def wl_coral_name(field_id: str) -> str:
    i = WL_PORT_PARENT.get(field_id, WL_RENAME.get(field_id, field_id))
    m = re.match(r"(FW|SG)(\d+)(?:-(\w+))?$", i)
    if not m:
        raise ValueError(f"unexpected well id {field_id!r}")
    p, n, s = m.groups()
    base = f"FW-{n.zfill(3)}" if p == "FW" else f"SG{n}"
    return base + (f"-{s}" if s else "")


def read_wl():
    ws = openpyxl.load_workbook(WL, read_only=True, data_only=True)["Sheet1"]
    rows = [tuple(r) for r in ws.iter_rows(values_only=True)]
    hdr = [str(c).strip() if c else "" for c in rows[0]]
    if hdr[:6] != ["Sample ID", "Water Level (ft)", "From", "Time (24h)", "Date", "Samplers"]:
        raise ValueError(f"water level header changed {hdr[:6]}")
    recs = [r for r in rows[1:] if r and r[0]]
    # Putt's renamed copy has the same rows in the same order; confirm the rename table against it.
    ws2 = openpyxl.load_workbook(WL_RENAMED, read_only=True, data_only=True)["Sheet1"]
    ren = [tuple(r) for r in ws2.iter_rows(values_only=True)][1:]
    ren = [r for r in ren if r and r[0]]
    if len(ren) != len(recs):
        raise ValueError("renamed copy has a different row count")
    for a, b in zip(recs, ren):
        if a[1] != b[1] or a[4] != b[4]:
            raise ValueError(f"renamed copy out of step at {a[:2]} vs {b[:2]}")
        exp = WL_RENAME.get(str(a[0]).strip(), WL_PORT_PARENT.get(str(a[0]).strip(), str(a[0]).strip()))
        if str(a[0]).strip() in WL_PHANTOM:
            exp = "FW114"
        if exp != str(b[0]).strip():
            raise ValueError(f"rename table disagrees with Putt's copy: {a[0]} -> {b[0]} (expected {exp})")
    return recs


def build_water_levels(locations: set[str]):
    recs = read_wl()
    kept, dropped, typo, nw = [], [], [], []
    for r in recs:
        fid, val, frm, tm, date, samplers = (str(r[0]).strip(), r[1], r[2], r[3], r[4], r[5])
        if samplers != "Putt & Kelly" or not isinstance(date, dt.datetime) or date.date() not in (dt.date(2020, 10, 15), dt.date(2020, 10, 20)):
            raise ValueError(f"unexpected row {r[:6]}")
        if frm != "TOC" or fid in WL_PHANTOM:
            dropped.append(f"{fid} {val if not isinstance(val, dt.time) else val.strftime('%H:%M')} ft from {frm} on {date:%Y-%m-%d}")
            continue
        if isinstance(val, dt.time):  # Excel read "11.21" as a clock time
            typo.append(f"{fid} '{val:%H:%M}' read as {val.hour}.{val.minute:02d} ft")
            val = val.hour + val.minute / 100
        elif val == "NW":
            nw.append(fid); val = None
        elif not isinstance(val, (int, float)):
            raise ValueError(f"{fid}: unexpected value {val!r}")
        when = f"{date:%Y-%m-%d}" + (f"T{tm:%H:%M:%S}{OFFSET}" if isinstance(tm, dt.time) else "")
        kept.append((wl_coral_name(fid), fid, when, None if val is None else round(float(val), 2)))
    if len(dropped) != 7 or len(typo) != 2 or sorted(nw) != ["FW101-50", "FW102-20"]:
        raise ValueError(f"unexpected exclusions: dropped {dropped}, typo {typo}, NW {nw}")
    new = {wl_coral_name(w) for w in NEW_WELLS}
    missing = sorted({k[0] for k in kept} - locations - new)
    if missing:
        raise ValueError(f"water-level wells not in CORAL: {missing}")
    locs = [k[0] for k in kept]
    dim = {"data_type": ab.term("environmental sample location"), "size": len(kept), "typed_values": [
        loc_ref(locs),
        typed("location", "string", [k[1] for k in kept], None, []),
        typed("datetime", "string", [k[2] for k in kept], None, [])]}
    variables = [float_var("depth", "foot", [ctx("top", sval("top of casing")), ctx("bottom", sval("water surface"))], [k[3] for k in kept])]
    by_date = Counter(k[2][:10] for k in kept)
    array_context = [
        ctx("ENIGMA campaign", oterm_value("Cone Penetrometer Survey")), ctx("personnel", oterm_value("Hazen Lab")),
        comment(f"Source: {rel(WL)} (field master sheet; samplers Putt & Kelly). Putt's renamed copies "
                f"({rel(WL_RENAMED)} and ..._final.xlsx) supplied the port names {', '.join(f'{a} -> {b}' for a, b in WL_RENAME.items())}; "
                "FW133-1/2 and FW134-1/2/3 are ports not in the construction records and are attached to FW-133 and FW-134 with the field label in the location string"),
        comment(f"Variable: depth to water below the top of casing in feet ({len(kept)} readings: {by_date['2020-10-15']} on 2020-10-15 and "
                f"{by_date['2020-10-20']} on 2020-10-20, the latter repeats of FW-111, -112, -116, -117, -126 and -127 plus FW-128). Datetimes carry the clock "
                "time where the sheet has one (UTC-4), otherwise the date only. Water-table elevations are not stored: subtract from the top-of-casing "
                "elevation in hazen_oak_ridge_well_construction_data_v3 (Brick0001698), with which Putt's elevations agree to 0.05 ft"),
        comment(f"Excluded from the sheet (7 of 81 rows): {'; '.join(dropped)}. 'TG' is an undefined measuring point whose readings do not reconcile "
                "with the casing stick-ups; FW114-57 and FW114-short are not ports of FW-114 (a 20 ft single-port well) and no Area 3 well has a 57 ft port"),
        comment(f"Corrections: {'; '.join(typo)} (Excel time autoconversions; neighbouring ports read 11.29/11.22 and 12.55 ft). "
                f"Null for {' and '.join(nw)}, marked 'NW' on the sheet"),
    ]
    obj = brick("hazen_manual_water_level_area3_cpt_2020",
                f"Manual depth to water below the top of casing in {len(set(locs))} FRC Area 3 wells, multiport-sampler ports and SG piezometers on 15 and "
                "20 October 2020 (Putt & Kelly, Hazen Lab) during the cone penetrometer survey; 74 readings from the field master sheet",
                "physical measurement", array_context, [dim], variables)
    return obj, sorted(set(locs)), {"kept": len(kept), "dropped": dropped, "typo": typo, "nw": nw}


# ----------------------------------------------------------------------------
# Static additions, protocols, processes
# ----------------------------------------------------------------------------

def location_rows(coral_locs: dict, sheet: dict) -> list[dict]:
    fields = ["name", "latitude", "longitude", "continent", "country", "region", "biome", "feature"]
    rows = []
    tmpl = coral_locs["CPT65S"]
    s = sheet["CPT-65"]
    rows.append({**{k: tmpl[k] for k in fields}, "name": "CPT65", "latitude": f"{s['lat']:.6f}", "longitude": f"{s['lon']:.6f}"})
    if abs(float(tmpl["latitude"]) - s["lat"]) > 1e-5 or abs(float(tmpl["longitude"]) - s["lon"]) > 1e-5:
        raise ValueError("CPT-65 is not where CPT65S is")
    ws = openpyxl.load_workbook(GE, read_only=True, data_only=True)["Wells"]
    ge = {str(r[2]).strip(): (r[0], r[1]) for r in ws.iter_rows(values_only=True) if r and r[2]}
    tmpl = coral_locs["FW-130-50"]
    for w in NEW_WELLS:
        lat, lon = ge[w]
        rows.append({**{k: tmpl[k] for k in fields}, "name": wl_coral_name(w), "latitude": f"{lat:.8f}", "longitude": f"{lon:.8f}"})
    for r in rows:
        if r["name"] in coral_locs:
            raise ValueError(f"{r['name']} already in CORAL")
    return rows


def protocol_rows(stats: dict) -> list[dict]:
    zone_table = "; ".join(f"{z} = {SBT_TABLE[z][0].replace(' (*)', '')}" + (f" (USCS {SBT_TABLE[z][1]})" if SBT_TABLE[z][1] else "") for z in range(13))
    return [
        {"name": PROTO_CPT, "link": "",
         "description": "Piezocone penetration testing (CPTu) of FRC Area 3 by a Fugro CPT crew (operator Bobby Brandt, job 04.00168068) for the Hazen Lab, 13-27 "
                        "October 2020: 94 soundings pushed at 2 cm/s with Fugro CP15 15 cm2 piezocones (CF75PB7SN2-P1E1, serials 2422, 2736 and 2874; the "
                        "CF25PB7SN2-P1E1 cone serial 2111 for CPT-01), recording cone tip resistance q_c, sleeve friction f_s and pore pressure u2 at the "
                        "shoulder filter every 2 cm, exported per bore as CSV (depth in feet, pressures in tons per square foot, friction ratio "
                        "R_f = f_s/q_c x 100 in percent, clipped at 10). Soil behavior type assigned by Fugro's software from the Robertson, Campanella, "
                        f"Gillespie and Greig (1986) q_c - R_f chart: {zone_table}; zone 0 = out of range. Bore coordinates and ground elevations from "
                        "the Location sheet of CPT Metadata FINAL/CPT_full_data.xlsx (Andrew Putt, 2021-10-28). Refusal depths 0.4 to 12.2 m. "
                        f"Total {stats['readings']} readings; {stats['negative_u2']} with negative u2 (suction above the water table or dilatant response)."},
        {"name": PROTO_WL, "link": "",
         "description": "Manual groundwater level survey of FRC Area 3 wells, multiport-sampler ports and SG piezometers during the October 2020 cone "
                        "penetrometer campaign (Andrew Putt and Kelly, Hazen Lab; 2020-10-15 with repeats 2020-10-20): depth to water read with an electric "
                        "water-level tape from the top of casing, in feet, recorded on the field master sheet Water Level Master 20201020.xlsx with the "
                        "measuring point ('TOC', or 'TG' for five undefined readings that are not loaded). Top-of-casing and ground elevations for "
                        "converting to water-table elevation are in the Oak Ridge well construction brick (hazen_oak_ridge_well_construction_data_v3)."},
    ]


def write_tsv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    stage_validator()
    ab.load_ontology_names()
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    ab.OUT = OUT
    ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT = (OUT / d for d in ("json", "static", "process", "check", "reports"))
    for d in (ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT):
        d.mkdir(parents=True)
    with (EXPORT / "Location.tsv").open() as h:
        coral_locs = {r["name"]: r for r in csv.DictReader(h, delimiter="\t")}
    with (EXPORT / "Protocol.tsv").open() as h:
        protocols = {r["name"] for r in csv.DictReader(h, delimiter="\t")}
    if {PROTO_CPT, PROTO_WL} & protocols:
        raise ValueError("protocol name already in CORAL")

    bores = read_fugro()
    stats = check_fugro(bores)
    sheet = location_sheet()
    if len(bores) != 94 or stats["readings"] != 28589:
        raise ValueError(f"expected 94 bores / 28589 readings, got {len(bores)} / {stats['readings']}")
    missing = [b for b in bores if coral_name(b) not in coral_locs and coral_name(b) != "CPT65"]
    if missing or any(b not in sheet for b in bores):
        raise ValueError(f"bores without CORAL Location or sheet row: {missing}")
    for b in bores:  # CORAL coordinates (from this sheet originally) still agree
        if coral_name(b) in coral_locs and (abs(float(coral_locs[coral_name(b)]["latitude"]) - sheet[b]["lat"]) > 2e-5 or abs(float(coral_locs[coral_name(b)]["longitude"]) - sheet[b]["lon"]) > 2e-5):
            raise ValueError(f"{b}: CORAL coordinates differ from the Location sheet")

    profiles, cpt_locs = build_profiles(bores, set(coral_locs))
    soundings = build_soundings(bores, sheet)
    water, wl_locs, wl_stats = build_water_levels(set(coral_locs))
    if [d["size"] for d in soundings["dim_context"]] != [94] or water["dim_context"][0]["size"] != 74:
        raise ValueError("unexpected brick sizes")
    paths = [ab.write_brick(o) for o in (profiles, soundings, water)]

    loc_rows = location_rows(coral_locs, sheet)
    write_tsv(ab.STATIC_OUT / f"Location_additions_{TAG}.tsv", loc_rows, ["name", "latitude", "longitude", "continent", "country", "region", "biome", "feature"])
    write_tsv(ab.STATIC_OUT / f"Protocol_additions_{TAG}.tsv", protocol_rows(stats), ["name", "description", "link"])
    cpt_dates = sorted(b["datetime"].date() for b in bores.values())
    proc = ab.PROCESS_OUT / f"process_assay_environment_{TAG}.tsv"
    write_process(proc, [
        {"process": "Assay Environment <PROCESS:0000004>", "person": PERSON, "campaign": CAMPAIGN, "protocol": PROTO_CPT,
         "date_start": f"{cpt_dates[0]}", "date_end": f"{cpt_dates[-1]}",
         "input_objects": ", ".join(f"Location: {l}" for l in cpt_locs), "output_objects": f"Generic: {profiles['name']}, Generic: {soundings['name']}"},
        {"process": "Assay Environment <PROCESS:0000004>", "person": PERSON, "campaign": CAMPAIGN, "protocol": PROTO_WL,
         "date_start": "2020-10-15", "date_end": "2020-10-20",
         "input_objects": ", ".join(f"Location: {l}" for l in wl_locs), "output_objects": f"Generic: {water['name']}"},
    ])
    jsons = [p.name for p in paths]
    files = [f"static/Location_additions_{TAG}.tsv", f"static/Protocol_additions_{TAG}.tsv"] + [f"json/{j}" for j in jsons] + [f"process/{proc.name}"]
    (OUT / "files_to_import.txt").write_text("\n".join(files) + "\n")
    (OUT / "import_to_coral.py").write_text("\n".join([
        "# Run on the CORAL hub after staging files_to_import.txt in data_import/data and installing + reloading the ontologies",
        "# (coral_import/ontology_update_20261104_cpt: toolx.upload_ontologies() with robertson_soil_behavior_type.obo in upload_config.json)",
        f"toolx.update_core('Location_additions_{TAG}.tsv', 'Location')",
        f"toolx.update_core('Protocol_additions_{TAG}.tsv', 'Protocol')"]
        + [f"toolx.upload_brick('{j}')" for j in jsons]
        + [f"toolx.upload_process('Assay Environment', '{proc.name}')", ""]))
    summary = {"release": RELEASE, "fugro": stats, "bores": len(bores), "cpt_locations": cpt_locs, "new_locations": [r["name"] for r in loc_rows],
               "water_levels": wl_stats, "water_level_locations": wl_locs,
               "bricks": [{"name": o["name"], "shape": [d["size"] for d in o["dim_context"]], "variables": len(o["typed_values"])} for o in (profiles, soundings, water)],
               "hashes": {f: sha(OUT / f) for f in files}}
    (ab.REPORT_OUT / "build_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    (OUT / "README.md").write_text(f"""# CORAL import package: CPT physical data, FRC Area 3, October 2020 ({RELEASE})

Built by `tools/build_cpt_physical_coral_import.py`. Requires the ontology update
`coral_import/ontology_update_20261104_cpt` (new `robertson_soil_behavior_type.obo`, COMO ME:0000518) installed
on stout and coral-enigma, registered in the hub's `upload_config.json`, and reloaded before import.

| Brick | Shape | Variables | Source |
| --- | --- | --- | --- |
| hazen_fugro_cpt_profiles_area3_2020 | {stats['readings']} readings | q_c, f_s, u2 (tsf), Robertson 1986 SBT | 94 Fugro CSV exports |
| hazen_fugro_cpt_soundings_area3_2020 | 94 bores | start time, cone serial, depth reached (ft), ground elevation (m) | Fugro headers + CPT_full_data.xlsx Location sheet |
| hazen_manual_water_level_area3_cpt_2020 | {wl_stats['kept']} readings | depth to water below top of casing (ft) | Water Level Master 20201020.xlsx (AREA 3) |

Static additions: Locations {', '.join(r['name'] for r in loc_rows)}; Protocols `{PROTO_CPT}`, `{PROTO_WL}`.
Process: two `Assay Environment` rows (Hazen Lab, Cone Penetrometer Survey).

Excluded water-level rows: {'; '.join(wl_stats['dropped'])}.
Corrections: {'; '.join(wl_stats['typo'])}; null for {', '.join(wl_stats['nw'])} ('NW').

Import order (`import_to_coral.py`): Location, Protocol, the three bricks, the process file.
Hashes of the staged files are in `reports/build_summary.json`.
""")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("cpt_locations", "water_level_locations", "hashes")}, indent=1))


if __name__ == "__main__":
    main()
