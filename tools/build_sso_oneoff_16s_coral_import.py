#!/usr/bin/env python3
"""Build the CORAL import package for the SSO one-off 16S ASV sets (IMPORT_PLAN batch D1-D3).

Three Zhou Lab amplicon sets from the 2024 SSO one-off sampling, loaded like the existing
SSO pump-test and pilot time-series sets (resampled tables):

* colloids  -- 2024-05-29 colloid filter fractions (Murtazina/Hazen), 8 filters, 5 L each
* ftp6      -- 2024-08-12 upper-well AOA survey (Arkin), 12 filters, 10 L each
* ftp7      -- 2024-08-20 microcalorimetry activity-assay water (Shreve/Fields), 4 filters, 1.2 L each

Per set: `zhou_lab_sso_oneoff_<set>_2024_ASV_16S` [ASV], `..._ASV_count` [ASV x community] and
`..._ASV_taxonomy` [taxon ID, confidence x ASV x taxonomic level]. Static additions: the filter
Samples, their same-named Communities, Reads, new OTU (ASV) names and new Taxon names.
Processes: Sampling (Location -> Sample + Community), 16S Sequencing (Sample -> Reads),
Classify OTUs (Reads -> bricks).

    python tools/build_sso_oneoff_16s_coral_import.py
"""
from __future__ import annotations

import csv
import gzip
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_sso_batch_ab_coral_import as ab  # noqa: E402
from build_sso_batch_ab_coral_import import T, NAMES, comment, ctx, oterm_value, sval, write_process  # noqa: E402

REPO = ab.REPO
ONEOFF = ab.DRIVE / "2023_2024_2025_One-Off Sampliing"
RELEASE = "20261020"
OUT = REPO / f"coral_import/sso_oneoff_16s_{RELEASE}"
EXPORT = REPO / "sync-coral-to-berdl/exports/sync-20261020-150557/coral_export/static_tsv"
NCBITAXON = Path("/home/coral/prod/data_import/ontologies/ncbitaxon.obo")
STAGED = Path("/tmp/claude-1000/-scratch-jmc-BERDL-ENIGMA-CORAL/e08931f7-7c7d-4424-a1ff-a5f1bad88ee0/scratchpad/stagedval")
CAMPAIGN = "Subsurface Observatory <ENIGMA:0000166>"
DATE_NAME_FIXES = {"24-Nov": "11-24", "4/29/2001": "4-29-1"}  # spreadsheet-mangled SILVA names, as in the 2026-07-24 taxonomy v2 bricks
LEVELS = [("Kingdom", "taxonomic domain", "ME:0000351"), ("Phylum", "phylum", "ME:0000252"), ("Class", "class", "ME:0000253"),
          ("Order", "order", "ME:0000254"), ("Family", "family", "ME:0000255"), ("Genus", "genus", "ME:0000256"), ("Species", "species", "ME:0000257")]
PROTOCOL = "li-ning-2024-dada2-silva138.1"
PROTOCOL_LINK = "https://drive.google.com/file/d/1cpRm7Y65Bk84oWlOUMlgko1MH4qNtbPa/view"  # ReadMe_OneOff-FTP6_16S.v20241029.docx, team drive
PROTOCOL_TEXT = (
    "Zhou Lab 16S rRNA gene ASV processing used for the 2024 SSO one-off sets (ReadMes v20240916 and v20241029; Hui Li, Daliang Ning, Ying Fu, Jizhong Zhou). "
    "QIIME2 (version 2021.2) was used to perform the ASV-based processing. After barcode and primer sequences were trimmed with zero maximum error, sequencing data were processed by DADA2 "
    "to identify exact amplicon sequence variants (ASV). The method 'consensus' was used to remove chimeras; samples are denoised independently; forward and reverse truncate positions are "
    "253 and 203, respectively, after quality trim with a quality score 2; maximal expected error score is 2.0 when combining forward and reverse sequences. The ASVs were identified "
    "taxonomically by RDP Naive Bayesian Classifier algorithm in DADA2 with a confidence threshold of 0.5, based on the Silva database (v138.1; silva_nr99_v138.1_train_set.fa.gz from "
    "https://benjjneb.github.io/dada2/training.html). After classification, ASVs identified as Chloroplast, Mitochondria, Eukaryota, or unclassified kingdom were removed. OTUs that had a "
    "1X read in the control and H2O compared to any of the SSO samples were also removed (CleanData). The cleaned ASV table was then resampled to the same number of sequences in each "
    "sample (ResampData). Amplicons: V4 region of prokaryotic 16S rRNA genes, primers 515F (GTGCCAGCMGCCGCGGTAA) and 806R (GGACTACHVGGGTWTCTAAT), two-step PCR with phasing primers, "
    "Illumina MiSeq.")
