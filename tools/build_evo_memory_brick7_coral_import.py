#!/usr/bin/env python3
"""Build the CORAL import package for the 2017 EVO injection (Memory campaign) and the
corrected replacement of Brick0000007 (hazen_field_post100ws).

Decisions and evidence: coral_import/EVO_MEMORY_PLAN_20261111.md.

Part 1 (this file, so far): hazen_field_post100ws_v2, rebuilt from the ORNL FRC sample
collection log (sample_spreadsheet_tab3.tsv, updated 2019-02-08) with:
  * correct ChEBI terms (K, U, Ga, As, Ag, Cl, Pb),
  * values in scientific notation parsed correctly (the old brick stored 57 of them 1e5-1e6 too large),
  * metals dropped where they are attached to the wrong wells (January 2015 time series),
    copied from another row, or are constant floor values,
  * measurements that belong to the EVO geochemistry brick removed,
  * samples without any value left out.
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import build_sso_batch_ab_coral_import as ab  # noqa: E402
import build_sso_oneoff_16s_coral_import as oo  # noqa: E402
from build_sso_batch_ab_coral_import import T, comment, ctx, oterm_value, sval, write_process  # noqa: E402

OUT = REPO / "coral_import" / "evo_memory_brick7_20261111"
LOG = Path("/h/jmc/data/enigma/clearinghouse/sample_data/input_data/sample_spreadsheet_tab3.tsv")
OLD_BRICK_CSV = REPO / "sync-coral-to-berdl/exports/sync-20261110-162303/coral_export/brick_csv/Brick0000007.csv"
EXPORT_SAMPLES = REPO / "sync-coral-to-berdl/exports/sync-20261110-162303/berdl_upload/data/sdt_sample.tsv"
TODAY = "2026-11-11"
DRIVE_META = Path("/mnt/net/dipa.jmcnet/data/backup/google-drive/enigma_team_drive_data_enigma_backup/2017 EVO Injection/Zhou - 16S sequencing/20230222.metadata.csv")
INJECTION = dt.date(2017, 12, 13)
EVO_SAMPLE_PREFIX = {"FW212": "FW212", "FW213": "FW213", "FW214": "FW214", "FW215": "FW215", "FW216": "FW216-19", "MLSB3": "MLSB3", "GP01": "GP01-18", "GP03": "GP03-19"}
SEDIMENT_XLSX = REPO / "coral_import/evo_memory_2017_source/FW306_Sediment_chemical_analysis.xlsx"  # soffice conversion of the Drive .xls
COMO_PATCHED = REPO / "coral_import/ontology_update_20261111_sediment/production/context_measurement_ontology.obo"

T.update({
    "specific conductivity": "ME:0000301", "redox potential": "ME:0000125", "organic": "ME:0000346",
    "ppm": "UO:0000169", "millivolt": "UO:0000247",
    "John-Marc Chandonia": "ENIGMA:0000057", "Field Sampling": "ENIGMA:0000095",
    "oxygen atom": "CHEBI:25805", "sulfide(2-)": "CHEBI:15138", "iron(2+)": "CHEBI:29033",
    "carbon dioxide": "CHEBI:16526", "methane": "CHEBI:16183", "carbon monoxide": "CHEBI:17245",
    "elemental carbon": "CHEBI:33415", "chloride": "CHEBI:17996", "phosphate ion": "CHEBI:35780", "sulfate": "CHEBI:16189",
    "lime buffer capacity": "ME:0000524", "cation exchange capacity": "ME:0000525",
    "meq/100 g": "ME:0000526", "ppm CaCO3/pH": "ME:0000527", "mmhos/cm": "ME:0000347",
    "Natural Organic Matter": "ENIGMA:0000027", "water": "CHEBI:15377", "nitrogen atom": "CHEBI:25555",
    "fluoride": "CHEBI:17051", "phosphorus atom": "CHEBI:28659", "element Mo": "CHEBI:28685",
    "elevation": "ME:0000220", "time elapsed": "ME:0000122", "day": "UO:0000033", "Memory": "ENIGMA:0000008",
    "acetate": "CHEBI:30089",
    "element Ag": "CHEBI:30512", "element Bi": "CHEBI:33301", "element Li": "CHEBI:30145",
})

# sample renames decided 2026-11-11 (ports per the Adams thesis screened intervals)
RENAME_PREFIX = {"GP01-30-": "GP01-18-", "GP03-29-": "GP03-19-"}


def mol(key, *extra):
    return [ctx("molecule from list", oterm_value(key))] + list(extra)


DISSOLVED = None


def organic(flag):
    return ctx("organic", {"scalar_type": "boolean", "boolean_value": flag})


VARS = collections.OrderedDict()


def make_vars():
    """Fill VARS (needs the ontology names loaded)."""
    global DISSOLVED
    DISSOLVED = ctx("physiochemical state", sval("dissolved"))


    # log column -> (variable term key, unit key, context)
    VARS.update(collections.OrderedDict([
        (10, ("pH", "pH unit", [])),
        (11, ("specific conductivity", "uS/cm", [dict(ctx("temperature", {"scalar_type": "float", "float_value": 20.0}), value_units=ab.term("degree Celsius"))])),
        (12, ("temperature", "degree Celsius", [])),
        (13, ("concentration", "mg/L", mol("oxygen atom", DISSOLVED))),
        (14, ("redox potential", "millivolt", [])),
        (15, ("count", "cells per milliliter", [ctx("category", oterm_value("cell")), ctx("method", sval("AODC"))])),
        (17, ("concentration", "ppm", mol("sulfide(2-)"))),
        (18, ("concentration", "mg/L", mol("iron(2+)"))),
        (19, ("concentration", "uM", mol("carbon dioxide"))),
        (20, ("concentration", "uM", mol("methane"))),
        (21, ("concentration", "uM", mol("carbon monoxide"))),
        (22, ("concentration", "mg/L", mol("elemental carbon", DISSOLVED, organic(0)))),
        (23, ("concentration", "mg/L", mol("elemental carbon", DISSOLVED, organic(1)))),
        (24, ("concentration", "mg/L", mol("chloride"))),
        (25, ("concentration", "mg/L", mol("nitrate"))),
        (26, ("concentration", "mg/L", mol("phosphate ion"))),
        (27, ("concentration", "mg/L", mol("sulfate"))),
    ]))
    for _c, _sym in enumerate(["Ag", "Al", "As", "Ba", "Be", "Bi", "Ca", "Cd", "Co", "Cr", "Cs", "Cu", "Fe", "Ga", "K", "Li", "Mg", "Mn", "Na",
                               "Ni", "Pb", "Se", "Sr", "U", "Zn"], start=28):
        VARS[_c] = ("concentration", "mg/L", mol(f"element {_sym}"))



EVO_DATES = {dt.date(2017, 12, 7): -6, dt.date(2017, 12, 14): 1, dt.date(2017, 12, 21): 8, dt.date(2017, 12, 28): 15,
             dt.date(2018, 1, 4): 22, dt.date(2018, 2, 1): 50}
EVO_BRICK_WELLS = {"FW215", "FW216", "MLSB3", "GP01", "GP03"}
EVO_NO_DRIVE = {("GP01", 1)}  # the Drive table has no GP01 row for day 1


# ----------------------------------------------------------------------------
# source log
# ----------------------------------------------------------------------------

def parse_cell(text):
    """Return (value, note). value is None when the cell is not a usable number."""
    t = text.strip().replace(",", "")
    if not t:
        return None, None
    try:
        return float(t), None
    except ValueError:
        pass
    m = re.fullmatch(r"\(-\)(\d+(?:\.\d+)?)", t)
    if m:
        return -float(m.group(1)), f"'{t}' read as {-float(m.group(1)):g}"
    if re.fullmatch(r"\d+\.\.\d+", t):
        return float(t.replace("..", ".")), f"'{t}' read as {t.replace('..', '.')}"
    if re.fullmatch(r"\d+\.\d\d\.\d\d", t):  # 38.32.41: the block's other DIC cells are NN.NNNN
        v = float(t[:t.rfind(".")] + t[t.rfind(".") + 1:])
        return v, f"'{t}' read as {v:g}"
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\^(\d+)", t)
    if m:
        v = float(m.group(1)) * 10 ** int(m.group(2))
        return v, f"'{t}' read as {v:g}"
    m = re.fullmatch(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)", t)
    if m:
        v = (float(m.group(1)) + float(m.group(2))) / 2
        return v, f"range '{t}' stored as its midpoint {v:g}"
    return None, f"'{t}' not a number, left blank"


def read_log():
    rows = list(csv.reader(LOG.open(errors="replace"), delimiter="\t"))
    header = [c.strip() for c in rows[1]]
    out = []
    for i, r in enumerate(rows[2:], start=3):
        if len(r) <= 8:
            continue
        try:
            m, d, y = r[2].strip().split("/")
            date = dt.date(int(y) if int(y) > 100 else 2000 + int(y), int(m), int(d))
        except ValueError:
            continue
        out.append({"line": i, "date": date, "campaign": r[3].strip(), "well": r[5].strip(), "sid": r[8].strip(),
                    "cells": {c: r[c] for c in range(10, 80) if c < len(r) and r[c].strip()}})
    return header, out


LOG_XLSX = REPO / "coral_import/evo_memory_2017_source/ORNL_Field_Sampling_Requirements_Responses.xlsx"  # Drive workbook (edited after the export)
_LOG_CACHE = {}


def _rounds_to(full, text):
    """True if the full-precision number, rounded as the export rounded it, gives the export's text."""
    t = text.strip().replace(",", "")
    try:
        shown = float(t)
    except ValueError:
        return False
    m = re.fullmatch(r"-?(\d*)\.?(\d*)(?:[eE]([-+]?\d+))?", t)
    if not m:
        return False
    whole, frac, exp = m.group(1), m.group(2), int(m.group(3) or 0)
    if frac:
        unit = 10.0 ** (exp - len(frac))
    else:
        unit = 10.0 ** (exp + len(whole) - len(whole.rstrip("0"))) if whole.strip("0") else 1.0
    return abs(full - shown) <= 0.5 * unit * 1.0001 + 1e-12 * abs(shown)


