#!/usr/bin/env python3
"""Build the CORAL import package for the 2019 27-well survey bug traps and the Fields Lab
bug-trap packed-bed reactors (IMPORT_PLAN batch D6 + D7, with the Adams bug-trap metals).

Bug traps (Hazen Lab, 27 Well Survey): 6-inch slotted PVC traps packed with dried, sieved,
autoclaved local FRC sediment, hung below the Aqua TROLL 600 in EU05, GW-835 and FW106. Each week
of 6 deployment weeks (2019-08-08 to 2019-10-03) three traps went into each well and one was pulled
after 4, 6 and 8 weeks: 54 traps. The starting sediment was also analysed; it is not a CORAL
Sample and appears in the bricks as a control column with no sample or community, as in the
SSOSTOR bricks.

* zhou_lab_27ws_bug_trap_2019_ASV_16S / _count / _taxonomy  (Zhou Lab MiSeq round 210507)
* adams_metals_27ws_bug_trap_2019                          (Adams Lab ICP-MS, mg/kg)
* zhou_lab_27ws_bug_trap_reactor_2020_ASV_16S / _count / _taxonomy
  (Fields Lab packed-bed reactors 1-3, inoculated from the 8-week traps of deployment week 6)

Static additions: 54 Samples, 54 bug-trap Communities, 54 Reads, 58 reactor Communities, three
reactor Conditions, new OTU and Taxon names, one Protocol.

    python tools/build_27ws_bug_trap_coral_import.py
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import io
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_sso_batch_ab_coral_import as ab  # noqa: E402
import build_sso_oneoff_16s_coral_import as oo  # noqa: E402
from build_sso_batch_ab_coral_import import T, NAMES, comment, ctx, oterm_value, sval, typed, write_process  # noqa: E402

REPO = ab.REPO
SURVEY = ab.DRIVE / "2019_Summer／Fall_27-Well Survey"
BT_DIR = SURVEY / "Zhou - 16S sequencing Bug trap samples"
ASV_DIR = BT_DIR / "V210507ASV"
RAW_READS = BT_DIR / "Raw sequencing data/Round-210507"
FIELD_LOG = SURVEY / "Hazen - Field Log and TROLL data/27Well_2019_Field_Log.xlsx"
ADAMS_BT = SURVEY / "Adams - metals/Adams_Metal_Data_Bug Trap_FW106_GW835_EU05_060921"
PBR_ZIP = SURVEY / "Fields - PBR/V012522.ESV.zip"
RELEASE = "20261027"
OUT = REPO / f"coral_import/27ws_bug_traps_{RELEASE}"
EXPORT = REPO / "sync-coral-to-berdl/exports/sync-20261027-134534/coral_export/static_tsv"
CAMPAIGN = "27 Well Survey <ENIGMA:0000101>"
RAW_READS_LINK = "https://drive.google.com/drive/folders/1h6fWGtnwK9dHu9nTKFPUwvf1hYhLjTm-"  # Round-210507, team drive
PROTOCOL = "fan-ning-2021-qiime2-silva132"
PROTOCOL_LINK = "https://drive.google.com/file/d/1hNGLIECYhyPOB3GqvH73UVzw_VDg8a3E/view"  # ReadMe_27wellbugtrap_16S_v20210507_final_version.docx, team drive
PROTOCOL_TEXT = (
    "Zhou Lab 16S rRNA gene ASV processing used for the 2019 27-well survey bug traps and the 2020 bug-trap packed-bed reactors (ReadMes v20210507 and v01252022; Yupeng Fan, "
    "Jonathan Michael, Daliang Ning, Ying Fu, Joy Van Nostrand, Jizhong Zhou). Microbial genomic DNA was extracted by a freeze-grinding method and purified with the DNeasy PowerSoil "
    "DNA isolation kit (QIAGEN; bead tubes not used); DNA quality was checked by NanoDrop and double-strand DNA measured by PicoGreen. Amplicons: V4 region of prokaryotic 16S rRNA "
    "genes, primers 515F (GTGCCAGCMGCCGCGGTAA) and 806R (GGACTACHVGGGTWTCTAAT), two-step PCR with phasing primers (10 cycles in the first step and 20 in the second), Illumina MiSeq. "
    "QIIME2 (version 2019.7) was used for the ASV-based processing: after barcode and primer sequences were trimmed with zero maximum error, sequencing data were processed by DADA2 "
    "to identify exact amplicon sequence variants (ASV), which were identified taxonomically with the silva-132-99-515-806-nb-classifier (naive Bayes, SILVA 132, 99% OTUs trimmed "
    "to 515F/806R). A phylogenetic tree was built with FastTree. Processing followed the Microbiome Helper Amplicon SOP v2 for qiime2-2019.7 "
    "(https://github.com/LangilleLab/microbiome_helper/wiki/Amplicon-SOP-v2-(qiime2-2019.7)).")
TROLL_NOTE = ("Depth is estimated: the traps hung side by side just below the well's Aqua TROLL 600. The sonde sat {sonde} ft below top of casing during the deployments "
              "(sensor depth below the water surface plus depth to water, Aqua TROLL 600 bricks {bricks}), which after subtracting the {stickup} ft casing stickup is {bgs} ft below ground; "
              "the trap centre is taken as 0.5 ft deeper ({trap} ft below ground); the well is screened {screen} ft below ground")
WELLS = {  # field-log area -> CORAL name prefix, location, Zhou Lab ID prefix, estimated trap depth (m), depth note values
    1: {"prefix": "EU05", "location": "EU05", "zhou": "EU05", "depth": 4.08,
        "note": {"sonde": "15.51 (15.39 after the 2019-10-04 redeployment)", "bricks": "Brick0001931 and Brick0001932", "stickup": "2.58", "bgs": "12.9", "trap": "13.4", "screen": "10.22 to 20.22"}},
    2: {"prefix": "GW-835", "location": "GW-835", "zhou": "GW835", "depth": 6.05,
        "note": {"sonde": "20.50 (20.86 after the 2019-10-04 redeployment)", "bricks": "Brick0001936 and Brick0001937", "stickup": "1.32", "bgs": "19.2 to 19.5", "trap": "19.9", "screen": "18.78 to 20.78"}},
    3: {"prefix": "FW106", "location": "FW-106", "zhou": "FW106", "depth": 12.38,
        "note": {"sonde": "40.53", "bricks": "Brick0001934", "stickup": "0.41", "bgs": "40.1", "trap": "40.6", "screen": "35.25 to 45.0"}},
}
CONTROL_DESC = "starting sediment used to fill all bug traps (dried, sieved, autoclaved local FRC sediment); never deployed"
LEVELS = [("taxonomic domain", "ME:0000351"), ("phylum", "ME:0000252"), ("class", "ME:0000253"), ("order", "ME:0000254"), ("family", "ME:0000255"), ("genus", "ME:0000256")]
REACTORS = {  # reactor -> field area of its inoculum trap, media pH and nitrate (Scales, Aim 1 SSO Legacy BugTrap PBR Paper, July 2025)
    1: {"area": 1, "pH": "7", "nitrate_mM": "0.035"},
    2: {"area": 2, "pH": "6.3", "nitrate_mM": "3.5"},
    3: {"area": 3, "pH": "4", "nitrate_mM": "23"},
}

T.update(oo.T)
T.update({"27 Well Survey": "ENIGMA:0000101", "Yupeng Fan": "ENIGMA:0000154", "Fields Lab": "ENIGMA:0000063", "Zhou Lab": "ENIGMA:0000090",
          "time elapsed": "ME:0000122", "ppm": "UO:0000169", "detection limit": "ME:0000038", "baseline control": "ME:0000516", "week": "UO:0000034", "date": "ME:0000009", "mg/kg": "UO:0000308"})


def trap_records():
    """The field log's Bug Traps sheet: one row per trap."""
    ws = openpyxl.load_workbook(FIELD_LOG, read_only=True, data_only=True)["Bug Traps"]
    rows = list(ws.iter_rows(values_only=True))
    if list(rows[0][:8]) != ["Trap ID", "Well ID", "Area", "Time Point", "Replicate", "Deployment Date", "Retrieval Date", "# of Weeks Deployed"]:
        raise ValueError(f"field log Bug Traps header {rows[0][:8]}")
    out = []
    for r in rows[1:]:
        if len(r) < 8 or r[2] is None:
            continue
        area, tp, rep, weeks = int(r[2]), int(r[3]), int(r[4]), int(r[7])
        w = WELLS[area]
        dep, ret = r[5].date(), r[6].date()
        if {1: 4, 2: 6, 3: 8}[rep] != weeks:
            raise ValueError(f"trap {area}.{tp}.{rep}: {weeks} weeks")
        name = f"{w['prefix']}-{ret:%Y%m%d}-TP{tp}-R{rep}"
        zhou = f"{w['zhou']}{ret:%Y%m%d}TP{tp}Rep{rep}"
        out.append({"area": area, "tp": tp, "rep": rep, "weeks": weeks, "deployed": dep, "retrieved": ret, "name": name, "zhou": zhou, "key": f"{area}.{tp}.{rep}"})
    if len(out) != 54 or len({t["name"] for t in out}) != 54:
        raise ValueError(f"{len(out)} traps")
    return out