ZONE_MID_M = {"VSZ": 3.5052, "SZ1": 5.1816, "SZ2": 7.0104}

SETS = {
    "colloids": {
        "dir": ONEOFF / "2023-Murtazina-Hazen-Zhou_ colloids",
        "resamp": "SSO.OneOff.DM.V240916ASV/ResampData", "table": "SSO.DM.16S.Resamp.ASVTable.csv",
        "classif": "SSO.DM.16S.Resamp.Classif.csv", "fasta": "SSO.DM.16S.Resamp.Seq.fasta", "raw": "16S.RawSequencingData",
        "raw_link": "https://drive.google.com/drive/folders/1lPCEAu6le9rjHJWUl_7I--dYsxx2onhL",
        "date": "2024-05-29", "volume": "5 L", "seq_date": "2024-08-23", "version": "2024-09-16",
        "title": "SSO one-off colloid filter fractions (Murtazina, Hazen Lab), 2024-05-29",
        "readme": "ReadMe_SSO.OneOff.DM_16S_20240916.docx",
        "notes": ["The lab's ReadMe warns that the extraction control (processed with the 8 samples from DNA extraction on) had a high read count; controls are not in the resampled table"],
    },
    "ftp6": {
        "dir": ONEOFF / "2024-FTP6-Arkin_Zhou-UpperWellAOA",
        "resamp": "ResampData", "table": "OneOffFTP6.Resamp.ASVTable.csv",
        "classif": "OneOffFTP6.Resamp.Classification.csv", "fasta": "OneOffFTP6.Resamp.Sequence.fasta", "raw": "RawSequencingData",
        "raw_link": "https://drive.google.com/drive/folders/1o__YVsA_Vy10Uo9OxihukXReF7LfX_eu",
        "date": "2024-08-12", "volume": "10 L", "seq_date": "2024-10-11", "version": "2024-10-29",
        "title": "SSO one-off field test plan 6, upper-well ammonia-oxidizing archaea survey (Arkin), 2024-08-12",
        "readme": "ReadMe_OneOff-FTP6_16S.v20241029.docx",
        "notes": ["Per the lab's ReadMe, tubes U2-SZ2 0.1 um and U3-SZ2 0.1 um arrived broken, and two filters were identified by the lab after discussion because tubes were mislabeled: "
                  "20240812-U3-SZ1-F01 is the white-membrane tube labeled U3-SZ2-8um-10L, and 20240812-U1-SZ2-F8 is the smaller-diameter tube labeled U1-SZ1-0.1um-10L"],
    },
    "ftp7": {
        "dir": ONEOFF / "2024-FTP7-Shreve-Field_Zhou-Microcalorimetry",
        "resamp": "ResampData", "table": "OneOffFTP7.Resamp.ASVTable.csv",
        "classif": "OneOffFTP7.Resamp.Classification.csv", "fasta": "OneOffFTP7.Resamp.Sequence.fasta", "raw": "RawSequencingData",
        "raw_link": "https://drive.google.com/drive/folders/1_yJdrMG8GFf9eQ1GMShVc7v-ZcWPdMc6",
        "date": "2024-08-20", "volume": "1.2 L", "seq_date": "2024-10-11", "version": "2024-10-29",
        "title": "SSO one-off field test plan 7, microcalorimetry activity-assay water (Shreve, Fields Lab), 2024-08-20",
        "readme": "ReadMe_OneOff-FTP7_16S.v20241029.docx",
        "notes": ["The filtered water (1.2 L per well) came from the Fields Lab microcalorimetry activity assay of each well's groundwater"],
    },
}