def log_rows():
    """The export's rows, each with x['num'][column] = the workbook's full-precision value where a workbook row with the same
    date, well, campaign and sample ID has a value that rounds to the export's."""
    if "rows" in _LOG_CACHE:
        return _LOG_CACHE["header"], _LOG_CACHE["rows"], _LOG_CACHE["stats"]
    import openpyxl
    import warnings
    header, rows = read_log()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ws = openpyxl.load_workbook(LOG_XLSX, read_only=True, data_only=True)["Collected Samples"]
        xl = [list(r) for r in ws.iter_rows(values_only=True)]
    raw = list(csv.reader(LOG.open(errors="replace"), delimiter="\t"))
    pool = collections.defaultdict(list)
    for r in xl[2:]:
        if len(r) > 8 and isinstance(r[2], dt.datetime):
            pool[(r[2].date(), str(r[5] or "").strip(), str(r[8] or "").strip())].append(r)
    stats = collections.Counter()
    for x in rows:
        x["num"] = {}
        cands = pool.get((x["date"], x["well"], x["sid"]), [])
        if not cands and x["cells"]:  # the workbook later relabelled some wells and sample IDs: fall back to the date and the well's letters and digits
            wkey = re.sub(r"[^A-Za-z0-9]", "", x["well"])
            cands = [r for k, v in pool.items() if k[0] == x["date"] and re.sub(r"[^A-Za-z0-9]", "", k[1]) == wkey for r in v]
        best = None
        for r in list(cands):
            ok = all((c >= len(r) or r[c] is None or not isinstance(r[c], (int, float)) or _rounds_to(float(r[c]), t)) for c, t in x["cells"].items()
                     if re.fullmatch(r"-?[\d.,]+(?:[eE][-+]?\d+)?", t.strip()))
            same_filled = sum(1 for c in x["cells"] if c < len(r) and r[c] is not None)
            if ok and (same_filled or not x["cells"]):
                best = r
                break
        if best is None:
            stats["rows without a matching workbook row" if x["cells"] else "rows without values"] += 1
            continue
        for v in pool.values():
            if any(r is best for r in v):
                v[:] = [r for r in v if r is not best]
        stats["rows matched"] += 1
        for c, t in x["cells"].items():
            if c < len(best) and isinstance(best[c], (int, float)) and _rounds_to(float(best[c]), t):
                x["num"][c] = float(f"{float(best[c]):.12g}")  # drop binary floating-point noise (81.50909999999999 -> 81.5091)
                stats["cells at full precision"] += 1
            else:
                stats["cells kept as exported"] += 1
    _LOG_CACHE.update(header=header, rows=rows, stats=stats)
    return header, rows, stats


def log_value(x, c):
    """(value, note) for a log cell: the workbook's full-precision number if matched, else the parsed export text."""
    if c in x.get("num", {}):
        return x["num"][c], None
    return parse_cell(x["cells"][c])


def old_brick():
    lines = OLD_BRICK_CSV.read_text().split("\n")
    i2 = next(i for i, l in enumerate(lines) if l.startswith("dmeta,2,"))
    idata = lines.index("data")
    names = {int(l.split(",", 1)[0]): l.split(",", 1)[1].split(" <")[0] for l in lines[i2 + 1:idata]}
    vals = collections.defaultdict(dict)
    for l in lines[idata + 1:]:
        if l.strip():
            v, s, x = l.split(",", 2)
            vals[int(s)][int(v)] = float(x)
    return names, vals


def align(names, vals, rows):
    """Map each old-brick sample to its log row (old brick variable n = log column 9 + n)."""
    def rowvals(x):
        out = {}
        for c, t in x["cells"].items():
            try:
                out[c - 9] = float(t.replace(",", ""))
            except ValueError:
                pass
        return out
    amap, j = {}, 0
    for s in sorted(names):
        bv = vals[s]
        for k in range(j, min(j + 60, len(rows))):
            rv = rowvals(rows[k])
            common = set(bv) & set(rv)
            agree = sum(1 for n in common if abs(bv[n] - rv[n]) <= 1e-6 * max(1, abs(rv[n])))
            if (common and agree >= 0.8 * len(common) and len(common) >= 0.8 * len(bv)) or \
                    (not bv and not rv and (not rows[k]["sid"] or names[s].startswith(rows[k]["sid"]))):
                amap[s] = k
                j = k + 1
                break
    used = set(amap.values())
    for s in sorted(names):
        if s not in amap:
            base = re.sub(r"-\d$", "", names[s]) if re.search(r"-\d\d-\d$", names[s]) else names[s]
            cand = [k for k, x in enumerate(rows) if k not in used and
                    (x["sid"] == base or (not x["sid"] and base == x["well"].replace("-", "") + "-" + x["date"].strftime("%m-%d-%y")))]
            if not cand:
                raise ValueError(f"old brick sample {names[s]} not found in the log")
            amap[s] = cand[0]
            used.add(cand[0])
    return amap


# ----------------------------------------------------------------------------
# Brick0000007 replacement
# ----------------------------------------------------------------------------

