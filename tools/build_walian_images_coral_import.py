#!/usr/bin/env python3
"""Build the CORAL import package for three Walian Lab image sets and the Spring 2019 groundwater EM tallies.

* CPT sediment TEM (2021): 11 JPEGs in `2020_Cone Penetrometer Sampling/CPT EM imaging/`, named by push and
  core letter, each mapped to a CORAL CPT sediment sample. Peter Walian's readme and deck give the method.
* Pilot-core micro-CT (ALS beamline 8.3.2, 2017-05-17): the 14 tomopy reconstructions delivered by Peter
  Walian in December 2019 (~/data/enigma/walian/microCT, 2,160 float32 slices of 2560 x 2560 each): one Image
  object per reconstruction (a directory in the EDR) plus the 10 slices he selected for the team Drive.
* Spring 2019 groundwater EM (Walian/Hazen R11 samples): the 51 morphotype crops in
  `ENIGMA_Imaging/Images_Groundwater/` whose file names carry a well and a field date, mapped to the R11
  sample of that well and timepoint (MLS field dates 3/18 and 4/15 are the 03-19 and 04-16 sampling days of
  the master sheet), plus three `MLS B6 ... 3 15 23` crops of the one-off MLSB6-2022-10-24-UF sample. Method
  trials (FW215/FW213 2018 grids, "UMB search/revisit" grids) are not loaded.
* Brick `walian_em_groundwater_counts_spring2019`: Peter Walian's "GW imaging stats.xlsx" (e-mail of
  2020-04-17): average microbes per EM grid window, all microbes and by category (large cells, ultra-small
  cells, phage), for GW821E, MLSB5 and FW100-20 at the five Spring 2019 timepoints.

Static additions: Samples MLSB5-2019-04-16/04-30/05-14-UF-R11 (EM bottles the master sheet omits; Peter's
stats cover all five MLS timepoints), three Protocols, 76 Images.

Run with the BERIL venv python (openpyxl, Pillow):
    python tools/build_walian_images_coral_import.py
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_sso_batch_ab_coral_import as ab  # noqa: E402
from build_sso_batch_ab_coral_import import T, brick, comment, ctx, float_var, oterm_value, sval, typed, write_process  # noqa: E402

REPO = ab.REPO
TEAM = ab.DRIVE
RELEASE = "20261106"
TAG = f"walian_images_{RELEASE}"
OUT = REPO / f"coral_import/{TAG}"
EXPORT = REPO / "sync-coral-to-berdl/exports/sync-20261105-153237/coral_export/static_tsv"
STAGED = Path("/tmp/claude-1000/-scratch-jmc-BERDL-ENIGMA-CORAL/e08931f7-7c7d-4424-a1ff-a5f1bad88ee0/scratchpad/stagedval")
EDR_IMAGES = Path("/mnt/net/dipa.jmcnet/data/edr/images")
TEM_DIR = TEAM / "2020_Cone Penetrometer Sampling/CPT EM imaging"
MICROCT_LOCAL = Path.home() / "data/enigma/walian/microCT"
MICROCT_DRIVE = TEAM / "2017_Pilot Sediment Campaign/PilotSediment micro-CT imaging/FW106 selected microCT images"
GW_DIR = TEAM / "ENIGMA_Imaging/Images_Groundwater"
GW_STATS = REPO / f"coral_import/{TAG}/source/GW_imaging_stats.xlsx"  # copied from the scratchpad by main()
GW_STATS_SRC = Path("/tmp/claude-1000/-scratch-jmc-BERDL-ENIGMA-CORAL/e08931f7-7c7d-4424-a1ff-a5f1bad88ee0/scratchpad/images2/GW_imaging_stats.xlsx")
WALIAN = "Walian Lab <ENIGMA:0000152>"
CAMPAIGN_CPT = "Cone Penetrometer Survey <ENIGMA:0000165>"
CAMPAIGN_PILOT = "Core Pilot <ENIGMA:0000021>"
CAMPAIGN_SPRING = "Spring 2019 Integrated Sampling <ENIGMA:0000100>"
CAMPAIGN_ATLAS = "Environmental Atlas <ENIGMA:0000167>"
PROTO_TEM = "walian-tem-cpt-sediment-wash-2021"
PROTO_CT = "walian-als-832-microct-pilot-core-2017"
PROTO_GW = "walian-tem-groundwater-spring-2019"
T.update({"microbial abundance": "DA:0000018", "Walian Lab": "ENIGMA:0000152", "Spring 2019 Integrated Sampling": "ENIGMA:0000100"})

# CPT TEM: file stem -> CORAL sample (push number + core letter of the sediment core sample names)
TEM_SAMPLES = {"CPT 10A": "CPT10SED-ZU-DA244", "CPT 19B": "CPT19SED-ZC-DB411", "CPT 21C": "CPT21SED-ZC-DC366",
               "CPT 26C": "CPT26SED-ZC-DC579", "CPT 52B": "CPT52SED-ZC-DB324", "CPT 63A": "CPT63SED-ZC-DA366",
               "CPT 63Ba": "CPT63SED-ZS-DB382", "CPT 63Bb": "CPT63SED-ZS-DB382", "CPT 65B": "CPT65SED-ZC-DB409",
               "CPT 69B": "CPT69SED-ZS-DB579", "SED 15B": "CPT15SED-ZC-DB366"}
TEM_NOTES = {  # Peter Walian's slide notes (CPT EM imaging.pptx) by push
    "CPT10": "NW zone, push 10A (~8 ft, vadose, nearly dry): few cells observed; sediment-associated prosthecate cell",
    "CPT15": "NW zone, push 15B (~12 ft, variably saturated, wet clay); AODC 0.4-1.4 x 10^6 cells/mL in the zone",
    "CPT21": "Mid-NW zone, push 21C (~12 ft, variably saturated, moist): most cells observed of all pushes; S-layer microbes predominant",
    "CPT26": "Mid-NW zone, push 26C (~19 ft, variably saturated, wet clay, rocks): highest uranium and nitrate; cell damage from the stronger extraction",
    "CPT52": "Mid-SE zone, push 52B (~10.5 ft, variably saturated): fewest cells of any zone; AODC 0.2-0.3 x 10^6 cells/mL",
    "CPT63": "SE zone, push 63 (~13 ft, variably saturated, clay): few cells; putative Rhodanobacter",
    "CPT65": "SE zone, push 65B (~13 ft, variably saturated): few cells; AODC 0.2-0.6 x 10^6 cells/mL",
}  # pushes 19B and 69B are not described in the deck
TEM_DATE = "2021-05-29"  # the JPEGs carry no EXIF; this is their date on the team Drive (the deck is from August 2021)

# micro-CT: reconstruction folder -> CORAL sample, and the 10 slices Peter Walian put on the Drive
CT_SAMPLE = {"106-4-5": "EB106-04-05", "106-5-5": "EB106-05-05", "106-6-3": "EB106-06-03", "106-6-5": "EB106-06-05",
             "106-7-6": "EB106-07-06", "106-8-5": "EB106-08-05", "106-9-4": "EB106-09-04", "106-10-1": "EB106-10-01",
             "271-2-2": "EB271-02-02", "271-3-3": "EB271-03-03", "271-4-1": "EB271-04-01", "271-4-4": "EB271-04-04",
             "271-5-1": "EB271-05-01", "271-5-2": "EB271-05-02"}
CT_DATE = "2017-05-17"
CT_PIXEL_UM = 0.638  # the 6.38e-05 cm scale applied in every reconstruction script

# groundwater EM
GW_WELLS = {"GW821": "GW821E", "821": "GW821E", "MLS": "MLSB5", "FW100": "FW100-20", "Area 3": "FW100-20"}
GW_DATE_ADJ = {("MLSB5", 4, 15): (4, 16), ("MLSB5", 3, 18): (3, 19)}  # field label vs master-sheet sampling day
NEW_R11 = ["MLSB5-2019-04-16-UF-R11", "MLSB5-2019-04-30-UF-R11", "MLSB5-2019-05-14-UF-R11"]
MLSB6 = "MLSB6-2022-10-24-UF"
GW_CATEGORIES = ["microbes", "large cells", "ultra-small cells", "phage"]
AODC_DIR = TEAM / "2019_Spring_Integrated Sampling/Hazen Lab/AODC"
HAZEN = "Hazen Lab <ENIGMA:0000066>"


def rel(p: Path) -> str:
    return f"ENIGMA team Google Drive {p.relative_to(TEAM)}"


def stage_validator() -> None:
    ab.ONTOLOGIES = STAGED / "names"
    cp = (STAGED / "classpath.txt").read_text().strip()

    def run(json_path):
        proc = subprocess.run(["java", "-Xmx8g", "-cp", cp, "gov.lbl.enigma.app.CheckGenericStaged", str(json_path)], capture_output=True, text=True)
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0 and "Generic is OK!" in out, out
    ab.run_checkgeneric = run


def image_row(name, description, path: Path, dims=None, mime=None, size=None):
    if dims is None:
        with Image.open(path) as im:
            dims = f"{im.size[0]},{im.size[1]}"
    return {"name": name, "description": description, "MIME type": mime or ("image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/tiff"),
            "size": size if size is not None else path.stat().st_size, "dimensions": dims, "link": f"/images/{name}"}


def manifest_row(path, name, lab, subject, technique, mime, size, source, original, objects):
    return {"path": path, "coral_image_name": name, "lab": lab, "subject": subject, "technique": technique, "mime_type": mime,
            "size_bytes": size, "source_drive_path": source, "original_name": original, "coral_objects": objects, "status": "pending"}


# ----------------------------------------------------------------------------

def build_tem(samples: set[str]):
    images, procs, manifest, copies = [], [], [], []
    per_sample = Counter(TEM_SAMPLES.values())
    seq = Counter()
    for stem, sample in TEM_SAMPLES.items():
        src = TEM_DIR / f"{stem}.jpg"
        if not src.is_file() or sample not in samples:
            raise FileNotFoundError(f"{src} or sample {sample}")
        seq[sample] += 1
        name = f"{sample}-tem.jpg" if per_sample[sample] == 1 else f"{sample}-tem-{seq[sample]}.jpg"
        note = TEM_NOTES.get(re.match(r"CPT\d+", sample).group(0))
        images.append(image_row(name, f"{sample} TEM image of a sediment wash (Walian Lab, from '{stem}.jpg')" + (f": {note}" if note else ""), src))
        procs.append({"process": "Image <PROCESS:0000047>", "person": WALIAN, "campaign": CAMPAIGN_CPT, "protocol": PROTO_TEM,
                      "date_start": TEM_DATE, "date_end": TEM_DATE, "input_objects": f"Sample: {sample}", "output_objects": f"Image: {name}"})
        manifest.append(manifest_row(f"walian_sediment_em/{name}", name, "walian", "sediment", "em", "image/jpeg", src.stat().st_size,
                                     str(TEM_DIR.relative_to(TEAM)) + "/", src.name, f"Sample:{sample}"))
        copies.append((src, EDR_IMAGES / "walian_sediment_em" / name))
    return images, procs, manifest, copies


def build_microct(samples: set[str]):
    images, procs, manifest, copies = [], [], [], []
    recon_dirs = sorted(p for p in MICROCT_LOCAL.glob("RECON_20170517_*_ORNL_pilot_*") if p.is_dir())
    if len(recon_dirs) != 14:
        raise ValueError(f"expected 14 reconstructions, found {len(recon_dirs)}")
    selected = {p.name: p for p in MICROCT_DRIVE.glob("*.tiff")}
    if len(selected) != 10:
        raise ValueError(f"expected 10 selected slices on the Drive, found {len(selected)}")
    for d in recon_dirs:
        key = d.name.split("_ORNL_pilot_")[1]
        sample = CT_SAMPLE[key]
        if sample not in samples:
            raise ValueError(f"no CORAL sample {sample}")
        tiffs = sorted(p for p in d.glob("*.tiff"))
        if len(tiffs) != 2160:
            raise ValueError(f"{d.name}: {len(tiffs)} slices")
        total = sum(p.stat().st_size for p in tiffs) + sum(p.stat().st_size for p in d.glob("*.py")) + sum(p.stat().st_size for p in d.glob("*.yml"))
        stack = f"{sample}-microct-recon"
        images.append({"name": stack, "description": f"{sample} X-ray micro-CT reconstruction (ALS beamline 8.3.2, tomopy gridrec, {CT_DATE}): "
                       f"directory of 2,160 float32 TIFF slices of 2560 x 2560 pixels at {CT_PIXEL_UM} um/pixel, with the reconstruction script and "
                       f"parameters; original folder {d.name}", "MIME type": "image/tiff", "size": total, "dimensions": "2560,2560,2160",
                       "link": f"/images/{stack}/"})
        procs.append({"process": "Image <PROCESS:0000047>", "person": WALIAN, "campaign": CAMPAIGN_PILOT, "protocol": PROTO_CT,
                      "date_start": CT_DATE, "date_end": CT_DATE, "input_objects": f"Sample: {sample}", "output_objects": f"Image: {stack}"})
        manifest.append(manifest_row(f"walian_sediment_microct/{d.name}/", stack, "walian", "sediment", "microct", "image/tiff", total,
                                     "~/data/enigma/walian/microCT (HDD from Peter Walian, Dec 2019); subset on the team Drive 2017_Pilot Sediment Campaign/PilotSediment micro-CT imaging/",
                                     d.name, f"Sample:{sample}"))
        for p in tiffs:
            if p.name in selected:
                local = p
                drive = selected[p.name]
                if local.stat().st_size != drive.stat().st_size:
                    raise ValueError(f"{p.name}: Drive and local copies differ in size")
                idx = p.stem.rsplit("_", 1)[1]
                name = f"{sample}-microct-{idx}.tiff"
                images.append(image_row(name, f"{sample} X-ray micro-CT reconstruction slice {int(idx)} of 2160 (ALS beamline 8.3.2, {CT_PIXEL_UM} um/pixel, "
                                        f"float32 linear attenuation), one of the ten slices selected for the team Drive; file {p.name} in {stack}", p, mime="image/tiff"))
                procs.append({"process": "Image <PROCESS:0000047>", "person": WALIAN, "campaign": CAMPAIGN_PILOT, "protocol": PROTO_CT,
                              "date_start": CT_DATE, "date_end": CT_DATE, "input_objects": f"Sample: {sample}", "output_objects": f"Image: {name}"})
                manifest.append(manifest_row(f"walian_sediment_microct/{d.name}/{p.name}", name, "walian", "sediment", "microct", "image/tiff", p.stat().st_size,
                                             str(MICROCT_DRIVE.relative_to(TEAM)) + "/", p.name, f"Sample:{sample}"))
                copies.append((p, None))  # installed on the hub from the EDR stack folder (see images_to_install.txt); no extra EDR copy
    return images, procs, manifest, copies, [d.name for d in recon_dirs]


def gw_sample_for(stem: str, r11: set[str]):
    if re.search(r"\bB6\b.*\b3 15 23\b", stem):
        return MLSB6
    if "UMB" in stem:
        return None
    m = re.search(r"(GW821|^821|MLS|FW100|Area 3)\b.*?\b(\d{1,2}) (\d{1,2})\b(?! \d{2}\b)", stem)
    if not m:
        return None
    well = GW_WELLS[m.group(1)]
    mo, dy = GW_DATE_ADJ.get((well, int(m.group(2)), int(m.group(3))), (int(m.group(2)), int(m.group(3))))
    cand = [s for s in r11 if s.startswith("%s-2019-%02d-%02d" % (well, mo, dy))]
    return cand[0] if cand else None


def build_groundwater(samples: set[str], sample_rows: dict):
    r11 = {s for s in samples | set(NEW_R11) if s.endswith("-R11") and re.match(r"(GW821E|MLSB5|FW100-20)-2019", s)}
    files = []
    for d, _, fs in os.walk(GW_DIR):
        for f in fs:
            if f.lower().endswith(".tif"):
                files.append(Path(d) / f)
    mapped, skipped = [], []
    for p in sorted(files, key=lambda x: (x.parent.name, x.name)):
        stem = re.sub(r"\s*\d{4}\s*\.tif$", "", p.name, flags=re.I)
        s = gw_sample_for(stem, r11)
        (mapped if s else skipped).append((p, stem, s))
    if len(mapped) != 51 or len(skipped) != 122:
        raise ValueError(f"groundwater mapping changed: {len(mapped)} mapped, {len(skipped)} skipped")
    images, procs, manifest, copies = [], [], [], []
    seq = Counter()
    for p, stem, s in mapped:
        seq[s] += 1
        name = f"{s}-em-{seq[s]:02d}.tif"
        morph = p.parent.name
        with Image.open(p) as im:
            dims = f"{im.size[0]},{im.size[1]}"
            tag_date = im.tag_v2.get(306) if hasattr(im, "tag_v2") else None
        if s == MLSB6:
            date, campaign = "2023-03-15", CAMPAIGN_ATLAS
        else:
            date, campaign = sample_rows[s]["date"] if s in sample_rows else s.split("-UF")[0][-10:], CAMPAIGN_SPRING
        treat = re.sub(r"^(GW821|821|MLS|FW100|Area 3)\s*(B6 Pos GD )?\s*\d{1,2} \d{1,2}( \d{2})?\s*", "", stem).strip()
        desc = f"{s} TEM morphotype crop, Walian Lab atlas folder '{morph}' (from '{p.name}'" + (f", grid '{treat}'" if treat else "") + ")"
        images.append(image_row(name, desc, p, dims=dims, mime="image/tiff"))
        procs.append({"process": "Image <PROCESS:0000047>", "person": WALIAN, "campaign": campaign, "protocol": PROTO_GW,
                      "date_start": date, "date_end": date, "input_objects": f"Sample: {s}", "output_objects": f"Image: {name}"})
        manifest.append(manifest_row(f"walian_groundwater_em/{name}", name, "walian", "groundwater", "em", "image/tiff", p.stat().st_size,
                                     f"ENIGMA_Imaging/Images_Groundwater/{morph}/", p.name, f"Sample:{s}"))
        copies.append((p, EDR_IMAGES / "walian_groundwater_em" / name))
    return images, procs, manifest, copies, [(p.name, p.parent.name) for p, _, _ in skipped]


def read_gw_stats():
    ws = openpyxl.load_workbook(GW_STATS, read_only=True, data_only=True)["Sheet1"]
    rows = [tuple(r) + (None,) * 20 for r in ws.iter_rows(values_only=True)]
    if rows[1][1] != "GW821" or rows[1][6] != "MLS" or rows[1][11] != "Area3 FW100":
        raise ValueError("stats sheet layout changed")
    dates = {"GW821E": ["2019-03-18", "2019-04-01", "2019-04-15", "2019-04-29", "2019-05-13"],
             "MLSB5": ["2019-03-19", "2019-04-02", "2019-04-16", "2019-04-30", "2019-05-14"],
             "FW100-20": ["2019-03-20", "2019-04-03", "2019-04-17", "2019-05-01", "2019-05-15"]}
    for i in range(5):  # the sheet's own dates for GW821 and MLS
        if rows[3 + i][1].strftime("%Y-%m-%d") != dates["GW821E"][i] or rows[3 + i][6].strftime("%Y-%m-%d") != dates["MLSB5"][i]:
            raise ValueError("stats sheet dates differ from the sampling dates")
    blocks = {"microbes": (3, {"GW821E": 3, "MLSB5": 8, "FW100-20": 12}),
              "large cells": (30, {"GW821E": 2, "MLSB5": 7, "FW100-20": 12}),
              "ultra-small cells": (39, {"GW821E": 2, "MLSB5": 7, "FW100-20": 12}),
              "phage": (48, {"GW821E": 2, "MLSB5": 7, "FW100-20": 12})}
    for label, r0 in (("large cells", 28), ("UMBs", 37), ("Phage", 46)):
        if rows[r0][1] != label:
            raise ValueError(f"block {label} not at row {r0}")
    values = {}  # (sample, category) -> float
    for cat, (r0, cols) in blocks.items():
        for well, col in cols.items():
            for i in range(5):
                v = rows[r0 + i][col]
                values[(f"{well}-{dates[well][i]}-UF-R11", cat)] = float(v)
    return values, dates


def build_gw_brick(values, dates):
    samples = [f"{w}-{d}-UF-R11" for w in ("GW821E", "MLSB5", "FW100-20") for d in dates[w]]
    data = [values[(s, c)] for s in samples for c in GW_CATEGORIES]
    dims = [ab.sample_dim(samples),
            {"data_type": ab.term("category"), "size": len(GW_CATEGORIES), "typed_values": [typed("category", "string", GW_CATEGORIES, None, [])]}]
    variables = [float_var("average", "count unit", [ctx("measurement", oterm_value("count")), ctx("relative", sval("EM grid window"))], data)]
    array_context = [
        ctx("ENIGMA campaign", oterm_value("Spring 2019 Integrated Sampling")), ctx("personnel", oterm_value("Walian Lab")),
        comment("Source: 'GW imaging stats.xlsx', sent by Peter Walian to John-Marc Chandonia on 2020-04-17 (copy in the package's source/ folder), "
                "described by him as the average number of microbes per EM grid window observed in groundwater from three wells over the five Spring 2019 "
                "timepoints; the raw observation tallies are in a student lab notebook at Donner"),
        comment("Category 'microbes' is the sheet's unlabelled upper table (columns headed only GW821, MLS and 'Area3 FW100'); it is not the sum of the "
                "other categories (for GW821E it is below 'large cells' alone). 'large cells', 'ultra-small cells' and 'phage' are the three tables headed "
                "'Valerie results (entries below are average observations per EM grid window for each of the 5 sampling dates)', labelled 'large cells', "
                "'UMBs' and 'Phage'; the FW100 column of the large-cells table carries the remark 'small large!'"),
        comment("Samples are the Walian/Hazen R11 EM bottles of the master field sheet (the three MLSB5 R11 samples of 04-16, 04-30 and 05-14 are added "
                "with this package); FW100-20 dates follow the sampling days of that well"),
    ]
    obj = brick("walian_em_groundwater_counts_spring2019",
                "Walian Lab transmission electron microscopy tallies of groundwater from GW821E, MLSB5 and FW100-20 at the five Spring 2019 Integrated Sampling "
                "timepoints: average observations per EM grid window of microbes, large cells, ultra-small cells and phage",
                "microbial abundance", array_context, dims, variables)
    return obj, samples


def aodc_sample_name(sheet_id: str) -> str:
    """'GW-821-E_041519_6' -> GW821E-2019-04-15-UF-R6; 'MLSB5_041619_6' -> MLSB5-2019-04-16-UF-R6; 'FW100-20_032019_6' -> FW100-20-2019-03-20-UF-R6."""
    well, mmddyy, r = sheet_id.split("_")
    well = well.replace("GW-", "GW").replace("-E", "E").replace("-D", "D")
    return f"{well}-20{mmddyy[4:6]}-{mmddyy[0:2]}-{mmddyy[2:4]}-UF-R{r}"


def read_aodc_numbers():
    """Sample number -> sheet sample ID from the two Hazen AODC workbooks (the upload workbook numbers 1-36, the final-timepoint one the rest)."""
    out = {}
    for fn in ("AODC_Active Sampling 2019_upload.xlsx", "AODC_Active Sampling 2019_final timepoint.xlsx"):
        ws = openpyxl.load_workbook(AODC_DIR / fn, read_only=True, data_only=True)["Sheet1"]
        rows = [tuple(r) + (None,) * 10 for r in ws.iter_rows(values_only=True)]
        hdr = [i for i, r in enumerate(rows) if r[1] and str(r[1]).startswith("Sample ID")][0]
        for r in rows[hdr + 1:]:
            if r[0] is not None and r[1]:
                out.setdefault(fn, {})[int(r[0])] = str(r[1]).strip()
    return out


def acquisition_time(xml_path: Path) -> str:
    m = re.search(r'DateTime IsReadOnly="true" Status="Valid">([^<]+)', xml_path.read_text(encoding="utf-8-sig", errors="ignore"))
    if not m:
        raise ValueError(f"no acquisition time in {xml_path.name}")
    return m.group(1)[:19]


def build_aodc(samples: set[str]):
    numbers = read_aodc_numbers()
    upload, final = numbers["AODC_Active Sampling 2019_upload.xlsx"], numbers["AODC_Active Sampling 2019_final timepoint.xlsx"]
    if sorted(upload) != list(range(1, 37)) or len(final) != 9:
        raise ValueError(f"workbook numbering changed: {sorted(upload)[:3]}.. {len(final)}")
    images, procs, manifest, copies = [], [], [], []
    files = sorted(p for p in AODC_DIR.iterdir() if p.suffix.lower() in (".jpg", ".png"))
    if len(files) != 45:
        raise ValueError(f"expected 45 AODC images, found {len(files)}")
    for p in files:
        m = re.match(r"2019AODC Active samplinq(\d+)\.(jpg|png)$", p.name)
        if m:
            n = int(m.group(1)); sheet_id = upload[n]; basis = f"image number {n} = sample number {n} of AODC_Active Sampling 2019_upload.xlsx"
        else:
            stem = p.stem  # e.g. GW821E_051319_6, FW101_20_051519_6
            cand = [v for v in final.values() if re.sub(r"[-_]", "", v) == re.sub(r"[-_]", "", stem)]
            if len(cand) != 1:
                raise ValueError(f"{p.name}: no unique final-timepoint sample ({cand})")
            sheet_id = cand[0]; basis = "named by sample in the Hazen AODC folder"
        sample = aodc_sample_name(sheet_id)
        if sample not in samples:
            raise ValueError(f"{p.name}: sample {sample} not in CORAL")
        when = acquisition_time(Path(str(p) + "_metadata.xml"))
        name = f"{sample}-aodc{p.suffix.lower()}"
        mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
        images.append(image_row(name, f"{sample} AODC epifluorescence micrograph (Hazen Lab, acquired {when.replace('T', ' ')}; {basis}; original file {p.name}, "
                                f"camera metadata in {p.name}_metadata.xml)", p, mime=mime))
        procs.append({"process": "Image <PROCESS:0000047>", "person": HAZEN, "campaign": CAMPAIGN_SPRING, "protocol": "null",
                      "date_start": when[:10], "date_end": when[:10], "input_objects": f"Sample: {sample}", "output_objects": f"Image: {name}"})
        manifest.append(manifest_row(f"hazen_aodc_micrograph/{name}", name, "hazen", "groundwater", "aodc_micrograph", mime, p.stat().st_size,
                                     str(AODC_DIR.relative_to(TEAM)) + "/", p.name, f"Sample:{sample}"))
        copies.append((p, EDR_IMAGES / "hazen_aodc_micrograph" / name))
        copies.append((Path(str(p) + "_metadata.xml"), EDR_IMAGES / "hazen_aodc_micrograph" / f"{name}_metadata.xml"))
    return images, procs, manifest, copies


def protocol_rows():
    return [
        {"name": PROTO_TEM, "link": "", "description":
            "Transmission electron microscopy of CPT sediment 'washes' by the Walian Lab (Peter Walian), used as a high-throughput means of imaging microbes "
            "in the 2020 cone penetrometer sediment samples (depth range 8-19 ft; water content from dry vadose to saturated; mostly clay-rich). Several "
            "extraction protocols were used, from gentle (lowest yield, best preservation of cell structure) to strong (higher yield, cell lysis and "
            "deformation). Findings (readme, 2021-09): few microbes observed regardless of protocol; most from push 21 (Mid-NW zone); the most common "
            "phenotype in Area 3 sediment is microbes with S-layers; Rhodanobacter among the more prominent non-S-layer microbes; no ultra-small cells or "
            "multi-cell clusters; maximum sediment AODC of ~10^6 cells/mL suggests about one cell per 100 um. Images are JPEG exports from the team Drive "
            "folder 'CPT EM imaging' (deck 'CPT EM imaging.pptx', readme 'Readme for CPT imaging.docx')."},
        {"name": PROTO_CT, "link": "", "description":
            "X-ray micro-computed tomography of pilot sediment core sections (FW106 and EB271 cores, 2017) at the Advanced Light Source beamline 8.3.2, run by "
            "Peter Walian (Walian Lab), scanned and reconstructed on 2017-05-17. Each scan: 1,025 projections over 180 degrees on a 2560 x 2160 detector, "
            "reconstructed with tomopy (gridrec, Butterworth filter order 2 cutoff 0.25, phase-correlation rotation centre, nearest-flats normalisation, "
            "1D outlier removal, Fourier-wavelet stripe removal (db5, level 8, sigma 4), edge padding, circular mask) by the beamline's dxchange pipeline; "
            f"slices scaled by 1/{CT_PIXEL_UM * 1e-4:.2e} cm, i.e. a pixel size of {CT_PIXEL_UM} um (2560 pixels = 1.63 mm), written as 2,160 float32 TIFF "
            "slices of 2560 x 2560 per section, with the reconstruction script (.py) and parameter file (.yml) kept beside them. Fourteen reconstructions "
            "(FW106 sections 4-5, 5-5, 6-3, 6-5, 7-6, 8-5, 9-4, 10-1; EB271 sections 2-2, 3-3, 4-1, 4-4, 5-1, 5-2; 742 GB) were delivered to "
            "John-Marc Chandonia on a hard drive in December 2019; ten representative slices are on the team Drive."},
        {"name": PROTO_GW, "link": "", "description":
            "Transmission electron microscopy of unfiltered groundwater by the Walian Lab (Peter Walian; tallies by a student, 'Valerie results'): water from "
            "the Walian/Hazen R11 sample bottles of the Spring 2019 Integrated Sampling (GW821E background well, MLSB5 Area 2 multi-level sampler, FW100-20 "
            "Area 3) was concentrated onto EM grids, some grids stained with uranyl acetate ('UA') or treated with Mg or water washes, and imaged; microbes "
            "were tallied per grid window and classified as large cells (> 1 um), ultra-small cells (UMBs), phage and other morphotypes, and representative "
            "crops were filed by morphotype in the ENIGMA Image Atlas drive (ENIGMA_Imaging/Images_Groundwater). The MLSB6 groundwater of 2022-10-24 "
            "(one-off, unfiltered, imaged 2023-03-15) was examined the same way for ultra-small bacteria. Summary slides: 2019_Spring_Integrated "
            "Sampling/Walian Lab/GW imaging.pptx."},
    ]


def write_tsv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> None:
    stage_validator()
    ab.load_ontology_names()
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    ab.OUT = OUT
    ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT = (OUT / d for d in ("json", "static", "process", "check", "reports"))
    for d in (ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT, OUT / "source"):
        d.mkdir(parents=True)
    shutil.copy2(GW_STATS_SRC, GW_STATS)
    with (EXPORT / "Sample.tsv").open() as h:
        sample_rows = {r["name"]: r for r in csv.DictReader(h, delimiter="\t")}
    samples = set(sample_rows)
    with (EXPORT / "Image.tsv").open() as h:
        existing_images = {r["name"] for r in csv.DictReader(h, delimiter="\t")}
    with (EXPORT / "Protocol.tsv").open() as h:
        if {PROTO_TEM, PROTO_CT, PROTO_GW} & {r["name"] for r in csv.DictReader(h, delimiter="\t")}:
            raise ValueError("protocol name already in CORAL")
    if set(NEW_R11) & samples or MLSB6 not in samples:
        raise ValueError("unexpected sample state")

    tem_images, tem_procs, tem_manifest, tem_copies = build_tem(samples)
    ct_images, ct_procs, ct_manifest, ct_copies, recon_dirs = build_microct(samples)
    gw_images, gw_procs, gw_manifest, gw_copies, gw_skipped = build_groundwater(samples, sample_rows)
    aodc_images, aodc_procs, aodc_manifest, aodc_copies = build_aodc(samples)
    values, dates = read_gw_stats()
    gw_brick, brick_samples = build_gw_brick(values, dates)
    all_images = tem_images + ct_images + gw_images + aodc_images
    names = [i["name"] for i in all_images]
    if len(set(names)) != len(names) or set(names) & existing_images:
        raise ValueError("duplicate or existing image names")
    brick_path = ab.write_brick(gw_brick)

    # new Samples: copies of the sibling R6 rows with Walian/Hazen as description
    tmpl_fields = ["name", "location", "depth", "elevation", "date", "time", "timezone", "material", "env_package", "description"]
    new_samples = []
    for s in NEW_R11:
        sib = sample_rows[s.replace("-R11", "-R6")]
        new_samples.append({"name": s, "location": sib["location_id"], "depth": sib["depth"], "elevation": sib["elevation"], "date": sib["date"],
                            "time": sib["time"], "timezone": sib["timezone"], "material": sib["material"], "env_package": sib["env_package"],
                            "description": "Walian/Hazen"})
    write_tsv(ab.STATIC_OUT / f"Sample_additions_{TAG}.tsv", new_samples, tmpl_fields)
    write_tsv(ab.STATIC_OUT / f"Protocol_additions_{TAG}.tsv", protocol_rows(), ["name", "description", "link"])
    write_tsv(ab.STATIC_OUT / f"Image_additions_{TAG}.tsv", all_images, ["name", "description", "MIME type", "size", "dimensions", "link"])
    write_process(ab.PROCESS_OUT / f"process_image_tem_{TAG}.tsv", tem_procs)
    write_process(ab.PROCESS_OUT / f"process_image_microct_{TAG}.tsv", ct_procs)
    write_process(ab.PROCESS_OUT / f"process_image_groundwater_{TAG}.tsv", gw_procs)
    write_process(ab.PROCESS_OUT / f"process_image_aodc_{TAG}.tsv", aodc_procs)
    write_process(ab.PROCESS_OUT / f"process_assay_cell_counts_{TAG}.tsv", [
        {"process": "Assay Cell Counts <PROCESS:0000008>", "person": WALIAN, "campaign": CAMPAIGN_SPRING, "protocol": PROTO_GW,
         "date_start": "2019-03-18", "date_end": "2019-05-15", "input_objects": ", ".join(f"Sample: {s}" for s in brick_samples),
         "output_objects": f"Generic: {gw_brick['name']}"}])

    # EDR manifest rows and copy lists
    manifest = tem_manifest + ct_manifest + gw_manifest + aodc_manifest
    write_tsv(OUT / f"edr_images_manifest_rows_{TAG}.tsv", manifest, list(manifest[0].keys()))
    with (OUT / "edr_copy_list.tsv").open("w") as h:  # source -> EDR destination (micro-CT stacks are rsynced separately)
        for src, dst in tem_copies + gw_copies + aodc_copies:
            h.write(f"{src}\t{dst}\n")
    with (OUT / "images_to_install.txt").open("w") as h:  # EDR path -> hub data_store/images/<name>
        for m in manifest:
            if not m["path"].endswith("/"):
                h.write(f"{m['path']}\t{m['coral_image_name']}\n")
    proc_files = [f"process_image_tem_{TAG}.tsv", f"process_image_microct_{TAG}.tsv", f"process_image_groundwater_{TAG}.tsv", f"process_image_aodc_{TAG}.tsv", f"process_assay_cell_counts_{TAG}.tsv"]
    files = [f"static/Sample_additions_{TAG}.tsv", f"static/Protocol_additions_{TAG}.tsv", f"static/Image_additions_{TAG}.tsv", f"json/{brick_path.name}"] + [f"process/{p}" for p in proc_files]
    (OUT / "files_to_import.txt").write_text("\n".join(files) + "\n")
    (OUT / "import_to_coral.py").write_text("\n".join([
        "# Stage files_to_import.txt in data_import/data and images_to_install.txt in data_store/images first",
        f"toolx.update_core('Sample_additions_{TAG}.tsv', 'Sample')",
        f"toolx.update_core('Protocol_additions_{TAG}.tsv', 'Protocol')",
        f"toolx.update_core('Image_additions_{TAG}.tsv', 'Image')",
        f"toolx.upload_brick('{brick_path.name}')",
        f"toolx.upload_process('Image', 'process_image_tem_{TAG}.tsv')",
        f"toolx.upload_process('Image', 'process_image_microct_{TAG}.tsv')",
        f"toolx.upload_process('Image', 'process_image_groundwater_{TAG}.tsv')",
        f"toolx.upload_process('Image', 'process_image_aodc_{TAG}.tsv')",
        f"toolx.upload_process('Assay Cell Counts', 'process_assay_cell_counts_{TAG}.tsv')", ""]))
    summary = {"release": RELEASE, "images": {"tem": len(tem_images), "microct_stacks": len(recon_dirs), "microct_slices": len(ct_images) - len(recon_dirs), "groundwater": len(gw_images), "aodc_spring2019": len(aodc_images)},
               "new_samples": NEW_R11, "brick": {"name": gw_brick["name"], "shape": [d["size"] for d in gw_brick["dim_context"]]},
               "groundwater_skipped": gw_skipped, "gw_values": {f"{k[0]}|{k[1]}": v for k, v in values.items()},
               "hashes": {f: hashlib.sha256((OUT / f).read_bytes()).hexdigest() for f in files}}
    (ab.REPORT_OUT / "build_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    (OUT / "README.md").write_text(f"""# CORAL import package: Walian Lab images and Spring 2019 groundwater EM tallies ({RELEASE})