T.update({
    "taxonomic assignment": "DA:0000067", "taxonomic abundance": "DA:0000028", "microbial sequence": "DA:0000064",
    "OTU": "ME:0000184", "OTU ID": "ME:0000222", "community": "ME:0000231", "community ID": "ME:0000233",
    "taxonomic level": "ME:0000090", "taxon ID": "ME:0000047", "confidence": "ME:0000160", "confidence unit": "ME:0000380",
    "sequence": "ME:0000282", "sequence type": "ME:0000189", "16S sequence": "ME:0000190",
    "Daliang Ning": "ENIGMA:0000092", "Ying Fu": "ENIGMA:0000168",
})


def stage_validator() -> None:
    ab.ONTOLOGIES = STAGED / "names"
    for d in ("names", "ont"):
        (STAGED / d / "context_measurement_ontology.obo").write_bytes(Path("/home/coral/prod/data_import/ontologies/context_measurement_ontology.obo").read_bytes())
    cp = (STAGED / "classpath.txt").read_text().strip()

    def run(json_path):
        proc = subprocess.run(["java", "-Xmx8g", "-cp", cp, "gov.lbl.enigma.app.CheckGenericStaged", str(json_path)], capture_output=True, text=True)
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0 and "Generic is OK!" in out, out
    ab.run_checkgeneric = run


def term(key):
    return ab.term(key)


def obj_values(names):
    return {"scalar_type": "object_ref", "object_refs": list(names), "string_values": list(names)}


def sample_name_map(key: str) -> dict[str, str]:
    """Zhou Lab output IDs -> one-off metadata-table sample names, from the lab's sample-information file."""
    s = SETS[key]
    out = {}
    if key == "colloids":
        rows = list(openpyxl.load_workbook(s["dir"] / "Sample.Information.20240916.xlsx", read_only=True, data_only=True).worksheets[0].iter_rows(values_only=True))
        for r in rows[1:]:
            if r[1] and r[1] != "NA":
                out[r[0]] = (r[1], r[2])  # metadata name, fastq name stem
    else:
        name = {"ftp6": "OneOff-FTP6-Adam_SampleInformation.v20241029.csv", "ftp7": "OneOff-FTP7-Molly_SampleInformation.v20241029.csv"}[key]
        for r in csv.DictReader((s["dir"] / name).open()):
            if r["SampleIDinMetaDataTable"] != "NA":
                out[r["SampleID"]] = (r["SampleIDinMetaDataTable"], r["SampleID"])
    for zid, (meta, _) in out.items():
        if not re.fullmatch(r"20240(529|812|820)-(EFP01|[ULM][1-9]-(VSZ|SZ[12]))-F(8|01)", meta):
            raise ValueError(f"{key}: unexpected sample name {meta}")
    return out


def read_count(raw_dir: Path, stem: str) -> int:
    """Total reads (R1 + R2), the convention of the existing SSO Reads objects."""
    total = 0
    for read in ("R1", "R2"):
        hits = sorted(raw_dir.glob(f"{stem}_*_L001_{read}_001.fastq.gz"))
        if len(hits) != 1:
            raise ValueError(f"{raw_dir.name}: {len(hits)} {read} files for {stem}")
        with gzip.open(hits[0], "rt") as h:
            n = sum(1 for _ in h)
        if n % 4:
            raise ValueError(f"{hits[0].name}: {n} lines")
        total += n // 4
    return total


def ncbi_ids(names: set[str]) -> dict[str, str]:
    found: dict[str, list[str]] = {}
    cur = None
    with NCBITAXON.open(errors="ignore") as h:
        for line in h:
            if line.startswith("id: "):
                cur = line[4:].strip()
            elif line.startswith("name: ") and cur:
                n = line[6:].strip()
                if n in names:
                    found.setdefault(n, []).append(cur)
    return {n: ids[0] for n, ids in found.items() if len(ids) == 1}