def read_count(stem: str) -> int:
    total = 0
    for read in ("R1", "R2"):
        hits = sorted(RAW_READS.glob(f"{stem}_*_L001_{read}_001.fastq.gz"))
        if len(hits) != 1:
            raise ValueError(f"{len(hits)} {read} files for {stem}")
        with gzip.open(hits[0], "rt") as h:
            n = sum(1 for _ in h)
        if n % 4:
            raise ValueError(f"{hits[0].name}: {n} lines")
        total += n // 4
    return total


def read_table(lines):
    rows = [l.rstrip("\r\n").split("\t") for l in lines if l.strip() and not l.startswith("# Constructed")]
    hdr = rows[0]
    if hdr[0] not in ("#OTU ID", "ID", " ID"):
        raise ValueError(f"table header {hdr[:2]}")
    return hdr[1:], [r[0] for r in rows[1:]], [[int(float(x)) for x in r[1:]] for r in rows[1:]]


def read_classification(lines, keep):
    """QIIME2 'Feature ID / Taxon / Confidence' with D_0__..D_6__ ranks; ranks D_0 to D_5 are kept."""
    rows = [l.rstrip("\r\n").split("\t") for l in lines if l.strip()]
    if rows[0][:3] != ["Feature ID", "Taxon", "Confidence"]:
        raise ValueError(f"classification header {rows[0]}")
    tax, conf = {}, {}
    for r in rows[1:]:
        if r[0] not in keep:
            continue
        levels = [None] * len(LEVELS)
        for part in ([] if r[1].strip() == "Unassigned" else r[1].split(";")):
            m = re.fullmatch(r"D_(\d)__(.*)", part.strip())
            if not m:
                raise ValueError(f"{r[0]}: rank {part!r}")
            k, name = int(m.group(1)), m.group(2).strip()
            if k < len(LEVELS) and name:
                levels[k] = name
        tax[r[0]], conf[r[0]] = levels, float(r[2])
    if set(tax) != set(keep):
        raise ValueError(f"classification lacks {len(set(keep) - set(tax))} ASVs")
    return tax, conf