Built by `tools/build_walian_images_coral_import.py`.

| Content | Count | Source |
| --- | --- | --- |
| CPT sediment TEM images (2021) | {len(tem_images)} | team Drive `2020_Cone Penetrometer Sampling/CPT EM imaging/` |
| Pilot-core micro-CT reconstructions (ALS 8.3.2, 2017-05-17) | {len(recon_dirs)} stacks + {len(ct_images) - len(recon_dirs)} slices | `~/data/enigma/walian/microCT` (HDD from Peter Walian, Dec 2019) |
| Spring 2019 groundwater EM morphotype crops | {len(gw_images)} | team Drive `ENIGMA_Imaging/Images_Groundwater/` (122 method-trial crops not loaded) |
| Spring 2019 AODC micrographs (Hazen Lab) | {len(aodc_images)} | team Drive `2019_Spring_Integrated Sampling/Hazen Lab/AODC/` (36 numbered by workbook sample number, 9 named) |
| Brick `walian_em_groundwater_counts_spring2019` | 15 samples x 4 categories | `source/GW_imaging_stats.xlsx` (Peter Walian e-mail, 2020-04-17) |

Static additions: Samples {', '.join(NEW_R11)}; Protocols `{PROTO_TEM}`, `{PROTO_CT}`, `{PROTO_GW}`; {len(all_images)} Images.
Processes: Image (Walian Lab) per image, Assay Cell Counts for the brick.

EDR: `images/walian_sediment_em/` (TEM), `images/walian_sediment_microct/<RECON folder>/` (full stacks, rsynced from the local copy),
`images/walian_groundwater_em/`, `images/hazen_aodc_micrograph/` (AODC, with camera XML); manifest rows in `edr_images_manifest_rows_{TAG}.tsv`; hub image files in `images_to_install.txt`.
""")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("hashes", "gw_values", "groundwater_skipped")}, indent=1))


if __name__ == "__main__":
    main()