def build_set(key: str, otus: set[str]):
    s = SETS[key]
    d = s["dir"] / s["resamp"]
    rows = list(csv.reader((d / s["table"]).open()))
    hdr, body = rows[0], rows[1:]
    if hdr[0] != "ASVID":
        raise ValueError(f"{key}: table header {hdr[:2]}")
    names = sample_name_map(key)
    zids = hdr[1:]
    if set(zids) != set(names):
        raise ValueError(f"{key}: table samples {zids} differ from sample information {sorted(names)}")
    asvs = [r[0] for r in body]
    counts = [[int(x) for x in r[1:]] for r in body]
    depth = {sum(c[j] for c in counts) for j in range(len(zids))}
    if len(depth) != 1:
        raise ValueError(f"{key}: resampled depths differ {depth}")
    cl = list(csv.reader((d / s["classif"]).open()))
    ch = cl[0]
    if ch[:8] != ["ASVID", "Kingdom", "Phylum", "Class", "Order", "Family", "Genus", "Species"] or [r[0] for r in cl[1:]] != asvs:
        raise ValueError(f"{key}: classification header or order {ch[:8]}")
    conf_cols = [ch.index(f"{lv}.Confidence") if f"{lv}.Confidence" in ch else None for lv, _, _ in LEVELS]
    seqs, cur = {}, None
    for line in (d / s["fasta"]).open():
        line = line.strip()
        if line.startswith(">"):
            cur = line[1:]; seqs[cur] = ""
        elif cur:
            seqs[cur] += line
    if set(seqs) != set(asvs):
        raise ValueError(f"{key}: fasta and table ASVs differ")
    # taxonomy cells
    fixes = Counter()
    taxa, conf = [], []
    for r in cl[1:]:
        genus = None
        for j, (lv, _, _) in enumerate(LEVELS):
            v = r[1 + j]
            v = None if v in ("NA", "", "Unclassified") else v  # the colloid file writes Unclassified where the others write NA
            if v in DATE_NAME_FIXES:
                fixes[v] += 1
                v = DATE_NAME_FIXES[v]
            if lv == "Genus":
                genus = v
            if lv == "Species" and v is not None:
                if genus is None:
                    raise ValueError(f"{key} {r[0]}: species without genus")
                v = f"{genus} {v}"
            taxa.append(v)
            c = conf_cols[j]
            conf.append(None if c is None or v is None or r[c] in ("NA", "") else float(r[c]))
    communities = [names[z][0] for z in zids]
    return {"key": key, "asvs": asvs, "counts": counts, "zids": zids, "communities": communities, "seqs": seqs, "taxa": taxa, "conf": conf,
            "depth": depth.pop(), "fixes": dict(fixes), "has_conf": any(c is not None for c in conf_cols), "names": names,
            "new_otus": [a for a in asvs if a not in otus]}