def build_brick7(report):
    make_vars()
    header, rows, upgrade = log_rows()
    names, old_vals = old_brick()
    amap = align(names, old_vals, rows)
    counts = collections.Counter()
    notes = []
    data = collections.OrderedDict()
    nitrate_below = set()
    for s in sorted(names):
        x = rows[amap[s]]
        if "evo" in x["campaign"].lower():
            counts["EVO injection samples (all their measurements are in the EVO geochemistry brick)"] += 1
            continue
        name = names[s]
        for old, new in RENAME_PREFIX.items():
            if name.startswith(old):
                name = new + name[len(old):]
        v = {}
        for c, text in x["cells"].items():
            if c > 52:
                continue
            val, note = log_value(x, c)
            if note:
                notes.append(f"{name}, {header[c]}: {note}")
            if val is not None:
                v[c] = val

        def drop(cols, why):
            for c in cols:
                if v.pop(c, None) is not None:
                    counts[why] += 1
        ts = x["campaign"] == "Time Series"
        if ts and 135 <= x["line"] <= 152:
            drop(range(28, 53), "January 2015 time-series metals attached to the wrong wells")
        if x["line"] in (82, 108):
            drop(range(28, 53), "metals copied from another row (log lines 82, 108)")
        if x["line"] == 139:
            drop([23], "DOC equal to DIC (log line 139)")
        if ts and x["date"].year in (2014, 2015):
            drop([33, 38, 51], "Bi, Cs, U floor values, 2014-2015 time series")
        if x["campaign"] == "Memory Response":
            drop([32, 50, 51, 52], "Be, Sr, U, Zn floor values, 2015-03-31 samples")
        if name == "GW456-12-15-14":  # 1.217 uS/cm where the well reads 220 to 370 on every other date
            if not 1.2 < v.get(11, 0) < 1.23:
                raise ValueError("GW456-12-15-14 conductivity is not the expected 1.217")
            drop([11], "implausible specific conductivity (GW456-12-15-14, 1.217 uS/cm)")
        if v.get(25) == 0:  # nitrate reported as 0 is below the reporting limit (0.29 mg/L in the November 2013 study)
            del v[25]
            nitrate_below.add(name)
            counts["nitrate zeros stored as below detection"] += 1
        if 16 in v:  # 'total uranium via ICPMS mg/L' holds one non-EVO value; same analyte and unit as the U column
            if 51 in v:
                raise ValueError(f"{name}: both uranium columns filled")
            v[51] = v.pop(16)
        if v:
            data[name] = v
        else:
            counts["samples without values left out"] += 1
    used_cols = [c for c in VARS if any(c in v for v in data.values())]
    extra = sorted({c for v in data.values() for c in v} - set(VARS))
    if extra:
        raise ValueError(f"unmapped log columns {[header[c] for c in extra]}")

    live = {r["sdt_sample_name"] for r in csv.DictReader(EXPORT_SAMPLES.open(), delimiter="\t")}
    renamed = [n for n in data if n not in live]
    if renamed:
        raise ValueError(f"samples not in CORAL: {renamed}")

    sample_names = list(data)
    variables = []
    for c in used_cols:
        key, unit, context = VARS[c]
        variables.append(ab.float_var(key, unit, context, [data[n].get(c) for n in sample_names]))
        if c == 25:
            variables.append(ab.bool_var("below", ab.below_ctx(mol("nitrate")),
                                         [True if n in nitrate_below else (False if 25 in data[n] else None) for n in sample_names]))
    array_context = [
        comment("Replaces hazen_field_post100ws (Brick0000007). Rebuilt from the ORNL FRC sample collection log (Collected Samples sheet, updated 2019-02-08)"),
        comment("Corrected molecule terms for K, U, Ga, As, Ag, Cl and Pb; values written in scientific notation, which the earlier brick stored 1e5 to 1e6 too large, are now correct"),
        comment("Left out: metals of the 18 time-series samples of 2015-01-05 to 2015-01-12 (attached to the wrong wells in the log); metals of GW458-12-1-14 and FW303-12-9-14 "
                "(copies of other rows); DOC of FW301-1-5-15 (copy of DIC); Bi, Cs and U of the 2014-2015 time series and Be, Sr, U and Zn of the 2015-03-31 samples "
                "(the same floor value in every well)"),
        comment("The 2017-2018 EVO injection samples of this log are not here: all their measurements are in hazen_geochemistry_evo_injection_2017"),
        comment("Values are at the precision of the log workbook on the ENIGMA Google Drive where a workbook row matches (the 2019 tab-separated export rounds to about five digits). "
                "Nitrate reported as 0 is stored as below detection. The specific conductivity of GW456-12-15-14 (1.217 uS/cm; 220 to 370 on the well's other dates) is left out"),
        comment("Dissolved organic carbon of November 2013 (15 to 20 mg/L) is as reported; it tracks dissolved inorganic carbon and is about 100 times the 2014-2015 values at the same wells"),
        comment("FW106-061015 was logged as ranges; midpoints are stored"),
        comment("CO2, CH4 and CO are in micromolar: the log heads the columns 'CO2', 'CH4 umol' and 'CO umol', and umol is read as micromolar"),
    ]
    obj = ab.brick("hazen_field_post100ws_v2", "Hazen Lab field sample measurements after the 100 Well Survey (corrected 2026-11-11)",
                   "chemical measurement", array_context, [ab.sample_dim(sample_names)], variables)
    ab.write_brick(obj)
    write_process(ab.PROCESS_OUT / "process_update_data_hazen_field_post100ws_v2_20261111.tsv", [{
        "process": "Update Data <PROCESS:0000053>", "person": "John-Marc Chandonia <ENIGMA:0000057>", "campaign": "Field Sampling <ENIGMA:0000095>",
        "protocol": "null", "date_start": TODAY, "date_end": TODAY,
        "input_objects": "Generic: hazen_field_post100ws.hndarray", "output_objects": "Generic: hazen_field_post100ws_v2.hndarray"}])

    n_old = sum(len(v) for v in old_vals.values())
    n_new = sum(len(v) for v in data.values())
    report += ["## hazen_field_post100ws_v2 (replaces Brick0000007)", "",
               f"- samples: {len(sample_names)} (old brick {len(names)}); variables: {len(used_cols)} (old 70); values: {n_new} (old {n_old})",
               "", "### Cells and rows removed", ""]
    report += [f"- {n}: {k}" for k, n in counts.most_common()]
    report += ["", "### Precision", ""] + [f"- {n}: {k}" for k, n in upgrade.most_common()]
    report += ["", "### Outliers to review (pH below 4 or above 9; specific conductivity below 20 or above 3000 uS/cm)", ""]
    for n, v in data.items():
        if (10 in v and not 4 <= v[10] <= 9) or (11 in v and not 20 <= v[11] <= 3000):
            report.append(f"- {n}: pH {v.get(10)}, conductivity {v.get(11)}, temperature {v.get(12)}, DO {v.get(13)}, redox {v.get(14)}")
    blank = sum("not a number" in n for n in notes)
    report += ["", "### Cells repaired or interpreted", ""] + [f"- {n}" for n in notes if "not a number" not in n] + [f"- left blank: {blank} non-numeric cells (AODC pending, redox none)"]
    report += ["", "### Values per variable", ""]
    for c in used_cols:
        report.append(f"- {header[c]}: {sum(1 for v in data.values() if c in v)}")
    report.append("")
    return data, header


# ----------------------------------------------------------------------------
# FWB-306 sediment chemistry (UGA Soil, Plant and Water Laboratory report)
# ----------------------------------------------------------------------------