def read_fasta(lines):
    seqs, cur = {}, None
    for line in lines:
        line = line.strip()
        if line.startswith(">"):
            cur = line[1:].split()[0]
            seqs[cur] = ""
        elif cur:
            seqs[cur] += line
    return seqs


def asv_dim(asvs, conf=None):
    tv = [{"value_type": oo.term("OTU ID"), "values": oo.obj_values(asvs)}]
    if conf is not None:
        tv.append({"value_type": oo.term("confidence"), "value_units": oo.term("confidence unit"),
                   "values": {"scalar_type": "float", "float_values": [conf[a] for a in asvs]}})
    return {"data_type": oo.term("OTU"), "size": len(asvs), "typed_values": tv}


def sixteen_s_bricks(stem, title, common, src_note, asvs, seqs, counts, comm_dim, count_notes, tax, conf, tax_src, rep_dim=None):
    """counts: [ASV][community], or [ASV][community][replicate] with rep_dim."""
    flat = [v for row in counts for v in row] if rep_dim is None else [v for row in counts for c in row for v in c]
    seq = {"name": f"{stem}_16S.ndarray", "description": f"Zhou Lab 16S ASV sequences, {title}", "data_type": oo.term("microbial sequence"),
           "array_context": common + [comment(src_note)], "n_dimensions": 1, "dim_context": [asv_dim(asvs)],
           "typed_values": [{"value_type": oo.term("sequence"), "values": {"scalar_type": "string", "string_values": [seqs[a] for a in asvs]},
                             "value_context": [ctx("sequence type", oterm_value("16S sequence"))]}]}
    count = {"name": f"{stem}_count.ndarray", "description": f"Zhou Lab 16S ASV counts, {title}", "data_type": oo.term("taxonomic abundance"),
             "array_context": common + [comment(n) for n in count_notes], "n_dimensions": 2 if rep_dim is None else 3,
             "dim_context": [asv_dim(asvs), comm_dim] + ([] if rep_dim is None else [rep_dim]),
             "typed_values": [{"value_type": oo.term("count"), "value_units": oo.term("count unit"),
                               "values": {"scalar_type": "int", "int_values": flat}}]}
    level_dim = {"data_type": oo.term("taxonomic level"), "size": len(LEVELS), "typed_values": [{"value_type": oo.term("taxonomic level"), "values": {
        "scalar_type": "oterm_ref", "oterm_refs": [i for _, i in LEVELS], "string_values": [n for n, _ in LEVELS]}}]}
    taxonomy = {"name": f"{stem}_taxonomy.ndarray", "description": f"Zhou Lab 16S ASV taxonomy (SILVA 132), {title}", "data_type": oo.term("taxonomic assignment"),
                "array_context": common + [
                    comment("Variable: taxon ID (a CORAL Taxon) for SILVA 132 ranks D_0 to D_5 (domain to genus), named exactly as in the classifier output; unassigned ranks are null. "
                            "The D_6 'species' rank, which SILVA 132 fills with clone and source names, is not loaded, as in the 27-well survey SILVA 132 taxonomy (Brick0000012). "
                            "The ASV confidence is the classifier confidence of the deepest assigned rank"),
                    comment(tax_src)],
                "n_dimensions": 2, "dim_context": [asv_dim(asvs, conf), level_dim],
                "typed_values": [{"value_type": oo.term("taxon ID"), "values": oo.obj_values([t for a in asvs for t in tax[a]])}]}
    return [seq, count, taxonomy]


def control_vars(is_control):
    """The control type, as in the SSOSTOR and other bricks with controls; the control itself is described in a brick comment."""
    return [{"value_type": oo.term("control"), "values": {"scalar_type": "oterm_ref", "oterm_refs": [T["baseline control"] if c else None for c in is_control],
                                                         "string_values": [NAMES[T["baseline control"]] if c else None for c in is_control]}}]


def read_adams_bt():
    with ADAMS_BT.open("rb") as h:
        wb = openpyxl.load_workbook(io.BytesIO(h.read()), data_only=True)
    sheets = {}
    for key, sheet in (("conc", "50X + 5X (mg per kg) FINAL"), ("sd", "50X + 5X (mg per kg) FINAL SD")):
        rows = list(wb[sheet].iter_rows(values_only=True))
        symbols = [str(v).strip() for v in rows[5][7:59]]
        if sorted(symbols) != sorted(e[0] for e in ab.ELEMENTS):
            raise ValueError(f"{sheet}: elements {symbols}")
        col = [7 + symbols.index(e[0]) for e in ab.ELEMENTS]  # the workbook lists Pr before Ce
        quant = dict(zip(symbols, rows[0][7:59]))
        if key == "conc":
            if str(rows[6][6]).strip() != "DL (final) (ppm)":
                raise ValueError(f"{sheet}: detection-limit row label {rows[6][6]!r}")
            dl = [float(rows[6][c]) or None for c in col]  # Te is 0.0 in the workbook although 6 Te values are <DL: not a usable limit
        if rows[7][:7] != ("Trap ID", "Well ID", "Area", "Deployment period", "Retrieval period", "# of Weeks Deployed", "Sample Name"):
            raise ValueError(f"{sheet}: header {rows[7][:7]}")
        data = [(str(r[0]).strip(), [r[c] for c in col]) for r in rows[8:] if r[0] is not None]
        sheets[key] = data
    if [k for k, _ in sheets["conc"]] != [k for k, _ in sheets["sd"]] or len(sheets["conc"]) != 55:
        raise ValueError("Adams bug-trap sheets differ")
    return sheets, quant, dl