def bricks_for(data: dict):
    s = SETS[data["key"]]
    stem = f"zhou_lab_sso_oneoff_{data['key']}_2024_ASV"
    title = s["title"]
    src = f"{ab.DRIVE_LABEL} {s['dir'].relative_to(ab.DRIVE)}/{s['resamp']}"
    common = [ctx("ENIGMA campaign", oterm_value("Subsurface Observatory")), ctx("personnel", oterm_value("Daliang Ning"))]
    asv_dim = {"data_type": term("OTU"), "size": len(data["asvs"]), "typed_values": [{"value_type": term("OTU ID"), "values": obj_values(data["asvs"])}]}
    notes = [comment(n) for n in s["notes"]]
    seq = {"name": f"{stem}_16S.ndarray", "description": f"Zhou Lab 16S ASV sequences, {title}",
           "data_type": term("microbial sequence"),
           "array_context": common + [comment(f"Source: {src}/{s['fasta']}")],
           "n_dimensions": 1, "dim_context": [asv_dim],
           "typed_values": [{"value_type": term("sequence"), "values": {"scalar_type": "string", "string_values": [data["seqs"][a] for a in data["asvs"]]},
                             "value_context": [ctx("sequence type", oterm_value("16S sequence"))]}]}
    comm_dim = {"data_type": term("community"), "size": len(data["communities"]), "typed_values": [{"value_type": term("community ID"), "values": obj_values(data["communities"])}]}
    count = {"name": f"{stem}_count.ndarray", "description": f"Zhou Lab 16S ASV counts (resampled to {data['depth']:,} reads per sample), {title}",
             "data_type": term("taxonomic abundance"),
             "array_context": common + [
                 ctx("method", sval(f"Each sample resampled to {data['depth']:,} reads (ResampData)")),
                 comment("Communities are the filter samples (F8 = 8 um filter, F01 = 0.1 um filter), named as in the one-off sampling metadata table"),
             ] + notes + [comment(f"Source: {src}/{s['table']}")],
             "n_dimensions": 2, "dim_context": [asv_dim, comm_dim],
             "typed_values": [{"value_type": term("count"), "value_units": term("count unit"),
                               "values": {"scalar_type": "int", "int_values": [v for row in data["counts"] for v in row]}}]}
    level_dim = {"data_type": term("taxonomic level"), "size": len(LEVELS), "typed_values": [{"value_type": term("taxonomic level"), "values": {
        "scalar_type": "oterm_ref", "oterm_refs": [i for _, _, i in LEVELS], "string_values": [n for _, n, _ in LEVELS]}}]}
    fix_note = ", ".join(f"'{a}' as '{DATE_NAME_FIXES[a]}' ({n})" for a, n in data["fixes"].items())
    tax_ctx = [
        comment("Variables: taxon ID (a CORAL Taxon; species are given as genus plus epithet; unassigned levels, NA or Unclassified in the source, are null) and the classifier confidence for each level; the source has no species confidence"
                if data["has_conf"] else
                "Variable: taxon ID (a CORAL Taxon; species are given as genus plus epithet; unassigned levels, NA or Unclassified in the source, are null). This set's classification file has no confidence columns, so the brick has no confidence variable"),
    ]
    if fix_note:
        tax_ctx.append(comment(f"Taxon names that a spreadsheet program had turned into dates are restored to the SILVA names, as in the 2026-07-24 taxonomy v2 bricks: {fix_note}"))
    tax = {"name": f"{stem}_taxonomy.ndarray", "description": f"Zhou Lab 16S ASV taxonomy, {title}",
           "data_type": term("taxonomic assignment"),
           "array_context": ([{"value_type": term("data variables type"), "value": oterm_value("taxonomic assignment")}] if data["has_conf"] else []) + common + tax_ctx + [comment(f"Source: {src}/{s['classif']}")],
           "n_dimensions": 2, "dim_context": [asv_dim, level_dim],
           "typed_values": [{"value_type": term("taxon ID"), "values": obj_values(data["taxa"])}] + (
               [{"value_type": term("confidence"), "value_units": term("confidence unit"), "values": {"scalar_type": "float", "float_values": data["conf"]}}] if data["has_conf"] else [])}
    return [seq, count, tax]


def write_brick(obj: dict) -> Path:
    """Like ab.write_brick, for the .ndarray names the existing Zhou Lab ASV bricks use."""
    ab.check_shape(obj)
    path = ab.JSON_OUT / obj["name"].replace(".ndarray", ".json")
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")
    ok, out = ab.run_checkgeneric(path)
    (ab.CHECK_OUT / (path.name + ".check")).write_text(out)
    if not ok:
        raise RuntimeError(f"CheckGeneric failed for {path}:\n{out[-3000:]}")
    print(f"built {obj['name']} shape {[d['size'] for d in obj['dim_context']]} vars {len(obj['typed_values'])} CheckGeneric OK", flush=True)
    return path