def build_sediment(report):
    import openpyxl
    rows = list(openpyxl.load_workbook(SEDIMENT_XLSX, data_only=True).worksheets[0].iter_rows(values_only=True))
    if rows[9][1] != "Samp" or rows[9][9:23] != ("Ca", "Cd", "Cr", "Cu", "Fe", "K", "Mg", "Mn", "Mo", "Na", "Ni", "P", "Pb", "Zn"):
        raise ValueError("sediment report: first table header")
    if tuple(rows[29][4:11]) != ("Cl", "F", "NO3-N", "PO4", "SO4", "U", "TOC") or rows[29][16:19] != ("C", "TOC", "N"):
        raise ValueError("sediment report: second table header")
    t1 = {(r[1], int(r[3])): r for r in rows[10:26]}
    t2 = {(r[1], int(r[3])): r for r in rows[30:46]}
    if len(t1) != 16 or set(t1) != set(t2):
        raise ValueError("sediment report: sample/replicate keys")
    for k in t1:
        if t1[k][0] != t2[k][0] or t1[k][2] != t2[k][2]:
            raise ValueError(f"sediment report: lab number or depth differs for {k}")
    labels = sorted({k[0] for k in t1})
    samples = [l.replace("FWB-306-", "FWB306-") for l in labels]
    live = {r["sdt_sample_name"] for r in csv.DictReader(EXPORT_SAMPLES.open(), delimiter="\t")}
    if [n for n in samples if n not in live]:
        raise ValueError("sediment samples not in CORAL")
    cells = [(l, rep) for l in labels for rep in (1, 2)]  # sample-major order, replicate 1 then 2

    def column(table, idx):
        vals, limits = [], []
        for k in cells:
            v = table[k][idx]
            if isinstance(v, str) and v.strip().startswith("<"):
                vals.append(None)
                limits.append(float(v.strip()[1:]))
            else:
                vals.append(float(v))
                limits.append(None)
        return vals, limits

    # ---- extractable analytes: sample x replicate x analyte
    analytes = [(sym, "phosphorus atom" if sym == "P" else f"element {sym}", "Mehlich 1", t1, i)
                for i, sym in enumerate(["Ca", "Cd", "Cr", "Cu", "Fe", "K", "Mg", "Mn", "Mo", "Na", "Ni", "P", "Pb", "Zn"], start=9)]
    analytes += [(lab, key, "water extract", t2, i) for i, (lab, key) in enumerate(
        [("chloride", "chloride"), ("fluoride", "fluoride"), ("nitrate", "nitrate"), ("phosphate", "phosphate ion"), ("sulfate", "sulfate"), ("U", "element U")], start=4)]
    kept, never, censored = [], [], []
    for lab, key, method, table, idx in analytes:
        vals, limits = column(table, idx)
        if all(v is None for v in vals):
            lo, hi = min(limits), max(limits)
            never.append(f"{lab} ({method}; limit {lo:g}" + (f" to {hi:g}" if hi != lo else "") + " mg/kg)")
        elif any(l is not None for l in limits):
            censored.append(f"{lab} {sum(l is not None for l in limits)} of 16")
        kept.append((key, method, vals, limits))
    if len(kept) != 20 or len(never) != 5:
        raise ValueError(f"expected 20 analytes, 5 of them never detected; got {len(kept)}, {len(never)}")
    n = len(kept)
    conc = [kept[j][2][c] for c in range(16) for j in range(n)]
    # one detection limit per analyte, on the molecule dimension: the smallest limit the report gives. The Mehlich 1 limits are reported per sample
    # on a dry-soil basis (0.04 becomes 0.05 or 0.06 for wetter samples), which is why the report's limits differ between samples
    base_limit = [min([l for l in k[3] if l is not None], default=None) for k in kept]
    spread = []
    for lab, _, _, table, idx in analytes:
        vals, lims = column(table, idx)
        distinct = sorted({x for x in lims if x is not None})
        if len(distinct) > 1:
            spread.append(f"{lab}: {', '.join(f'{x:g}' for x in distinct)}")
    report_ctx = comment("Soil test report of the University of Georgia Soil, Plant, and Water Laboratory (Athens, GA) for Sindhu Jagadamma, completed 2015-08-06; "
                         "eight depth intervals of the FWB-306 core collected 2015-06-10, each analysed in duplicate")
    source_ctx = comment("Source: ENIGMA Google Drive, FRC Well Metadata/Core samples/FW306_Sediment_chemical analysis.xls. "
                         "The ORNL FRC sample collection log carries a rounded copy of these values")
    extract = ab.brick(
        "hazen_sediment_extractable_fwb306_2015", "Hazen Lab extractable elements and anions of the FWB-306 sediment core (UGA soil test, 2015)", "chemical measurement",
        [report_ctx,
         comment("Method Mehlich 1: elements extracted from the soil by the Mehlich 1 dilute acid solution. Method water extract: 5 g soil shaken in 20 mL deionized water "
                 "for 15 minutes. All values are mg per kg of soil. Nitrate is reported as nitrate nitrogen"),
         comment("A blank concentration is a value the laboratory reported as below its detection limit; every sample was measured for every analyte. The detection "
                 "limit of each analyte is on the molecule dimension (blank for analytes that were always detected). For the Mehlich 1 elements it is the smallest "
                 "limit in the report: the laboratory states a limit for each sample, and it differs between samples (" + "; ".join(spread) + " mg/kg; for Cd, Cr and Mo "
                 "the limit rises with the sample's moisture, which suggests a dry-soil basis)"),
         comment("Below the detection limit in every sample (all concentrations blank): " + "; ".join(never)),
         source_ctx],
        [ab.sample_dim(samples), ab.replicate_dim(2),
         ab.molecule_dim([k for k, _, _, _ in kept], [ab.typed("method", "string", [m for _, m, _, _ in kept]), ab.float_var("detection limit", "mg/kg", [], base_limit)])],
        [ab.float_var("concentration", "mg/kg", [], conc)])
    extract["array_context"] = [c for c in extract["array_context"] if c["value_type"]["oterm_ref"] != T["data variables type"]]  # one measured variable
    extract["name"] = extract["name"].replace(".hndarray", ".ndarray")
    oo.write_brick(extract)

    # ---- soil properties: sample x replicate
    def one(table, idx):
        vals, limits = column(table, idx)
        if any(l is not None for l in limits):
            raise ValueError("unexpected below-limit soil property")
        return vals
    props = ab.brick(
        "hazen_sediment_soil_properties_fwb306_2015", "Hazen Lab soil properties of the FWB-306 sediment core (UGA soil test, 2015)", "chemical measurement",
        [report_ctx,
         comment("Lime buffer capacity and pH per the laboratory's methods (UGA CAES publications 7335 and 7336). Equivalent water pH is the laboratory's conversion of the "
                 "CaCl2 pH (CaCl2 pH + 0.6). Cation exchange capacity is the laboratory's calculated value. Base saturation (extractable bases as a share of cation "
                 "exchange capacity) is not stored"),
         comment("Water-extractable organic carbon: 5 g soil shaken in 20 mL deionized water for 15 minutes, mg per kg of soil. Total carbon, total organic carbon and total nitrogen are percent of the soil"),
         source_ctx],
        [ab.sample_dim(samples), ab.replicate_dim(2)],
        [ab.float_var("pH", "pH unit", [ctx("method", sval("in 0.01 M CaCl2"))], one(t1, 5)),
         ab.float_var("pH", "pH unit", [ctx("method", sval("equivalent water pH"))], one(t1, 6)),
         ab.float_var("lime buffer capacity", "ppm CaCO3/pH", [], one(t1, 4)),
         ab.float_var("cation exchange capacity", "meq/100 g", [], one(t1, 8)),
         ab.float_var("concentration", "percent", mol("water", ctx("physiochemical state", sval("in soil"))), one(t2, 12)),
         ab.float_var("conductivity", "mmhos/cm", [ctx("method", sval("soluble salts"))], one(t2, 14)),
         ab.float_var("concentration", "mg/kg", mol("elemental carbon", organic(1), ctx("method", sval("water extract"))), one(t2, 10)),
         ab.float_var("concentration", "percent", mol("elemental carbon"), one(t2, 16)),
         ab.float_var("concentration", "percent", mol("elemental carbon", organic(1)), one(t2, 17)),
         ab.float_var("concentration", "percent", mol("nitrogen atom"), one(t2, 18))])
    ab.write_brick(props)
    write_process(ab.PROCESS_OUT / "process_assay_geochemistry_fwb306_sediment_20261111.tsv", [{
        "process": "Assay Geochemistry <PROCESS:0000005>", "person": "Hazen Lab <ENIGMA:0000066>", "campaign": "Natural Organic Matter <ENIGMA:0000027>",
        "protocol": "null", "date_start": "2015-08-06", "date_end": "2015-08-06",
        "input_objects": ", ".join(f"Sample: {x}" for x in samples),
        "output_objects": "Generic: hazen_sediment_extractable_fwb306_2015.ndarray, Generic: hazen_sediment_soil_properties_fwb306_2015.hndarray"}])
    report += ["## FWB-306 sediment: hazen_sediment_extractable_fwb306_2015 and hazen_sediment_soil_properties_fwb306_2015", "",
               f"- samples: {', '.join(samples)}; 2 replicates", f"- extractable: {n} analytes; below-limit cells: {'; '.join(censored)}",
               f"- never detected (kept, all blank): {'; '.join(never)}", "- soil properties: 10 variables", ""]


# ----------------------------------------------------------------------------
# EVO geochemistry (Drive/paper Table S1, corrected, plus chloride and phosphate from the sample log)
# ----------------------------------------------------------------------------

def evo_sample_name(well, day):
    date = INJECTION + dt.timedelta(days=day)
    return f"{EVO_SAMPLE_PREFIX[well]}-{date.strftime('%m-%d-%y')}"


