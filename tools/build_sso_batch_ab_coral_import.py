#!/usr/bin/env python3
"""Build the CORAL import package for SSO batches A and B of IMPORT_PLAN_20261009.

Batch A (samples already in CORAL):
  A1 Adams Lab ICP-MS metals, 2024 pump test (17 samples) and 2024 pilot time
     series (38 samples, the 2025-09 "-Final" workbook).
  A2 Baliga Lab Gallery ammonium and nitrite, 2024 pilot time series (57
     samples).
  A3 Hazen Lab AODC, 2024 pump test (17 samples): processed and raw counts.
Batch B (2023 data):
  B1 Initial well characterization, June to August 2023: 28 new Sample rows
     with Sampling processes, field readings brick, Adams metals, AODC.
  B2 2023 sediment cores: Adams metals (37 digests, mg/kg dry weight) and the
     four Northen Lab GNPS feature tables (C18 and HILIC, positive and
     negative).

Loading decisions follow coral_import/LAB_QUESTIONS_20261009.md section 3.
Outputs: coral_import/sso_batch_ab_20261009/ with json/, static/, process/,
check/, reports/, files_to_import.txt, import_to_coral.py and README.md.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
import subprocess
from collections import OrderedDict, defaultdict
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parents[1]
DRIVE = Path("/mnt/net/dipa.jmcnet/data/backup/google-drive/enigma_team_drive_data_enigma_backup")
EXPORT_ROOT = REPO / "sync-coral-to-berdl/exports/sync-20261009-134304/coral_export"
EXPORT = EXPORT_ROOT / "static_tsv"
ONTOLOGIES = Path("/home/coral/prod/data_import/ontologies")
RELEASE = "20261009"
OUT = REPO / f"coral_import/sso_batch_ab_{RELEASE}"
JSON_OUT, STATIC_OUT, PROCESS_OUT, CHECK_OUT, REPORT_OUT = (OUT / d for d in ("json", "static", "process", "check", "reports"))
DRIVE_LABEL = "ENIGMA team Google Drive"
CAMPAIGN = "Subsurface Observatory <ENIGMA:0000166>"

CHECKGENERIC_CLASSES = Path("/h/jmc/src/java/classes")
JACKSON_JARS = [Path(f"/h/jmc/.m2/repository/com/fasterxml/jackson/core/{a}/2.5.1/{a}-2.5.1.jar") for a in ("jackson-annotations", "jackson-core", "jackson-databind")]


def drive(pattern: str) -> Path:
    hits = sorted(DRIVE.glob(pattern))
    if len(hits) != 1:
        raise FileNotFoundError(f"{pattern}: {len(hits)} matches")
    return hits[0]


ADAMS_PUMP = drive("2024_SSO_Pump Test/Adams_Metals/2024-06-29_Adams-Lab_ENIGMA-SSO-Pump-Test_Metal-Data.xlsm")
ADAMS_TS = drive("2024_SSO_Pilot Time Series/Adams_Metals/2024-10-09_Adams-Lab_ENIGMA-SSO-Pilot-Time-Series_Metal-Data-Final.xlsm")
ADAMS_IWC = drive("2023_SSO_Initial Well Characterization/2023-Adams-Metals/2024-06-29_Adams-Lab_ENIGMA-SSO-Initial-GW_Metal-Data.xlsm")
ADAMS_SED = drive("2023_SSO_Drilling*Sediment Core/2023-Adams-Metals-sediment/2024-06-29_Adams-Lab_ENIGMA-SSO-Sediment_Metal-Data.xlsm")
BALIGA = drive("2024_SSO_Pilot Time Series/Baliga_Ammonia*/202111_SSO samples.xlsx")
AODC_PUMP = drive("2024_SSO_Pump Test/Hazen_AODC/AODC_pump test _UTK .xlsx")
AODC_IWC = drive("2023_SSO_Initial Well Characterization/2023-Hazen-AODC/2023-Hazen-AODC_SSO_IWC .xlsx")
IWC_META = drive("2023_SSO_Initial Well Characterization/SSO_Initial Well Characterization metadata.xlsx")
NORTHEN = drive("2023_SSO_Drilling*Sediment Core/2023-Northen-Metabolomics-sediment")


def rel(p: Path) -> str:
    return f"{DRIVE_LABEL} {p.relative_to(DRIVE)}"


# ----------------------------------------------------------------------------
# ontology terms (verified against the production OBO files at build time)
# ----------------------------------------------------------------------------
T = {
    "chemical measurement": "DA:0000005", "microbial abundance": "DA:0000018",
    "environmental measurement": "DA:0000004", "metabolite assay": "DA:0000006",
    "data variables type": "ME:0000293", "instrument": "ME:0000012", "method": "ME:0000007",
    "comment": "ME:0000011", "description": "ME:0000202", "personnel": "ENIGMA:0000029",
    "ENIGMA campaign": "ENIGMA:0000002", "Subsurface Observatory": "ENIGMA:0000166",
    "environmental sample": "ME:0000100", "environmental sample ID": "ME:0000102",
    "environmental sample location": "ME:0000099", "environmental sample location ID": "ME:0000228", "location": "ME:0000210", "date": "ME:0000009",
    "molecule": "ME:0000027", "molecule from list": "ME:0000381", "replicate series": "ME:0000005",
    "experimental context": "ME:0000002", "technical replicate": "ME:0000287",
    "concentration": "ME:0000129", "standard deviation": "ME:0000149", "detection limit": "ME:0000038",
    "below": "ME:0000363", "above": "ME:0000362", "relative": "ME:0000020",
    "count": "ME:0000126", "category": "ME:0000013", "cell": "ME:0000040",
    "coefficient of variation": "ME:0000358", "average": "ME:0000147",
    "volume": "ME:0000360", "weight": "ME:0000359",
    "pH": "ME:0000121", "temperature": "ME:0000123", "conductivity": "ME:0000124",
    "saturation": "ME:0000304", "physiochemical state": "ME:0000037", "depth": "ME:0000219", "rate": "ME:0000264",
    "index": "ME:0000468", "mass": "ME:0000135", "time series": "ME:0000004", "time": "ME:0000010", "ionization mode": "ME:0000385",
    "positive polarity": "ME:0000386", "negative polarity": "ME:0000387", "molecular formula": "ME:0000383",
    "InChIKey": "ME:0000384", "ion intensity": "ME:0000390", "control name": "ME:0000482",
    "measurement": "ME:0000120", "chemical context": "ME:0000026", "reference compound": "ME:0000389",
    "retention time": "ME:0000506", "m/z": "ME:0000507", "spectral library compound name": "ME:0000508",
    "spectral library match ID": "ME:0000509", "spectral match score": "ME:0000510", "adduct": "ME:0000511", "MS1 feature area": "ME:0000512",
    "control": "ME:0000283", "negative control": "ME:0000284", "positive control": "ME:0000285",
    "dimensionless unit": "UO:0000186",
    # units
    "uM": "UO:0000064", "mg/L": "UO:0000273", "ug/L": "UO:0000301", "mg/kg": "UO:0000308",
    "percent": "UO:0000187", "pH unit": "UO:0000196", "degree Celsius": "UO:0000027",
    "uS/cm": "ME:0000295", "cells per milliliter": "UO:0000201", "cells per well": "UO:0000317",
    "milliliter": "UO:0000098", "liter": "UO:0000099", "gram": "UO:0000021", "meter": "UO:0000008",
    "minute": "UO:0000031", "dalton": "UO:0000221",
    "relative ion intensity unit": "ME:0000471", "count unit": "UO:0000189",
    # molecules
    "dioxygen": "CHEBI:15379", "ammonium": "CHEBI:28938", "nitrite": "CHEBI:16301", "nitrate": "CHEBI:17632",
    # people
    "Farris Poole": "ENIGMA:0000103", "Nitin Baliga": "ENIGMA:0000044", "Terry Hazen": "ENIGMA:0000067",
    "Hazen Lab": "ENIGMA:0000066", "Suzanne Kosina": "ENIGMA:0000072",
}
ELEMENTS = [  # order of the ICP-MS template columns L..BK and of Brick0000080 (adams_metals_27ws)
    ("Be", "CHEBI:30501"), ("B", "CHEBI:27560"), ("Na", "CHEBI:26708"), ("Mg", "CHEBI:25107"), ("Al", "CHEBI:28984"),
    ("P", "CHEBI:30207"), ("K", "CHEBI:26216"), ("Ca", "CHEBI:22984"), ("Ti", "CHEBI:33341"), ("V", "CHEBI:27698"),
    ("Cr", "CHEBI:28073"), ("Mn", "CHEBI:18291"), ("Fe", "CHEBI:18248"), ("Co", "CHEBI:27638"), ("Ni", "CHEBI:28112"),
    ("Cu", "CHEBI:28694"), ("Zn", "CHEBI:27363"), ("Ga", "CHEBI:49631"), ("Ge", "CHEBI:30441"), ("As", "CHEBI:27563"),
    ("Se", "CHEBI:27568"), ("Rb", "CHEBI:33322"), ("Sr", "CHEBI:33324"), ("Zr", "CHEBI:33342"), ("Nb", "CHEBI:33344"),
    ("Mo", "CHEBI:28685"), ("Cd", "CHEBI:22977"), ("Sn", "CHEBI:27007"), ("Sb", "CHEBI:30513"), ("Te", "CHEBI:30452"),
    ("Cs", "CHEBI:30514"), ("Ba", "CHEBI:32594"), ("La", "CHEBI:33336"), ("Ce", "CHEBI:33369"), ("Pr", "CHEBI:49828"),
    ("Nd", "CHEBI:33372"), ("Sm", "CHEBI:33374"), ("Eu", "CHEBI:32999"), ("Gd", "CHEBI:33375"), ("Dy", "CHEBI:33377"),
    ("Ho", "CHEBI:49648"), ("Er", "CHEBI:33379"), ("Tm", "CHEBI:33380"), ("Yb", "CHEBI:33381"), ("Lu", "CHEBI:33382"),
    ("Hf", "CHEBI:33343"), ("Ta", "CHEBI:33348"), ("W", "CHEBI:27998"), ("Tl", "CHEBI:30440"), ("Pb", "CHEBI:25016"),
    ("Th", "CHEBI:33385"), ("U", "CHEBI:27214"),
]
for sym, cid in ELEMENTS:
    T[f"element {sym}"] = cid
NAMES: dict[str, str] = {}


def load_ontology_names() -> None:
    for obo in sorted(ONTOLOGIES.glob("*.obo")):
        cur = None
        with obo.open(errors="ignore") as h:
            for line in h:
                line = line.strip()
                if line == "[Term]":
                    cur = None
                elif line.startswith("id: "):
                    cur = line[4:].strip()
                elif line.startswith("name: ") and cur:
                    NAMES.setdefault(cur, line[6:].strip())
                    cur = None
    missing = [k for k, v in T.items() if v not in NAMES]
    if missing:
        raise SystemExit(f"ontology ids not found: {missing}")


def term(key: str) -> dict:
    ref = T[key]
    return {"term_name": NAMES[ref], "oterm_ref": ref, "oterm_name": NAMES[ref]}


def oterm_value(key: str) -> dict:
    return {"scalar_type": "oterm_ref", "oterm_ref": T[key], "string_value": NAMES[T[key]]}


def ctx(type_key: str, value: dict) -> dict:
    return {"value_type": term(type_key), "value": value}


def sval(text: str) -> dict:
    return {"scalar_type": "string", "string_value": text}


def comment(text: str) -> dict:
    return ctx("comment", sval(text))


# ----------------------------------------------------------------------------
# brick assembly
# ----------------------------------------------------------------------------

def typed(type_key: str, scalar: str, values: list, unit_key: str | None = None, context: list[dict] | None = None) -> dict:
    key = {"float": "float_values", "int": "int_values", "string": "string_values", "boolean": "boolean_values"}[scalar]
    if scalar == "boolean":
        values = [None if v is None else (1 if v else 0) for v in values]
    out = {"value_type": term(type_key), "values": {"scalar_type": scalar, key: values}}
    if unit_key:
        out["value_units"] = term(unit_key)
    if context is not None:
        out["value_context"] = context
    return out


def float_var(type_key, unit_key, context, values):
    return typed(type_key, "float", [None if v is None else float(v) for v in values], unit_key, context)


def bool_var(type_key, context, values):
    return typed(type_key, "boolean", values, None, context)


def sample_dim(names: list[str | None], extra: list[dict] | None = None) -> dict:
    tv = [{"value_type": term("environmental sample ID"), "values": {"scalar_type": "object_ref", "object_refs": list(names), "string_values": list(names)}}]
    return {"data_type": term("environmental sample"), "size": len(names), "typed_values": tv + (extra or [])}


def molecule_dim(keys: list[str], extra: list[dict] | None = None) -> dict:
    tv = [{"value_type": term("molecule from list"), "values": {"scalar_type": "oterm_ref", "oterm_refs": [T[k] for k in keys], "string_values": [NAMES[T[k]] for k in keys]}}]
    return {"data_type": term("molecule"), "size": len(keys), "typed_values": tv + (extra or [])}


def replicate_dim(n: int, context_key: str | None = None) -> dict:
    context = [ctx("experimental context", oterm_value(context_key))] if context_key else []
    return {"data_type": term("replicate series"), "size": n, "typed_values": [typed("replicate series", "int", list(range(1, n + 1)), "count unit", context)]}


def below_ctx(extra: list[dict] | None = None) -> list[dict]:
    return [ctx("relative", sval("detection limit"))] + (extra or [])


def brick(name: str, description: str, dtype_key: str, array_context: list[dict], dims: list[dict], variables: list[dict]) -> dict:
    marker = {"value_type": term("data variables type"), "value": oterm_value(dtype_key)}
    return {"name": f"{name}.hndarray", "description": description, "data_type": term(dtype_key),
            "array_context": [marker] + array_context, "n_dimensions": len(dims), "dim_context": dims, "typed_values": variables}


def fnum(v):
    if v is None or v == "" or (isinstance(v, str) and v.strip().startswith("#")):
        return None
    return float(v)


def rows_of(path: Path, sheet: str) -> list[tuple]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    return list(wb[sheet].iter_rows(values_only=True))


def live_samples() -> dict[str, dict]:
    out = {}
    with (EXPORT / "Sample.tsv").open() as h:
        for r in csv.DictReader(h, delimiter="\t"):
            out[r["name"]] = r
    return out


PERIOD_SUFFIX = {"PRE": "1", "POST": "2", "0L": "", "100L": "100", "200L": "200"}
PUMP_DATES = {"U2-SZ1": "20240313", "L8-SZ1": "20240314", "M5-SZ1": "20240318", "U2-SZ2": "20240319",
              "L8-SZ2": "20240320", "M5-SZ2": "20240321", "M5-SZ3": "20240328"}


def pump_sample(well: str, zone: str, period: str, assay: str) -> str:
    wz = f"{well}-{zone}"
    period = period.upper()
    if period in ("0L", "100L", "200L"):
        return f"{wz}-20240329-{assay}{PERIOD_SUFFIX[period]}"
    return f"{wz}-{PUMP_DATES[wz]}-{assay}{PERIOD_SUFFIX[period]}"


ZONE_DEPTH_M = {"VSZ": 3.5052, "SZ1": 5.1816, "SZ2": 7.0104, "SZ3": 9.4488}  # screen midpoints 11.5, 17, 23, 31 ft


# ----------------------------------------------------------------------------
# B1: initial well characterization metadata (28 ports)
# ----------------------------------------------------------------------------

def parse_clock(v, after: dt.time | None = None) -> dt.time | None:
    if v is None:
        return None
    if isinstance(v, dt.datetime):
        return v.time()
    if isinstance(v, dt.time):
        t = v
    else:
        s = str(v).strip().lower().replace(" ", "")
        if s.endswith("am") or s.endswith("pm"):
            t = dt.datetime.strptime(s, "%I:%M%p").time()
        else:
            t = dt.datetime.strptime(s, "%H:%M:%S").time()
    if after is not None and t < after and t.hour < 12:
        t = t.replace(hour=t.hour + 12)  # "12:14am" written for 12:14 pm
    return t


def read_iwc_meta() -> "OrderedDict[str, dict]":
    rows = rows_of(IWC_META, "Sheet1")
    header = [str(c).strip() if c is not None else "" for c in rows[1]]
    out: "OrderedDict[str, dict]" = OrderedDict()
    for r in rows[3:]:
        if not r or not r[0]:
            continue
        r = tuple(r) + (None,) * (26 - len(r))
        well, zone = str(r[0]).split("_")
        date = r[1].date() if isinstance(r[1], dt.datetime) else dt.date.fromisoformat(str(r[1])[:10])
        start = parse_clock(r[2])
        end = parse_clock(r[3], after=start)
        rec = {"well": well, "zone": zone, "date": date, "pump_start": start, "pump_end": end,
               "ph_start": fnum(r[4]), "ph_end": fnum(r[5]), "do_mgl_start": fnum(r[6]), "do_mgl_end": fnum(r[7]),
               "do_sat_start": fnum(r[8]), "do_sat_end": fnum(r[9]), "cond_start": fnum(r[10]), "cond_end": fnum(r[11]),
               "temp_start": fnum(r[12]), "temp_end": fnum(r[13]), "no3_start": fnum(r[14]), "no3_end": fnum(r[15]),
               "dtw_start": fnum(r[16]), "dtw_end": fnum(r[17]), "pump_rate": fnum(r[18]),
               "notes": (str(r[24]).strip() if len(r) > 24 and r[24] else None)}
        rec["sample"] = f"{well}-{zone}-{date:%Y%m%d}"  # port-visit stem; bottle samples add -METALS and -AODC
        rec["metals"] = f"{rec['sample']}-METALS"
        rec["aodc"] = f"{rec['sample']}-AODC"
        rec["adams_id"] = f"SSO-{len(out) + 1}"  # Adams Lab numbering follows this sheet's row order
        out[f"{well}_{zone}"] = rec
    if len(out) != 28:
        raise ValueError(f"expected 28 IWC ports, found {len(out)}")
    return out


def iwc_sample_rows(meta) -> list[list]:
    rows = []
    for rec in meta.values():
        pump = (f"2023 SSO initial well characterization, port {rec['well']}_{rec['zone']} (field sheet label); "
                f"{rec['pump_rate']:g} mL/min pump from {rec['pump_start']:%H:%M} to {rec['pump_end']:%H:%M}")
        if rec["notes"]:
            pump += f"; field note: {rec['notes']}"
        metals = f"Metals, unfiltered (arrived unacidified); Adams Lab ID {rec['adams_id']}. {pump}"
        aodc = f"AODC, unfiltered, formaldehyde-fixed. {pump}"
        for name, desc in ((rec["metals"], metals), (rec["aodc"], aodc)):
            rows.append([name, f"SSO-{rec['well']}", ZONE_DEPTH_M[rec["zone"]], "null", rec["date"].isoformat(),
                         f"{rec['pump_end']:%H:%M}", "UTC-4", "ground water <ENVO:00002041>", "water <MIxS:0000017>", desc])
    return rows


COMPROMISED_SONDE_PORTS = ("U1_SZ1", "U1_SZ2")  # 2023-07-03: flow cell evidently not filled with groundwater
COMPROMISED_SONDE_FIELDS = ("cond_start", "cond_end", "do_mgl_start", "do_mgl_end", "do_sat_start", "do_sat_end", "temp_start", "temp_end")


def build_iwc_field(meta) -> tuple[dict, list[str]]:
    recs = []
    for port, rec in meta.items():
        rec = dict(rec)
        if port in COMPROMISED_SONDE_PORTS:
            for k in COMPROMISED_SONDE_FIELDS:
                rec[k] = None
        recs.append(rec)
    locations = [f"SSO-{r['well']}" for r in recs]
    loc_dim = {"data_type": term("environmental sample location"), "size": len(recs), "typed_values": [
        {"value_type": term("environmental sample location ID"), "values": {"scalar_type": "object_ref", "object_refs": locations, "string_values": locations}},
        typed("location", "string", [f"{r['well']}-{r['zone']}" for r in recs], None, []),
        typed("depth", "float", [ZONE_DEPTH_M[r["zone"]] for r in recs], "meter", []),
        typed("date", "string", [r["date"].isoformat() for r in recs], None, []),
    ]}
    start = [ctx("category", sval("pump start"))]
    end = [ctx("category", sval("pump end"))]
    do_ctx = [ctx("molecule from list", oterm_value("dioxygen"))]
    no3_ctx = [ctx("molecule from list", oterm_value("nitrate"))]
    dtw_ctx = []
    ft = 0.3048
    def col(k):
        return [r[k] for r in recs]
    variables = [
        float_var("pH", "pH unit", start, col("ph_start")), float_var("pH", "pH unit", end, col("ph_end")),
        float_var("concentration", "mg/L", do_ctx + start, col("do_mgl_start")), float_var("concentration", "mg/L", do_ctx + end, col("do_mgl_end")),
        float_var("saturation", "percent", do_ctx + start, col("do_sat_start")),
        float_var("saturation", "percent", do_ctx + end, col("do_sat_end")),
        float_var("conductivity", "uS/cm", start, col("cond_start")), float_var("conductivity", "uS/cm", end, col("cond_end")),
        float_var("temperature", "degree Celsius", start, col("temp_start")), float_var("temperature", "degree Celsius", end, col("temp_end")),
        float_var("concentration", "mg/L", no3_ctx + start, col("no3_start")), float_var("concentration", "mg/L", no3_ctx + end, col("no3_end")),
        float_var("depth", "meter", dtw_ctx + start, [None if v is None else round(v * ft, 4) for v in col("dtw_start")]),
        float_var("depth", "meter", dtw_ctx + end, [None if v is None else round(v * ft, 4) for v in col("dtw_end")]),
        typed("time", "string", [f"{r['pump_start']:%H:%M}" for r in recs], None, start),
        typed("time", "string", [f"{r['pump_end']:%H:%M}" for r in recs], None, end),
    ]
    array_context = [
        ctx("personnel", oterm_value("Hazen Lab")),
        ctx("method", sval("Field readings from the Hazen Lab sonde at the start and end of each ~30 min, 230 to 300 mL/min pump of the newly installed SSO multilevel wells; "
                            "VSZ ports ran dry after 6 to 10 min")),
        comment("Variables with category pump start and pump end are the readings at pump start and pump end; time is the local pump start and end time (the sampling time is the pump end time); "
                "dissolved oxygen is given as mg/L and as percent saturation; nitrate is the sonde ion-selective electrode reading as written in the field sheet, taken to be mg/L of nitrate ion as the sheet reports it (the TROLL 9500 default is mg/L as N, but at ports that were stable in 2024, such as U2-SZ1, U3-SZ1 and M4-SZ2, the readings agree with the 2024 lab nitrate-ion values only on a nitrate-ion basis); "
                "depth is the depth to water below the top of casing, converted from feet to meters; pump rate (230 to 300 mL/min) and field notes are in the METALS and AODC Sample descriptions"),
        comment("One row per port visit: the location is the CORAL well Location, location gives the port (well and screened zone), depth is the screen midpoint and date the sampling date. "
                "Like the Aqua TROLL bricks, the readings are linked to the well Location rather than a sample: the sonde measured pumped water in a flow cell and no water was kept for it. "
                "The METALS and AODC bottle samples taken from the same pump are named WELL-ZONE-YYYYMMDD-METALS and -AODC; INT-formazan and anion bottles were also collected but have no results"),
        comment(f"Source: {rel(IWC_META)}, sheet Sheet1"),
        comment("U1-SZ1 and U1-SZ2 (2023-07-03): conductivity, dissolved oxygen (mg/L and percent saturation) and temperature are set to null because the sonde evidently was not reading groundwater. The sheet recorded conductivity of 0.05 to 0.055 (the 2024-25 Aqua TROLL medians at these ports are 706 and 4,922 uS/cm), 94 to 100 percent oxygen saturation (other ports 1 to 48 percent) and 25 to 31 C (other ports mostly 18 to 22 C), with heavy drawdown during pumping, consistent with air in the flow cell. pH and nitrate are kept as recorded but may be affected; depth to water and pump times are unaffected"),
    ]
    obj = brick("hazen_field_sso_initial_well_characterization_2023", "Hazen Lab field readings (pH, dissolved oxygen, conductivity, temperature, sonde nitrate, depth to water, pump rate) at pump start and end for the 2023 SSO initial well characterization",
                "environmental measurement", array_context, [loc_dim], variables)
    return obj, sorted(set(locations))


# ----------------------------------------------------------------------------
# Adams Lab ICP-MS workbooks (static exports of the Adams Lab processing template)
# ----------------------------------------------------------------------------

def read_adams(path: Path, unit_sheet: str) -> dict:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheets = {}
    for kind in ("Sample - Blank", "SD", "DL", "BEC"):
        ws = wb[f"{kind} ({unit_sheet})"]
        rows = list(ws.iter_rows(values_only=True))
        symbols = [str(s).strip() for s in rows[2][11:63]]
        if symbols != [e[0] for e in ELEMENTS]:
            raise ValueError(f"{path.name} {kind}: unexpected element order {symbols[:5]}")
        data = []
        for r in rows[6:]:
            if len(r) < 63 or r[8] != "Sample":
                break
            data.append({"meta": r[:11], "key": (str(r[9]).strip(), str(r[10]).strip()), "values": [fnum(v) for v in r[11:63]]})
        sheets[kind] = data
    keys = [d["key"] for d in sheets["Sample - Blank"]]
    for kind in ("SD", "DL", "BEC"):
        if [d["key"] for d in sheets[kind]] != keys:
            raise ValueError(f"{path.name}: row order differs between Sample - Blank and {kind}")
    det = wb["ICP-MS Experiment Details"]
    text = {}
    for i, r in enumerate(det.iter_rows(values_only=True)):
        cells = [str(c).strip() for c in r if c is not None]
        if cells:
            text[i + 1] = " ".join(cells)
    info = list(wb["Sample Info"].iter_rows(values_only=True))
    return {"sheets": sheets, "details": text, "sample_info": info}


def adams_array_context(path: Path, parsed: dict, run_date: str, extra: list[str]) -> list[dict]:
    d = parsed["details"]
    overview = d.get(14, "")
    prep = d.get(26, "")
    out = [
        ctx("instrument", sval("Agilent 7900 ICP-MS with MicroMist nebulizer, UHMI spray chamber, quartz torch, Pt cones and ORS collision cell (no gas or He); external calibration with Inorganic Ventures IV-ICPMS-71A/71B (0 to 500 ppb) and IV-ICPMS-71D internal standard at 1 ppm")),
        ctx("method", sval(f"{overview} {prep}".strip())),
        ctx("personnel", oterm_value("Farris Poole")),
        comment(f"Run date {run_date}; samples prepared and run by Farris Poole, results processed by Farris Poole and Michael Thorgersen (Adams Lab, University of Georgia)"),
        comment("All concentrations, standard deviations and detection limits are reported for the original, undiluted sample: the Adams Lab processing template multiplies each instrument reading by that row's dilution factor (and, for sediment, by the digest volume over the dry mass). The dilution factors named in the method text describe sample preparation for the ICP-MS, not the basis of the reported values; the higher detection limits of the elements run at high dilution are a consequence of that back-calculation" + (" (verified 2026-10-12: the cations of the 2024 pump test balance the Chakraborty chloride, sulfate and nitrate within the expected bicarbonate excess)" if "Pump-Test" in path.name else "")),
        comment("Variables: concentration (sample minus process blank), standard deviation of the concentration (three ICP-MS replicate readings), detection limit, and below relative to the detection limit (true when the concentration is zero); the background equivalent concentrations are in the source workbook and are not loaded"),
        comment("Values are the template's 'Sample - Blank' concentrations (sample minus process blank), which the Adams Lab recommends for publication; the template auto-zeroes negative differences, so a zero means below the listed detection limit or blank-dominated"),
        comment(f"Source: {rel(path)}"),
    ] + [comment(e) for e in extra]
    return out


def build_metals(name: str, description: str, path: Path, parsed: dict, sample_of, unit_key: str, run_date: str, extra: list[str], sample_extra=None) -> tuple[dict, list[str]]:
    sb = parsed["sheets"]["Sample - Blank"]
    samples = [sample_of(d) for d in sb]
    if len(set(samples)) != len(samples):
        raise ValueError(f"{name}: duplicate samples {[s for s in samples if samples.count(s) > 1]}")
    n = len(samples)
    def flat(kind):
        return [v for d in parsed["sheets"][kind] for v in d["values"]]
    conc = flat("Sample - Blank")
    below = [None if v is None else (v <= 0.0) for v in conc]
    variables = [
        float_var("concentration", unit_key, [], conc),
        float_var("standard deviation", unit_key, [ctx("measurement", oterm_value("concentration"))], flat("SD")),
        float_var("detection limit", unit_key, [], flat("DL")),
        bool_var("below", below_ctx(), below),
    ]
    dims = [sample_dim(samples, sample_extra(sb) if sample_extra else None), molecule_dim([f"element {sym}" for sym, _ in ELEMENTS])]
    obj = brick(name, description, "chemical measurement", adams_array_context(path, parsed, run_date, extra), dims, variables)
    return obj, samples


def pump_metals_sample(d: dict) -> str:
    m = re.match(r"([A-Z]\d)-(SZ\d)-(Pre|Post|0L|100L|200L)$", d["key"][0])
    if not m:
        raise ValueError(f"unrecognised pump-test metals row {d['key']}")
    return pump_sample(m.group(1), m.group(2), m.group(3), "METALS")


def ts_metals_sample_factory(parsed: dict):
    tube_to_sample = {}
    for r in parsed["sample_info"][1:]:
        if r[1] and r[3]:
            tube_to_sample[str(r[1]).strip().upper()] = str(r[3]).strip().upper()
    def f(d: dict) -> str:
        tube = d["key"][1].upper().replace("HN03", "HNO3")
        if tube not in tube_to_sample:
            raise ValueError(f"time-series tube {d['key'][1]} not in Sample Info")
        return tube_to_sample[tube]
    return f


def iwc_metals_sample_factory(meta):
    def f(d: dict) -> str:
        port, sso = d["key"][0].split()
        rec = meta[port]
        if sso != rec["adams_id"]:
            raise ValueError(f"Adams ID {sso} for {port} does not follow the metadata row order ({rec['adams_id']})")
        return rec["metals"]
    return f


def sediment_sample(d: dict) -> str:
    sid = d["key"][0]
    m = re.match(r"SSO-([A-Z]\d[AB]?)-C(\d+)$", sid)
    if not m:
        raise ValueError(f"unrecognised sediment id {sid}")
    well = {"M4": "M4A", "L9": "L9B"}.get(m.group(1), m.group(1))
    return f"SSO-{well}-C{m.group(2)}-00"


def sediment_sample_extra(sb: list[dict]) -> list[dict]:
    return [
        typed("weight", "float", [fnum(d["meta"][0]) for d in sb], "gram", [ctx("category", sval("dry sediment digested"))]),
        typed("volume", "float", [fnum(d["meta"][1]) for d in sb], "liter", [ctx("category", sval("digest resuspension volume"))]),
    ]


# ----------------------------------------------------------------------------
# A2: Baliga Lab Gallery ammonium and nitrite
# ----------------------------------------------------------------------------
N_MASS = 14.007
GALLERY_TESTS = {
    "Ammon H UW": ("ammonium", "high range"),
    "NH4 L Tri": ("ammonium", "low range"),
    "Nitrite KC": ("nitrite", None),
}


def build_baliga() -> tuple[dict, list[str], dict]:
    rows = rows_of(BALIGA, "Raw data")
    header = [str(c).strip() if c is not None else "" for c in rows[9]]
    col = {h: i for i, h in enumerate(header)}
    seen = set()
    recs = []
    for r in rows[10:]:
        if len(r) <= col["Dilution 1 +"] or r[col["Pat/Ctr/cAl"]] != "P" or not r[col["Location"]]:
            continue
        test = str(r[col["Test name"]]).strip()
        if test not in GALLERY_TESTS:
            continue
        date = r[col["Sample date"]]
        date = date.date() if isinstance(date, dt.datetime) else dt.date.fromisoformat(str(date)[:10])
        rtime = r[col["Result time"]]
        key = (str(r[col["Sample/ctrl ID"]]), test, str(rtime), r[col["Result"]])
        if key in seen:
            continue
        seen.add(key)
        err = str(r[col["Errors"]]).strip().strip(",") if r[col["Errors"]] else ""
        recs.append({"sample": f"{r[col['Location']]}-{r[col['Depth']]}-{date:%Y%m%d}-NH3NO2", "date": date, "id": str(r[col["Sample/ctrl ID"]]),
                     "test": test, "result": fnum(r[col["Result"]]), "unit": str(r[col["Result unit"]]), "time": rtime,
                     "err": err, "dil": int(fnum(r[col["Dilution 1 +"]]) or 0)})
    samples = []
    for rec in sorted(recs, key=lambda x: (x["date"], 0)):
        if rec["sample"] not in samples:
            samples.append(rec["sample"])
    # keep the raw-data row order within a date
    order = []
    for rec in recs:
        if rec["sample"] not in order:
            order.append(rec["sample"])
    samples = sorted(order, key=lambda s: (s.split("-")[2], order.index(s)))
    by = defaultdict(list)
    for rec in recs:
        by[(rec["sample"], rec["test"])].append(rec)
    n_rep = 2
    values = {t: [] for t in GALLERY_TESTS}
    below = {t: [] for t in GALLERY_TESTS}
    above = {t: [] for t in GALLERY_TESTS}
    log = {"used_1plus4_rerun": [], "over_range_unresolved": [], "below_range": [], "negative": [], "two_runs": []}
    for s in samples:
        for test in GALLERY_TESTS:
            rs = sorted(by.get((s, test), []), key=lambda x: str(x["time"]))
            ok0 = [r for r in rs if r["dil"] == 0 and not r["err"]]
            ok4 = [r for r in rs if r["dil"] == 4 and not r["err"]]
            chosen = ok0 or ok4
            if ok4 and not ok0:
                log["used_1plus4_rerun"].append(f"{s} {test}")
            if len(chosen) > 1:
                log["two_runs"].append(f"{s} {test} ({len(chosen)} runs)")
            errs0 = {r["err"] for r in rs if r["dil"] == 0}
            factor = (1000.0 / N_MASS) if test == "Ammon H UW" else (1.0 / N_MASS)
            vals, bel, abv = [], [], []
            for i in range(n_rep):
                if i < len(chosen):
                    v = chosen[i]["result"]
                    if v is None:
                        vals.append(None); bel.append(None); abv.append(None)
                    elif v < 0:
                        vals.append(None); bel.append(True); abv.append(False)
                        log["negative"].append(f"{s} {test} run {i + 1}")
                    else:
                        vals.append(round(v * factor, 4)); bel.append(False); abv.append(False)
                elif i == 0 and not chosen and rs:
                    if "30" in errs0:
                        vals.append(None); bel.append(True); abv.append(False)
                        log["below_range"].append(f"{s} {test}")
                    elif "19" in errs0:
                        vals.append(None); bel.append(False); abv.append(True)
                        log["over_range_unresolved"].append(f"{s} {test}")
                    else:
                        vals.append(None); bel.append(None); abv.append(None)
                else:
                    vals.append(None); bel.append(None); abv.append(None)
            values[test].extend(vals); below[test].extend(bel); above[test].extend(abv)
    variables = []
    for test, (mol, method) in GALLERY_TESTS.items():
        mctx = [ctx("molecule from list", oterm_value(mol))] + ([ctx("method", sval(method))] if method else [])
        variables.append(float_var("concentration", "uM", mctx, values[test]))
        rng = [ctx("relative", sval("calibration range"))]
        variables.append(bool_var("below", rng + mctx, below[test]))
        if any(above[test]):
            variables.append(bool_var("above", rng + mctx, above[test]))
    array_context = [
        ctx("instrument", sval("Thermo Fisher Gallery discrete analyzer (University of Washington, SN 861000110448), software 5.3")),
        ctx("method", sval("Spectrophotometric ammonia (Ammonia R1/R2 kits; high-range Ammon H UW and low-range NH4 L Tri methods) and nitrite (TON R1/R2 kit, Nitrite KC method) on 0.2 um syringe-filtered groundwater stored at 4 C; "
                            "results are reported as nitrogen (mg N/L for Ammon H UW, ug N/L for the others; the export's 'U/l' is ug/L) and converted here to micromolar with 14.007 g/mol")),
        ctx("personnel", oterm_value("Nitin Baliga")),
        comment("Only undiluted injections are loaded (the instrument's 1+9 auto-dilution series carries a 10x-amplified blank offset); where the undiluted injection was over range (Gallery error 19) the 1+4 re-run is loaded instead; "
                "Gallery error 30 (below range) and negative results are stored as null with the below flag set; the replicate series holds technical replicates: replicate 2 is the second undiluted run of the two samples that were run twice (KH1, KH9)"),
        comment("Ammonium method high range = Gallery Ammon H UW (0.04 to 2 mg N/L, calibrated 2024-10-07); low range = NH4 L Tri (0 to 200 ug N/L, calibration dated 2021-03-09); nitrite = Nitrite KC. "
                "below calibration range is true when the Gallery reported below range (error 30) or a negative result; above calibration range is true when a result stayed over range"),
        comment("The lab's reportable ammonia value is the high-range method; the low-range method's calibration was 3.5 years old at run time and is included for the samples within its range"),
        comment(f"Source: {rel(BALIGA)}, sheet Raw data (Gallery exports of 2024-10-08 and 2024-11-11); sample codes KH1-KH38 map to the 2024-09-09 and 2024-09-18 samplings and the port-named codes to 2024-10-14"),
    ]
    obj = brick("baliga_ammonium_nitrite_sso_pilot_time_series_2024", "Baliga Lab Gallery analyzer ammonium and nitrite concentrations for the 2024 SSO pilot time series groundwater samples",
                "chemical measurement", array_context, [sample_dim(samples), replicate_dim(n_rep)], variables)
    return obj, samples, log


# ----------------------------------------------------------------------------
# A3 / B1: Hazen Lab AODC
# ----------------------------------------------------------------------------

def read_aodc(path: Path, iwc: bool):
    rows = rows_of(path, "Sheet1")
    header = [str(c).strip() if c is not None else "" for c in rows[11]]
    if header[1] != "Sample ID" or header[8] != "Field 1":
        raise ValueError(f"{path.name}: unexpected AODC layout {header[:9]}")
    recs, blank = [], None
    for r in rows[12:]:
        r = tuple(r) + (None,) * (18 - len(r))
        sid = r[1]
        if sid is None:
            if recs:
                break
            continue
        if iwc and r[0] and str(r[0]).endswith("_INT"):
            continue
        label = str(sid).strip()
        note = " ".join(label.split()[1:]) if iwc and len(label.split()) > 1 else ""
        cmt = str(r[4]).strip() if r[4] else None
        if note:
            cmt = f"{cmt}; {note}" if cmt else note
        rec = {"label": label, "datetime": r[2], "cells_per_ml": fnum(r[3]), "comment": cmt,
               "dilution_ml": fnum(r[5]), "cv": fnum(r[6]), "mean_per_field": fnum(r[7]),
               "fields": [None if v is None else int(v) for v in r[8:18]]}
        if rec["label"].lower() == "blank":
            blank = rec
        else:
            recs.append(rec)
    return recs, blank


def aodc_context(path: Path, blank: dict | None, extra: list[str]) -> list[dict]:
    out = [
        ctx("ENIGMA campaign", oterm_value("Subsurface Observatory")),
        ctx("personnel", oterm_value("Terry Hazen")),
        comment("Microscope ID 3335000410"),
        ctx("instrument", sval("Objective Lens 100X N-Achroplan Oil")),
        ctx("method", sval("Acridine orange direct counts (Hazen UTK lab book); 1 mL of sample membrane filtered, 0.01 mL in a 6 mm well, 10X ocular, 11,815 fields per 25 mm filter; cells/mL = mean cells per field x fields per filter / volume filtered; slides prepared by D. C. Joyner, counted by T. C. Hazen")),
        comment("Processed variables: cell count per mL, coefficient of variation of the cell counts across microscope fields (percent), and average cell count per microscope field; raw counts are cells per field for up to 10 fields (replicate series); the sample volume is the volume filtered"),
        comment(f"Source: {rel(path)}, sheet Sheet1"),
    ]
    if blank:
        out.append(comment(f"Filter blank: mean {blank['mean_per_field']:g} cells per field, {blank['cells_per_ml']:.0f} cells/mL, CV {blank['cv']:.1f}% (not subtracted)"))
    return out + [comment(e) for e in extra]


def build_aodc(name_stem: str, description: str, path: Path, recs: list[dict], samples: list[str], blank, extra: list[str]):
    sample_extra = [
        typed("volume", "float", [r["dilution_ml"] for r in recs], "milliliter", []),
        typed("comment", "string", [r["comment"] for r in recs], None, []),
    ]
    cell = [ctx("category", oterm_value("cell")), ctx("method", sval("AODC"))]
    processed = brick(f"hazen_aodc_{name_stem}", description, "microbial abundance", aodc_context(path, blank, extra), [sample_dim(samples, sample_extra)], [
        float_var("count", "cells per milliliter", cell, [r["cells_per_ml"] for r in recs]),
        float_var("coefficient of variation", "percent", [ctx("measurement", oterm_value("count")), ctx("category", oterm_value("cell"))], [r["cv"] for r in recs]),
        float_var("average", "cells per well", [ctx("measurement", oterm_value("count")), ctx("category", oterm_value("cell"))], [r["mean_per_field"] for r in recs]),
    ])
    raw_counts = [v for r in recs for v in r["fields"]]
    raw = brick(f"hazen_aodc_raw_{name_stem}", description.replace("processed", "raw field counts"), "microbial abundance", aodc_context(path, blank, extra),
                [sample_dim(samples, sample_extra), replicate_dim(10)],
                [typed("count", "int", raw_counts, "cells per well", cell)])
    return processed, raw


def pump_aodc_sample(label: str) -> str:
    m = re.match(r"([A-Z]\d)-(SZ\d)[ -](PRE|POST|0L|100L|200L)$", label.upper())
    if not m:
        raise ValueError(f"unrecognised AODC label {label}")
    return pump_sample(m.group(1), m.group(2), m.group(3), "AODC")


# ----------------------------------------------------------------------------
# B2: Northen Lab GNPS feature tables
# ----------------------------------------------------------------------------
RUNS = [
    ("c18_pos", "*C18-EP*/RP pos *", "positive polarity", "C18 reversed-phase", "2023-11-14"),
    ("c18_neg", "*C18-EP*/RP neg *", "negative polarity", "C18 reversed-phase", "2023-11-14"),
    ("hilic_pos", "*HILICZ*/HILIC POS *", "positive polarity", "HILIC-Z", "2023-11-17"),
    ("hilic_neg", "*HILICZ*/HILIC neg *", "negative polarity", "HILIC-Z", "2023-11-17"),
]
WELL_ORDER = ["U1", "U2", "U3", "M4", "M5", "M6", "L7", "L8", "L9"]
SOIL_RE = re.compile(r"_MS2_\d+_soil-([A-Z]\d)-([A-Z0-9]+)-C(\d+)_tr(\d)_")
CTRL_RE = re.compile(r"_MS2_\d+_(ExCtrl-NA-NA-NA)_(\d)_")
QC_RE = re.compile(r"_MS2_\d+_(QC-[A-Za-z0-9-]+)_")


_CHEBI_BY_INCHIKEY: dict[str, str] = {}


def chebi_by_inchikey() -> dict[str, str]:
    """InChIKey -> CHEBI id from the production chebi.obo (first id listed for a key)."""
    if not _CHEBI_BY_INCHIKEY:
        cur = None
        with (ONTOLOGIES / "chebi.obo").open(errors="ignore") as h:
            for line in h:
                if line.startswith("id: "):
                    cur = line[4:].strip()
                elif "chebi/inchikey" in line and cur:
                    key = line.split('"')[1]
                    _CHEBI_BY_INCHIKEY.setdefault(key, cur)
    return _CHEBI_BY_INCHIKEY


def unquote(value):
    """GNPS exports some library compound names wrapped in literal double quotes; strip one wrapping pair."""
    if isinstance(value, str) and len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    if isinstance(value, str) and value.strip().upper() in ("", "N/A", "NA", "NONE", "NULL"):
        return None  # GNPS placeholders for a missing library field
    return value


def gnps_sample(colname: str):
    m = SOIL_RE.search(colname)
    if m:
        well = {"M4": "M4A", "L9": "L9B"}.get(m.group(1), m.group(1))
        return (f"SSO-{well}-C{m.group(3)}-00", None, int(m.group(4)), (WELL_ORDER.index(m.group(1)), int(m.group(3))))
    m = CTRL_RE.search(colname)
    if m:
        return (None, f"ExCtrl_{m.group(2)}", 1, (90, int(m.group(2))))
    m = QC_RE.search(colname)
    if m:
        return (None, m.group(1), 1, (99, 0))
    raise ValueError(f"cannot parse GNPS file column {colname}")


def build_metabolomics(key: str, pattern: str, polarity: str, chromatography: str, run_date: str, staged: set[str]):
    run_dir = drive(f"2023_SSO_Drilling*Sediment Core/2023-Northen-Metabolomics-sediment/{pattern}")
    job = run_dir.name.split()[-1]
    ft_path = run_dir / "nf_output/clustering/featuretable_reformated.csv"
    lib_path = run_dir / "nf_output/library/merged_results_with_gnps.tsv"
    with ft_path.open() as h:
        rows = list(csv.DictReader(h))
    cols = [c for c in rows[0].keys() if c.endswith(" Peak area")]
    parsed = {c: gnps_sample(c) for c in cols}
    entities = OrderedDict()
    for c, (sample, control, rep, order) in parsed.items():
        ent = sample or control
        entities.setdefault(ent, {"sample": sample, "control": control, "order": order, "cols": {}})
        if rep in entities[ent]["cols"]:
            raise ValueError(f"{key}: duplicate replicate {rep} for {ent}")
        entities[ent]["cols"][rep] = c
    ents = sorted(entities.values(), key=lambda e: e["order"])
    names = [e["sample"] for e in ents]
    controls = [e["control"] for e in ents]
    for s in names:
        if s and s not in staged:
            raise ValueError(f"{key}: sample {s} not in CORAL")
    n_rep = max(max(e["cols"]) for e in ents)
    best = {}
    with lib_path.open() as h:
        for r in csv.DictReader(h, delimiter="\t"):
            scan = r["#Scan#"]
            score = float(r["MQScore"] or 0)
            if scan not in best or score > best[scan][0]:
                best[scan] = (score, r)
    intens, idx, mz, rt, desc, formula, inchikey, chebi, match_id, score_v, adduct = [], [], [], [], [], [], [], [], [], [], []
    for r in rows:
        rid = r["row ID"]
        idx.append(int(rid)); mz.append(float(r["row m/z"])); rt.append(float(r["row retention time"]))
        hit = best.get(rid)
        if hit:
            score, lr = hit
            ik = unquote(lr.get("InChIKey")) or None
            desc.append(unquote(lr["Compound_Name"]) or None)
            formula.append(unquote(lr.get("molecular_formula")) or None)
            inchikey.append(ik)
            chebi.append(chebi_by_inchikey().get(ik) if ik else None)
            match_id.append(lr["SpectrumID"] or None)
            score_v.append(round(score, 6))
            adduct.append(unquote(lr.get("Adduct")) or None)
        else:
            for lst in (desc, formula, inchikey, chebi, match_id, adduct):
                lst.append(None)
            score_v.append(None)
        for e in ents:
            for rep in range(1, n_rep + 1):
                c = e["cols"].get(rep)
                intens.append(None if c is None else float(r[c]))
    ref = [ctx("chemical context", oterm_value("reference compound"))]
    mol_extra = [
        typed("index", "int", idx, "count unit", []),
        typed("m/z", "float", mz, "dimensionless unit", []),
        typed("retention time", "float", rt, "minute", []),
        {"value_type": term("ionization mode"), "values": {"scalar_type": "oterm_ref", "oterm_refs": [T[polarity]] * len(rows), "string_values": [NAMES[T[polarity]]] * len(rows)}},
        {"value_type": term("molecule from list"), "value_context": ref, "values": {"scalar_type": "oterm_ref", "oterm_refs": chebi, "string_values": [NAMES[c] if c else None for c in chebi]}},
        typed("InChIKey", "string", inchikey, None, ref),
        typed("molecular formula", "string", formula, None, ref),
        typed("spectral library compound name", "string", desc, None, []),
        typed("spectral library match ID", "string", match_id, None, []),
        typed("spectral match score", "float", score_v, "dimensionless unit", []),
        typed("adduct", "string", adduct, None, []),
    ]
    mol_dim = {"data_type": term("molecule"), "size": len(rows), "typed_values": mol_extra}
    ctype = [None if c is None else ("positive control" if c.startswith("QC") else "negative control") for c in controls]
    sdim = sample_dim(names, [
        {"value_type": term("control"), "values": {"scalar_type": "oterm_ref", "oterm_refs": [T[c] if c else None for c in ctype], "string_values": [NAMES[T[c]] if c else None for c in ctype]}},
        typed("control name", "string", controls, None, []),
    ])
    array_context = [
        ctx("instrument", sval(f"Thermo Q Exactive Orbitrap LC-MS, {chromatography} chromatography, {NAMES[T[polarity]].replace(' polarity', '')} electrospray ionization (QE119)")),
        ctx("method", sval("Water extraction of sediment, LC-MS and annotation per Davenport et al. 2023 PNAS (doi:10.1073/pnas.2303335120); MZmine feature finding (peak area, no normalization) and GNPS2 feature-based molecular networking for MS2 library matching")),
        ctx("personnel", oterm_value("Suzanne Kosina")),
        comment(f"GNPS2 feature-based molecular networking job {job} (submitter smkosina, 2024-02-20); LC-MS run {run_date}; {chromatography} {NAMES[T[polarity]]}"),
        comment("Feature variables: index = MZmine feature row ID; m/z = feature m/z; retention time in minutes; for features whose MS2 spectrum matched a GNPS library spectrum (best MQScore when several), the library compound name, match spectrum ID, MQScore and adduct, and as the reference compound its InChIKey, molecular formula and, where CHEBI has that InChIKey, the CHEBI molecule"),
        comment("Values are MS1 feature areas (MZmine peak area, instrument arbitrary units, no normalization); controls are columns with no sample: control = negative control for the extraction blanks ExCtrl_1 to ExCtrl_4 and positive control for the QC standard mix QC-SDM89-SOPv4, each injected once; replicate 1 and 2 are the two technical-replicate injections (tr1, tr2) of each core, separately numbered vials from the single metabolomics aliquot of the core, run in randomized order; library annotation is the best-scoring GNPS match of the feature's MS2 scan, when any"),
        comment(f"Source: {rel(ft_path)} and {lib_path.name}; GNPS M4 and L9 cores are the CORAL SSO-M4A and SSO-L9B samples"),
    ]
    obj = brick(f"northen_metabolomics_sso_sediment_2023_{key}", f"Northen Lab untargeted LC-MS metabolomics feature table ({chromatography}, {NAMES[T[polarity]]}) for the 2023 SSO sediment core samples",
                "metabolite assay", array_context, [mol_dim, sdim, replicate_dim(n_rep, "technical replicate")],
                [float_var("MS1 feature area", "dimensionless unit", [], intens)])
    return obj, [s for s in names if s], run_date


# ----------------------------------------------------------------------------
# validation and packaging
# ----------------------------------------------------------------------------

def run_checkgeneric(json_path: Path) -> tuple[bool, str]:
    cp = [str(CHECKGENERIC_CLASSES), os.environ.get("CLASSPATH", "")] + [str(p) for p in JACKSON_JARS]
    proc = subprocess.run(["java", "-cp", os.pathsep.join(p for p in cp if p), "gov.lbl.enigma.app.CheckGeneric", str(json_path)], capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0 and "Generic is OK!" in out, out


def _len(values: dict) -> int:
    for k in ("float_values", "int_values", "string_values", "boolean_values", "object_refs", "oterm_refs"):
        if k in values:
            return len(values[k])
    raise ValueError(f"no value list in {list(values)}")


def check_shape(obj: dict) -> None:
    n = 1
    for d in obj["dim_context"]:
        n *= d["size"]
        for tv in d["typed_values"]:
            if _len(tv["values"]) != d["size"]:
                raise ValueError(f"{obj['name']}: dimension variable {tv['value_type']['term_name']} length {_len(tv['values'])} != {d['size']}")
    for v in obj["typed_values"]:
        if _len(v["values"]) != n:
            raise ValueError(f"{obj['name']}: variable {v['value_type']['term_name']} length {_len(v['values'])} != {n}")


def write_brick(obj: dict) -> Path:
    check_shape(obj)
    path = JSON_OUT / obj["name"].replace(".hndarray", ".json")
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")
    ok, out = run_checkgeneric(path)
    (CHECK_OUT / (path.name + ".check")).write_text(out)
    if not ok:
        raise RuntimeError(f"CheckGeneric failed for {path}:\n{out[-3000:]}")
    print(f"built {obj['name']} shape {[d['size'] for d in obj['dim_context']]} vars {len(obj['typed_values'])} CheckGeneric OK", flush=True)
    return path


def write_process(path: Path, rows: list[dict]) -> None:
    fieldnames = ["process", "person", "campaign", "protocol", "date_start", "date_end", "input_objects", "output_objects"]
    with path.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> None:
    load_ontology_names()
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    for d in (JSON_OUT, STATIC_OUT, PROCESS_OUT, CHECK_OUT, REPORT_OUT):
        d.mkdir(parents=True)
    live = live_samples()
    summary: dict = {"release": RELEASE, "source_export": str(EXPORT.relative_to(REPO)), "bricks": [], "new_samples": []}
    processes: dict[str, list[dict]] = defaultdict(list)

    # ---- B1 samples
    meta = read_iwc_meta()
    sample_rows = iwc_sample_rows(meta)
    for r in sample_rows:
        if r[0] in live:
            raise ValueError(f"IWC sample {r[0]} already exists in CORAL")
    sample_path = STATIC_OUT / f"Sample_additions_{RELEASE}.tsv"
    with sample_path.open("w", newline="") as h:
        w = csv.writer(h, delimiter="\t", lineterminator="\n")
        w.writerow(["name", "location", "depth", "elevation", "date", "time", "timezone", "material", "env_package", "description"])
        w.writerows(sample_rows)
    staged = set(live) | {r[0] for r in sample_rows}
    summary["new_samples"] = [r[0] for r in sample_rows]
    summary["iwc_crosswalk"] = [{"port": k, "adams_id": v["adams_id"], "port_visit": v["sample"], "metals_sample": v["metals"], "aodc_sample": v["aodc"], "pump_start": f"{v['pump_start']:%H:%M}", "pump_end": f"{v['pump_end']:%H:%M}"} for k, v in meta.items()]
    sampling_path = PROCESS_OUT / f"process_sampling_sso_iwc_{RELEASE}.tsv"
    write_process(sampling_path, [{"process": "Sampling <PROCESS:0000002>", "person": "Hazen Lab <ENIGMA:0000066>", "campaign": CAMPAIGN, "protocol": "null",
                                   "date_start": rec["date"].isoformat(), "date_end": rec["date"].isoformat(),
                                   "input_objects": f"Location: SSO-{rec['well']}", "output_objects": f"Sample: {rec['metals']}, Sample: {rec['aodc']}"} for rec in meta.values()])

    def record(obj, samples, process, person, date_start, date_end=None, protocol="null", outputs=None, inputs=None):
        missing = [s for s in samples if s not in staged]
        if missing:
            raise ValueError(f"{obj['name']}: samples not in CORAL or staged: {missing[:5]}")
        path = write_brick(obj)
        summary["bricks"].append({"name": obj["name"], "json": path.name, "shape": [d["size"] for d in obj["dim_context"]], "variables": len(obj["typed_values"]), "samples": len(samples)})
        processes[process].append({"process": process, "person": person, "campaign": CAMPAIGN, "protocol": protocol, "date_start": date_start, "date_end": date_end or date_start,
                                   "input_objects": inputs or ", ".join(f"Sample: {s}" for s in samples), "output_objects": outputs or f"Generic: {obj['name']}"})
        return path

    GEO = "Assay Geochemistry <PROCESS:0000005>"
    CELLS = "Assay Cell Counts <PROCESS:0000008>"
    ENV = "Assay Environment <PROCESS:0000004>"
    METAB = "Assay Metabolites <PROCESS:0000009>"
    poole = f"Farris Poole <{T['Farris Poole']}>"

    # ---- B1 field readings
    obj, locations = build_iwc_field(meta)
    record(obj, [], ENV, "Hazen Lab <ENIGMA:0000066>", "2023-06-26", "2023-08-09", inputs=", ".join(f"Location: {l}" for l in locations))

    # ---- A1 / B1 / B2 metals
    parsed = read_adams(ADAMS_PUMP, "uM")
    obj, samples = build_metals("adams_metals_sso_pump_test_2024", "Adams Lab ICP-MS metal concentrations (52 elements, sample minus blank) for the 2024 SSO pump test groundwater samples",
                                ADAMS_PUMP, parsed, pump_metals_sample, "uM", "2024-06-29",
                                ["Pre and Post samples of each port map to the start-of-pumping (...METALS1) and end-of-pumping (...METALS2) CORAL samples; the M5-SZ3 0, 100 and 200 L samples map to the 2024-03-29 METALS, METALS100 and METALS200 samples",
                                 "Na, Mg, Al, K, Ca, Mn, Fe, Sr and U were measured at 375x dilution, the other elements at 1.2x"])
    record(obj, samples, GEO, poole, "2024-06-29")

    parsed = read_adams(ADAMS_TS, "uM")
    obj, samples = build_metals("adams_metals_sso_pilot_time_series_2024", "Adams Lab ICP-MS metal concentrations (52 elements, sample minus blank) for the 2024 SSO pilot time series groundwater samples (2024-09-09 and 2024-09-18)",
                                ADAMS_TS, parsed, ts_metals_sample_factory(parsed), "uM", "2024-10-09 (re-run 2025-09-17)",
                                ["Final data set of 2025-09-17: Na, Mg, Al, K, Ca, Mn, Sr and U re-measured at 600x dilution after the ICP-MS repair; Fe was not re-run and remains the 1.2x measurement, which the lab flagged as semi-quantitative",
                                 "Data rows are joined to samples by tube number (HNO3-3000 to HNO3-3037, written HN03 in the data sheet) through the Sample Info sheet"])
    record(obj, samples, GEO, poole, "2024-10-09", "2025-09-17")

    parsed = read_adams(ADAMS_IWC, "uM")
    obj, samples = build_metals("adams_metals_sso_initial_well_characterization_2023", "Adams Lab ICP-MS metal concentrations (52 elements, sample minus blank) for the 2023 SSO initial well characterization groundwater samples (28 ports)",
                                ADAMS_IWC, parsed, iwc_metals_sample_factory(meta), "uM", "2024-06-29",
                                ["Samples arrived unacidified despite the tube labels and were run as raw groundwater after about 3 months at 4 C (2.4x dilution; Na, Mg, Al, K, Ca, Mn, Fe, Sr and U at 750x)",
                                 "Adams Lab IDs SSO-1 to SSO-28 follow the order of the Hazen metadata sheet (L7, L8, L9, M4, M5, M6, U1, U2, U3; SZ2, SZ1, VSZ within each well)"])
    record(obj, samples, GEO, poole, "2024-06-29")

    parsed = read_adams(ADAMS_SED, "mg per Kg")
    obj, samples = build_metals("adams_metals_sso_sediment_cores_2023", "Adams Lab ICP-MS metal concentrations (52 elements, mg per kg dry sediment, sample minus blank) for the 2023 SSO sediment core samples",
                                ADAMS_SED, parsed, sediment_sample, "mg/kg", "2024-06-29",
                                ["Concentrations are per kg dry sediment from the EPA 3051A microwave nitric-acid digest (the sample weight is the dry mass digested and the sample volume is the digest resuspension volume; 250x final dilution, Mg, Al, K, Ca, Mn and Fe at 25,000x); detection limits and background equivalent concentrations are computed for a nominal 0.5 g",
                                 "Sample IDs SSO-<well>-C<n> are the CORAL -00 subsamples; the Adams workbook calls the M4 cores SSO-M4 (CORAL SSO-M4A) and notes that some hand-written IDs were matched approximately"],
                                sample_extra=sediment_sample_extra)
    record(obj, samples, GEO, poole, "2024-06-29")

    # ---- A2 Baliga
    obj, samples, log = build_baliga()
    summary["baliga_selection"] = log
    record(obj, samples, GEO, f"Nitin Baliga <{T['Nitin Baliga']}>", "2024-10-08", "2024-11-11")

    # ---- A3 AODC pump test
    recs, blank = read_aodc(AODC_PUMP, iwc=False)
    samples = [pump_aodc_sample(r["label"]) for r in recs]
    proc, raw = build_aodc("sso_pump_test_2024", "Hazen Lab AODC processed data for the 2024 SSO pump test groundwater samples", AODC_PUMP, recs, samples, blank,
                           ["PRE and POST labels map to the start-of-pumping (...AODC1) and end-of-pumping (...AODC2) CORAL samples; M5-SZ3 0L, 100L and 200L map to the 2024-03-29 AODC, AODC100 and AODC200 samples; the workbook has no count dates"])
    write_brick(raw)
    summary["bricks"].append({"name": raw["name"], "json": raw["name"].replace(".hndarray", ".json"), "shape": [d["size"] for d in raw["dim_context"]], "variables": 1, "samples": len(samples)})
    record(proc, samples, CELLS, f"Terry Hazen <{T['Terry Hazen']}>", "2024-08-20", protocol="hazen-2016-aodc", outputs=f"Generic: {proc['name']}, Generic: {raw['name']}")

    # ---- B1 AODC
    recs, blank = read_aodc(AODC_IWC, iwc=True)
    samples = []
    for r in recs:
        port = r["label"].split()[0].replace("-", "_")
        rec = meta[port]
        if r["datetime"] and isinstance(r["datetime"], dt.datetime) and r["datetime"].date() != rec["date"]:
            raise ValueError(f"AODC date {r['datetime']} differs from metadata for {port}")
        samples.append(rec["aodc"])
    proc, raw = build_aodc("sso_initial_well_characterization_2023", "Hazen Lab AODC processed data for the 2023 SSO initial well characterization groundwater samples", AODC_IWC, recs, samples, blank,
                           ["Each port's second workbook row (_INT, intracellular count) has no field tallies and is not loaded; the L7-SZ2 slide is annotated 'Clumping'"])
    write_brick(raw)
    summary["bricks"].append({"name": raw["name"], "json": raw["name"].replace(".hndarray", ".json"), "shape": [d["size"] for d in raw["dim_context"]], "variables": 1, "samples": len(samples)})
    record(proc, samples, CELLS, f"Terry Hazen <{T['Terry Hazen']}>", "2023-11-21", protocol="hazen-2016-aodc", outputs=f"Generic: {proc['name']}, Generic: {raw['name']}")

    # ---- B2 metabolomics
    for key, pattern, polarity, chrom, run_date in RUNS:
        obj, samples, _ = build_metabolomics(key, pattern, polarity, chrom, run_date, staged)
        record(obj, samples, METAB, f"Suzanne Kosina <{T['Suzanne Kosina']}>", run_date)

    # ---- process files and packaging
    process_files = []
    for process, rows in processes.items():
        slug = process.split(" <")[0].lower().replace(" ", "_")
        path = PROCESS_OUT / f"process_{slug}_sso_batch_ab_{RELEASE}.tsv"
        write_process(path, rows)
        process_files.append((process.split(" <")[0], path.name))
    files = [f"static/{sample_path.name}", f"process/{sampling_path.name}"] + [f"json/{b['json']}" for b in summary["bricks"]] + [f"process/{n}" for _, n in process_files]
    (OUT / "files_to_import.txt").write_text("\n".join(files) + "\n")
    script = ["# Paste into the CORAL import notebook after uploading every file in files_to_import.txt", "# (files are referenced by basename). Run the cells in order.", "",
              "# Cell 1: the 56 initial-well-characterization samples (28 ports x METALS, AODC) and their 28 Sampling processes.",
              f"toolx.update_core('{sample_path.name}', 'Sample')", f"toolx.upload_process('Sampling', '{sampling_path.name}')", "",
              "# Cell 2: the bricks."] + [f"toolx.upload_brick('{b['json']}')" for b in summary["bricks"]] + ["", "# Cell 3: the assay processes linking samples to bricks."] + \
             [f"toolx.upload_process('{p}', '{n}')" for p, n in process_files] + [""]
    (OUT / "import_to_coral.py").write_text("\n".join(script))
    (REPORT_OUT / "build_summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    readme = [f"# SSO batches A and B CORAL import ({RELEASE})", "",
              "Bricks built from the team Google Drive workbooks (see `tools/build_sso_batch_ab_coral_import.py`); loading decisions are documented in `coral_import/LAB_QUESTIONS_20261009.md` section 3.", "",
              "| Brick | Shape | Variables | Samples |", "| --- | --- | --- | --- |"] + \
             [f"| `{b['name']}` | {b['shape']} | {b['variables']} | {b['samples']} |" for b in summary["bricks"]] + ["",
              f"* Static additions: {len(sample_rows)} initial-well-characterization samples (`static/{sample_path.name}`): for each of the 28 ports a `WELL-ZONE-YYYYMMDD-METALS` and a `WELL-ZONE-YYYYMMDD-AODC` bottle sample, both outputs of one Sampling process per port; sampling time = pump end. The sonde readings are keyed by well Location and port (like the Aqua TROLL bricks), not by sample.",
              "* Adams metals: `Sample - Blank` concentrations with SD, DL and BEC as data variables; zeros are kept with the below-detection-limit flag set.",
              "* Baliga: micromolar ammonium (high- and low-range methods) and nitrite from the undiluted Gallery injections (1+4 re-run where over range); see `reports/build_summary.json` for the selection log.",
              "* AODC: processed (cells/mL, CV, mean per field) and raw field-count bricks per campaign.",
              "* Metabolomics: four GNPS feature tables (C18 and HILIC, positive and negative) with MZmine peak areas, two injections per extract, extraction blanks and QC as control columns.",
              "", "Import order: samples and Sampling processes, then bricks, then the assay process files (`import_to_coral.py`). All JSON files pass CheckGeneric (`check/`).", ""]
    (OUT / "README.md").write_text("\n".join(readme))
    print(json.dumps({k: v for k, v in summary.items() if k not in ("bricks", "iwc_crosswalk")}, indent=2, default=str))


if __name__ == "__main__":
    main()
