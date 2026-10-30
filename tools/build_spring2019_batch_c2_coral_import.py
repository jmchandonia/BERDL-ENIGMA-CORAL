#!/usr/bin/env python3
"""Build the CORAL import package for the remaining Spring 2019 items of IMPORT_PLAN_20261009.

Batch C2 (third package of the plan): C3 Elias ferrozine iron, C4 Fields cell counts,
biomass production (3H-leucine) and water isotopes, C6 Stahl ammonia oxidation and
natural-abundance nitrogen isotopes, and C7 Hazen field readings.

* Bottles: Elias R5; Fields R7 (field-fixed counts), R1 (activity and lab-fixed counts) and
  R8 (water isotopes); Stahl R21-R24 and R151-R153. The bottle legend is the scanned field
  sheet GW-821-E_031819_Sampling_Sheet.pdf (see coral_import/LAB_QUESTIONS_20261009.md).
* Field readings are keyed by well Location, like the Aqua TROLL and 2023 SSO sonde bricks.
* The Fields lab also sampled GW821E and GW822E on 2019-03-11, a week before the first sampling in the
  2019 Spring Master Spreadsheet; four Sample objects are added for those bottles (R1 and R8).
* Needs ontology update ME:0000513-ME:0000515 (coral_import/ontology_update_20261019).

Run with the spark-minio/BERIL venv python (openpyxl):
    python tools/build_spring2019_batch_c2_coral_import.py
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_sso_batch_ab_coral_import as ab  # shared term, brick and validation helpers
from build_sso_batch_ab_coral_import import (  # noqa: E402
    T, NAMES, bool_var, below_ctx, brick, comment, ctx, float_var, oterm_value, rel, sample_dim, sval, typed, write_process,
)

REPO = ab.REPO
DRIVE = ab.DRIVE
EXPORT = REPO / "sync-coral-to-berdl/exports/sync-20261019-161321/coral_export/static_tsv"
RELEASE = "20261019"
OUT = REPO / f"coral_import/spring2019_batch_c2_{RELEASE}"
SPRING = DRIVE / "2019_Spring_Integrated Sampling"
FERROZINE = SPRING / "Elias Lab/Ferrozine-ENIGMA-2019.xlsx"
COUNTS = SPRING / "Fields Lab/2019SpringSampling_CellCounts_FieldsLab.xlsx"
ACTIVITY = SPRING / "Fields Lab/2019SpringSampling_activity_FieldsLab.xlsx"
WATER_ISO = SPRING / "Fields Lab/2019SpringSampling_18O_2H.xlsx"
STAHL = SPRING / "Stahl Lab/190618_StableIsotopes_AO_FvN.xlsx"
MASTER = SPRING / "Hazen Lab/Field Sheets/2019 Spring Master Spreadsheet-Metadata.xlsx"
CAMPAIGN = "Spring 2019 Integrated Sampling <ENIGMA:0000100>"
ONTOLOGY_UPDATE = REPO / "coral_import/ontology_update_20261019"
STAGED = Path("/tmp/claude-1000/-scratch-jmc-BERDL-ENIGMA-CORAL/e08931f7-7c7d-4424-a1ff-a5f1bad88ee0/scratchpad/stagedval")

T.update({
    "Spring 2019 Integrated Sampling": "ENIGMA:0000100", "microbial activity": "DA:0000022",
    "iron atom": "CHEBI:18248", "iron(2+)": "CHEBI:29033", "iron(3+)": "CHEBI:29034",
    "water": "CHEBI:15377", "oxygen-18 atom": "CHEBI:33815", "deuterium atom": "CHEBI:29237", "nitrogen-15 atom": "CHEBI:36934",
    "elemental carbon": "CHEBI:33415", "ammonia": "CHEBI:16134", "dinitrogen oxide": "CHEBI:17045",
    "isotope ratio": "ME:0000403", "isotope": "ME:0000408", "oxidation": "ME:0000439", "redox potential": "ME:0000125",
    "biomass production rate": "ME:0000514", "ng/mL/day": "ME:0000513", "time since sample collection": "ME:0000515",
    "hour": "UO:0000032", "top": "ME:0000311", "bottom": "ME:0000312",
    "per mil": "UO:0000168", "mM": "UO:0000063", "nM": "UO:0000065", "millivolt": "UO:0000247",
    "Caitlin Gionfriddo": "ENIGMA:0000127", "Katie Davis": "ENIGMA:0000129", "Matthew Fields": "ENIGMA:0000064",
    "Kristopher Hunt": "ENIGMA:0000164", "Fields Lab": "ENIGMA:0000063",
})

WELL_ORDER = ["GW821E", "GW822E", "GW823D", "MLSB5", "MLSD5", "MLSF5", "FW100-20", "FW101-20", "FW102-20"]
FIELDS_WELLS = {"GW821": "GW821E", "GW822": "GW822E", "GW823": "GW823D", "MLSB": "MLSB5", "MLSD": "MLSD5", "MLSF": "MLSF5",
                "FW100": "FW100-20", "FW101": "FW101-20", "FW102": "FW102-20"}
ELIAS_WELLS = {"GW-821-E": "GW821E", "GW-822-E": "GW822E", "GW-823-D": "GW823D", "MLS-B5": "MLSB5", "MLS-D5": "MLSD5", "MLS-F5": "MLSF5",
               "FW-100-20": "FW100-20", "FW-101-20": "FW101-20", "FW-102-20": "FW102-20"}
ROUNDS = [(dt.date(2019, 3, 18), dt.date(2019, 3, 20)), (dt.date(2019, 4, 1), dt.date(2019, 4, 3)), (dt.date(2019, 4, 15), dt.date(2019, 4, 17)),
          (dt.date(2019, 4, 29), dt.date(2019, 5, 1)), (dt.date(2019, 5, 13), dt.date(2019, 5, 15))]
PRECAMPAIGN = dt.date(2019, 3, 11)
NAME_RE = re.compile(r"^(?P<well>.+?)-(?P<date>\d{4}-\d{2}-\d{2})-(?P<frac>UF|F\d\d)-(?P<r>R\d+)$")


def stage_ontology() -> None:
    """Names and validation use the production ontologies plus the staged ME:0000513-0000514 update."""
    prod = (ONTOLOGY_UPDATE / "production/context_measurement_ontology.obo").read_bytes()
    for d in ("names", "ont"):
        (STAGED / d / "context_measurement_ontology.obo").write_bytes(prod)
    ab.ONTOLOGIES = STAGED / "names"
    cp = (STAGED / "classpath.txt").read_text().strip()

    def run_staged(json_path):
        proc = subprocess.run(["java", "-Xmx4g", "-cp", cp, "gov.lbl.enigma.app.CheckGenericStaged", str(json_path)], capture_output=True, text=True)
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0 and "Generic is OK!" in out, out
    ab.run_checkgeneric = run_staged


def order_key(name: str):
    m = NAME_RE.match(name)
    return (WELL_ORDER.index(m.group("well")), m.group("date"), int(m.group("r")[1:]))


class Bottles:
    """Registered CORAL Spring 2019 bottles, looked up by well, date and R-code."""

    def __init__(self, live: dict[str, dict]):
        self.by = {}
        for name in live:
            m = NAME_RE.match(name)
            if m and m.group("well") in WELL_ORDER and m.group("date").startswith("2019-"):
                self.by[(m.group("well"), dt.date.fromisoformat(m.group("date")), m.group("r"))] = name
        self.extra: dict[tuple, str] = {}

    def get(self, well: str, date: dt.date, rcode: str) -> str:
        key = (well, date, rcode)
        if key in self.by:
            return self.by[key]
        if key in self.extra:
            return self.extra[key]
        raise KeyError(f"no registered bottle {key}")

    def in_round(self, well: str, rnd: int, rcode: str) -> str:
        lo, hi = ROUNDS[rnd]
        hits = [n for (w, d, r), n in self.by.items() if w == well and r == rcode and lo <= d <= hi]
        if len(hits) != 1:
            raise ValueError(f"{well} round {rnd + 1} {rcode}: {hits}")
        return hits[0]


def as_date(v) -> dt.date:
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    raise ValueError(f"not a date: {v!r}")


def mdy(text: str) -> dt.date:
    m, d, y = text.split("/")
    return dt.date(2000 + int(y), int(m), int(d))


def sheet(path: Path, name: str) -> list[tuple]:
    return list(openpyxl.load_workbook(path, read_only=True, data_only=True)[name].iter_rows(values_only=True))


def stat(key: str, extra=()):
    return [ctx("measurement", oterm_value(key))] + list(extra)


# ----------------------------------------------------------------------------
# C3 Elias Lab ferrozine iron
# ----------------------------------------------------------------------------

def parse_fe(v):
    """Returns (value, standard deviation, below detection limit) for one Summary cell."""
    if v is None:
        raise ValueError("empty ferrozine cell")
    if isinstance(v, (int, float)):
        return float(v), None, False
    s = str(v).strip()
    if s.startswith("<"):
        if s != "<0.1":
            raise ValueError(f"unexpected censored value {s}")
        return None, None, True
    m = re.fullmatch(r"([\d.]+) \+/- ([\d.]+)", s)
    if m:
        return float(m.group(1)), float(m.group(2)), False
    raise ValueError(f"unexpected ferrozine value {s!r}")


def build_ferrozine(bottles: Bottles):
    rows = sheet(FERROZINE, "Summary")
    if [rows[1][c] for c in (1, 2, 3)] != ["Total Fe [mg/L]", "Fe (III) [mg/L]", "Fe (II) [mg/L]"]:
        raise ValueError("ferrozine header changed")
    if not str(rows[15][0]).startswith("Detection limit for total Fe: 0.1 mg/L"):
        raise ValueError("ferrozine detection limit note changed")
    recs = {}
    skipped = []
    for r in rows[2:13]:
        if not r[0] or str(r[0]).startswith("Area"):
            continue
        well = ELIAS_WELLS[str(r[0]).strip()]
        for rnd in range(5):
            cells = r[1 + 3 * rnd: 4 + 3 * rnd]
            if all(str(c).strip() == "n.s." for c in cells):
                skipped.append((well, rnd + 1))
                continue
            name = bottles.in_round(well, rnd, "R5")
            recs[name] = dict(zip(("total", "fe3", "fe2"), (parse_fe(c) for c in cells)))
    if skipped != [("GW823D", 2)]:
        raise ValueError(f"unexpected unsampled ferrozine cells {skipped}")
    samples = sorted(recs, key=order_key)
    variables = []
    for key, mol in (("total", "iron atom"), ("fe3", "iron(3+)"), ("fe2", "iron(2+)")):
        m = [ctx("molecule from list", oterm_value(mol))]
        variables += [
            float_var("concentration", "mg/L", m, [recs[s][key][0] for s in samples]),
            float_var("standard deviation", "mg/L", stat("concentration", m), [recs[s][key][1] for s in samples]),
            bool_var("below", below_ctx(m), [recs[s][key][2] for s in samples]),
        ]
    method = " ".join(str(r[0]).strip() for r in sheet(FERROZINE, "Method") if r and r[0])
    array_context = [
        ctx("personnel", oterm_value("Caitlin Gionfriddo")),
        ctx("ENIGMA campaign", oterm_value("Spring 2019 Integrated Sampling")),
        ctx("instrument", sval("Thermo spectrophotometer, 562 nm, 1 cm cuvettes")),
        ctx("method", sval(method)),
        comment("Variables: concentration of total iron (iron atom: ferrozine after hydroxylamine reduction), Fe(III) (iron(3+)) and Fe(II) (iron(2+)) in mg/L, as reported in the Summary sheet; standard deviation of the concentration where the lab reported a triplicate mean (GW821E 2019-03-18 and FW101-20 2019-05-15; the other four triplicate samples were below 0.1 mg/L); and below relative to the detection limit (true where the lab reported <0.1). The lab states a detection limit of 0.1 mg/L for total iron; Fe(II) and Fe(III) values below 0.1 are reported where total iron was quantified"),
        comment("Linked to the HCl-preserved ferrozine bottle (assay 5, R5) of each sampling. GW823D was not sampled for ferrozine on 2019-04-01 (n.s.); its registered R5 bottle has no result"),
        comment(f"Source: {rel(FERROZINE)}, sheets Summary and Method"),
    ]
    obj = brick("elias_ferrozine_iron_spring2019_integrated_sampling", "Elias Lab ferrozine iron (total iron, Fe(III) and Fe(II)) for the Spring 2019 Integrated Sampling groundwater samples",
                "chemical measurement", array_context, [sample_dim(samples)], variables)
    return obj, samples


# ----------------------------------------------------------------------------
# C4 Fields Lab cell counts, biomass production and water isotopes
# ----------------------------------------------------------------------------

def count_date(text: str) -> dt.date:
    m, d, y = (int(x) for x in text.split("."))
    if y == 18:  # one entry error, 07.03.18 among 2019 counts
        y = 19
    return dt.date(2000 + y, m, d)


def build_counts(bottles: Bottles):
    rows = sheet(COUNTS, "Sheet1")
    if list(rows[0][:5]) != ["Well", "ID", "Count Date", "Count total", "Std Dev"]:
        raise ValueError("cell count header changed")
    recs = {}
    for r in rows[1:]:
        if not r or not r[0]:
            continue
        well = FIELDS_WELLS[str(r[0]).strip()]
        ident = str(r[1]).strip()
        m = re.fullmatch(r"\S+ (\d+/\d+/\d+)-Sample (?:& Fixed|(\d+/\d+/\d+)-Fi?x?e?d?)", ident)
        if not m:
            raise ValueError(f"unexpected count ID {ident}")
        sampled = mdy(m.group(1))
        fixed = mdy(m.group(2)) if m.group(2) else sampled
        name = bottles.get(well, sampled, "R7" if fixed == sampled else "R1")
        if name in recs:
            raise ValueError(f"duplicate count {name}")
        recs[name] = {"fixed": fixed, "counted": count_date(str(r[2]).strip()), "count": float(r[3]), "sd": float(r[4])}
    samples = sorted(recs, key=order_key)
    cell = [ctx("category", oterm_value("cell")), ctx("method", sval("SYBR Gold"))]
    dim = sample_dim(samples, [
        typed("date", "string", [recs[s]["fixed"].isoformat() for s in samples], None, [ctx("category", sval("fixation date"))]),
        typed("date", "string", [recs[s]["counted"].isoformat() for s in samples], None, [ctx("category", sval("count date"))]),
    ])
    variables = [
        float_var("count", "cells per milliliter", cell, [recs[s]["count"] for s in samples]),
        float_var("standard deviation", "cells per milliliter", stat("count", cell), [recs[s]["sd"] for s in samples]),
    ]
    array_context = [
        ctx("personnel", oterm_value("Katie Davis")),
        ctx("ENIGMA campaign", oterm_value("Spring 2019 Integrated Sampling")),
        ctx("method", sval("SYBR Gold direct epifluorescence counts of formaldehyde-fixed groundwater")),
        comment("Variables: cell count (cells/mL, Count total) and standard deviation of the count. Dimension variables: fixation date and count date"),
        comment("Field-fixed counts (source ID '<well> <date>-Sample & Fixed', fixation date = sampling date) are linked to the 10 mL formaldehyde bottle pipetted from the 1 L bottle in the field (assay 7, R7). "
                "Lab-fixed counts (source ID '<well> <date>-Sample <date>-Fixed', rounds 4 and 5 and the 2019-03-11 sampling) were fixed at the Fields Lab when the activity assay started and are linked to the 1 L activity bottle (assay 1, R1). The Fields Lab's per-cell activity uses the field-fixed counts"),
        comment("2019-03-11 is a pre-campaign sampling of GW821E and GW822E only (not in the 2019 Spring Master Spreadsheet); its counts were fixed on 2019-03-13. One count date written 07.03.18 is taken as 2019-07-03"),
        comment(f"Source: {rel(COUNTS)}, sheet Sheet1"),
    ]
    obj = brick("fields_cell_counts_spring2019_integrated_sampling", "Fields Lab SYBR Gold cell counts for the Spring 2019 Integrated Sampling groundwater samples",
                "microbial abundance", array_context, [dim], variables)
    return obj, samples, recs


def build_activity(bottles: Bottles):
    rows = sheet(ACTIVITY, "Per mL Activity")
    blocks = [(2, 3, 10), (20, 21, 28), (38, 39, 46)]  # 1-based header row, value-date row, sd-date row
    recs: dict[str, dict] = defaultdict(dict)
    for title_row, vrow, srow in blocks:
        title = str(rows[title_row - 1][2])
        if not title.endswith("activity (ng C/mL/day)") or str(rows[srow - 2][2]) != "std dev (ng C/mL/day)":
            raise ValueError(f"activity block header changed: {title}")
        vdates, sdates = rows[vrow - 1][2:], rows[srow - 1][2:]
        if [as_date(d) for d in vdates if d] != [as_date(d) for d in sdates if d]:
            raise ValueError("activity value and std dev dates differ")
        dates = [as_date(d) if d else None for d in vdates]
        for which, start in (("rate", vrow), ("sd", srow)):
            for r in rows[start:start + 6]:
                label = str(r[1]).strip() if r and r[1] else ""
                if not label or label.startswith("std dev") or label == "Sample":
                    break
                m = re.fullmatch(r"(\w+?)\s*(?:-\s*(24|48)\s*hr)?", label)
                well, hours = FIELDS_WELLS[m.group(1)], int(m.group(2) or 24)
                for d, v in zip(dates, r[2:]):
                    if d is None or v is None:
                        continue
                    name = bottles.get(well, d, "R1")
                    key = f"{which}{hours}"
                    if key in recs[name]:
                        raise ValueError(f"duplicate activity {name} {key}")
                    recs[name][key] = float(v)
    for name, rec in recs.items():
        for h in (24, 48):
            if (f"rate{h}" in rec) != (f"sd{h}" in rec):
                raise ValueError(f"{name}: value without std dev at {h} h")
    samples = sorted(recs, key=order_key)
    carbon = [ctx("molecule from list", oterm_value("elemental carbon"))]
    hours = (24, 48)
    delay_dim = {"data_type": term("time since sample collection"), "size": len(hours), "typed_values": [
        typed("time since sample collection", "float", [float(h) for h in hours], "hour", [ctx("category", sval("incubation start"))])]}
    variables = [
        float_var("biomass production rate", "ng/mL/day", carbon, [recs[s].get(f"rate{h}") for s in samples for h in hours]),
        float_var("standard deviation", "ng/mL/day", stat("biomass production rate", carbon), [recs[s].get(f"sd{h}") for s in samples for h in hours]),
    ]
    array_context = [
        ctx("personnel", oterm_value("Katie Davis")),
        ctx("ENIGMA campaign", oterm_value("Spring 2019 Integrated Sampling")),
        ctx("method", sval("Heterotrophic biomass production from 3H-leucine incorporation into protein in unfiltered groundwater from the 1 L sterile glass bottle (assay 1), shipped at 4 C; reported as ng carbon per mL per day")),
        comment("Variables: biomass production rate (ng C/mL/day, as elemental carbon) and its standard deviation. The second dimension is the time from sample collection to the start of the incubation: 24 h for every campaign sampling, and 48 h for the 2019-03-11 samples (received at 48 h) and for repeat incubations of GW821E 2019-04-01 and MLSB5 2019-04-02, which gave 1.7 to 1.8 times the 24 h rate"),
        comment("Linked to the 1 L activity bottle (assay 1, R1). The source workbook also divides each rate by the field-fixed cell count (Per Cell sheets); that per-cell activity is not loaded, because it is the ratio of this brick to the Fields cell-count brick (and the MLSB 2019-04-02 per-cell value used the MLSF count). FW102-20 was not shipped on 2019-03-20"),
        comment("2019-03-11 is a pre-campaign sampling of GW821E and GW822E only (not in the 2019 Spring Master Spreadsheet)"),
        comment(f"Source: {rel(ACTIVITY)}, sheet Per mL Activity"),
    ]
    obj = brick("fields_biomass_production_spring2019_integrated_sampling", "Fields Lab 3H-leucine biomass production (ng C/mL/day) for the Spring 2019 Integrated Sampling groundwater samples",
                "microbial activity", array_context, [sample_dim(samples), delay_dim], variables)
    return obj, samples


def build_water_isotopes(bottles: Bottles):
    data = {}
    for sn, iso in (("18O", "oxygen-18 atom"), ("2H", "deuterium atom")):
        rows = sheet(WATER_ISO, sn)
        if list(rows[1][1:7]) != ["Sample Date", "Sample ID", "Area", "18O analysis date", "delta 18O", "delta 18O std dev"]:
            raise ValueError(f"{sn} header changed")
        for r in rows[2:]:
            if not r or not r[1]:
                continue
            if r[5] is None:
                if (str(r[2]), as_date(r[1])) != ("FW102", dt.date(2019, 3, 20)):
                    raise ValueError(f"unexpected empty isotope row {r}")
                continue
            name = bottles.get(FIELDS_WELLS[str(r[2]).strip()], as_date(r[1]), "R8")
            analyzed = as_date(r[4])
            if analyzed.year == 2018:
                analyzed = analyzed.replace(year=2019)
            sd = float(r[6])
            data.setdefault(name, {})[sn] = {"delta": float(r[5]), "sd": sd if sd > 0 else None, "analyzed": analyzed}
    if any(set(v) != {"18O", "2H"} for v in data.values()):
        raise ValueError("18O and 2H sheets list different samples")
    if any(v["18O"]["analyzed"] != v["2H"]["analyzed"] for v in data.values()):
        raise ValueError("18O and 2H analysis dates differ")
    samples = sorted(data, key=order_key)
    dim = sample_dim(samples, [typed("date", "string", [data[s]["18O"]["analyzed"].isoformat() for s in samples], None, [ctx("category", sval("analysis date"))])])
    variables = []
    for sn, iso in (("18O", "oxygen-18 atom"), ("2H", "deuterium atom")):
        c = [ctx("molecule from list", oterm_value("water")), ctx("isotope", oterm_value(iso))]
        variables += [
            float_var("isotope ratio", "per mil", c, [data[s][sn]["delta"] for s in samples]),
            float_var("standard deviation", "per mil", stat("isotope ratio", c), [data[s][sn]["sd"] for s in samples]),
        ]
    nulled = sum(1 for s in samples if data[s]["18O"]["sd"] is None)
    array_context = [
        ctx("personnel", oterm_value("Katie Davis")),
        ctx("ENIGMA campaign", oterm_value("Spring 2019 Integrated Sampling")),
        ctx("method", sval("Water stable isotopes (delta 18O and delta 2H, per mil relative to VSMOW, Vienna Standard Mean Ocean Water) of 0.2 um filtered groundwater collected in amber glass without headspace (assay 8)")),
        comment("Variables: isotope ratio of water oxygen-18 (delta 18O) and deuterium (delta 2H), per mil, each with its standard deviation as given by the lab for each analysis batch (0.10 or 0.12 per mil for delta 18O; 1 or 2 per mil for delta 2H). Dimension variable: analysis date (2019-03-21, 2019-04-24 or 2019-06-03)"),
        comment(f"The delta 18O standard deviation of the 2019-06-03 batch ({nulled} samples) is null: the sheet gives -0.1 times the delta value, an entry error. The 2019-03-21 batch is written 2018-03-21 in the sheet. Linked to the filtered isotope bottle (assay 8, R8; the 2019 Spring Master Spreadsheet labels it UF). FW102-20 was not shipped on 2019-03-20"),
        comment("2019-03-11 is a pre-campaign sampling of GW821E and GW822E only (not in the 2019 Spring Master Spreadsheet)"),
        comment(f"Source: {rel(WATER_ISO)}, sheets 18O and 2H"),
    ]
    obj = brick("fields_water_isotopes_spring2019_integrated_sampling", "Fields Lab water delta 18O and delta 2H for the Spring 2019 Integrated Sampling groundwater samples",
                "chemical measurement", array_context, [dim], variables)
    return obj, samples


# ----------------------------------------------------------------------------
# C6 Stahl Lab ammonia oxidation and natural-abundance nitrogen isotopes
# ----------------------------------------------------------------------------

def build_stahl(bottles: Bottles):
    rows = [tuple(r) + (None,) * (30 - len(r)) for r in sheet(STAHL, "Processed")]
    hdr = list(rows[1][:11])
    if hdr[:10] != ["Identifier 1", "Measured", "mL used", "Ampl  44", "Area All", "N mmol/L", "d18Ovsmow", "d15Nair", "18O/16O", "15N/14N"]:
        raise ValueError(f"Stahl header changed {hdr}")
    def bottle_of(ident: str) -> str:
        m = re.fullmatch(r"(GW ?821|MLSB)_(\d{6})_(\d+)\.(\d)", ident.strip())
        well = {"GW821": "GW821E", "GW 821": "GW821E", "MLSB": "MLSB5"}[m.group(1)]
        d = dt.datetime.strptime(m.group(2), "%m%d%y").date()
        return bottles.get(well, d, f"R{m.group(3)}{m.group(4)}")
    recs: dict[str, dict] = defaultdict(dict)
    for i in list(range(2, 10)) + list(range(11, 17)):  # nitrate/nitrite pool rows 3-10 and 12-17
        r = rows[i]
        name = bottle_of(r[0])
        too_low = bool(r[10]) and str(r[10]).startswith("concentration too low")
        recs[name].update({"no3": None if too_low else r[5], "no3_d18": r[6], "no3_d15": r[7], "nh3_ox": rows[i][22] if i < 10 else None})
    for i in range(20, 26):  # dissolved N2O rows 21-26
        r = rows[i]
        name = bottle_of(r[0])
        recs[name].update({"n2o": r[5], "n2o_d18": r[6], "n2o_d15": r[7]})
    samples = sorted(recs, key=order_key)
    if len(samples) != 14:
        raise ValueError(f"expected 14 Stahl bottles, found {len(samples)}")
    kill = [s.endswith("-R24") for s in samples]
    control = {"value_type": term("control"), "values": {"scalar_type": "oterm_ref",
               "oterm_refs": [T["negative control"] if k else None for k in kill],
               "string_values": [NAMES[T["negative control"]] if k else None for k in kill]}}
    def col(k):
        return [None if recs[s].get(k) is None else float(recs[s][k]) for s in samples]
    no3 = [ctx("molecule from list", oterm_value("nitrate"))]
    n2o = [ctx("molecule from list", oterm_value("dinitrogen oxide")), ctx("physiochemical state", sval("dissolved"))]
    iso = lambda c, k: c + [ctx("isotope", oterm_value(k))]
    variables = [
        float_var("concentration", "mM", no3, col("no3")),
        float_var("isotope ratio", "per mil", iso(no3, "nitrogen-15 atom"), col("no3_d15")),
        float_var("isotope ratio", "per mil", iso(no3, "oxygen-18 atom"), col("no3_d18")),
        float_var("isotope ratio", "per mil", iso(n2o, "nitrogen-15 atom"), col("n2o_d15")),
        float_var("isotope ratio", "per mil", iso(n2o, "oxygen-18 atom"), col("n2o_d18")),
        float_var("concentration", "nM", [ctx("molecule from list", oterm_value("ammonia")), ctx("chemical context", oterm_value("oxidation"))], col("nh3_ox")),
    ]
    array_context = [
        ctx("personnel", oterm_value("Kristopher Hunt")),
        ctx("ENIGMA campaign", oterm_value("Spring 2019 Integrated Sampling")),
        ctx("method", sval("Ammonia oxidation assay (assay 2): 120 mL serum bottles of unfiltered groundwater amended with 0.5 uM 15N-ammonium (99 atom percent) and incubated 24 h; bottle 4 killed with azide. "
                            "Natural abundance (assay 15): 30 mL of 0.1 um filtered groundwater. Nitrate plus nitrite converted to N2O by the denitrifier method and dissolved N2O measured by IRMS; "
                            "delta 15N vs air and delta 18O vs VSMOW calibrated with USGS40, USGS41, IAEA-SO-5 and IAEA-SO-6; 1 mM nitrate carrier added to the assay 2 bottles before analysis")),
        comment("Variables: nitrate (the nitrate plus nitrite pool, mM as N, measured by ion chromatography) with its delta 15N and delta 18O (per mil); delta 15N and delta 18O of dissolved nitrous oxide (dinitrogen oxide); "
                "and ammonia oxidized during the 24 h incubation (nM, = 1e9 x (15N/14N of the live bottle x its NOx - 15N/14N of the kill control x its NOx) / 0.99, the lab's calculation). The kill control (bottle 4, control = negative control) is the background for its well"),
        comment("The assay 2 nitrate concentrations include the 1 mM carrier. GW821E natural-abundance nitrate was below quantitation (the area came from the blank) and is null, and its nitrous oxide was too low for isotope ratios; MLSB5 has all values. The sheet's N2O 'N mmol/L' column is not loaded: it is the N2O peak area divided by 1000, not normalized to sample volume or calibrated, so it is not a concentration. "
                "The lab's mean and standard error of ammonia oxidized per well (GW821E 2.9 +/- 1.3 nM, MLSB5 0.95 +/- 0.47 nM per 24 h) are not loaded because they are computed from the three live bottles"),
        comment("Bottles: identifier WELL_MMDDYY_assay.bottle, so GW821_040119_2.1 is GW821E 2019-04-01 bottle R21 and MLSB_040219_15.3 is MLSB5 2019-04-02 bottle R153. FW100-20 was not sampled (no radiation clearance)"),
        comment(f"Source: {rel(STAHL)}, sheet Processed"),
    ]
    obj = brick("stahl_ammonia_oxidation_isotopes_spring2019_integrated_sampling", "Stahl Lab 15N ammonia oxidation assay and natural-abundance nitrate and nitrous oxide isotopes for GW821E and MLSB5, Spring 2019 Integrated Sampling",
                "chemical measurement", array_context, [sample_dim(samples, [control])], variables)
    return obj, samples


def term(key: str) -> dict:
    return ab.term(key)


# ----------------------------------------------------------------------------
# C7 Hazen field readings
# ----------------------------------------------------------------------------

def build_field(live: dict[str, dict]):
    rows = sheet(MASTER, "Sheet1")
    hdr = [str(x).strip() if x else "" for x in rows[2][:14]]
    if hdr[:6] + hdr[7:13] != ["Date Collected", "Time", "Campaign", "WELL", "FRC Area", "VOLUME (ml)", "Recipient", "DO", "ORP (mV)", "Cond (mS/cm)", "Temp", "pH"] or not hdr[6].startswith("SAMPLE ID"):
        raise ValueError(f"master header changed {hdr}")
    events: dict[tuple, dict] = {}
    for r in rows[3:]:
        if not r[0]:
            continue
        well = str(r[3]).strip()  # the WELL column; a few SAMPLE IDs are malformed (R161-168)
        if well not in WELL_ORDER:
            raise ValueError(f"unexpected well {well}")
        date = as_date(r[0])
        reading = tuple(None if v is None or str(v).strip() in ("", "NA") else float(v) for v in r[8:13])
        t = r[1]
        ev = events.setdefault((well, date), {"readings": set(), "times": set(), "note": None})
        ev["readings"].add(reading)
        if isinstance(t, dt.time):
            ev["times"].add(t)
        if len(r) > 13 and r[13]:
            ev["note"] = str(r[13]).strip()
    recs = []
    for (well, date), ev in sorted(events.items(), key=lambda kv: (WELL_ORDER.index(kv[0][0]), kv[0][1])):
        if len(ev["readings"]) != 1:
            raise ValueError(f"{well} {date}: several field readings {ev['readings']}")
        reading = next(iter(ev["readings"]))
        if all(v is None for v in reading):
            continue
        sample = bottles_any(live, well, date)
        recs.append({"location": live[sample]["location_id"], "date": date, "time": min(ev["times"]).strftime("%H:%M") if ev["times"] else None,
                     "do": reading[0], "orp": reading[1], "cond": reading[2], "temp": reading[3], "ph": reading[4]})
    skipped = defaultdict(list)
    for (w, d), ev in sorted(events.items(), key=lambda kv: (kv[0][1], WELL_ORDER.index(kv[0][0]))):
        if all(v is None for v in next(iter(ev["readings"]))):
            skipped[d].append(w)
    notes = sorted({ev["note"] for ev in events.values() if ev["note"]})
    if notes != ["Techincal issues in field. No geochemical data. Purged 3L before samples based on previous stabilizaiton data."]:
        raise ValueError(f"unexpected field notes {notes}")
    locations = [r["location"] for r in recs]
    loc_dim = {"data_type": term("environmental sample location"), "size": len(recs), "typed_values": [
        {"value_type": term("environmental sample location ID"), "values": {"scalar_type": "object_ref", "object_refs": locations, "string_values": locations}},
        typed("date", "string", [r["date"].isoformat() for r in recs], None, []),
        typed("time", "string", [r["time"] for r in recs], None, []),
    ]}
    col = lambda k: [r[k] for r in recs]
    variables = [
        float_var("concentration", "mg/L", [ctx("molecule from list", oterm_value("dioxygen")), ctx("physiochemical state", sval("dissolved"))], col("do")),
        float_var("redox potential", "millivolt", [], col("orp")),
        float_var("conductivity", "uS/cm", [], col("cond")),
        float_var("temperature", "degree Celsius", [], col("temp")),
        float_var("pH", "pH unit", [], col("ph")),
    ]
    array_context = [
        ctx("personnel", oterm_value("Hazen Lab")),
        ctx("ENIGMA campaign", oterm_value("Spring 2019 Integrated Sampling")),
        ctx("method", sval("Field readings of the pumped groundwater in a flow cell after the readings stabilized, recorded once per well visit in the 2019 Spring Master Spreadsheet")),
        comment("Variables: dissolved oxygen (dioxygen, mg/L), redox potential (ORP, mV), conductivity, temperature and pH. Conductivity is uS/cm: the spreadsheet header says mS/cm, but the values (24 to 672) are plausible only in uS/cm and the field sheet template records uS/cm"),
        comment("One row per well visit, keyed by the well Location like the Aqua TROLL bricks, since the sonde kept no water; date is the collection date and time the earliest bottle time of that visit. "
                "The bottle samples of the visit are named WELL-YYYY-MM-DD-FRACTION-Rn"),
        comment("No readings (NA in the spreadsheet) for " + "; ".join(f"{d.isoformat()} {', '.join(w)}" for d, w in skipped.items())
                + ". The spreadsheet notes for round 5: technical issues in the field, no geochemical data; purged 3 L before sampling based on previous stabilization data"),
        comment(f"Source: {rel(MASTER)}, sheet Sheet1 (DO, ORP, Cond, Temp and pH columns)"),
    ]
    obj = brick("hazen_field_spring2019_integrated_sampling", "Hazen Lab field readings (dissolved oxygen, ORP, conductivity, temperature, pH) for each well visit of the Spring 2019 Integrated Sampling",
                "environmental measurement", array_context, [loc_dim], variables)
    return obj, sorted(set(locations), key=locations.index), recs


SONDE_V1 = REPO / "coral_import/sso_batch_ab_20261009/json/hazen_field_sso_initial_well_characterization_2023.json"
SONDE_NOTE = ("pump start and pump end are now a second dimension (time series, category pump start or pump end) instead of duplicated variables; dissolved oxygen (mg/L and percent saturation) now carries physiochemical state = dissolved; "
              "depth to water now carries top = top of casing and bottom = water surface, and the port depth top = ground surface and bottom = screen midpoint; values unchanged")


def build_sonde_v2():
    """2023 SSO sonde brick with explicit dissolved state and depth reference points."""
    obj, locations = ab.build_iwc_field(ab.read_iwc_meta())
    def insert_after_molecule(context, extra):
        i = next(k for k, c in enumerate(context) if c["value_type"]["oterm_ref"] == T["molecule from list"])
        return context[:i + 1] + extra + context[i + 1:]
    changed = defaultdict(int)
    for tv in obj["typed_values"]:
        c = tv.get("value_context", [])
        if any(x["value_type"]["oterm_ref"] == T["molecule from list"] and x["value"].get("oterm_ref") == T["dioxygen"] for x in c):
            tv["value_context"] = insert_after_molecule(c, [ctx("physiochemical state", sval("dissolved"))])
            changed["dissolved oxygen"] += 1
        elif tv["value_type"]["oterm_ref"] == T["depth"]:
            tv["value_context"] = [ctx("top", sval("top of casing")), ctx("bottom", sval("water surface"))] + c
            changed["depth to water"] += 1
    for tv in obj["dim_context"][0]["typed_values"]:
        if tv["value_type"]["oterm_ref"] == T["depth"]:
            tv["value_context"] = [ctx("top", sval("ground surface")), ctx("bottom", sval("screen midpoint"))]  # SSO Cheat Sheet: screen depths BGS
            changed["port depth"] += 1
    if dict(changed) != {"dissolved oxygen": 4, "depth to water": 2, "port depth": 1}:
        raise ValueError(f"unexpected sonde changes {dict(changed)}")
    # Pump start and pump end as a dimension: the builder emits each variable as a (pump start, pump end) pair.
    stages = ("pump start", "pump end")
    pairs = [obj["typed_values"][k:k + 2] for k in range(0, len(obj["typed_values"]), 2)]
    merged = []
    for a, b in pairs:
        cat = [[c["value"].get("string_value") for c in tv["value_context"] if c["value_type"]["oterm_ref"] == T["category"]] for tv in (a, b)]
        if cat != [["pump start"], ["pump end"]] or a["value_type"] != b["value_type"]:
            raise ValueError(f"unexpected sonde variable pair {a['value_type']['term_name']} {cat}")
        rest = [c for c in a["value_context"] if c["value_type"]["oterm_ref"] != T["category"]]
        if rest != [c for c in b["value_context"] if c["value_type"]["oterm_ref"] != T["category"]] or a.get("value_units") != b.get("value_units"):
            raise ValueError(f"{a['value_type']['term_name']}: start and end contexts differ")
        key = next(k for k in a["values"] if k.endswith("_values"))
        tv = {"value_type": a["value_type"], "values": {"scalar_type": a["values"]["scalar_type"],
              key: [x for pair in zip(a["values"][key], b["values"][key]) for x in pair]}}
        if "value_units" in a:
            tv["value_units"] = a["value_units"]
        tv["value_context"] = rest
        merged.append(tv)
    obj["typed_values"] = merged
    obj["dim_context"].append({"data_type": term("time series"), "size": 2, "typed_values": [typed("category", "string", list(stages), None, [])]})
    obj["n_dimensions"] = len(obj["dim_context"])
    for c in obj["array_context"]:
        if c["value_type"]["oterm_ref"] == T["comment"] and c["value"]["string_value"].startswith("Variables with category pump start and pump end"):
            c["value"]["string_value"] = c["value"]["string_value"].replace(
                "Variables with category pump start and pump end are the readings at pump start and pump end; time is the local pump start and end time",
                "The second dimension gives the readings at pump start and pump end; time is the local clock time of each reading (24 h)")
            break
    else:
        raise ValueError("sonde variables comment not found")
    v1 = json.load(open(SONDE_V1))
    old = v1["name"]
    obj["name"] = old.replace(".hndarray", "_v2.hndarray")
    if not any(c["value_type"]["oterm_ref"] == T["ENIGMA campaign"] for c in obj["array_context"]):
        obj["array_context"].append(ctx("ENIGMA campaign", oterm_value("Subsurface Observatory")))
    obj["array_context"].append(comment(f"Version 2 of {old}: {SONDE_NOTE}"))
    def interleave(a, b):
        key = next(k for k in a if k.endswith("_values"))
        return [x for pair in zip(a[key], b[key]) for x in pair]
    v_old = [interleave(v1["typed_values"][k]["values"], v1["typed_values"][k + 1]["values"]) for k in range(0, len(v1["typed_values"]), 2)]
    v_new = [tv["values"][next(k for k in tv["values"] if k.endswith("_values"))] for tv in obj["typed_values"]]
    if v_old != v_new or [tv["values"] for tv in v1["dim_context"][0]["typed_values"]] != [tv["values"] for tv in obj["dim_context"][0]["typed_values"]]:
        raise ValueError("sonde v2 values differ from v1")
    obj["array_context"].append(comment("Depth to water is the field sheet's DTW_TOC column (feet below the top of casing, measured with a water-level tape from the top of casing, converted to meters); the casing stick-ups above ground are 2.0 to 3.1 ft per port (SSO Cheat Sheet). The port depth is the midpoint of the screened interval below ground surface: VSZ 10-13 ft, SZ1 15-19 ft, SZ2 21-25 ft, SZ3 27-35 ft (SSO Cheat Sheet and SSO Well Install Diagram)"))
    return old, obj


BRICK_CSV = REPO / "sync-coral-to-berdl/exports/sync-20261019-161321/coral_export/brick_csv"
FIELD_V2_NOTE = ("each variable now names its molecule (dioxygen with physiochemical state = dissolved; nitrate) and the source-column comments that added nothing are gone; "
                 "the two pH variables carry their instrument; values unchanged")


def read_brick_csv(brick_id: str):
    """Name, sample names and {variable index: {sample index: value}} of a one-dimensional CORAL brick export."""
    lines = (BRICK_CSV / f"{brick_id}.csv").read_text().split("\n")
    name = lines[0].split(",", 1)[1]
    i = lines.index("data")
    d2 = next(k for k, l in enumerate(lines) if l.startswith("dmeta,2,"))
    samples = [re.match(r"\d+,(\S+) <", l).group(1) for l in lines[d2 + 1:i] if re.match(r"\d+,", l)]
    nvar = sum(1 for l in lines[next(k for k, l in enumerate(lines) if l.startswith("dmeta,1,")) + 1:d2] if re.match(r"\d+,", l))
    vals = defaultdict(dict)
    for l in lines[i + 1:]:
        if l:
            v, smp, x = l.split(",", 2)
            vals[int(v) - 1][int(smp) - 1] = float(x)
    return name, samples, [[vals[v].get(k) for k in range(len(samples))] for v in range(nvar)]


def build_sso_field_v2():
    """2025 pump test (Brick0001603) and one-off (Brick0001605) field readings with molecule contexts."""
    out = []
    dissolved_o2 = [ctx("molecule from list", oterm_value("dioxygen")), ctx("physiochemical state", sval("dissolved"))]
    no3 = [ctx("molecule from list", oterm_value("nitrate"))]
    # Brick0001603: H = pH (w/ meter); I-N under the merged header "AquaTROLL Measurements at End".
    old, samples, v = read_brick_csv("Brick0001603")
    if old != "pumptest_2025_field_measurements.hndarray" or len(v) != 8:
        raise ValueError(f"unexpected Brick0001603 {old} {len(v)}")
    variables = [
        float_var("volume", "milliliter", [], v[0]),
        float_var("pH", "pH unit", [ctx("instrument", sval("pH meter"))], v[1]),
        float_var("pH", "pH unit", [ctx("instrument", sval("Aqua TROLL"))], v[2]),
        float_var("conductivity", "uS/cm", [], v[3]),
        float_var("temperature", "degree Celsius", [], v[4]),
        float_var("concentration", "mg/L", dissolved_o2, v[5]),
        float_var("redox potential", "millivolt", [], v[6]),
        float_var("concentration", "mg/L", no3, v[7]),
    ]
    array_context = [
        ctx("ENIGMA campaign", oterm_value("Subsurface Observatory")),
        comment("Source file: 2024_2025_sso_folders/2025_SSO_PumpTest2/2025_PumpTest_Metadata.xlsx; tab: Sample Metadata"),
        comment("pH with instrument pH meter is the 'pH (w/ meter)' column; the other pH, conductivity, temperature, dissolved oxygen (RDO), ORP and nitrate are the Aqua TROLL readings at the end of pumping (merged header 'AquaTROLL Measurements at End'), copied onto every bottle of the pump event. "
                "Nitrate is the Aqua TROLL reading as recorded (mg/L of nitrate ion). The Aqua TROLL in M5-SZ3 had no pH or RDO probe (sheet note by Kathleen Walker); ORP recorded as TBD is null"),
        comment(f"Version 2 of {old}: {FIELD_V2_NOTE}"),
    ]
    obj = brick(old.replace(".hndarray", "_v2"), "2025 SSO PumpTest2 sample environmental and geochemical measurements from the metadata workbook",
                "environmental measurement", array_context, [sample_dim(samples)], variables)
    out.append((old, obj, samples))
    # Brick0001605: one-off sheet columns volume, pH, Cond, Temp, DO, ORP, Nitrate.
    old, samples, v = read_brick_csv("Brick0001605")
    if old != "oneoff_260609_sample_metadata.hndarray" or len(v) != 7:
        raise ValueError(f"unexpected Brick0001605 {old} {len(v)}")
    variables = [
        float_var("volume", "milliliter", [], v[0]),
        float_var("pH", "pH unit", [], v[1]),
        float_var("conductivity", "uS/cm", [], v[2]),
        float_var("temperature", "degree Celsius", [], v[3]),
        float_var("concentration", "mg/L", dissolved_o2, v[4]),
        float_var("redox potential", "millivolt", [], v[5]),
        float_var("concentration", "mg/L", no3, v[6]),
    ]
    array_context = [
        ctx("ENIGMA campaign", oterm_value("Subsurface Observatory")),
        comment("Source file: 2024_2025_sso_folders/SSO_Metadata_One Off Sampling.xlsx - Sheet1.tsv"),
        comment("pH, conductivity, temperature, dissolved oxygen, ORP and nitrate are the field readings of the sampling event (columns pH, Cond, Temp, DO, ORP, Nitrate), copied onto every bottle of the event"),
        comment(f"Version 2 of {old}: {FIELD_V2_NOTE.replace('; the two pH variables carry their instrument', '')}"),
    ]
    obj = brick(old.replace(".hndarray", "_v2"), "SSO one-off sample environmental and geochemical measurements from the one-off sampling spreadsheet",
                "environmental measurement", array_context, [sample_dim(samples)], variables)
    out.append((old, obj, samples))
    for old, obj, samples in out:
        _, s0, v0 = read_brick_csv({"pumptest_2025_field_measurements.hndarray": "Brick0001603", "oneoff_260609_sample_metadata.hndarray": "Brick0001605"}[old])
        if s0 != samples or v0 != [tv["values"]["float_values"] for tv in obj["typed_values"]]:
            raise ValueError(f"{obj['name']}: values differ from {old}")
    return out


def bottles_any(live: dict[str, dict], well: str, date: dt.date) -> str:
    name = f"{well}-{date.isoformat()}-UF-R1"
    if name not in live:
        raise KeyError(f"no R1 bottle for {well} {date}")
    return name


# ----------------------------------------------------------------------------

def main() -> None:
    stage_ontology()
    ab.load_ontology_names()
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    ab.OUT = OUT
    ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT = (OUT / d for d in ("json", "static", "process", "check", "reports"))
    for d in (ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT):
        d.mkdir(parents=True)
    live = {}
    with (EXPORT / "Sample.tsv").open() as h:
        for r in csv.DictReader(h, delimiter="\t"):
            live[r["name"]] = r
    bottles = Bottles(live)
    summary = {"release": RELEASE, "source_export": str(EXPORT.relative_to(REPO)), "bricks": [], "new_samples": []}

    # Pre-campaign 2019-03-11 bottles (Fields Lab R1 and R8 for GW821E and GW822E).
    new_rows, sampling_rows = [], []
    desc = {"R1": "Fields; 1 L sterile glass, unfiltered (assay 1): biomass production (3H-leucine) and lab-fixed cell count",
            "R8": "Fields; amber glass, 0.2 um filtered (assay 8): water delta 18O and delta 2H"}
    for well in ("GW821E", "GW822E"):
        names = []
        for rc in ("R1", "R8"):
            tmpl = live[f"{well}-2019-03-18-UF-{rc}"]
            name = f"{well}-{PRECAMPAIGN.isoformat()}-UF-{rc}"
            if name in live:
                raise ValueError(f"{name} already in CORAL")
            bottles.extra[(well, PRECAMPAIGN, rc)] = name
            new_rows.append([name, tmpl["location_id"], tmpl["depth"], "null", PRECAMPAIGN.isoformat(), "null", "null", tmpl["material"], tmpl["env_package"],
                             desc[rc] + ". Pre-campaign sampling of 2019-03-11, not in the 2019 Spring Master Spreadsheet; the Fields Lab reports results for it" + ("; activity started 48 h after collection" if rc == "R1" else "")])
            names.append(name)
        sampling_rows.append({"process": "Sampling <PROCESS:0000002>", "person": "Hazen Lab <ENIGMA:0000066>", "campaign": CAMPAIGN, "protocol": "null",
                              "date_start": PRECAMPAIGN.isoformat(), "date_end": PRECAMPAIGN.isoformat(), "input_objects": f"Location: {tmpl['location_id']}",
                              "output_objects": ", ".join(f"Sample: {n}" for n in names)})
    sample_path = ab.STATIC_OUT / f"Sample_additions_{RELEASE}.tsv"
    with sample_path.open("w", newline="") as h:
        w = csv.writer(h, delimiter="\t", lineterminator="\n")
        w.writerow(["name", "location", "depth", "elevation", "date", "time", "timezone", "material", "env_package", "description"])
        w.writerows(new_rows)
    summary["new_samples"] = [r[0] for r in new_rows]
    sampling_path = ab.PROCESS_OUT / f"process_sampling_spring2019_{RELEASE}.tsv"
    write_process(sampling_path, sampling_rows)
    staged = set(live) | set(summary["new_samples"])

    processes = defaultdict(list)
    def record(obj, samples, process, person, d0, d1, inputs=None):
        missing = [s for s in samples if s not in staged]
        if missing:
            raise ValueError(f"{obj['name']}: samples not staged: {missing[:5]}")
        path = ab.write_brick(obj)
        summary["bricks"].append({"name": obj["name"], "json": path.name, "shape": [d["size"] for d in obj["dim_context"]], "variables": len(obj["typed_values"]), "samples": len(samples)})
        if process:
            processes[process].append({"process": process, "person": person, "campaign": CAMPAIGN, "protocol": "null", "date_start": d0, "date_end": d1,
                                   "input_objects": inputs or ", ".join(f"Sample: {s}" for s in samples), "output_objects": f"Generic: {obj['name']}"})

    GEO, CELLS, ACT, ENV = ("Assay Geochemistry <PROCESS:0000005>", "Assay Cell Counts <PROCESS:0000008>",
                            "Assay Microbial Activity <PROCESS:0000048>", "Assay Environment <PROCESS:0000004>")
    fe, fe_samples = build_ferrozine(bottles)
    record(fe, fe_samples, GEO, f"Caitlin Gionfriddo <{T['Caitlin Gionfriddo']}>", "2019-05-21", "2019-05-21")
    cc, cc_samples, cc_recs = build_counts(bottles)
    record(cc, cc_samples, CELLS, f"Katie Davis <{T['Katie Davis']}>", min(r["counted"] for r in cc_recs.values()).isoformat(), max(r["counted"] for r in cc_recs.values()).isoformat())
    act, act_samples = build_activity(bottles)
    record(act, act_samples, ACT, f"Katie Davis <{T['Katie Davis']}>", "2019-03-13", "2019-05-17")
    wi, wi_samples = build_water_isotopes(bottles)
    record(wi, wi_samples, GEO, f"Katie Davis <{T['Katie Davis']}>", "2019-03-21", "2019-06-03")
    st, st_samples = build_stahl(bottles)
    record(st, st_samples, GEO, f"Kristopher Hunt <{T['Kristopher Hunt']}>", "2019-04-02", "2019-06-18")
    fr, fr_locations, fr_recs = build_field(live)
    record(fr, [], ENV, "Hazen Lab <ENIGMA:0000066>", "2019-03-18", "2019-05-01", inputs=", ".join(f"Location: {l}" for l in fr_locations))
    old, sonde = build_sonde_v2()
    record(sonde, [], None, None, None, None)
    today = f"{RELEASE[:4]}-{RELEASE[4:6]}-{RELEASE[6:]}"
    processes["Update Data <PROCESS:0000053>"].append({"process": "Update Data <PROCESS:0000053>", "person": "John-Marc Chandonia <ENIGMA:0000057>",
        "campaign": "Subsurface Observatory <ENIGMA:0000166>", "protocol": "null", "date_start": today, "date_end": today,
        "input_objects": f"Generic: {old}", "output_objects": f"Generic: {sonde['name']}"})
    summary["superseded"] = [{"old": old, "new": sonde["name"], "change": SONDE_NOTE}]
    for old, obj, smp in build_sso_field_v2():
        staged_missing = [x for x in smp if x not in staged]
        if staged_missing:
            raise ValueError(f"{obj['name']}: samples not in CORAL {staged_missing[:3]}")
        record(obj, [], None, None, None, None)
        processes["Update Data <PROCESS:0000053>"].append({"process": "Update Data <PROCESS:0000053>", "person": "John-Marc Chandonia <ENIGMA:0000057>",
            "campaign": "Subsurface Observatory <ENIGMA:0000166>", "protocol": "null", "date_start": today, "date_end": today,
            "input_objects": f"Generic: {old}", "output_objects": f"Generic: {obj['name']}"})
        summary["superseded"].append({"old": old, "new": obj["name"], "change": FIELD_V2_NOTE})

    process_files = []
    for process, rows in processes.items():
        slug = process.split(" <")[0].lower().replace(" ", "_")
        path = ab.PROCESS_OUT / f"process_{slug}_spring2019_{RELEASE}.tsv"
        write_process(path, rows)
        process_files.append((process.split(" <")[0], path.name))
    files = [f"static/{sample_path.name}", f"process/{sampling_path.name}"] + [f"json/{b['json']}" for b in summary["bricks"]] + [f"process/{n}" for _, n in process_files]
    (OUT / "files_to_import.txt").write_text("\n".join(files) + "\n")
    script = ["# Before this notebook: run coral_import/ontology_update_20261019/install_me0000513_0000515.sh (ME:0000513-ME:0000515).",
              "# Paste into the CORAL import notebook after uploading every file in files_to_import.txt", "",
              "# Cell 1: the four 2019-03-11 Fields bottles and their Sampling processes.",
              f"toolx.update_core('{sample_path.name}', 'Sample')", f"toolx.upload_process('Sampling', '{sampling_path.name}')", "",
              "# Cell 2: the bricks."] + [f"toolx.upload_brick('{b['json']}')" for b in summary["bricks"]] + ["", "# Cell 3: the assay processes."] + \
             [f"toolx.upload_process('{p}', '{n}')" for p, n in process_files] + [""]
    (OUT / "import_to_coral.py").write_text("\n".join(script))
    (ab.REPORT_OUT / "build_summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    readme = [f"# Spring 2019 batch C2 CORAL import ({RELEASE})", "",
              "Elias ferrozine iron, Fields cell counts, biomass production and water isotopes, Stahl ammonia oxidation and nitrogen isotopes, and Hazen field readings for the Spring 2019 Integrated Sampling, built by `tools/build_spring2019_batch_c2_coral_import.py`.", "",
              "| Brick | Shape | Variables | Samples |", "| --- | --- | --- | --- |"] + \
             [f"| `{b['name']}` | {b['shape']} | {b['variables']} | {b['samples']} |" for b in summary["bricks"]] + ["",
              "* Bottles: Elias R5; Fields R7 (field-fixed counts), R1 (biomass production and lab-fixed counts), R8 (water isotopes); Stahl R21-R24 and R151-R153. Field readings are keyed by well Location.",
              "* Requires `coral_import/ontology_update_20261019` (ME:0000513 nanogram per milliliter per day, ME:0000514 biomass production rate, ME:0000515 time since sample collection) before the bricks are loaded.",
              f"* Superseding `_v2` of the 2023 SSO sonde brick (one Update Data process): {SONDE_NOTE}.",
              f"* Superseding `_v2` of the 2025 pump-test and one-off SSO field-measurement bricks (Brick0001603, Brick0001605; one Update Data process each): {FIELD_V2_NOTE}.",
              f"* Static additions: {', '.join(summary['new_samples'])} (pre-campaign 2019-03-11 Fields bottles, with one Sampling process per well).",
              "", "Import order: the samples and their Sampling processes, then the bricks, then the assay processes (`import_to_coral.py`). All JSON files pass CheckGeneric (`check/`).", ""]
    (OUT / "README.md").write_text("\n".join(readme))
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