def build_evo_geochem(report, new_samples):
    rows = [r for r in csv.DictReader(DRIVE_META.open(errors="replace")) if r["Ca_mgL"].strip()]
    if len(rows) != 44 or {r["EVOYear"].strip() for r in rows} != {"2017"} or {r["FilterSize"].strip() for r in rows} != {"0.2um"}:
        raise ValueError("Drive EVO metadata: expected 44 rows of 2017 0.2um geochemistry")
    recs = {}
    for r in rows:
        day = int(float(r["DaysPostinjection"]))
        recs[(r["WellID"], day)] = r
    # field readings and ion chromatography results of the ORNL sample log (2017-12-07 to 2018-02-01, all eight wells);
    # chloride and phosphate sit under the As and Be headers there
    header, log, _ = log_rows()
    logv = {}
    for x in log:
        if "evo" in x["campaign"].lower() and x["date"] in EVO_DATES and x["well"] in EVO_SAMPLE_PREFIX:
            vals = {}
            for c in (10, 12, 13, 14, 30, 32):
                if c in x["cells"]:
                    v, note = log_value(x, c)
                    if note or v is None:
                        raise ValueError(f"EVO log cell {x['well']} {x['date']} {header[c]}: {x['cells'][c]}")
                    vals[c] = v
            if vals:
                k = (x["well"], EVO_DATES[x["date"]])
                if k in logv:
                    raise ValueError(f"two log rows for {k}")
                logv[k] = vals
    for k, r in recs.items():  # where both sources have pH and dissolved oxygen they agree
        for c, dc in ((10, "pH"), (13, "DissolvedOxygen _mgL")):
            if k in logv and c in logv[k] and abs(logv[k][c] - float(r[dc])) > 0.006:
                raise ValueError(f"{k} {dc}: log {logv[k][c]} differs from the published table {r[dc]}")
    order = sorted(set(recs) | set(logv), key=lambda k: (k[1], list(EVO_SAMPLE_PREFIX).index(k[0])))
    log_only = [k for k in order if k not in recs]
    if len(order) != 58 or len(log_only) != 14:
        raise ValueError(f"expected 58 well-visits (14 from the log only); got {len(order)}, {len(log_only)}")
    names = [evo_sample_name(w, d) for w, d in order]

    live = {r["sdt_sample_name"] for r in csv.DictReader(EXPORT_SAMPLES.open(), delimiter="\t")}
    renamed_live = {n for n in live} | {new + n[len(old):] for n in live for old, new in RENAME_PREFIX.items() if n.startswith(old)}
    for n in names:
        if n not in renamed_live:
            new_samples.append(n)
    if len(new_samples) != 15:
        raise ValueError(f"expected 15 new samples, got {len(new_samples)}: {new_samples}")

    def col(c):
        return {k: (float(recs[k][c]) if k in recs else None) for k in order}

    def field(c, dc):  # pH, dissolved oxygen: the published table, else the log
        return [float(recs[k][dc]) if k in recs else logv[k].get(c) for k in order]
    U, Mn, Fe = col("U238_mgL"), col("Mn_mgL"), col("Fe54_mgL")
    no3, so4, ac, nh4 = col("NO3_mgL"), col("SO4_mgL"), col("Acetate_mgL"), col("NH4_mgL")
    # day -6 metals are doubled in the published table (Adams thesis: MLSB3 1111.5 ug/L U before injection; table 2.223 mg/L)
    if abs(U[("MLSB3", -6)] - 2.223) > 1e-9:
        raise ValueError("MLSB3 day -6 uranium is not the published 2.223")
    for m in (U, Mn, Fe):
        for k in order:
            if k[1] == -6 and m[k] is not None:
                m[k] = m[k] / 2
    # FW215 and FW216 nitrate and sulfate are swapped on day 15 in the published table (sample log and 2018 slides agree)
    a, b = ("FW215", 15), ("FW216", 15)
    if not (abs(no3[a] - 17.74) < 0.01 and abs(no3[b] - 1.49) < 0.01 and abs(so4[a] - 67.56) < 0.01 and abs(so4[b] - 60.29) < 0.01):
        raise ValueError("day-15 FW215/FW216 nitrate/sulfate are not the published (swapped) values")
    no3[a], no3[b] = no3[b], no3[a]
    so4[a], so4[b] = so4[b], so4[a]

    cl = {k: v[30] for k, v in logv.items() if 30 in v}
    po4 = {k: v[32] for k, v in logv.items() if 32 in v}
    if len(cl) != 29 or len(po4) != 11:
        raise ValueError(f"log chloride/phosphate counts {len(cl)}, {len(po4)}")

    below = {}

    def censor(name, m):  # a zero in the published table is a value below detection
        below[name] = [None if m[k] is None else m[k] == 0 for k in order]
        return [None if not m[k] else m[k] for k in order]
    variables = [
        ab.float_var("pH", "pH unit", [], field(10, "pH")),
        ab.float_var("temperature", "degree Celsius", [], [logv.get(k, {}).get(12) for k in order]),
        ab.float_var("concentration", "mg/L", mol("oxygen atom", DISSOLVED), field(13, "DissolvedOxygen _mgL")),
        ab.float_var("redox potential", "millivolt", [], [logv.get(k, {}).get(14) for k in order]),
        ab.float_var("specific conductivity", "uS/cm", [], [col("SpecificConductivity.uScm")[k] for k in order]),
        ab.float_var("elevation", "meter", [ctx("category", sval("water level"))],
                     [col("WaterLevel_mAMSL")[k] for k in order]),
        ab.float_var("concentration", "mg/L", mol("element U"), [U[k] for k in order]),
        ab.float_var("concentration", "mg/L", mol("element Mn"), [Mn[k] for k in order]),
        ab.float_var("concentration", "mg/L", mol("element Fe"), censor("element Fe", Fe)),
        ab.float_var("concentration", "mg/L", mol("nitrate"), censor("nitrate", no3)),
        ab.float_var("concentration", "mg/L", mol("sulfate"), [so4[k] for k in order]),
        ab.float_var("concentration", "mg/L", mol("acetate"), censor("acetate", ac)),
        ab.float_var("concentration", "mg/L", mol("ammonium"), censor("ammonium", nh4)),
        ab.float_var("concentration", "mg/L", mol("chloride"), [cl.get(k) for k in order]),
        ab.float_var("concentration", "mg/L", mol("phosphate ion"), [po4.get(k) for k in order]),
    ]
    for key, flags in below.items():
        variables.append(ab.bool_var("below", ab.below_ctx(mol(key)), flags))
    for label, c in (("oxygen content", "Oxygen_content"), ("nitrate reduction", "nitrate_reduction"), ("sulfate reduction", "sulfate_reduction"), ("phase", "phase")):
        variables.append(ab.typed("description", "string", [recs[k][c].strip() if k in recs else None for k in order], None, [ctx("category", sval(label))]))
    days = ab.typed("time elapsed", "float", [float(k[1]) for k in order], "day", [ctx("relative", sval("EVO injection"))])
    array_context = [
        comment("Geochemistry of the injection wells FW212, FW213 and FW214, the control well FW215 and the monitoring wells FW216, MLSB3, GP01 and GP03 before and after the "
                "emulsified vegetable oil injection of 2017-12-13 (ORR Area 2). Published as Table S1 of Michael et al. 2024, Water Research, doi:10.1016/j.watres.2024.121460; "
                "source: ENIGMA Google Drive, 2017 EVO Injection/Zhou - 16S sequencing/20230222.metadata.csv (provided by Andrew Putt)"),
        comment("Corrections to the published table: (1) U, Mn and Fe of 2017-12-07 are halved, because that day's metals are doubled in the table "
                "(Adams 2019 thesis: MLSB3 1111.5 ug/L U before injection, table 2.223 mg/L; later dates agree); "
                "(2) nitrate and sulfate of FW215 and FW216 on 2017-12-28 are exchanged back (the ORNL sample log and the Hazen Lab slides of May 2018 agree against the table)"),
        comment("A zero in the published table is stored as below detection (blank value, below = true) for Fe, nitrate, acetate and ammonium. "
                "Acetate was measured in micromolar and converted to mg/L in the table. For 2018-04-26 the table has no detectable acetate, "
                "but the Adams thesis lists 63.75 (FW215), 70.41 (FW216), 10.00 (MLSB3), 105.81 (GP01) and 256.75 (GP03) micromolar"),
        comment("Temperature and redox potential, and every measurement of the injection wells FW212, FW213 and FW214 and of GP01 on 2017-12-14 (pH, temperature, dissolved "
                "oxygen, redox potential), are from the ORNL FRC sample collection log, which covers 2017-12-07 to 2018-02-01; the published table has only the control and monitoring wells"),
        comment("Chloride and phosphate are from the ORNL FRC sample collection log (2017-12-07 to 2018-02-01), where the ion chromatography results sit under the As and Be headers. "
                "Chloride of 2018-02-01 (52 to 73 mg/L in four wells) is 4 to 5 times the earlier visits and is unexplained"),
        comment("Water level is the elevation of the water surface in the well in meters above mean sea level, from the depth to water measured before pumping "
                "(ground surface at these wells is 304.5 to 304.7 m). FW216 on 2017-12-14 and 2017-12-21 and MLSB3 on 2017-12-21 read 0.8 to 1.7 m below the other wells "
                "of the same day, and are as published"),
        comment("GP01 nitrate of 2018-03-29 is 17.63 mg/L here and 1.76 in the Hazen Lab slides. Iron is the Fe-54 isotope reading and is erratic"),
        comment("Mg, K, Ca and Al of the published table are not stored: Mg, K and Ca cannot be mg/L as labelled (about 0.14 meq/L of cations against 1.2 meq/L of sulfate), "
                "and Al is the same in every well and visit"),
        comment("The four description variables (categories oxygen content, nitrate reduction, sulfate reduction, phase) are the paper authors' groupings of the well-visits"),
    ]
    obj = ab.brick("hazen_geochemistry_evo_injection_2017", "Hazen Lab groundwater geochemistry during the 2017 EVO injection (Memory campaign)", "chemical measurement",
                   array_context, [ab.sample_dim(names, [days])], variables)
    ab.write_brick(obj)
    write_process(ab.PROCESS_OUT / "process_assay_geochemistry_evo_2017_20261111.tsv", [{
        "process": "Assay Geochemistry <PROCESS:0000005>", "person": "Hazen Lab <ENIGMA:0000066>", "campaign": "Memory <ENIGMA:0000008>",
        "protocol": "null", "date_start": "2017-12-07", "date_end": "2018-04-26",
        "input_objects": ",".join(f"Sample: {n}" for n in names), "output_objects": "Generic: hazen_geochemistry_evo_injection_2017.hndarray"}])
    report += ["## hazen_geochemistry_evo_injection_2017", "", f"- samples: {len(names)} ({len(new_samples)} new: {', '.join(new_samples)})",
               f"- variables: {len(variables)}; below-detection cells: " + ", ".join(f"{k} {sum(1 for x in v if x)}" for k, v in below.items()),
               f"- chloride values {len(cl)}, phosphate values {len(po4)}", ""]


# ----------------------------------------------------------------------------
# 16S: samples, communities, reads, zOTU bricks (2009 and 2017 EVO injections)
# ----------------------------------------------------------------------------
import glob  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402

import build_corepilot_its_geochip_coral_import as cp  # noqa: E402

ZDIR = DRIVE_META.parent
SRC16 = REPO / "coral_import/evo_memory_2017_source"
STATIC_EXPORT = REPO / "sync-coral-to-berdl/exports/sync-20261110-162303/coral_export/static_tsv"
EVO_DRIVE_LINK = "https://drive.google.com/drive/folders/184N2FokUsWbXp7g17hcwf3KsgI9AzZ_t"  # team drive, 2017 EVO Injection
INJECTIONS = {"2009": dt.date(2009, 2, 9), "2017": INJECTION}
DAY_RELABEL = {"2": 1, "81": 78, "107": 106}  # 0.1 um libraries: day labels of the visits of days 1, 78, 106
WELLS = {  # well -> (sample name prefix, Location, depth m)
    "FW215": ("FW215", "FW-215", 4.94538), "FW216": ("FW216-19", "FW-216-19", 5.518404), "MLSB3": ("MLSB3", "MLSB3-16.8", 4.94538),
    "GP01": ("GP01-18", "GP01-18", 4.01), "GP03": ("GP03-19", "GP03-19", 4.255), "MLSG4": ("MLSG4", "MLSG4-17.0", 5.0673),
    "MLSA3": ("MLSA3", "MLSA3-18.2", 5.54736), "FW202": ("FW202-19", "FW-202-19", 5.7912)}