def main() -> None:
    stage_validator()
    ab.load_ontology_names()
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    ab.OUT = OUT
    ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT = (OUT / d for d in ("json", "static", "process", "check", "reports"))
    for d in (ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT):
        d.mkdir(parents=True)
    tsv = lambda name: list(csv.DictReader((EXPORT / name).open(), delimiter="\t"))
    samples = {r["name"]: r for r in tsv("Sample.tsv")}
    communities = {r["name"] for r in tsv("Community.tsv")}
    reads = {r["name"] for r in tsv("Reads.tsv")}
    otus = {r["name"] for r in tsv("OTU.tsv")}
    taxa = {r["name"] for r in tsv("Taxon.tsv")}
    locations = {r["name"] for r in tsv("Location.tsv")}

    sample_rows, community_rows, reads_rows, new_otus, new_taxa = [], [], [], [], set()
    sampling, sequencing, classify = [], [], []
    summary = {"release": RELEASE, "sets": {}}
    for key, s in SETS.items():
        data = build_set(key, otus)
        for zid in data["zids"]:
            name, stem = data["names"][zid]
            if name in samples or name in communities or f"{name}.reads" in reads:
                raise ValueError(f"{name} already in CORAL")
            well, *zone = name.split("-")[1:-1]
            filt = name.rsplit("-", 1)[1]
            loc = "EFPW01" if well == "EFP01" else f"SSO-{well}"
            if loc not in locations:
                raise ValueError(f"Location {loc} not in CORAL")
            parent = samples.get(name.rsplit("-", 1)[0])
            depth = ZONE_MID_M[zone[0]] if zone else float(parent["depth"])
            desc = (f"{'8 um' if filt == 'F8' else '0.1 um'} filter, {s['volume']} groundwater; "
                    f"16S amplicons (Zhou Lab). {s['title']}")
            if key == "ftp6" and name in ("20240812-U3-SZ1-F01", "20240812-U1-SZ2-F8"):
                desc += "; identity inferred by the Zhou Lab (mislabeled tube, see the ReadMe)"
            sample_rows.append([name, loc, f"{depth:g}", "null", s["date"], "null", "null", "ground water <ENVO:00002041>", "water <MIxS:0000017>", desc])
            community_rows.append([name, "Environmental Community <ME:0000326>", name, "null", "null", "null", "null"])
            n = read_count(s["dir"] / s["raw"], stem)
            reads_rows.append([f"{name}.reads", str(n), "Paired End Read <ME:0000113>", "Illumina <ME:0000117>", s["raw_link"]])
            sampling.append({"process": "Sampling <PROCESS:0000002>", "person": "Hazen Lab <ENIGMA:0000066>", "campaign": CAMPAIGN, "protocol": "null",
                             "date_start": s["date"], "date_end": s["date"], "input_objects": f"Location: {loc}", "output_objects": f"Sample: {name}, Community: {name}"})
            sequencing.append({"process": "16S Sequencing <PROCESS:0000020>", "person": "Ying Fu <ENIGMA:0000168>", "campaign": CAMPAIGN, "protocol": "null",
                               "date_start": s["seq_date"], "date_end": s["seq_date"], "input_objects": f"Sample: {name}", "output_objects": f"Reads: {name}.reads"})
        for a in data["new_otus"]:
            if a not in new_otus:
                new_otus.append(a)
        new_taxa |= {t for t in data["taxa"] if t is not None and t not in taxa}
        objs = bricks_for(data)
        for o in objs:
            write_brick(o)
        out = ", ".join(f"Generic: {o['name']}" for o in objs)
        for zid in data["zids"]:
            classify.append({"process": "Classify OTUs <PROCESS:0000031>", "person": "Daliang Ning <ENIGMA:0000092>", "campaign": CAMPAIGN, "protocol": PROTOCOL,
                             "date_start": s["version"], "date_end": s["version"], "input_objects": f"Reads: {data['names'][zid][0]}.reads", "output_objects": out})
        summary["sets"][key] = {"asvs": len(data["asvs"]), "communities": data["communities"], "depth": data["depth"], "new_otus": len(data["new_otus"]),
                                "date_name_fixes": data["fixes"], "bricks": [o["name"] for o in objs]}
    ids = ncbi_ids(new_taxa)
    taxon_rows = [[t, ids.get(t, "null")] for t in sorted(new_taxa)]

    def write(name, header, rows):
        with (ab.STATIC_OUT / name).open("w", newline="") as h:
            w = csv.writer(h, delimiter="\t", lineterminator="\n")
            w.writerow(header); w.writerows(rows)
    protocols = {r["name"] for r in tsv("Protocol.tsv")}
    if PROTOCOL in protocols:
        raise ValueError(f"protocol {PROTOCOL} already in CORAL")
    write(f"Protocol_additions_{RELEASE}.tsv", ["name", "description", "link"], [[PROTOCOL, PROTOCOL_TEXT, PROTOCOL_LINK]])
    write(f"Sample_additions_{RELEASE}.tsv", ["name", "location", "depth", "elevation", "date", "time", "timezone", "material", "env_package", "description"], sample_rows)
    write(f"Community_additions_{RELEASE}.tsv", ["name", "community_type", "sample", "parent_community", "condition", "defined_strains", "description"], community_rows)
    write(f"Reads_additions_{RELEASE}.tsv", ["name", "read_count", "read_type", "sequencing_technology", "link"], reads_rows)
    write(f"OTU_additions_{RELEASE}.tsv", ["name"], [[a] for a in new_otus])
    write(f"Taxon_additions_{RELEASE}.tsv", ["name", "ncbi_taxid"], taxon_rows)
    write_process(ab.PROCESS_OUT / f"process_sampling_sso_oneoff_16s_{RELEASE}.tsv", sampling)
    write_process(ab.PROCESS_OUT / f"process_16s_sequencing_sso_oneoff_{RELEASE}.tsv", sequencing)
    write_process(ab.PROCESS_OUT / f"process_classify_otus_sso_oneoff_{RELEASE}.tsv", classify)
    summary.update({"samples": len(sample_rows), "new_otus": len(new_otus), "new_taxa": len(taxon_rows), "new_taxa_with_ncbi": sum(1 for r in taxon_rows if r[1] != "null")})
    (ab.REPORT_OUT / "build_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    bricks = [b for v in summary["sets"].values() for b in v["bricks"]]
    files = [f"static/{n}" for n in (f"Protocol_additions_{RELEASE}.tsv", f"Taxon_additions_{RELEASE}.tsv", f"OTU_additions_{RELEASE}.tsv", f"Sample_additions_{RELEASE}.tsv",
                                     f"Community_additions_{RELEASE}.tsv", f"Reads_additions_{RELEASE}.tsv")] + \
            [f"process/process_sampling_sso_oneoff_16s_{RELEASE}.tsv", f"process/process_16s_sequencing_sso_oneoff_{RELEASE}.tsv"] + \
            [f"json/{b.replace('.ndarray', '.json')}" for b in bricks] + [f"process/process_classify_otus_sso_oneoff_{RELEASE}.tsv"]
    (OUT / "files_to_import.txt").write_text("\n".join(files) + "\n")
    (OUT / "import_to_coral.py").write_text("\n".join([
        "# Paste into the CORAL import notebook after uploading every file in files_to_import.txt", "",
        "# Cell 1: static objects, in dependency order.",
        f"toolx.update_core('Protocol_additions_{RELEASE}.tsv', 'Protocol')",
        f"toolx.update_core('Taxon_additions_{RELEASE}.tsv', 'Taxon')", f"toolx.update_core('OTU_additions_{RELEASE}.tsv', 'OTU')",
        f"toolx.update_core('Sample_additions_{RELEASE}.tsv', 'Sample')", f"toolx.update_core('Community_additions_{RELEASE}.tsv', 'Community')",
        f"toolx.update_core('Reads_additions_{RELEASE}.tsv', 'Reads')", "",
        "# Cell 2: sampling and sequencing processes.",
        f"toolx.upload_process('Sampling', 'process_sampling_sso_oneoff_16s_{RELEASE}.tsv')",
        f"toolx.upload_process('16S Sequencing', 'process_16s_sequencing_sso_oneoff_{RELEASE}.tsv')", "",
        "# Cell 3: the bricks."] + [f"toolx.upload_brick('{b.replace('.ndarray', '.json')}')" for b in bricks] + [
        "", "# Cell 4: the classification processes.", f"toolx.upload_process('Classify OTUs', 'process_classify_otus_sso_oneoff_{RELEASE}.tsv')", ""]))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
