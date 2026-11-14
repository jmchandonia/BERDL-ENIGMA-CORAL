#!/usr/bin/env python3
"""Build the FW305 sediment core import (2013): 54 Samples at Location FW-305 and the Elias Lab brick of
anions, organic acids, iron and moisture.

Sources (ENIGMA Google Drive; local copies in coral_import/fw305_core_2013_source/):
  IC Analysis of Core.xlsx                                   Kathryn Bailey (ORNL, Elias Lab), created 2013-08-02
  FW305 Core Depths with coordinating sample numbers.xlsx    Kathryn Bailey, created 2013-08-06

Nothing here touches the CORAL hub.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import build_sso_batch_ab_coral_import as ab  # noqa: E402
import build_sso_oneoff_16s_coral_import as oo  # noqa: E402
from build_sso_batch_ab_coral_import import T, comment, ctx, oterm_value, sval, write_process  # noqa: E402

SRC = REPO / "coral_import/fw305_core_2013_source"
IC = SRC / "IC Analysis of Core.xlsx"
DEPTHS = SRC / "FW305 Core Depths with coordinating sample numbers.xlsx"
OUT = REPO / "coral_import/fw305_core_20261113"
STAMP = "20261113"
LIVE_SAMPLES = REPO / "sync-coral-to-berdl/exports/sync-20261113-102740/berdl_upload/data/sdt_sample.tsv"
LOCATION = "FW-305"
DATE = "2013-05-29"  # completion of well FW-305; the core was taken while the well was installed
CAMPAIGN = "Natural and Synthetic Ecologies <ENIGMA:0000010>"
FT = 0.3048

T.update({
    "iron(2+)": "CHEBI:29033", "iron(3+)": "CHEBI:29034", "fluoride": "CHEBI:17051", "chloride": "CHEBI:17996", "bromide": "CHEBI:15858",
    "sulfate": "CHEBI:16189", "phosphate ion": "CHEBI:35780", "lactate": "CHEBI:24996", "acetate": "CHEBI:30089", "propionate": "CHEBI:17272",
    "formate": "CHEBI:15740", "butyrate": "CHEBI:17968", "pyruvate": "CHEBI:15361", "succinate": "CHEBI:26806", "fumarate(2-)": "CHEBI:29806",
    "citrate(3-)": "CHEBI:16947", "water": "CHEBI:15377", "mg/g": "ME:0000352",
    "Elias Lab": "ENIGMA:0000061", "Natural and Synthetic Ecologies": "ENIGMA:0000010",
})

# IC sheet column -> (variable, unit, molecule key, extra context)
HEADER = ("Injection #", "Core ID", "Moisture Content (%)", "Fe2+ (mg Fe/g soil)", "Fe3+ (mg Fe/g soil)", "Fluoride (µM)", "Chloride (µM)", "Bromide (µM)",
          "Nitrate (µM)", "Sulfate (µM)", "Phosphate (µM)", "Lactate (µM)", "Acetate (µM)", "Propionate (µM)", "Formate (µM)", "Butyrate (µM)",
          "Pyruvate (µM)", "Succinate (µM)", "Fumarate (µM)", "Citrate (µM)", None, "Depth (ft)")
ANIONS = ["fluoride", "chloride", "bromide", "nitrate", "sulfate", "phosphate ion", "lactate", "acetate", "propionate", "formate", "butyrate", "pyruvate",
          "succinate", "fumarate(2-)", "citrate(3-)"]
# cells blanked as typing errors: (sample, column header) -> source value
BLANKED = {("FW305-01-36", "Formate (µM)"): 6969}


def mol(key, *extra):
    return [ctx("molecule from list", oterm_value(key))] + list(extra)


def read_sources():
    rows = [r for r in openpyxl.load_workbook(IC, data_only=True).worksheets[0].iter_rows(values_only=True) if any(c is not None for c in r)]
    if tuple(rows[0][:22]) != HEADER:
        raise ValueError(f"IC sheet header: {rows[0]}")
    ic = {r[1]: r for r in rows[1:]}
    drows = [r for r in openpyxl.load_workbook(DEPTHS, data_only=True).worksheets[0].iter_rows(values_only=True) if any(c is not None for c in r)]
    if tuple(drows[0][:3]) != ("Core ID", "Depth (ft)", "remaining sample"):
        raise ValueError("depth sheet header")
    order = [r[0] for r in drows[1:]]
    if len(order) != 54 or len(ic) != 54 or [r[1] for r in rows[1:]] != order:
        raise ValueError("the two sheets do not list the same 54 sections in the same order")
    for r in drows[1:]:
        if abs(float(r[1]) - float(ic[r[0]][21])) > 1e-9:
            raise ValueError(f"depth differs between the sheets for {r[0]}")
    return order, ic, {r[0]: (float(r[1]), r[2]) for r in drows[1:]}


def build_samples(order, depths, report):
    live = {r["sdt_sample_name"] for r in csv.DictReader(LIVE_SAMPLES.open(), delimiter="\t")}
    clash = [n for n in order if n in live]
    if clash:
        raise ValueError(f"sample names already in CORAL: {clash}")
    rows = []
    for n in order:
        _, run, inch = n.split("-")
        ft, _ = depths[n]
        rows.append([n, LOCATION, f"{ft * FT:.4f}".rstrip("0").rstrip("."), "null", DATE, "null", "null", "sediment <ENVO:00002007>", "sediment <MIxS:0000014>",
                     f"Sediment core taken during installation of well FW-305 (May 2013; the date is the completion of the well): core run {int(run)}, "
                     f"section starting {int(inch)} inches into the run; depth {ft:g} ft as recorded by the Elias Lab (the bottom of the section, judging from the section lengths)"])
    with (ab.STATIC_OUT / f"Sample_additions_{STAMP}.tsv").open("w", newline="") as h:
        w = csv.writer(h, delimiter="\t", lineterminator="\n")
        w.writerow(["name", "location", "depth", "elevation", "date", "time", "timezone", "material", "env_package", "description"])
        w.writerows(rows)
    write_process(ab.PROCESS_OUT / f"process_sampling_fw305_core_{STAMP}.tsv", [{
        "process": "Sampling <PROCESS:0000002>", "person": "Elias Lab <ENIGMA:0000061>", "campaign": CAMPAIGN, "protocol": "null",
        "date_start": DATE, "date_end": DATE, "input_objects": f"Location: {LOCATION}", "output_objects": f"Sample: {n}"} for n in order])
    back = [(a, b) for a, b in zip(order, order[1:]) if depths[b][0] < depths[a][0]]
    report += ["## Samples", "", f"- {len(rows)} samples at {LOCATION}, {rows[0][2]} to {rows[-1][2]} m ({depths[order[0]][0]:g} to {depths[order[-1]][0]:g} ft)",
               f"- depth not increasing: {', '.join(f'{a} {depths[a][0]:g} ft then {b} {depths[b][0]:g} ft' for a, b in back) or 'none'}",
               f"- no sample remaining per the depth sheet: {', '.join(n for n in order if depths[n][1] == 'NONE')}", ""]


def build_brick(order, ic, report):
    def col(i):
        out = []
        for n in order:
            v = ic[n][i]
            key = (n, HEADER[i])
            if key in BLANKED:
                if v != BLANKED[key]:
                    raise ValueError(f"expected {BLANKED[key]} at {key}, found {v}")
                v = None
            out.append(None if v is None else float(v))
        return out

    soil = ctx("physiochemical state", sval("in soil"))
    variables = [ab.float_var("concentration", "percent", mol("water", soil), col(2)),
                 ab.float_var("concentration", "mg/g", mol("iron(2+)"), col(3)),
                 ab.float_var("concentration", "mg/g", mol("iron(3+)"), col(4))]
    stats, flags = [], []
    for i, key in enumerate(ANIONS, start=5):
        vals = col(i)
        variables.append(ab.float_var("concentration", "uM", mol(key), vals))
        flags.append(ab.bool_var("below", ab.below_ctx(mol(key)), [v is None and (n, HEADER[i]) not in BLANKED for n, v in zip(order, vals)]))
        got = [v for v in vals if v is not None]
        stats.append(f"| {HEADER[i]} | {ab.NAMES[T[key]]} ({T[key]}) | {len(got)} | {min(got):g} | {max(got):g} |" if got else f"| {HEADER[i]} | {ab.NAMES[T[key]]} ({T[key]}) | 0 | | |")
    name = "elias_sediment_anions_iron_fw305_core_2013"
    obj = ab.brick(
        name, "Elias Lab anions, organic acids, iron and moisture of the FW305 sediment core (2013)", "chemical measurement",
        [comment("Sediment core taken during the installation of well FW-305 (Oak Ridge FRC, Background A; well completed 2013-05-29), 54 sections from 0.5 to 26.08 ft "
                 "below ground surface. Measured by the Elias Lab (ORNL); workbook by Kathryn Bailey, 2013-08-02"),
         comment("Anions and organic acids by ion chromatography, micromolar as given in the workbook. Iron(2+) and iron(3+) are mg of iron per g of soil. "
                 "Moisture content is percent"),
         comment("Where the workbook leaves an anion or organic acid cell empty, the analyte was not detected in that section: the concentration is blank and the below variable "
                 "of that analyte is true. The workbook gives no detection limits; every section has values from the same ion chromatography run. Butyrate and citrate "
                 "were not detected in any section. Formate of FW305-01-36 is blank with below false: the workbook has 6969, a typing error with no recoverable value "
                 "(all other formate values are 0.03 to 6.95)"),
         comment("Source: ENIGMA Google Drive, IC Analysis of Core.xlsx. The workbook's injection number (order of the instrument runs) is not stored")],
        [ab.sample_dim(order)], variables + flags)
    ab.write_brick(obj)
    write_process(ab.PROCESS_OUT / f"process_assay_geochemistry_fw305_core_anions_{STAMP}.tsv", [{
        "process": "Assay Geochemistry <PROCESS:0000005>", "person": "Elias Lab <ENIGMA:0000061>", "campaign": CAMPAIGN, "protocol": "null",
        "date_start": "2013-08-02", "date_end": "2013-08-02", "input_objects": ", ".join(f"Sample: {n}" for n in order),
        "output_objects": f"Generic: {name}.hndarray"}])
    report += [f"## {name}", "", f"- {len(order)} samples x {len(variables) + len(flags)} variables ({len(flags)} below flags, true in {sum(sum(f["values"]["boolean_values"]) for f in flags)} cells)", "",
               "| source column | term | values | min | max |", "|---|---|---|---|---|"]
    for i, lab in ((2, "water, in soil (percent)"), (3, "iron(2+) (mg/g)"), (4, "iron(3+) (mg/g)")):
        got = [v for v in col(i) if v is not None]
        report.append(f"| {HEADER[i]} | {lab} | {len(got)} | {min(got):g} | {max(got):g} |")
    report += stats + [""]
    return name


# ----------------------------------------------------------------------------
# Adams Lab ICP-MS metals: sample x isotope x instrument run
# ----------------------------------------------------------------------------
ICPMS = SRC / "Static Loaded Preprocessed sorted 07272013ORNL+Batch 2 ZeroAvgOnlyORNL.xlsm"
T.update({"molecular weight": "ME:0000350", "presence": "ME:0000144", "helium(0)": "CHEBI:33681", "Adams Lab": "ENIGMA:0000030",
          "element Tc": "CHEBI:33353", "element Ru": "CHEBI:30682", "element Rh": "CHEBI:33359", "element Pd": "CHEBI:33363", "element Ag": "CHEBI:30512",
          "element Re": "CHEBI:49882", "element Ir": "CHEBI:49666", "element Pt": "CHEBI:33364", "element Au": "CHEBI:29287"})
UNLABELLED = {15, 33, 44}  # masses the workbook gives no element for: not stored


def build_metals(order, report):
    wb = openpyxl.load_workbook(ICPMS, data_only=True)
    runs = []
    for k in (1, 2, 3):
        raw = [list(r) for r in wb[f"Run {k} (ppb)"].iter_rows(values_only=True)]
        opt = [list(r) for r in wb[f"Run Optional {k}"].iter_rows(values_only=True)]
        if opt[4][0] != "Soil: Opt(g) + Dil Fac(g) -> ng/g(ppb) of dry soil" or raw[2][0] != "All Data (ppb)":
            raise ValueError(f"run {k}: sheet titles")
        def label(r):  # "FW305-05-24 :1" has a stray space
            return r[9].replace(" ", "")
        if [label(r) for r in raw[6:60]] != [f"{n}:{k}" for n in order] or [label(r) for r in opt[6:60]] != [f"{n}:{k}" for n in order]:
            raise ValueError(f"run {k}: sample order")
        if raw[:6] and [raw[i][11:79] for i in (1, 2, 5)] != [opt[i][11:79] for i in (1, 2, 5)]:
            raise ValueError(f"run {k}: column headers differ between the ppb and ng/g sheets")
        for a, b in zip(raw[6:60], opt[6:60]):  # ng/g = ppb x dilution factor / soil mass
            for j in range(12, 79):
                e = a[j] * a[1] / a[0]
                if abs(e - b[j]) > 1e-6 * max(1.0, abs(e)) or b[j] < 0:
                    raise ValueError(f"run {k} {a[9]} column {j}: {b[j]} is not ppb x dilution / mass")
        runs.append((raw, opt))
    head = runs[0][0]
    if any(r[0][i][11:79] != head[i][11:79] for r in runs for i in (0, 1, 2, 5)):
        raise ValueError("column headers differ between runs")
    cols = []
    for j in range(12, 79):
        mass, sym, label = int(head[1][j]), (head[2][j] or "").strip("()"), head[5][j]
        step = label.strip()[-5:]
        if step not in ("[ 1 ]", "[ 2 ]") or (head[0][j] == "Yes") != (step == "[ 1 ]"):
            raise ValueError(f"column {j}: gas mode and tune step disagree")
        if not sym:
            if mass not in UNLABELLED:
                raise ValueError(f"unlabelled mass {mass}")
            continue
        cols.append((j, f"element {sym}", mass, step == "[ 1 ]"))
    n = len(cols)
    conc, below = [], []
    for i in range(54):
        for j, _, _, _ in cols:
            for _, opt in runs:
                v = float(opt[6 + i][j]) / 1000.0  # ng/g -> mg/kg
                conc.append(None if v == 0 else v)
                below.append(v == 0)
    dates = sorted({str(r[6])[:10] for raw, _ in runs for r in raw[6:60]})
    masses = [float(r[0]) for r in runs[0][0][6:60]]
    if any([float(r[0]) for r in raw[6:60]] != masses for raw, _ in runs):
        raise ValueError("soil mass differs between runs")
    never = [f"{ab.NAMES[T[k]]} (mass {m})" for idx, (j, k, m, _) in enumerate(cols) if all(below[(i * n + idx) * 3 + r] for i in range(54) for r in range(3))]
    name = "adams_metals_fw305_core_2013"
    dims = [ab.sample_dim(order, [ab.typed("weight", "float", masses, "gram", [ctx("category", sval("dry sediment digested"))])]),
            ab.molecule_dim([k for _, k, _, _ in cols], [ab.typed("molecular weight", "float", [float(m) for _, _, m, _ in cols], "dalton"),
                                                         ab.typed("presence", "boolean", [g for _, _, _, g in cols], None, mol("helium(0)"))]),
            ab.replicate_dim(3, "technical replicate")]
    obj = ab.brick(
        name, f"Adams Lab ICP-MS element concentrations ({n} isotopes, three instrument runs) of the FW305 sediment core (2013)", "chemical measurement",
        [comment("Sediment core taken during the installation of well FW-305 (Oak Ridge FRC, Background A; well completed 2013-05-29), 54 sections from 0.5 to 26.08 ft "
                 "below ground surface. ICP-MS by the Adams Lab (University of Georgia), acquired " + dates[0] + " to " + dates[-1] + " (acquisition method 072613.m)"),
         comment("Each section's digest was read three times in succession (replicate 1 to 3); the values are the three readings, not an average. Concentrations are "
                 "mg of element per kg of dry soil: the Adams Lab template's ng/g values (instrument reading in ppb x dilution factor 499 / dry soil mass) divided "
                 "by 1000, the unit of the other Adams Lab sediment bricks. The dry soil mass of each section is on the sample dimension. The workbook does not "
                 "describe the digestion"),
         comment("Each entry of the molecule dimension is one monitored isotope of an element (molecular weight = isotope mass), read with or without collision gas "
                 "(presence of helium, as in the Adams Lab core pilot bricks; the workbook says only 'Gas Mode (ORS)'). Elements monitored at more than one isotope, "
                 "or in both gas modes, have several entries; each is that isotope's estimate of the element's concentration, and they can differ where an isotope "
                 "suffers interference (for example cadmium at masses 106 and 111)"),
         comment("A reading of zero in the workbook is stored as below detection (blank concentration, below = true). The workbook subtracts no blank and gives no "
                 "detection limits. Never above zero: " + ("; ".join(never) or "none")),
         comment("Not stored: three masses the workbook assigns to no element (15, all zero; 33; and 44, which follows calcium-43 at 2.1 to 2.8 times its value), the internal standards (Li, Sc, Y, In, Tb, Bi), and the workbook's averages, standard deviations and "
                 "'Dwayne' sheet, which derive from these readings"),
         comment("Source: ENIGMA Google Drive, Static Loaded Preprocessed sorted 07272013ORNL+Batch 2 ZeroAvgOnlyORNL.xlsm (sheets Run Optional 1 to 3)")],
        dims, [ab.float_var("concentration", "mg/kg", [], conc), ab.bool_var("below", ab.below_ctx(), below)])
    ab.write_brick(obj)
    write_process(ab.PROCESS_OUT / f"process_assay_geochemistry_fw305_core_metals_{STAMP}.tsv", [{
        "process": "Assay Geochemistry <PROCESS:0000005>", "person": "Adams Lab <ENIGMA:0000030>", "campaign": CAMPAIGN, "protocol": "null",
        "date_start": dates[0], "date_end": dates[-1], "input_objects": ", ".join(f"Sample: {x}" for x in order), "output_objects": f"Generic: {name}.hndarray"}])
    report += [f"## {name}", "", f"- {len(order)} samples x {n} isotopes x 3 runs = {len(conc)} cells; below detection (zero in the workbook): {sum(below)}",
               f"- never above zero: {'; '.join(never)}", "", "| element | mass | helium | median mg/kg | zero readings (of 162) |", "|---|---|---|---|---|"]
    import statistics
    for idx, (j, k, m, g) in enumerate(cols):
        vals = [conc[(i * n + idx) * 3 + r] for i in range(54) for r in range(3)]
        got = [v for v in vals if v is not None]
        report.append(f"| {ab.NAMES[T[k]]} | {m} | {g} | {statistics.median([v or 0 for v in vals]):.4g} | {len(vals) - len(got)} |")
    report.append("")


# ----------------------------------------------------------------------------
# FWB-306 core (2015): Chakraborty Lab pH, nitrate, organic carbon and freeze-dry moisture
# ----------------------------------------------------------------------------
SUMMARY = SRC / "1506_CoreSummary.xlsx"
T.update({"Chakraborty Lab": "ENIGMA:0000053", "Natural Organic Matter": "ENIGMA:0000027", "elemental carbon": "CHEBI:33415", "organic": "ME:0000346"})
NOM = "Natural Organic Matter <ENIGMA:0000027>"


def build_fw306(report):
    wb = openpyxl.load_workbook(SUMMARY, data_only=True)
    live = {r["sdt_sample_name"] for r in csv.DictReader(LIVE_SAMPLES.open(), delimiter="\t")}
    rows = [r for r in wb["FW306 summary"].iter_rows(values_only=True) if any(c is not None for c in r)]
    if tuple(rows[0][:15]) != ("Sample Id", "Sample depth (ft)", None, "pH", "stdev pH", None, "Nitrate (mg/kg)", "stdev", None, "Sulfate (mg/kg)", None, None, "Moisture%", None, "OC %"):
        raise ValueError(f"summary header {rows[0]}")
    if rows[7][3] != "from Alex" or rows[7][6] != "from Alex" or rows[7][9] != "from Sindhu" or rows[7][12] != "from Sindhu":
        raise ValueError("summary attribution row")
    data = {r[0].strip().replace("FWB-306-", "FWB306-"): r for r in rows[1:7]}
    if sorted(data) != [f"FWB306-0{i}" for i in range(2, 8)]:
        raise ValueError(f"summary samples {sorted(data)}")
    mrows = [r for r in wb["FW306 moisture"].iter_rows(values_only=True) if any(c is not None for c in r)]
    if tuple(mrows[0][:6]) != (None, "Bag /g", "Bag+Sediment (before freeze-dry) /g", "Bag+Sediment (after freeze-dry) /g", None, "Moisture %"):
        raise ValueError("moisture header")
    reps = {}
    for r in mrows[1:15]:
        calc = (r[2] - r[3]) / (r[2] - r[1]) * 100
        if abs(calc - r[5]) > 1e-6:
            raise ValueError(f"moisture of {r[0]} is not (before - after) / (before - bag)")
        reps.setdefault(f"FWB306-{r[0].split('-')[1]}", []).append(float(r[5]))
    samples = sorted(reps)
    if samples != [f"FWB306-0{i}" for i in range(1, 9)] or any(n not in live for n in samples) or any(len(v) > 2 for v in reps.values()):
        raise ValueError("moisture samples")

    def col(i, blank_zero=False):
        out = []
        for n in samples:
            v = None if n not in data else float(data[n][i])
            out.append(None if (blank_zero and n in data and float(data[n][6]) == 0) else v)
        return out

    nbelow = [None if n not in data else float(data[n][6]) == 0 for n in samples]
    one_of_three = [n for n in samples if n in data and data[n][6] > 0 and abs(data[n][7] / data[n][6] - 3 ** 0.5) < 1e-6]
    sdctx = lambda key, *extra: [ctx("measurement", oterm_value(key))] + list(extra)  # noqa: E731
    moist = lambda k: mol("water", ctx("physiochemical state", sval("in soil")), dict(ctx("replicate series", {"scalar_type": "int", "int_value": k}), value_units=ab.term("count unit")))  # noqa: E731
    name = "chakraborty_sediment_properties_fwb306_2015"
    obj = ab.brick(
        name, "Chakraborty Lab pH, nitrate, organic carbon and freeze-dry moisture of the FWB-306 sediment core (2015)", "chemical measurement",
        [comment("Depth intervals of the FWB-306 core collected 2015-06-10; workbook by Xiaoqin Wu (Chakraborty Lab, LBNL), 2015-08-24. pH, nitrate and organic carbon "
                 "cover FWB306-02 to FWB306-07 (3 to 18 ft); moisture covers all eight intervals"),
         comment("pH and nitrate were measured by Alex Aaring; the workbook gives only the mean and standard deviation of each. The standard deviations are consistent "
                 "with three replicates: where the nitrate standard deviation is exactly the square root of 3 times the mean (" + ", ".join(one_of_three) + "), one "
                 "replicate of three was above zero"),
         comment("Nitrate is mg per kg of sediment. The nitrate means include replicates read as zero. Nitrate of FWB306-06 is 0 with standard deviation 0 in the "
                 "workbook and is stored as below detection (blank concentration and standard deviation, below = true); the workbook gives no detection limit"),
         comment("Organic carbon is percent of the sediment. It is a separate measurement from the total organic carbon of the UGA soil test "
                 "(hazen_sediment_soil_properties_fwb306_2015)"),
         comment("Moisture is by freeze-drying: mass lost as percent of the wet sediment mass, (before - after) / (before - bag). FWB306-02 to FWB306-07 were weighed "
                 "as two portions (replicate 1 and replicate 2); FWB306-01 and FWB306-08 as one. These values are separate from, and do not agree with, the moisture of "
                 "the UGA soil test: FWB306-03 and FWB306-04 lost about 0.2 percent of their mass here, and the UGA test found 30 and 18 to 20 percent"),
         comment("Not stored: the workbook's sulfate and moisture summary columns, which are the UGA soil test values already in "
                 "hazen_sediment_extractable_fwb306_2015_v2 and hazen_sediment_soil_properties_fwb306_2015; and the bag and sediment weights"),
         comment("Source: ENIGMA Google Drive, 1506_CoreSummary.xlsx, sheets FW306 summary and FW306 moisture")],
        [ab.sample_dim(samples)],
        [ab.float_var("pH", "pH unit", [], col(3)),
         ab.float_var("standard deviation", "pH unit", sdctx("pH"), col(4)),
         ab.float_var("concentration", "mg/kg", mol("nitrate"), col(6, True)),
         ab.float_var("standard deviation", "mg/kg", sdctx("concentration", *mol("nitrate")), col(7, True)),
         ab.bool_var("below", ab.below_ctx(mol("nitrate")), nbelow),
         ab.float_var("concentration", "percent", mol("elemental carbon", ctx("organic", {"scalar_type": "boolean", "boolean_value": 1})), col(14)),
         ab.float_var("concentration", "percent", moist(1), [reps[n][0] for n in samples]),
         ab.float_var("concentration", "percent", moist(2), [reps[n][1] if len(reps[n]) > 1 else None for n in samples])])
    ab.write_brick(obj)
    write_process(ab.PROCESS_OUT / f"process_assay_geochemistry_fwb306_chakraborty_{STAMP}.tsv", [
        {"process": "Assay Geochemistry <PROCESS:0000005>", "person": "Chakraborty Lab <ENIGMA:0000053>", "campaign": NOM, "protocol": "null",
         "date_start": "2015-08-24", "date_end": "2015-08-24", "input_objects": ", ".join(f"Sample: {x}" for x in samples), "output_objects": f"Generic: {name}.hndarray"}])
    f = lambda v, d=2: "" if v is None else f"{v:.{d}f}"  # noqa: E731
    report += [f"## {name}", "", "| sample | pH | SD | nitrate mg/kg | SD | below | organic C % | moisture 1 % | moisture 2 % |", "|---|---|---|---|---|---|---|---|---|"]
    cols = [col(3), col(4), col(6, True), col(7, True), nbelow, col(14), [reps[n][0] for n in samples], [reps[n][1] if len(reps[n]) > 1 else None for n in samples]]
    for k, n in enumerate(samples):
        report.append(f"| {n} | {f(cols[0][k])} | {f(cols[1][k])} | {f(cols[2][k])} | {f(cols[3][k])} | {'' if cols[4][k] is None else str(cols[4][k]).lower()} | {f(cols[5][k], 3)} | {f(cols[6][k])} | {f(cols[7][k])} |")
    report.append("")


def main():
    oo.stage_validator()
    ab.load_ontology_names()
    if OUT.exists():
        raise FileExistsError(f"{OUT} exists; remove it to rebuild")
    ab.OUT = OUT
    ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT = (OUT / d for d in ("json", "static", "process", "check", "reports"))
    for d in (ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT):
        d.mkdir(parents=True)
    order, ic, depths = read_sources()
    report = ["# FW305 sediment core (2013): build report", ""]
    build_samples(order, depths, report)
    build_brick(order, ic, report)
    build_metals(order, report)
    build_fw306(report)
    (ab.REPORT_OUT / "build_report.md").write_text("\n".join(report) + "\n")
    bricks = ["elias_sediment_anions_iron_fw305_core_2013", "adams_metals_fw305_core_2013", "chakraborty_sediment_properties_fwb306_2015"]
    assays = [f"process_assay_geochemistry_fw305_core_anions_{STAMP}.tsv", f"process_assay_geochemistry_fw305_core_metals_{STAMP}.tsv",
              f"process_assay_geochemistry_fwb306_chakraborty_{STAMP}.tsv"]
    files = [f"static/Sample_additions_{STAMP}.tsv", f"process/process_sampling_fw305_core_{STAMP}.tsv"] + [f"json/{b}.json" for b in bricks] + [f"process/{f}" for f in assays]
    missing = [f for f in files if not (OUT / f).exists()]
    if missing:
        raise FileNotFoundError(missing)
    (OUT / "files_to_import.txt").write_text("\n".join(files) + "\n")
    lines = ["# Run on the CORAL hub, in order, after copying every file in files_to_import.txt to /home/coral/prod/data_import/data/ on coral-enigma.",
             f"toolx.update_core('Sample_additions_{STAMP}.tsv', 'Sample')", f"toolx.upload_process('Sampling', 'process_sampling_fw305_core_{STAMP}.tsv')"]
    lines += [f"toolx.upload_brick('{b}.json')" for b in bricks] + [f"toolx.upload_process('Assay Geochemistry', '{f}')" for f in assays]
    (OUT / "import_to_coral.py").write_text("\n".join(lines) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main()