RUN_DATES = {"141003": "2014-10-03", "141031": "2014-10-31", "180507": "2018-05-07", "180717": "2018-07-17", "200724": "2020-07-24"}
CLASSIFY_PROTO = "michael-ning-2023-unoise3-silva138"
CLASSIFY_TEXT = (
    "Zhou Lab 16S rRNA gene zOTU processing for the 2009 and 2017 emulsified vegetable oil injections at ORR Area 2 (Michael et al. 2024, Water Research, "
    "doi:10.1016/j.watres.2024.121460; ReadMe_EVOinjection2017_16S_v20230222). DNA was extracted from the filters by freeze-grinding (Zhou et al. 1996) and purified with "
    "DNeasy PowerSoil kits without bead beating. Amplicons of the V4 region (primers 515F and 806R, two-step PCR, Wu et al. 2015) were sequenced on Illumina MiSeq "
    "(500-cycle v2); DNA of the 2009 injection, stored at -80 C, was sequenced in 2014 and that of the 2017 injection in 2018 and 2020. Sequences were processed with USEARCH "
    "11.0.667: demultiplexing, merging pairs with at most 10 mismatches and at least 80% alignment, primer trimming without mismatch, quality filtering with at most 1 expected "
    "error and at least 100 bases. UNOISE3 generated the zOTU table. For samples with several filters, one sample was generated by resampling each zOTU table weighted by the "
    "DNA amount of each extraction (emr_combine_resample.r). Taxonomy was assigned by the RDP naive Bayesian classifier (assignTaxonomy in DADA2) against SILVA 138. "
    "Chloroplast and mitochondrial sequences were removed and every sample was rarefied to 10,448 reads (processed zOTU table). The lab also built a FastTree tree of the "
    "representative sequences (20230222.zOTU.tree.nwk), which is not in CORAL.")