def main() -> None:
    oo.stage_validator()
    ab.load_ontology_names()
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    ab.OUT = OUT
    ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT = (OUT / d for d in ("json", "static", "process", "check", "reports"))
    for d in (ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT):
        d.mkdir(parents=True)
    tsv = lambda name: list(csv.DictReader((EXPORT / name).open(), delimiter="\t"))
    samples, communities = {r["name"] for r in tsv("Sample.tsv")}, {r["name"] for r in tsv("Community.tsv")}
    reads_live, otus, taxa = {r["name"] for r in tsv("Reads.tsv")}, {r["name"] for r in tsv("OTU.tsv")}, {r["name"] for r in tsv("Taxon.tsv")}
    locations, conditions, protocols = {r["name"] for r in tsv("Location.tsv")}, {r["name"] for r in tsv("Condition.tsv")}, {r["name"] for r in tsv("Protocol.tsv")}
    if PROTOCOL in protocols:
        raise ValueError(f"{PROTOCOL} already in CORAL")
    summary = {"release": RELEASE}

    # ---------------- D6: bug-trap samples
    traps = trap_records()
    by_zhou = {t["zhou"]: t for t in traps}
    by_key = {t["key"]: t for t in traps}
    sample_rows, community_rows, reads_rows, sampling, sequencing = [], [], [], [], []
    for t in traps:
        w = WELLS[t["area"]]
        if t["name"] in samples or t["name"] in communities or f"{t['name']}.reads" in reads_live:
            raise ValueError(f"{t['name']} already in CORAL")
        if w["location"] not in locations:
            raise ValueError(f"Location {w['location']} not in CORAL")
        desc = (f"Bug trap (Hazen Lab trap {t['key']}): 6-inch slotted 1-inch PVC well screen packed with dried, sieved, autoclaved local FRC sediment (500-2000 um in the capped ends, under 500 um in the "
                f"slotted section), deployed in {w['location']} below the Aqua TROLL 600 from {t['deployed']} to {t['retrieved']} ({t['weeks']} weeks; deployment week {t['tp']} of 6, "
                f"the {['first', 'second', 'third'][t['rep'] - 1]} of three traps deployed that week). " + TROLL_NOTE.format(**w["note"]) + ".")
        sample_rows.append([t["name"], w["location"], f"{w['depth']:g}", "null", t["retrieved"].isoformat(), "null", "null", "sediment <ENVO:00002007>", "sediment <MIxS:0000014>", desc])
        community_rows.append([t["name"], "Environmental Community <ME:0000326>", t["name"], "null", "null", "null", "null"])
        reads_rows.append([f"{t['name']}.reads", str(read_count(t["zhou"])), "Paired End Read <ME:0000113>", "Illumina <ME:0000117>", RAW_READS_LINK])
        sampling.append({"process": "Sampling <PROCESS:0000002>", "person": "Hazen Lab <ENIGMA:0000066>", "campaign": CAMPAIGN, "protocol": "null",
                         "date_start": t["deployed"].isoformat(), "date_end": t["retrieved"].isoformat(),
                         "input_objects": f"Location: {w['location']}", "output_objects": f"Sample: {t['name']}, Community: {t['name']}"})
        sequencing.append({"process": "16S Sequencing <PROCESS:0000020>", "person": "Ying Fu <ENIGMA:0000168>", "campaign": CAMPAIGN, "protocol": "null",
                           "date_start": "2021-05-07", "date_end": "2021-05-07", "input_objects": f"Sample: {t['name']}", "output_objects": f"Reads: {t['name']}.reads"})

    # ---------------- D6: bug-trap 16S (clean table: raw table minus 13 chloroplast ASVs; keeps the starting-sediment control)
    clean = ASV_DIR / "Clean ASV table"
    cols, asvs, counts = read_table((clean / "210507.ASV.table.txt").open())
    if set(cols) != set(by_zhou) | {"Control"}:
        raise ValueError(f"bug-trap table columns {sorted(set(cols) ^ (set(by_zhou) | {'Control'}))}")
    order = sorted((c for c in cols if c != "Control"), key=lambda c: (by_zhou[c]["area"], by_zhou[c]["tp"], by_zhou[c]["rep"])) + ["Control"]
    idx = [cols.index(c) for c in order]
    counts = [[row[j] for j in idx] for row in counts]
    raw_tax_lines = (ASV_DIR / "Raw ASV table/210507.ASV.Classification.txt").open().readlines()
    tax, conf = read_classification(raw_tax_lines, set(asvs))
    raw_ids = {l.split("\t")[0] for l in raw_tax_lines[1:]}
    removed = sorted(raw_ids - set(asvs))
    removed_chloro = [a for a in removed if "D_3__Chloroplast" in next(l for l in raw_tax_lines if l.startswith(a))]
    if len(removed) != 13 or removed_chloro != removed:
        raise ValueError(f"clean table removed {len(removed)} ASVs, {len(removed_chloro)} chloroplast")
    seqs = read_fasta((clean / "210507.ASV.RepSeq.fasta").open())
    if not set(asvs) <= set(seqs):
        raise ValueError("bug-trap fasta lacks ASVs")
    names = [by_zhou[c]["name"] if c != "Control" else None for c in order]
    comm_dim = {"data_type": oo.term("community"), "size": len(order), "typed_values": [
        {"value_type": oo.term("community ID"), "values": oo.obj_values(names)}] + control_vars([n is None for n in names]) + [
        typed("date", "string", [by_zhou[c]["deployed"].isoformat() if c != "Control" else None for c in order], None, [comment("deployment")]),
        typed("time elapsed", "float", [float(by_zhou[c]["weeks"]) if c != "Control" else None for c in order], "week", [comment("deployment")])]}
    src = f"{ab.DRIVE_LABEL} {ASV_DIR.relative_to(ab.DRIVE)}"
    common = [ctx("ENIGMA campaign", oterm_value("27 Well Survey")), ctx("personnel", oterm_value("Yupeng Fan"))]
    depths = [sum(r[j] for r in counts) for j in range(len(order))]
    bt_bricks = sixteen_s_bricks(
        "zhou_lab_27ws_bug_trap_2019_ASV", "2019 27-well survey bug traps (EU05, GW-835, FW106)", common,
        f"Source: {src}/Clean ASV table/210507.ASV.RepSeq.fasta", asvs, seqs, counts, comm_dim,
        [f"Counts are not resampled ({min(depths[:-1]):,} to {max(depths[:-1]):,} reads per trap); chloroplast ASVs (13) were removed by the Zhou Lab (Clean ASV table). "
         "The lab's resampled table is not used because it was drawn from the raw table, chloroplasts included, and omits the starting-sediment control",
         "The column with no community is the baseline control, the " + CONTROL_DESC,
         "Each trap's date (deployment) is the day it went into the well and its time elapsed (deployment) is how long it stayed there; its retrieval date is the date of its sample",
         f"Source: {src}/Clean ASV table/210507.ASV.table.txt"],
        tax, conf, f"Source: {src}/Raw ASV table/210507.ASV.Classification.txt (the same assignments as the Clean ASV table's classification, which lacks the confidence and, in 7 ASVs, shows the SILVA order 11-24 as '24-Nov' after a spreadsheet date conversion)")
    for o in bt_bricks:
        oo.write_brick(o)
    classify = [{"process": "Classify OTUs <PROCESS:0000031>", "person": "Yupeng Fan <ENIGMA:0000154>", "campaign": CAMPAIGN, "protocol": PROTOCOL,
                 "date_start": "2021-05-07", "date_end": "2021-05-07", "input_objects": f"Reads: {t['name']}.reads",
                 "output_objects": ", ".join(f"Generic: {o['name']}" for o in bt_bricks)} for t in traps]
    new_otus = [a for a in asvs if a not in otus]
    new_taxa = {x for a in asvs for x in tax[a] if x and x not in taxa}
    summary["bug_trap_16S"] = {"asvs": len(asvs), "traps": len(traps), "control_reads": depths[-1], "trap_reads": [min(depths[:-1]), max(depths[:-1])]}

    # ---------------- Adams bug-trap metals
    sheets, quant, dl = read_adams_bt()
    keys = [k for k, _ in sheets["conc"]]
    if keys[0] != "CONTROL" or set(keys[1:]) != set(by_key):
        raise ValueError(f"Adams trap IDs {keys[:3]}")
    m_names = [None if k == "CONTROL" else by_key[k]["name"] for k in keys]
    m_order = sorted(range(len(keys)), key=lambda i: (m_names[i] is None, keys[i]))
    def num(v):
        return None if v in (None, "<DL") else float(v)
    conc = [num(v) for i in m_order for v in sheets["conc"][i][1]]
    below = [None if v is None else v == "<DL" for i in m_order for v in sheets["conc"][i][1]]
    sd = [num(v) for i in m_order for v in sheets["sd"][i][1]]
    dl_cells = Counter(ab.ELEMENTS[j][0] for i in m_order for j, v in enumerate(sheets["conc"][i][1]) if v == "<DL")
    ordered = [m_names[i] for i in m_order]
    sample_dim = {"data_type": ab.term("environmental sample"), "size": len(ordered), "typed_values": [
        {"value_type": ab.term("environmental sample ID"), "values": {"scalar_type": "object_ref", "object_refs": ordered, "string_values": ordered}}] + control_vars([n is None for n in ordered])}
    metals = ab.brick(
        "adams_metals_27ws_bug_trap_2019", "Adams Lab ICP-MS acid-extractable element concentrations (52 elements, mg per kg dry sediment) in the 2019 27-well survey bug traps and their starting sediment",
        "chemical measurement",
        [ctx("ENIGMA campaign", oterm_value("27 Well Survey")),
         ctx("method", sval("Metals were extracted by microwave-assisted acid digestion with concentrated nitric acid (EPA Method 3051A); extracts were diluted 250X or 2500X into 2% nitric acid and measured by ICP-MS "
                            "against Inorganic Ventures 71A and 71B standards (0 to 1,000 ppb, 11-point curve), 27-Well Survey acquisition method. Mg, Al, K, Mn and Fe are from the 2500X dilution, the other elements from the 250X dilution. "
                            "Undiluted concentrations are normalized to the dry weight of the sediment and reported as mg per kg sediment")),
         ctx("personnel", oterm_value("Farris Poole")),
         comment("Run date 2021-05-01; samples prepared by Jennifer Goff, Michael Thorgersen and Farris Poole, run by Jennifer Goff and Farris Poole, results processed by Jennifer Goff (Adams Lab, University of Georgia)"),
         comment("Variables: concentration, standard deviation of the concentration (three ICP-MS technical replicates of the same sample tube), and below relative to the detection limit "
                 f"(the element's detection limit is a variable of the molecule dimension; true where the lab reports <DL: {', '.join(f'{k} {v}' for k, v in sorted(dl_cells.items()))}; the concentration is then null)"),
         comment("The detection limit of each element (molecule dimension) is the lab's method detection limit in the measured digest solution, accounting for the dilution, in ppm; "
                 "it is not converted to mg per kg sediment. Te has no limit: the workbook gives 0 although six Te results are reported <DL"),
         comment("Per the lab, Fe in some samples was slightly above the instrument's quantification range at both dilutions, so Fe is semi-quantitative"),
         comment("The row with no sample is the baseline control, the " + CONTROL_DESC + "; it has not been subtracted from the trap values"),
         comment(f"Source: {ab.DRIVE_LABEL} {ADAMS_BT.relative_to(ab.DRIVE)} (sheets '50X + 5X (mg per kg) FINAL' and '... FINAL SD')")],
        [sample_dim, ab.molecule_dim([f"element {s}" for s, _ in ab.ELEMENTS], [
            typed("detection limit", "float", dl, "ppm")])],
        [ab.float_var("concentration", "mg/kg", [], conc),
         ab.float_var("standard deviation", "mg/kg", [ctx("measurement", oterm_value("concentration"))], sd),
         ab.bool_var("below", ab.below_ctx(), below)])
    if quant != {**{s: "Yes" for s, _ in ab.ELEMENTS}, "Fe": "Maybe"}:
        raise ValueError(f"unexpected quantitative flags {quant}")
    ab.write_brick(metals)
    geochem = [{"process": "Assay Geochemistry <PROCESS:0000005>", "person": "Farris Poole <ENIGMA:0000103>", "campaign": CAMPAIGN, "protocol": "null",
                "date_start": "2021-05-01", "date_end": "2021-05-01", "input_objects": ", ".join(f"Sample: {n}" for n in ordered if n),
                "output_objects": f"Generic: {metals['name']}"}]

    # ---------------- D7: packed-bed reactors
    zf = zipfile.ZipFile(PBR_ZIP)
    base = "V012522.ESV/"
    wb = openpyxl.load_workbook(io.BytesIO(zf.read(base + "Raw ESV table/BugTrapReactor_SampleInfo_V012522_Metadata Sheet.xlsx")), data_only=True)
    meta = [r for r in wb.worksheets[0].iter_rows(values_only=True)][1:]
    p_cols, p_asvs, p_counts = read_table(zf.read(base + "Raw sequencing data/V012522.esv.table.txt").decode().splitlines(True))
    p_tax, p_conf = read_classification(zf.read(base + "Raw sequencing data/V012522.esv.classification.txt").decode().splitlines(True), set(p_asvs))
    p_seqs = read_fasta(zf.read(base + "Raw sequencing data/V012522.esv.repseq.fasta").decode().splitlines())
    if not set(p_asvs) <= set(p_seqs):
        raise ValueError("reactor fasta lacks ASVs")
    lib = {}
    for r in meta:
        if not r[5]:
            continue
        short, longid, vol, kind, zid = str(r[0]).strip(), str(r[2]).strip(), r[3], str(r[4]).strip(), str(r[5]).strip()
        m = re.match(r"Area (\d), (?:replicate sample #(\d), (planktonic|sediment) 16s sample|(filtered) liquid reactor effluent), (\d\d)\.(\d\d)\.(\d\d)$", longid)
        if not m:
            raise ValueError(f"reactor sample {longid!r}")
        reactor, rep = int(m.group(1)), m.group(2)
        date = dt.date(2000 + int(m.group(7)), int(m.group(5)), int(m.group(6)))
        if m.group(3) == "sediment":
            name, what = f"PBR{reactor}-{date:%Y%m%d}-SED", f"endpoint reactor sediment, three {vol} mL subsamples sequenced as technical replicates"
        elif m.group(4):
            name, what = f"PBR{reactor}-{date:%Y%m%d}-FILTERED", f"filtered liquid reactor effluent, {vol} mL"
            kind, rep = "filtered liquid reactor effluent", "1"
        else:
            name, what = f"PBR{reactor}-{date:%Y%m%d}", f"liquid reactor effluent (planktonic), two {vol} mL samples sequenced as technical replicates"
        lib[zid] = {"name": name, "rep": int(rep), "reactor": reactor, "date": date, "what": what, "kind": kind}
    if not set(p_cols) <= set(lib):
        raise ValueError(f"reactor libraries without metadata {set(p_cols) - set(lib)}")
    comm = {}
    for z, L in lib.items():
        comm.setdefault(L["name"], L)
    p_order = sorted(comm, key=lambda n: (comm[n]["reactor"], comm[n]["kind"] == "sediment", comm[n]["date"], n))
    n_rep = max(L["rep"] for L in lib.values())
    cell = {(L["name"], L["rep"]): p_cols.index(z) for z, L in lib.items() if z in p_cols}
    if len(cell) != len(p_cols):
        raise ValueError("reactor libraries collide on community and replicate")
    p_counts = [[[row[cell[(n, r)]] if (n, r) in cell else None for r in range(1, n_rep + 1)] for n in p_order] for row in p_counts]
    inoculum = {rx: next(t for t in traps if t["area"] == v["area"] and t["tp"] == 6 and t["rep"] == 3) for rx, v in REACTORS.items()}
    cond_rows, enrich, pbr_comm = [], [], []
    cond_name = {rx: f"{v['nitrate_mM']}mM Nitrate + pH {v['pH']}" for rx, v in REACTORS.items()}
    for rx, c in cond_name.items():
        if c not in conditions:
            cond_rows.append([c])
    for n in p_order:
        L = comm[n]
        if L["name"] in communities:
            raise ValueError(f"{L['name']} already in CORAL")
        src_trap = inoculum[L["reactor"]]
        pbr_comm.append([L["name"], "enrichment <ME:0000236>", src_trap["name"], "null", cond_name[L["reactor"]], "null",
                         f"Fields Lab (Montana State University) packed-bed reactor {L['reactor']}, inoculated with sediment from bug trap {src_trap['name']} and run at pH "
                         f"{REACTORS[L['reactor']]['pH']} with {REACTORS[L['reactor']]['nitrate_mM']} mM nitrate to match its well; {L['what']}, {L['date']}"])
        enrich.append({"process": "Enrichment <PROCESS:0000011>", "person": "Fields Lab <ENIGMA:0000063>", "campaign": CAMPAIGN, "protocol": "null",
                       "date_start": L["date"].isoformat(), "date_end": L["date"].isoformat(), "input_objects": f"Sample: {src_trap['name']}", "output_objects": f"Community: {L['name']}"})
    p_names = list(p_order)
    p_comm_dim = {"data_type": oo.term("community"), "size": len(p_order), "typed_values": [
        {"value_type": oo.term("community ID"), "values": oo.obj_values(p_names)},
        typed("date", "string", [comm[n]["date"].isoformat() for n in p_order], None, [comment("sampling")]),
        typed("description", "string", [comm[n]["kind"] for n in p_order], None, [comment("sample type")])]}
    rep_dim = ab.replicate_dim(n_rep, "technical replicate")
    p_common = [ctx("ENIGMA campaign", oterm_value("27 Well Survey")), ctx("personnel", oterm_value("Yupeng Fan"))]
    p_src = f"{ab.DRIVE_LABEL} {PBR_ZIP.relative_to(ab.DRIVE)}"
    p_depths = [sum(row[i][r] for row in p_counts) for i in range(len(p_order)) for r in range(n_rep) if p_counts[0][i][r] is not None]
    missing_libs = sorted((z for z in lib if z not in p_cols), key=lambda z: int(z[2:]))
    missing_txt = ", ".join(f"{lib[z]['name']} replicate {lib[z]['rep']}" for z in missing_libs)
    empty = sum(1 for i in range(len(p_order)) for r in range(n_rep) if p_counts[0][i][r] is None)
    pbr_bricks = sixteen_s_bricks(
        "zhou_lab_27ws_bug_trap_reactor_2020_ASV", "2020 Fields Lab packed-bed reactors inoculated from the 2019 27-well survey bug traps", p_common,
        f"Source: {p_src} (Raw sequencing data/V012522.esv.repseq.fasta)", p_asvs, p_seqs, p_counts, p_comm_dim,
        [f"Counts are the Zhou Lab's raw ESV table (no cleanup or resampling; {min(p_depths):,} to {max(p_depths):,} reads per library), four MiSeq rounds (2020-09-08, 2020-12-01, 2021-10-11, 2022-01-25)",
         f"Effluent communities have two technical replicates, endpoint sediment three and filtered effluent one; the {empty} cells without a library have null counts, "
         f"including the {len(missing_libs)} libraries that failed amplification ({missing_txt})",
         f"Source: {p_src} (Raw sequencing data/V012522.esv.table.txt; sample information in Raw ESV table/BugTrapReactor_SampleInfo_V012522_Metadata Sheet.xlsx)"],
        p_tax, p_conf, f"Source: {p_src} (Raw sequencing data/V012522.esv.classification.txt)", rep_dim)
    for o in pbr_bricks:
        oo.write_brick(o)
    pbr_seq = [{"process": "16S Sequencing <PROCESS:0000020>", "person": "Ying Fu <ENIGMA:0000168>", "campaign": CAMPAIGN, "protocol": PROTOCOL,
                "date_start": "2020-09-08", "date_end": "2022-01-25", "input_objects": f"Community: {n}",
                "output_objects": ", ".join(f"Generic: {o['name']}" for o in pbr_bricks)} for n in p_names]
    new_otus += [a for a in p_asvs if a not in otus and a not in new_otus]
    new_taxa |= {x for a in p_asvs for x in p_tax[a] if x and x not in taxa}
    summary["reactor_16S"] = {"asvs": len(p_asvs), "communities": len(p_order), "libraries": len(p_cols), "empty_cells": empty, "failed": missing_txt}

    # ---------------- static and process files
    ids = oo.ncbi_ids(new_taxa)
    def write(name, header, rows):
        with (ab.STATIC_OUT / name).open("w", newline="") as h:
            w = csv.writer(h, delimiter="\t", lineterminator="\n")
            w.writerow(header)
            w.writerows(rows)
    write(f"Protocol_additions_27ws_bug_traps_{RELEASE}.tsv", ["name", "description", "link"], [[PROTOCOL, PROTOCOL_TEXT, PROTOCOL_LINK]])
    write(f"Taxon_additions_27ws_bug_traps_{RELEASE}.tsv", ["name", "ncbi_taxid"], [[t, ids.get(t, "null")] for t in sorted(new_taxa)])
    write(f"OTU_additions_27ws_bug_traps_{RELEASE}.tsv", ["name"], [[a] for a in new_otus])
    write(f"Condition_additions_27ws_bug_traps_{RELEASE}.tsv", ["name"], cond_rows)
    write(f"Sample_additions_27ws_bug_traps_{RELEASE}.tsv", ["name", "location", "depth", "elevation", "date", "time", "timezone", "material", "env_package", "description"], sample_rows)
    write(f"Community_additions_27ws_bug_traps_{RELEASE}.tsv", ["name", "community_type", "sample", "parent_community", "condition", "defined_strains", "description"], community_rows + pbr_comm)
    write(f"Reads_additions_27ws_bug_traps_{RELEASE}.tsv", ["name", "read_count", "read_type", "sequencing_technology", "link"], reads_rows)
    pfiles = {"sampling": sampling, "16s_sequencing": sequencing + pbr_seq, "enrichment": enrich, "assay_geochemistry": geochem, "classify_otus": classify}
    for k, rows in pfiles.items():
        write_process(ab.PROCESS_OUT / f"process_{k}_27ws_bug_traps_{RELEASE}.tsv", rows)
    bricks = [o["name"] for o in bt_bricks + pbr_bricks] + [metals["name"]]
    summary.update({"samples": len(sample_rows), "communities": len(community_rows) + len(pbr_comm), "reads": len(reads_rows), "conditions": len(cond_rows),
                    "new_otus": len(new_otus), "new_taxa": len(new_taxa), "new_taxa_with_ncbi": sum(1 for t in new_taxa if t in ids), "bricks": bricks,
                    "metals_below_dl": dict(dl_cells)})
    (ab.REPORT_OUT / "build_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    static = [f"Protocol_additions_27ws_bug_traps_{RELEASE}.tsv", f"Taxon_additions_27ws_bug_traps_{RELEASE}.tsv", f"OTU_additions_27ws_bug_traps_{RELEASE}.tsv", f"Condition_additions_27ws_bug_traps_{RELEASE}.tsv",
              f"Sample_additions_27ws_bug_traps_{RELEASE}.tsv", f"Community_additions_27ws_bug_traps_{RELEASE}.tsv", f"Reads_additions_27ws_bug_traps_{RELEASE}.tsv"]
    jsons = [b.rsplit(".", 1)[0] + ".json" for b in bricks]
    files = [f"static/{n}" for n in static] + [f"process/process_{k}_27ws_bug_traps_{RELEASE}.tsv" for k in pfiles] + [f"json/{j}" for j in jsons]
    (OUT / "files_to_import.txt").write_text("\n".join(files) + "\n")
    (OUT / "import_to_coral.py").write_text("\n".join(
        ["# Paste into the CORAL import notebook after staging every file in files_to_import.txt", "",
         "# Cell 1: static objects, in dependency order."]
        + [f"toolx.update_core('{n}', '{n.split('_additions')[0]}')" for n in static]
        + ["", "# Cell 2: sampling, enrichment and bug-trap sequencing processes.",
           f"toolx.upload_process('Sampling', 'process_sampling_27ws_bug_traps_{RELEASE}.tsv')",
           f"toolx.upload_process('Enrichment', 'process_enrichment_27ws_bug_traps_{RELEASE}.tsv')", "",
           "# Cell 3: the bricks."] + [f"toolx.upload_brick('{j}')" for j in jsons]
        + ["", "# Cell 4: processes that output bricks.",
           f"toolx.upload_process('16S Sequencing', 'process_16s_sequencing_27ws_bug_traps_{RELEASE}.tsv')",
           f"toolx.upload_process('Classify OTUs', 'process_classify_otus_27ws_bug_traps_{RELEASE}.tsv')",
           f"toolx.upload_process('Assay Geochemistry', 'process_assay_geochemistry_27ws_bug_traps_{RELEASE}.tsv')", ""]))
    (OUT / "README.md").write_text(README.format(release=RELEASE, n_comm=len(community_rows) + len(pbr_comm), n_pbr=len(pbr_comm), n_otu=len(new_otus), n_taxa=len(new_taxa),
                                                 bt_asv=len(asvs), p_asv=len(p_asvs), empty=empty))
    print(json.dumps(summary, indent=1))


