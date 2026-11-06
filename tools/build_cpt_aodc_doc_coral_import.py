#!/usr/bin/env python3
"""Build the CORAL import package for the 2020 CPT sediment lab data (IMPORT_PLAN gap item 8, first part).

* hazen_aodc_cpt_sediment_2020 / hazen_aodc_raw_cpt_sediment_2020: Hazen Lab acridine orange direct
  counts on 32 CPT sediment samples (cells per gram), laid out like the core-pilot sediment AODC
  bricks (Brick0000052, Brick0000055), with the four AODC micrographs as CORAL Images.
* chakraborty_doc_cpt_sediment_2020: Chakraborty Lab water-extractable DOC (Northen extraction) on
  30 CPT sediment samples, in ppm of the extract as reported.

All samples already exist in CORAL (Sampling processes of the Cone Penetrometer Survey).

    python tools/build_cpt_aodc_doc_coral_import.py
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import struct
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_sso_batch_ab_coral_import as ab  # noqa: E402
import build_sso_oneoff_16s_coral_import as oo  # noqa: E402
from build_sso_batch_ab_coral_import import T, comment, ctx, oterm_value, sval, typed, write_process  # noqa: E402

REPO = ab.REPO
CPT = ab.DRIVE / "2020_Cone Penetrometer Sampling"
AODC = CPT / "AODC 2020 CPT/CPT_sediments_AODC_04062021.xlsx"
DOC = CPT / "Chakraborty CPT DOC data/waterextract_TOC_Northenmethod.xlsx"
RELEASE = "20261030"
TAG = f"cpt_sediment_{RELEASE}"
OUT = REPO / f"coral_import/{TAG}"
EXPORT = REPO / "sync-coral-to-berdl/exports/sync-20261029-174321/coral_export/static_tsv"
CAMPAIGN = "Cone Penetrometer Survey <ENIGMA:0000165>"
SRC_RE = re.compile(r"CPT(\d+[A-D]?)SED-([A-Z]{2})-D?([A-C])?(\d+(?:\.\d+)?)$")
# Water-extract DOC depth typos: the CORAL sample (and the AODC sheet) give the other depth.
DOC_DEPTH_FIXES = {("10", "C"): (605, 305), ("63", "B"): (387.35, 382.35)}
IMAGE_FILES = {  # micrograph file -> source sample ID as written in the AODC sheet
    "CPT26SED-ZC-DB548.jpg": "CPT26SED-ZC-DB548", "CPT47SED-ZS-DA883.9.jpg": "CPT47SED-ZS-DA883.9",
    "CPT59SED-ZC-D294.jpg": "CPT59SED-ZC-DB294", "CPT73SED-ZC-DA548.jpg": "CPT73SED-ZC-DA548",
}

T.update({"Cone Penetrometer Survey": "ENIGMA:0000165", "Chakraborty Lab": "ENIGMA:0000053", "cells per gram": "ME:0000361",
          "subsample": "ME:0000289", "image ID": "ME:0000355", "elemental carbon": "CHEBI:33415", "organic": "ME:0000346",
          "ppm": "UO:0000169", "Terry Hazen": "ENIGMA:0000067"})


def coral_cpt_samples():
    out = {}
    for r in csv.DictReader((EXPORT / "Sample.tsv").open(), delimiter="\t"):
        m = SRC_RE.match(r["name"])
        if m and r["name"].startswith("CPT"):
            key = (m.group(1), m.group(3))
            if key in out:
                raise ValueError(f"two CORAL CPT samples for {key}")
            out[key] = {"name": r["name"], "depth_cm": float(r["depth"]) * 100, "name_cm": float(m.group(4))}
    return out


def match(samples, num, letter, depth_cm, what):
    s = samples.get((num, letter))
    if s is None:
        raise ValueError(f"{what}: no CORAL sample for CPT{num} {letter}")
    if min(abs(depth_cm - s["name_cm"]), abs(depth_cm - s["depth_cm"])) > 1.0:  # the name and depth of a few CORAL CPT samples disagree
        raise ValueError(f"{what}: depth {depth_cm} cm does not match {s['name']}")
    return s["name"]


def read_aodc(samples):
    wb = openpyxl.load_workbook(AODC, data_only=True)
    rows = list(wb.worksheets[0].iter_rows(values_only=True))
    if rows[11][1:8] != ("Sample ID", "grams", "Cells/ml", "Comments", "Total dilution (ml)", "CV %", "Mean Cells/Field"):
        raise ValueError(f"AODC header {rows[11][1:8]}")
    fields_per_filter = rows[8][3]
    recs = []
    for r in rows[12:]:
        if r[1] is None:
            break
        sid = str(r[1]).strip()
        m = SRC_RE.match(sid)
        if not m:
            raise ValueError(f"AODC sample {sid}")
        name = match(samples, m.group(1), m.group(3), float(m.group(4)), f"AODC {sid}")
        fields = [None if v is None else int(v) for v in r[8:18]]
        n = [v for v in fields if v is not None]
        mean = sum(n) / len(n)
        cells_g = mean * fields_per_filter / 1.0 / r[5]  # the sheet's formula: mean x fields per filter / mL filtered / g on the filter
        if abs(cells_g - r[3]) > 1e-6 * r[3] or abs(mean - r[7]) > 1e-9:
            raise ValueError(f"AODC {sid}: recomputed {cells_g} vs {r[3]}")
        recs.append({"src": sid, "name": name, "grams": float(r[2]), "on_filter_g": float(r[5]), "comment": str(r[4]).strip(),
                     "cells_g": float(r[3]), "cv": float(r[6]), "mean": float(r[7]), "fields": fields})
    if len(recs) != 32 or len({x["name"] for x in recs}) != 32:
        raise ValueError(f"{len(recs)} AODC samples")
    return recs, fields_per_filter


def read_doc(samples):
    rows = list(openpyxl.load_workbook(DOC, data_only=True).worksheets[0].iter_rows(values_only=True))
    if rows[0][4] != "DOC(ppm)" or rows[1][3:6] != ("Depth", "Average", "StdDev"):
        raise ValueError("DOC header")
    recs, fixes = [], []
    for r in rows[2:]:
        if r[0] is None:
            continue
        num, letter, depth = str(r[1]), (r[2] or None), float(r[3])
        if letter is None and num == "63":
            letter = "A"  # the unlabelled CPT63 row is the shallower (A) sample
        if (num, letter) in DOC_DEPTH_FIXES:
            bad, good = DOC_DEPTH_FIXES[(num, letter)]
            if depth != bad:
                raise ValueError(f"DOC CPT{num} {letter}: expected the typo {bad}, found {depth}")
            fixes.append(f"CPT{num} {letter} {bad:g} cm read as {good:g} cm")
            depth = good
        recs.append({"name": match(samples, num, letter, depth, f"DOC CPT{num} {letter}"), "mean": float(r[4]), "sd": float(r[5])})
    if len(recs) != 30 or len({x["name"] for x in recs}) != 30:
        raise ValueError(f"{len(recs)} DOC samples")
    return recs, fixes


def jpeg_size(path: Path):
    d = path.read_bytes()
    i = 2
    while i < len(d) and d[i] == 0xFF:
        marker, length = d[i + 1], struct.unpack(">H", d[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC2):
            h, w = struct.unpack(">HH", d[i + 5:i + 9])
            return w, h
        i += 2 + length
    raise ValueError(f"{path.name}: no JPEG frame header")


def main() -> None:
    oo.stage_validator()
    ab.load_ontology_names()
    if OUT.exists():
        raise FileExistsError(OUT)
    ab.OUT = OUT
    ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT = (OUT / d for d in ("json", "static", "process", "check", "reports"))
    for d in (ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT, OUT / "images"):
        d.mkdir(parents=True)
    samples = coral_cpt_samples()
    images_live = {r["name"] for r in csv.DictReader((EXPORT / "Image.tsv").open(), delimiter="\t")}

    # ---------------- AODC
    recs, fpf = read_aodc(samples)
    by_src = {r["src"]: r for r in recs}
    image_rows, image_of = [], {}
    for fname, src in IMAGE_FILES.items():
        r = by_src[src]
        iname = f"{r['name']}-aodc.jpg"
        if iname in images_live:
            raise ValueError(f"{iname} already in CORAL")
        p = AODC.parent / fname
        w, h = jpeg_size(p)
        shutil.copyfile(p, OUT / "images" / iname)
        image_rows.append([iname, f"{r['name']} AODC image", "image/jpeg", str(p.stat().st_size), f"{w},{h}", f"/images/{iname}"])
        image_of[r["name"]] = iname
    recs.sort(key=lambda r: r["name"])
    names = [r["name"] for r in recs]
    sample_extra = [
        typed("weight", "float", [r["grams"] for r in recs], "gram", [ctx("category", oterm_value("subsample"))]),
        typed("weight", "float", [r["on_filter_g"] for r in recs], "gram", [ctx("category", sval("filtered"))]),
        {"value_type": ab.term("image ID"), "values": {"scalar_type": "object_ref", "object_refs": [image_of.get(n) for n in names],
                                                       "string_values": [image_of.get(n) for n in names]}},
    ]
    common = [ctx("ENIGMA campaign", oterm_value("Cone Penetrometer Survey")), ctx("personnel", oterm_value("Terry Hazen"))]
    aodc_ctx = common + [
        comment("Microscope ID 3335000410"),
        ctx("instrument", sval("Objective Lens 100X N-Achroplan Oil")),
        ctx("method", sval(f"Acridine orange direct counts (Hazen UTK lab book UTK-001): 1 g sediment in 10 mL solution, 1 mL membrane filtered onto a 25 mm filter "
                           f"(0.1 of the sediment mass), 10X ocular, {fpf:,.0f} fields per filter; cells per gram = mean cells per field x fields per filter / grams on the filter. "
                           "Fields counted: 10, or 5 when the CV is under 50% and the mean exceeds 10 cells per field; slides prepared by D. C. Joyner, counted by T. C. Hazen")),
        comment("The sheet heads the result column Cells/ml, but its formula divides by the grams of sediment on the filter, so the values are cells per gram of sediment"),
        comment("Sample weights: subsample = sediment weighed into the dilution; filtered = the share of it on the filter. Four samples have a micrograph (CORAL Image)"),
        comment(f"Source: {ab.DRIVE_LABEL} {AODC.relative_to(ab.DRIVE)}, sheet Sheet1 (sample IDs written with unrounded depths, matched to the CORAL samples)"),
    ]
    cell = [ctx("category", oterm_value("cell"))]
    processed = ab.brick("hazen_aodc_cpt_sediment_2020", "Hazen Lab acridine orange direct counts (cells per gram) on 2020 CPT sediment samples", "microbial abundance",
                         aodc_ctx, [ab.sample_dim(names, sample_extra)], [
                             ab.float_var("count", "cells per gram", cell, [r["cells_g"] for r in recs]),
                             ab.float_var("coefficient of variation", "percent", [ctx("measurement", oterm_value("count"))], [r["cv"] for r in recs]),
                             ab.float_var("average", "cells per well", [ctx("measurement", oterm_value("count"))], [r["mean"] for r in recs])])
    raw = ab.brick("hazen_aodc_raw_cpt_sediment_2020", "Hazen Lab acridine orange direct counts, raw field counts, on 2020 CPT sediment samples", "microbial abundance",
                   aodc_ctx, [ab.sample_dim(names, sample_extra), ab.replicate_dim(10)],
                   [typed("count", "int", [v for r in recs for v in r["fields"]], "cells per well", cell)])
    # one measured variable: the raw brick has no data-variables marker
    raw["array_context"] = [c for c in raw["array_context"] if c["value_type"]["oterm_ref"] != T["data variables type"]]
    raw["name"] = raw["name"].replace(".hndarray", ".ndarray")
    for o in (processed, raw):
        ab.write_brick(o) if o["name"].endswith(".hndarray") else oo.write_brick(o)

    # ---------------- DOC
    doc, fixes = read_doc(samples)
    doc.sort(key=lambda r: r["name"])
    carbon = [ctx("molecule from list", oterm_value("elemental carbon")), ctx("physiochemical state", sval("dissolved")),
              ctx("organic", {"scalar_type": "boolean", "boolean_value": 1})]
    doc_brick = ab.brick("chakraborty_doc_cpt_sediment_2020", "Chakraborty Lab water-extractable dissolved organic carbon (ppm in the extract) of 2020 CPT sediment samples",
                         "chemical measurement",
                         [ctx("ENIGMA campaign", oterm_value("Cone Penetrometer Survey")), ctx("personnel", oterm_value("Chakraborty Lab")),
                          ctx("method", sval("Water extraction (Northen Lab method): core segments stored at -80 C were thawed at 4 C overnight; 1 g sediment was incubated 1 h at 4 C with "
                                             "4 mL HPLC-grade water in 5 mL conical tubes at about 30 degrees on a thermal shaker at 1400 rpm, centrifuged (5000 x g, 5 min) and the "
                                             "supernatant 0.22 um filtered; TOC of the extract was measured as DOC")),
                          comment("Values are the lab's mean and standard deviation in ppm of the water extract, as reported (1 g sediment per 4 mL water); the number of replicates is not given"),
                          comment("Depths in the sheet are those reported by the Hazen Lab at sample distribution (fall 2020). Two are typos and were matched by the CORAL and AODC depth: "
                                  + "; ".join(fixes)),
                          comment(f"Source: {ab.DRIVE_LABEL} {DOC.relative_to(ab.DRIVE)} and README.docx")],
                         [ab.sample_dim([r["name"] for r in doc])],
                         [ab.float_var("concentration", "ppm", carbon, [r["mean"] for r in doc]),
                          ab.float_var("standard deviation", "ppm", [ctx("measurement", oterm_value("concentration"))], [r["sd"] for r in doc])])
    ab.write_brick(doc_brick)

    # ---------------- static, process and import files
    with (ab.STATIC_OUT / f"Image_additions_{TAG}.tsv").open("w", newline="") as h:
        w = csv.writer(h, delimiter="\t", lineterminator="\n")
        w.writerow(["name", "description", "MIME type", "size", "dimensions", "link"])
        w.writerows(sorted(image_rows))
    write_process(ab.PROCESS_OUT / f"process_assay_cell_counts_{TAG}.tsv", [
        {"process": "Assay Cell Counts <PROCESS:0000008>", "person": "Terry Hazen <ENIGMA:0000067>", "campaign": CAMPAIGN, "protocol": "null",
         "date_start": "2021-04-06", "date_end": "2021-04-06", "input_objects": ", ".join(f"Sample: {n}" for n in names),
         "output_objects": f"Generic: {processed['name']}, Generic: {raw['name']}"}])
    write_process(ab.PROCESS_OUT / f"process_image_{TAG}.tsv", [  # provenance of each micrograph, as the Walian isolate images have
        {"process": "Image <PROCESS:0000047>", "person": "Hazen Lab <ENIGMA:0000066>", "campaign": CAMPAIGN, "protocol": "null",
         "date_start": "2021-04-06", "date_end": "2021-04-06", "input_objects": f"Sample: {r['name']}", "output_objects": f"Image: {image_of[r['name']]}"}
        for r in recs if r["name"] in image_of])
    write_process(ab.PROCESS_OUT / f"process_assay_geochemistry_{TAG}.tsv", [
        {"process": "Assay Geochemistry <PROCESS:0000005>", "person": "Chakraborty Lab <ENIGMA:0000053>", "campaign": CAMPAIGN, "protocol": "null",
         "date_start": "2021-11-09", "date_end": "2021-11-09", "input_objects": ", ".join(f"Sample: {r['name']}" for r in doc),
         "output_objects": f"Generic: {doc_brick['name']}"}])
    jsons = [o["name"].rsplit(".", 1)[0] + ".json" for o in (processed, raw, doc_brick)]
    files = [f"static/Image_additions_{TAG}.tsv"] + [f"json/{j}" for j in jsons] + [f"process/process_assay_cell_counts_{TAG}.tsv", f"process/process_assay_geochemistry_{TAG}.tsv", f"process/process_image_{TAG}.tsv"]
    (OUT / "files_to_import.txt").write_text("\n".join(files) + "\n")
    (OUT / "images_to_install.txt").write_text("\n".join(f"images/{r[0]}" for r in sorted(image_rows)) + "\n")
    (OUT / "import_to_coral.py").write_text("\n".join(
        ["# Stage files_to_import.txt in data_import/data and images_to_install.txt in data_store/images first", "",
         f"toolx.update_core('Image_additions_{TAG}.tsv', 'Image')"] + [f"toolx.upload_brick('{j}')" for j in jsons]
        + [f"toolx.upload_process('Assay Cell Counts', 'process_assay_cell_counts_{TAG}.tsv')",
           f"toolx.upload_process('Assay Geochemistry', 'process_assay_geochemistry_{TAG}.tsv')",
           f"toolx.upload_process('Image', 'process_image_{TAG}.tsv')", ""]))
    summary = {"release": RELEASE, "aodc_samples": len(recs), "doc_samples": len(doc), "images": [r[0] for r in sorted(image_rows)], "doc_depth_fixes": fixes,
               "bricks": [processed["name"], raw["name"], doc_brick["name"]]}
    (ab.REPORT_OUT / "build_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (OUT / "README.md").write_text(
        f"# 2020 CPT sediment AODC and water-extractable DOC, {RELEASE}\n\nBuilt by `tools/build_cpt_aodc_doc_coral_import.py` (regenerates this file).\n\n"
        f"- `{processed['name']}` [{len(recs)} samples]: cells per gram, CV, mean per field; sample weights; image ID for 4 samples\n"
        f"- `{raw['name']}` [{len(recs)} samples x 10 fields]: raw counts per field\n"
        f"- `{doc_brick['name']}` [{len(doc)} samples]: DOC mean and SD, ppm in the water extract\n"
        f"- 4 Images (`images/`, link `/images/<name>`): copy into coral-enigma `/home/coral/prod/data_store/images/` and into the EDR\n\n"
        "All samples already exist in CORAL. DOC depth typos: " + "; ".join(fixes) + ".\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