def tsv_write(path, header, rows):
    with path.open("w", newline="") as h:
        w = csv.writer(h, delimiter="\t", lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def library_key():
    hdr = (ZDIR / "V230222.zOTU/20230222.zOTU.tabular").open().readline().rstrip("\n").split("\t")
    g = {r[""]: r for r in csv.DictReader((SRC16 / "github_ps.EVO_all_sample_data.tsv").open(), delimiter="\t")}
    if len(hdr) != 136 or set(hdr) != set(g):
        raise ValueError("zOTU table libraries differ from the GitHub sample table")
    key = collections.OrderedDict()
    for lib in hdr:
        r = g[lib]
        day = r["DaysAfter"]
        if r["EVOYear"] == "2017" and r["FilterSize"] == "0.1" and day in DAY_RELABEL:
            day = DAY_RELABEL[day]
        day = 106 if lib == "APEVO28" else int(day)  # labelled FW215 day 81 (a duplicate of APEVO24); it is the day 106 visit
        date = INJECTIONS[r["EVOYear"]] + dt.timedelta(days=day)
        sample = f"{WELLS[r['WellID']][0]}-{date.strftime('%m-%d-%y')}"
        key[lib] = {"year": r["EVOYear"], "well": r["WellID"], "day": day, "filter": r["FilterSize"], "date": date, "sample": sample,
                    "community": f"{sample} {r['FilterSize']} micron filter"}
    if len({k["community"] for k in key.values()}) != 136:
        raise ValueError("duplicate communities")
    return key


def sra_label_to_library(label):
    m = re.fullmatch(r"(EMR\d+)s\d+", label)
    if m:
        return m.group(1)
    m = re.fullmatch(r"W(\d)_(\d+)d", label)
    if m:
        return f"W{m.group(1)}D{m.group(2)}"
    return label


def build_16s(report, geochem_new_samples):
    key = library_key()
    live_samples = {r["name"]: r for r in csv.DictReader((STATIC_EXPORT / "Sample.tsv").open(), delimiter="\t")}
    renamed = {new + n[len(old):] for n in live_samples for old, new in RENAME_PREFIX.items() if n.startswith(old)}
    existing = (set(live_samples) - {n for n in live_samples if n.startswith(tuple(RENAME_PREFIX))}) | renamed
    live_comm = {r["name"] for r in csv.DictReader((STATIC_EXPORT / "Community.tsv").open(), delimiter="\t")}
    live_otu = {r["name"] for r in csv.DictReader((STATIC_EXPORT / "OTU.tsv").open(), delimiter="\t")}
    live_taxa = {r["name"] for r in csv.DictReader((STATIC_EXPORT / "Taxon.tsv").open(), delimiter="\t")}
    live_reads = {r["name"] for r in csv.DictReader((STATIC_EXPORT / "Reads.tsv").open(), delimiter="\t")}
    live_proto = {r["name"] for r in csv.DictReader((STATIC_EXPORT / "Protocol.tsv").open(), delimiter="\t")}

    # ---- samples
    samples = collections.OrderedDict()
    for k in sorted(key.values(), key=lambda k: (k["date"], list(WELLS).index(k["well"]))):
        samples.setdefault(k["sample"], k)
    new_samples = [n for n in samples if n not in existing]
    if not set(geochem_new_samples) <= set(new_samples) or len(new_samples) != 76:
        raise ValueError(f"new samples: {len(new_samples)}; geochemistry samples missing: {set(geochem_new_samples) - set(new_samples)}")
    tsv_write(ab.STATIC_OUT / "Sample_additions_20261111.tsv",
              ["name", "location", "depth", "elevation", "date", "time", "timezone", "material", "env_package", "description"],
              [[n, WELLS[samples[n]["well"]][1], WELLS[samples[n]["well"]][2], "null", samples[n]["date"].isoformat(), "null", "null",
                "ground water <ENVO:00002041>", "water <MIxS:0000017>", "Monitoring well"] for n in new_samples])
    write_process(ab.PROCESS_OUT / "process_sampling_evo_20261111.tsv", [{
        "process": "Sampling <PROCESS:0000002>", "person": "Hazen Lab <ENIGMA:0000066>", "campaign": "Memory <ENIGMA:0000008>", "protocol": "null",
        "date_start": samples[n]["date"].isoformat(), "date_end": samples[n]["date"].isoformat(),
        "input_objects": f"Location: {WELLS[samples[n]['well']][1]}", "output_objects": f"Sample: {n}"} for n in new_samples])

    # ---- communities and filter processes
    comms = [k["community"] for k in key.values()]
    if [c for c in comms if c in live_comm]:
        raise ValueError("community already in CORAL")
    tsv_write(ab.STATIC_OUT / "Community_additions_20261111.tsv",
              ["name", "community_type", "sample", "parent_community", "condition", "defined_strains", "description"],
              [[k["community"], "Environmental Community <ME:0000326>", k["sample"], "null", "null", "null", "null"] for k in key.values()])
    write_process(ab.PROCESS_OUT / "process_filter_evo_20261111.tsv", [{
        "process": "Filter <PROCESS:0000012>", "person": "Hazen Lab <ENIGMA:0000066>", "campaign": "Memory <ENIGMA:0000008>", "protocol": f"{k['filter']} micron filter",
        "date_start": k["date"].isoformat(), "date_end": k["date"].isoformat(),
        "input_objects": f"Sample: {k['sample']}", "output_objects": f"Community: {k['community']}"} for k in key.values()])

    # ---- reads
    drive_reads = {}
    for f in sorted(glob.glob(str(ZDIR / "Raw sequencing data/*/Raw.Reads.csv"))):
        for r in csv.DictReader(open(f)):
            if r["SampleID"] in drive_reads:
                raise ValueError(f"library {r['SampleID']} in two sequencing runs")
            drive_reads[r["SampleID"]] = (Path(f).parent.name, int(r["Reads"]))
    bios = {x["acc"]: x for x in json.load((SRC16 / "biosamples.json").open())}
    reads, in_sra = [], set()
    for r in csv.DictReader((SRC16 / "ena.tsv").open(), delimiter="\t"):
        x = bios[r["sample_accession"]]
        lib = sra_label_to_library(x["label"])
        k = key[lib]
        eid = x["ENIGMA_ID"].split("_")
        if eid[1] != k["well"] or eid[2] != k["date"].strftime("%Y%m%d") or r["collection_date"] != k["date"].isoformat():
            raise ValueError(f"SRA {x['label']}: {x['ENIGMA_ID']} disagrees with the library key {k}")
        run, n = drive_reads[x["label"]]
        if n != int(r["read_count"]):
            raise ValueError(f"{x['label']}: read count differs between SRA and Drive")
        reads.append({"name": f"{x['ENIGMA_ID']}.16S.reads", "count": n, "link": f"https://www.ncbi.nlm.nih.gov/sra/{r['run_accession']}", "community": k["community"], "run": run})
        in_sra.add(lib)
    drive_only = [lib for lib in key if lib not in in_sra]
    for lib in drive_only:
        k = key[lib]
        label = lib if lib in drive_reads else re.sub(r"W(\d)D(\d+)", r"W\1_\2d", lib)
        run, n = drive_reads[label]
        name = f"EVO{k['year'][2:]}_{k['well']}_{k['date'].strftime('%Y%m%d')}_F{k['filter'].replace('.', '')}_R1.16S.reads"
        reads.append({"name": name, "count": n, "link": EVO_DRIVE_LINK, "community": k["community"], "run": run})
    names = [r["name"] for r in reads]
    if len(reads) != 169 or len(set(names)) != 169 or [n for n in names if n in live_reads]:
        raise ValueError(f"reads: {len(reads)} records, {len(set(names))} distinct")
    reads.sort(key=lambda r: r["name"])
    tsv_write(ab.STATIC_OUT / "Reads_additions_20261111.tsv", ["name", "read_count", "read_type", "sequencing_technology", "link"],
              [[r["name"], r["count"], "Paired End Read <ME:0000113>", "Illumina <ME:0000117>", r["link"]] for r in reads])
    write_process(ab.PROCESS_OUT / "process_16s_sequencing_evo_20261111.tsv", [{
        "process": "16S Sequencing <PROCESS:0000020>", "person": "Zhou Lab <ENIGMA:0000090>", "campaign": "Memory <ENIGMA:0000008>", "protocol": "null",
        "date_start": RUN_DATES[r["run"]], "date_end": RUN_DATES[r["run"]],
        "input_objects": f"Community: {r['community']}", "output_objects": f"Reads: {r['name']}"} for r in reads])

    # ---- zOTU table, classification, sequences
    rows = list(csv.reader((ZDIR / "V230222.zOTU/20230222.zOTU.tabular").open(), delimiter="\t"))
    libs, body = rows[0], rows[1:]
    ids = [r[0] for r in body]
    counts = [[int(float(x)) for x in r[1:]] for r in body]
    if any(float(x) != int(float(x)) for r in body for x in r[1:]) or {sum(c[j] for c in counts) for j in range(136)} != {10448}:
        raise ValueError("zOTU table: non-integer counts or depth not 10,448")
    cl = list(csv.reader((ZDIR / "V230222.zOTU/20230222.zOTU.Classification.tabular").open(), delimiter="\t"))
    ch = cl[0]
    if ch[:7] != [lv for lv, _, _ in oo.LEVELS] or [r[0] for r in cl[1:]] != ids:
        raise ValueError("classification header or order")
    conf_cols = [ch.index(f"{lv}.Confidence") if f"{lv}.Confidence" in ch else None for lv, _, _ in oo.LEVELS]
    seqs, cur = {}, None
    for line in (ZDIR / "V230222.zOTU/Unprocessed data/20230222.repseq.fasta").open():
        line = line.strip()
        if line.startswith(">"):
            cur = line[1:].split()[0]
            seqs[cur] = ""
        elif cur:
            seqs[cur] += line
    if any(hashlib.md5(seqs[i].encode()).hexdigest() != i for i in ids):
        raise ValueError("a zOTU ID is not the MD5 of its sequence")
    taxa, conf, unassigned = [], [], collections.Counter()
    for r in cl[1:]:
        genus = None
        for j, (lv, _, _) in enumerate(oo.LEVELS):
            v = r[1 + j]
            v = None if v in ("NA", "", "Unclassified") else v
            if v is None:
                unassigned[lv] += 1
            if re.fullmatch(r"\d+-[A-Z][a-z]{2}|\d+/\d+/\d{4}", v or ""):
                raise ValueError(f"date-like taxon name {v}")
            if lv == "Genus":
                genus = v
            if lv == "Species" and v is not None:
                if genus is None:
                    raise ValueError(f"{r[0]}: species without genus")
                v = f"{genus} {v}"
            taxa.append(v)
            c = conf_cols[j]
            conf.append(None if c is None or v is None or r[1 + c] in ("NA", "") else float(r[1 + c]))
    # a taxon CORAL already has under another spelling (space or underscore, capitalization) is referenced by the existing record
    def spelling_key(t):
        return re.sub(r"[_ ]+", " ", t.lower())
    by_key = collections.defaultdict(list)
    for t in live_taxa:
        by_key[spelling_key(t)].append(t)
    respell = {"Clostridium_sensu_stricto_7 homopropionicum": "Clostridium sensu stricto 7 homopropionicum"}  # as its sibling 'Clostridium sensu stricto 12 magnum' is written
    for t in sorted({t for t in taxa if t and t not in live_taxa}):
        same = by_key.get(spelling_key(t))
        if same:
            respell[t] = sorted(same, key=lambda x: (-x.count("_"), x))[0]
    if len(respell) != 6:
        raise ValueError(f"expected 5 existing spellings and 1 respelling, got {respell}")
    taxa = [respell.get(t, t) for t in taxa]
    new_otus = [i for i in ids if i not in live_otu]
    tsv_write(ab.STATIC_OUT / "OTU_additions_20261111.tsv", ["name"], [[i] for i in new_otus])
    new_taxa = sorted({t for t in taxa if t and t not in live_taxa})
    taxid, how = cp.ncbi_ids_extended(set(new_taxa))
    tsv_write(ab.STATIC_OUT / "Taxon_additions_20261111.tsv", ["name", "ncbi_taxid"], [[t, taxid.get(t, "null")] for t in new_taxa])
    protos = [[CLASSIFY_PROTO, CLASSIFY_TEXT, "https://doi.org/10.1016/j.watres.2024.121460"]]
    if "0.1 micron filter" not in live_proto:
        protos.append(["0.1 micron filter", "Groundwater filtered through a 0.1 micron filter (here the filtrate of the 0.2 micron filter); the community is the material retained on the filter", "null"])
    if CLASSIFY_PROTO in live_proto or "0.2 micron filter" not in live_proto:
        raise ValueError("protocol state")
    tsv_write(ab.STATIC_OUT / "Protocol_additions_20261111.tsv", ["name", "description", "link"], protos)

    # ---- bricks
    stem = "zhou_lab_evo_injection_2009_2017_zOTU"
    title = "2009 and 2017 EVO injections, ORR Area 2"
    src = "ENIGMA Google Drive, 2017 EVO Injection/Zhou - 16S sequencing/V230222.zOTU"
    otu_dim = {"data_type": oo.term("OTU"), "size": len(ids), "typed_values": [{"value_type": oo.term("OTU ID"), "values": oo.obj_values(ids)}]}
    naming = comment("zOTUs are named by the MD5 of their representative sequence, as the other Zhou Lab ASV sets are")
    seq = {"name": f"{stem}_16S.ndarray", "description": f"Zhou Lab 16S zOTU sequences, {title}", "data_type": oo.term("microbial sequence"),
           "array_context": [naming, comment(f"Source: {src}/Unprocessed data/20230222.repseq.fasta (the 10,216 zOTUs of the processed table)")],
           "n_dimensions": 1, "dim_context": [otu_dim],
           "typed_values": [{"value_type": oo.term("sequence"), "values": {"scalar_type": "string", "string_values": [seqs[i] for i in ids]},
                             "value_context": [ctx("sequence type", oterm_value("16S sequence"))]}]}
    comm_dim = {"data_type": oo.term("community"), "size": 136, "typed_values": [
        {"value_type": oo.term("community ID"), "values": oo.obj_values([key[l]["community"] for l in libs])},
        ab.typed("date", "string", [INJECTIONS[key[l]["year"]].isoformat() for l in libs], None, [ctx("category", sval("EVO injection"))]),
        ab.typed("time elapsed", "float", [float(key[l]["day"]) for l in libs], "day", [ctx("relative", sval("EVO injection"))]),
        ab.typed("description", "string", list(libs), None, [ctx("category", sval("source library label"))])]}
    count = {"name": f"{stem}_count.ndarray", "description": f"Zhou Lab 16S zOTU counts (rarefied to 10,448 reads per sample), {title}",
             "data_type": oo.term("taxonomic abundance"),
             "array_context": [
                 ctx("method", sval("Processed zOTU table: chloroplast and mitochondrial sequences removed, replicate filters of a sample combined by resampling weighted by DNA amount, every sample rarefied to 10,448 reads")),
                 comment("Communities are the filters of each groundwater sample: 53 of the 2009 injection (0.2 micron; injection 2009-02-09, days -28 to 269) and 83 of the 2017 "
                         "injection (48 on 0.2 micron filters, days -6 to 372; 35 on 0.1 micron filters, days 1 to 246; injection 2017-12-13)"),
                 comment("Library key: SRA PRJNA1084851 (0.2 micron libraries; collection dates and wells agree with this key) and the sample table of the paper's code "
                         "(github.com/jpmichael93/Publications). In that table the 0.1 micron libraries labelled day 2, 81 and 107 are the visits of days 1, 78 and 106, and "
                         "APEVO28 (labelled FW215 day 81, as APEVO24 is) is taken as the FW215 visit of day 106. The 0.1 micron libraries and W7D80 (GP03, 2009-04-30) are not in SRA"),
                 comment("On the community dimension: the date of the injection the community belongs to (2009-02-09 or 2017-12-13), the days from that injection to the "
                         "sampling date, and the laboratory's library label (the column name in the zOTU table)"),
                 naming, comment(f"Source: {src}/20230222.zOTU.tabular")],
             "n_dimensions": 2, "dim_context": [otu_dim, comm_dim],
             "typed_values": [{"value_type": oo.term("count"), "value_units": oo.term("count unit"), "values": {"scalar_type": "int", "int_values": [v for row in counts for v in row]}}]}
    level_dim = {"data_type": oo.term("taxonomic level"), "size": len(oo.LEVELS), "typed_values": [{"value_type": oo.term("taxonomic level"), "values": {
        "scalar_type": "oterm_ref", "oterm_refs": [i for _, _, i in oo.LEVELS], "string_values": [n for _, n, _ in oo.LEVELS]}}]}
    tax = {"name": f"{stem}_taxonomy.ndarray", "description": f"Zhou Lab 16S zOTU taxonomy (RDP classifier, SILVA 138), {title}", "data_type": oo.term("taxonomic assignment"),
           "array_context": [{"value_type": oo.term("data variables type"), "value": oterm_value("taxonomic assignment")},
                             comment("Variables: taxon ID (a CORAL Taxon; species are given as genus plus epithet; unassigned levels, NA in the source, are null) and the classifier confidence for each level; the source has no species confidence"),
                             comment("Taxon names are SILVA 138's, as in the source, except where CORAL already has the taxon under another spelling: "
                                     + "; ".join(f"{a} is stored as {b}" for a, b in sorted(respell.items()))),
                             naming, comment(f"Source: {src}/20230222.zOTU.Classification.tabular")],
           "n_dimensions": 2, "dim_context": [otu_dim, level_dim],
           "typed_values": [{"value_type": oo.term("taxon ID"), "values": oo.obj_values(taxa)},
                            {"value_type": oo.term("confidence"), "value_units": oo.term("confidence unit"), "values": {"scalar_type": "float", "float_values": conf}}]}
    for o in (seq, count, tax):
        oo.write_brick(o)
    write_process(ab.PROCESS_OUT / "process_classify_otus_evo_20261111.tsv", [{
        "process": "Classify OTUs <PROCESS:0000031>", "person": "Jonathan Michael <ENIGMA:0000156>", "campaign": "Memory <ENIGMA:0000008>", "protocol": CLASSIFY_PROTO,
        "date_start": "2023-02-22", "date_end": "2023-02-22", "input_objects": ", ".join(f"Reads: {n}" for n in sorted(names)),
        "output_objects": ", ".join(f"Generic: {o['name']}" for o in (seq, count, tax))}])
    report += ["## 16S: samples, communities, reads, zOTU bricks", "",
               f"- samples: {len(samples)} referenced, {len(new_samples)} new ({sum(n.endswith('-09') for n in new_samples)} of 2009)",
               f"- communities: {len(comms)} new; reads: {len(reads)} ({len(in_sra)} libraries with {len(reads) - len(drive_only)} SRA runs; {len(drive_only)} libraries on Drive only)",
               f"- zOTUs: {len(ids)} ({len(new_otus)} new OTU records); taxa: {len({t for t in taxa if t})} distinct, {len(new_taxa)} new "
               f"({sum(1 for t in new_taxa if t in taxid)} with an NCBI taxid; " + ", ".join(f"{k} {n}" for k, n in collections.Counter(how.values()).most_common()) + ")",
               "- unassigned per level: " + ", ".join(f"{lv} {n}" for lv, n in unassigned.items()),
               f"- protocols added: {', '.join(p[0] for p in protos)}", ""]


# ----------------------------------------------------------------------------
# hub scripts: move the GP01/GP03 samples to the upper ports (rename the 12 EVO samples)
# ----------------------------------------------------------------------------

def write_sample_moves(report):
    samples = {r["name"]: r for r in csv.DictReader((STATIC_EXPORT / "Sample.tsv").open(), delimiter="\t")}
    locs = {r["name"]: r["id"] for r in csv.DictReader((STATIC_EXPORT / "Location.tsv").open(), delimiter="\t")}
    port = {"GP01-30": ("GP01-18", WELLS["GP01"][2]), "GP03-29": ("GP03-19", WELLS["GP03"][2])}
    moves = []
    for name, r in sorted(samples.items()):
        if r["location_id"] in port:
            new_loc, depth = port[r["location_id"]]
            new_name = name
            for old, new in RENAME_PREFIX.items():
                if name.startswith(old):
                    new_name = new + name[len(old):]
            moves.append({"key": r["id"], "old_name": name, "new_name": new_name, "old_loc": r["location_id"], "new_loc": new_loc,
                          "old_loc_id": locs[r["location_id"]], "new_loc_id": locs[new_loc], "old_depth": float(r["depth"]), "new_depth": depth})
    if len(moves) != 14 or sum(m["old_name"] != m["new_name"] for m in moves) != 12:
        raise ValueError(f"expected 14 samples to move, 12 to rename; got {len(moves)}")
    d = OUT / "hub"
    d.mkdir()
    template = (REPO / "tools/templates/evo_sample_moves_hub.py.tmpl").read_text()
    for fname, flag in (("preflight_sample_moves.py", "False"), ("apply_sample_moves.py", "True")):
        (d / fname).write_text(template.replace("__APPLY__", flag).replace("__MOVES__", json.dumps(moves)))
    report += ["## Sample moves (hub scripts in hub/)", "", "| Sample | New name | Location | Depth m |", "| --- | --- | --- | --- |"]
    report += [f"| {m['old_name']} | {m['new_name'] if m['new_name'] != m['old_name'] else '(unchanged)'} | {m['old_loc']} -> {m['new_loc']} | {m['old_depth']:.4g} -> {m['new_depth']} |" for m in moves]
    report.append("")


def main():
    oo.stage_validator()
    for d in ("names", "ont"):  # validate against the COMO of ontology_update_20261111_sediment (unlink first: never write through a link)
        staged = oo.STAGED / d / "context_measurement_ontology.obo"
        staged.unlink()
        staged.write_bytes(COMO_PATCHED.read_bytes())
    ab.load_ontology_names()
    if OUT.exists():
        shutil.rmtree(OUT)
    ab.OUT = OUT
    ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT = (OUT / d for d in ("json", "static", "process", "check", "reports"))
    for d in (ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT):
        d.mkdir(parents=True)
    report = ["# EVO Memory campaign and Brick0000007 replacement: build report", ""]
    build_brick7(report)
    build_sediment(report)
    new_samples = []
    build_evo_geochem(report, new_samples)
    build_16s(report, new_samples)
    write_sample_moves(report)
    (ab.REPORT_OUT / "build_report.md").write_text("\n".join(report) + "\n")
    statics = ["Protocol", "Taxon", "OTU", "Sample", "Community", "Reads"]
    first = [("Sampling", "process_sampling_evo_20261111.tsv"), ("Filter", "process_filter_evo_20261111.tsv"), ("16S Sequencing", "process_16s_sequencing_evo_20261111.tsv")]
    bricks = ["hazen_field_post100ws_v2", "hazen_sediment_extractable_fwb306_2015", "hazen_sediment_soil_properties_fwb306_2015", "hazen_geochemistry_evo_injection_2017",
              "zhou_lab_evo_injection_2009_2017_zOTU_16S", "zhou_lab_evo_injection_2009_2017_zOTU_count", "zhou_lab_evo_injection_2009_2017_zOTU_taxonomy"]
    last = [("Classify OTUs", "process_classify_otus_evo_20261111.tsv"), ("Assay Geochemistry", "process_assay_geochemistry_evo_2017_20261111.tsv"),
            ("Assay Geochemistry", "process_assay_geochemistry_fwb306_sediment_20261111.tsv"), ("Update Data", "process_update_data_hazen_field_post100ws_v2_20261111.tsv")]
    files = [f"static/{t}_additions_20261111.tsv" for t in statics] + [f"process/{f}" for _, f in first] + [f"json/{b}.json" for b in bricks] + [f"process/{f}" for _, f in last]
    missing = [f for f in files if not (OUT / f).exists()]
    if missing:
        raise FileNotFoundError(missing)
    (OUT / "files_to_import.txt").write_text("\n".join(files) + "\n")
    lines = ["# Run on the CORAL hub, in order, after (1) installing coral_import/ontology_update_20261111_sediment on stout and coral-enigma and",
             "# reloading the ontologies, and (2) copying every file in files_to_import.txt to /home/coral/prod/data_import/data/ on coral-enigma.", "",
             "# Step 1: move the GP01/GP03 samples to the upper ports (hub/apply_sample_moves.py; guarded, prints what it changed).", "",
             "# Step 2: static objects, in dependency order."]
    lines += [f"toolx.update_core('{t}_additions_20261111.tsv', '{t}')" for t in statics]
    lines += ["", "# Step 3: sampling, filter and sequencing processes."] + [f"toolx.upload_process('{n}', '{f}')" for n, f in first]
    lines += ["", "# Step 4: the bricks."] + [f"toolx.upload_brick('{b}.json')" for b in bricks]
    lines += ["", "# Step 5: classification, assay and update processes."] + [f"toolx.upload_process('{n}', '{f}')" for n, f in last]
    (OUT / "import_to_coral.py").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