README = """# 27-well survey bug traps and bug-trap reactors (IMPORT_PLAN D6 + D7), {release}

Built by `tools/build_27ws_bug_trap_coral_import.py` (regenerates this file) from the team-drive folder
`2019_Summer／Fall_27-Well Survey/`: Zhou bug-trap 16S V210507ASV, the Hazen field log Bug Traps sheet,
the Adams bug-trap metals workbook (060921) and the Fields PBR V012522.ESV.zip. Needs COMO with
ME:0000122 time elapsed as a dimension variable and ME:0000516 baseline control
(`coral_import/ontology_update_20261028*`, installed 2026-10-28).

| Brick | Shape | Notes |
| --- | --- | --- |
| zhou_lab_27ws_bug_trap_2019_ASV_16S | [{bt_asv} ASV] | clean-table fasta; all ASVs already OTUs in CORAL (Brick0000452) |
| zhou_lab_27ws_bug_trap_2019_ASV_count | [{bt_asv} ASV x 55 community] | clean (chloroplast-free, not resampled) counts; last column = baseline control (starting sediment), no community; deployment date and time elapsed (weeks) |
| zhou_lab_27ws_bug_trap_2019_ASV_taxonomy | [{bt_asv} ASV x 6 rank] | SILVA 132 D_0-D_5 from the raw classification (the clean file shows order 11-24 as 24-Nov); ASV confidence |
| adams_metals_27ws_bug_trap_2019 | [55 sample x 52 element] | mg/kg concentration, SD, below DL; element detection limit (ppm, Te null) on the molecule dimension; last row = baseline control |
| zhou_lab_27ws_bug_trap_reactor_2020_ASV_16S | [{p_asv} ASV] | |
| zhou_lab_27ws_bug_trap_reactor_2020_ASV_count | [{p_asv} ASV x 30 community x 3 technical replicate] | raw ESV table; {empty} empty cells null (incl. 2 failed libraries) |
| zhou_lab_27ws_bug_trap_reactor_2020_ASV_taxonomy | [{p_asv} ASV x 6 rank] | |

Static additions: 54 Samples (`<well>-<retrieval date>-TP<n>-R<n>`, sediment; depth estimated as 0.5 ft
below the Aqua TROLL 600; description carries the Hazen trap ID), {n_comm} Communities (54 bug traps, {n_pbr}
reactor communities `PBR<n>-<date>`, `-FILTERED`, `-SED`, type enrichment, parent = the week-6 8-week trap of
the reactor's well, Condition pH + nitrate), 54 Reads, 3 Conditions, {n_otu} OTUs, {n_taxa} Taxa, Protocol
`fan-ning-2021-qiime2-silva132`. Reactor reads are not on Drive, so reactor 16S Sequencing processes go
Community -> bricks. The starting sediment's FRC source is undocumented (question for Katie Walker).
"""


if __name__ == "__main__":
    main()
