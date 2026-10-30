#!/usr/bin/env python3
"""Build the CORAL package that corrects the Zhou Lab 16S Classify OTUs protocols.

* Two new Protocols, from each dataset's own Zhou Lab ReadMe:
  - li-ning-2024-pump-test-dada2-silva138.1  (2024 SSO pump test, ReadMe v20240722)
  - fan-ning-2023-dada2-silva138.1           (2023 SSO sediment, ReadMe v20230726b)
* The 2024 SSO pilot time series had Reads but no processes: 40 16S Sequencing rows
  (Sample -> Reads) and 40 Classify OTUs rows (Reads -> its three ASV bricks) citing
  li-ning-2024-dada2-silva138.1, whose text matches that ReadMe (v20241029b) exactly.
* An arangosh script that changes the protocol attribute, in place, of the 14 pump-test and
  37 sediment Classify OTUs processes from ning-lui-2021-qiime2 to the new protocols
  (dry run by default; --apply writes a before-state backup, updates and verifies).

    python tools/build_zhou_16s_protocol_fix.py --export <dir with a fresh static_tsv>
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RELEASE = "20261027"
OUT = REPO / f"coral_import/zhou_16s_protocol_fix_{RELEASE}"
CAMPAIGN = "Subsurface Observatory <ENIGMA:0000166>"
OLD = "ning-lui-2021-qiime2"
AMPLICON = ("Amplicons: V4 region of prokaryotic 16S rRNA genes, primers 515F (GTGCCAGCMGCCGCGGTAA) and 806R (GGACTACHVGGGTWTCTAAT), "
            "two-step PCR with phasing primers, Illumina MiSeq.")
DADA2_COMMON = ("QIIME2 (version 2021.2) was used to perform the ASV-based processing. After barcode and primer sequences were trimmed with zero maximum error, "
                "sequencing data were processed by DADA2 to identify exact amplicon sequence variants (ASV). The method 'consensus' was used to remove chimeras; "
                "samples are denoised independently; forward and reverse truncate positions are {f} and {r}, respectively, after quality trim with a quality score 2; "
                "maximal expected error score is 2.0 when combining forward and reverse sequences. The ASVs were identified taxonomically by RDP Naive Bayesian "
                "Classifier algorithm in DADA2 with a confidence threshold of 0.5, based on the Silva database (v138.1; silva_nr99_v138.1_train_set.fa.gz from "
                "https://benjjneb.github.io/dada2/training.html). After classification, ASVs identified as Chloroplast, Mitochondria, Eukaryota, or unclassified "
                "kingdom were removed.")
PROTOCOLS = {
    "li-ning-2024-pump-test-dada2-silva138.1": {
        "match": r"Brick0000462",  # zhou_lab_sso_pump_test_ASV_count
        "expected": 14,
        "link": "https://drive.google.com/file/d/1s_6GDvXaoldqGgxAT5noFwdvJDfpFqOD/view",  # ReadMe_SSOfilter_16S_v20240722.docx, team drive
        "text": ("Zhou Lab 16S rRNA gene ASV processing used for the 2024 SSO pump test (ReadMe v20240722; Hui Li, Daliang Ning, Jonathan Michael, Yupeng Fan, "
                 "Ying Fu, Jizhong Zhou). " + DADA2_COMMON.format(f=252, r=203) + " ASVs that had a >1X read in the negative control compared to any of the 14 "
                 "samples were also removed as suspected contamination ASVs (clean table). The clean ASV table was then resampled to the same number of sequences "
                 "in each sample. " + AMPLICON),
    },
    "fan-ning-2023-dada2-silva138.1": {
        "match": r"Brick0000459",  # zhou_lab_sso_sediment_ASV_count
        "expected": 37,
        "link": "https://drive.google.com/file/d/1ca73Yh8KUGSfjrWnGC4U2sO-2QRjsD9y/view",  # ReadMe_SSOSediment_16S_v20230726b.docx, team drive
        "text": ("Zhou Lab 16S rRNA gene ASV processing used for the 2023 SSO sediment cores (ReadMe v20230726b; Yupeng Fan, Daliang Ning, Jonathan Michael, "
                 "Muhe Diao, Ying Fu, Jizhong Zhou). DNA was extracted from 5 g sediment by freeze-grinding and purified with the DNeasy PowerSoil Pro Kit "
                 "(bead tubes not used). " + DADA2_COMMON.format(f=200, r=160) + " The prokaryotic ASV sequences were aligned using MAFFT in QIIME2, without "
                 "mask, and a phylogenetic tree was built by FastTree constrained with a guide tree of prokaryotes from the All-Species Living Tree. The ASV "
                 "table was then resampled to the same number of sequences in each sample. 15 low-DNA samples used 12 and 23 PCR cycles in the two steps "
                 "(others 10 and 20). " + AMPLICON),
    },
}
PILOT = {"protocol": "li-ning-2024-dada2-silva138.1", "seq_date": "2024-10-11", "version_date": "2024-10-29",
         "bricks": ["zhou_lab_sso_pilot_time_series_ASV_16S.ndarray", "zhou_lab_sso_pilot_time_series_ASV_count.ndarray",
                    "zhou_lab_sso_pilot_time_series_ASV_taxonomy.ndarray"],
         "count_brick": "Brick0000479"}


def read_tsv(path: Path):
    csv.field_size_limit(10 ** 9)
    return list(csv.DictReader(path.open(), delimiter="\t"))


def write_tsv(path: Path, header, rows):
    with path.open("w", newline="") as h:
        w = csv.writer(h, delimiter="\t", lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True, help="directory holding a fresh CORAL static_tsv export")
    ap.add_argument("--brick-csv", default=str(REPO / "sync-coral-to-berdl/exports/sync-20261020-150557/coral_export/brick_csv"))
    a = ap.parse_args()
    E, BC = Path(a.export), Path(a.brick_csv)
    if OUT.exists():
        raise FileExistsError(OUT)
    for d in ("static", "process", "scripts", "reports"):
        (OUT / d).mkdir(parents=True)
    protocols = {r["name"] for r in read_tsv(E / "Protocol.tsv")}
    if PILOT["protocol"] not in protocols:
        raise ValueError(f"{PILOT['protocol']} is not in CORAL yet")
    clash = [p for p in PROTOCOLS if p in protocols]
    if clash:
        raise ValueError(f"protocols already in CORAL: {clash}")
    write_tsv(OUT / f"static/Protocol_additions_{RELEASE}.tsv", ["name", "description", "link"],
              [[n, p["text"], p["link"]] for n, p in PROTOCOLS.items()])

    # Processes to patch in place.
    procs = read_tsv(E / "Process.tsv")
    patches = []
    for name, p in PROTOCOLS.items():
        rows = [r for r in procs if r["process"].startswith("Classify OTUs") and r.get("protocol_id") == OLD and re.search(p["match"] + r"\b", r["output_objects"])]
        if len(rows) != p["expected"]:
            raise ValueError(f"{name}: expected {p['expected']} processes, found {len(rows)}")
        patches += [{"id": r["id"], "from": OLD, "to": name, "inputs": r["input_objects"], "outputs": r["output_objects"]} for r in rows]

    # Pilot time series: Sample -> Reads and Reads -> bricks.
    lines = (BC / f"{PILOT['count_brick']}.csv").read_text().split("\n")
    i = next(k for k, l in enumerate(lines) if l.startswith("dmeta,2"))
    comms = []
    for l in lines[i + 1:]:
        m = re.match(r"\d+,(\S+) <", l)
        if not m:
            break
        comms.append(m.group(1))
    samples = {r["name"] for r in read_tsv(E / "Sample.tsv")}
    reads = {r["name"]: r["id"] for r in read_tsv(E / "Reads.tsv")}
    missing = [c for c in comms if c not in samples or f"{c}.reads" not in reads]
    if len(comms) != 40 or missing:
        raise ValueError(f"pilot time series: {len(comms)} communities, missing {missing[:5]}")
    rid = {reads[f"{c}.reads"] for c in comms}
    existing = [r["id"] for r in procs if any(re.search(re.escape(x) + r"\b", r["input_objects"] + r["output_objects"]) for x in rid)]
    if existing:
        raise ValueError(f"pilot time-series Reads already have processes: {existing[:5]}")
    seq = [{"process": "16S Sequencing <PROCESS:0000020>", "person": "Ying Fu <ENIGMA:0000168>", "campaign": CAMPAIGN, "protocol": "null",
            "date_start": PILOT["seq_date"], "date_end": PILOT["seq_date"], "input_objects": f"Sample: {c}", "output_objects": f"Reads: {c}.reads"} for c in comms]
    cls = [{"process": "Classify OTUs <PROCESS:0000031>", "person": "Daliang Ning <ENIGMA:0000092>", "campaign": CAMPAIGN, "protocol": PILOT["protocol"],
            "date_start": PILOT["version_date"], "date_end": PILOT["version_date"], "input_objects": f"Reads: {c}.reads",
            "output_objects": ", ".join(f"Generic: {b}" for b in PILOT["bricks"])} for c in comms]
    hdr = ["process", "person", "campaign", "protocol", "date_start", "date_end", "input_objects", "output_objects"]
    write_tsv(OUT / f"process/process_16s_sequencing_sso_pilot_time_series_{RELEASE}.tsv", hdr, [[r[k] for k in hdr] for r in seq])
    write_tsv(OUT / f"process/process_classify_otus_sso_pilot_time_series_{RELEASE}.tsv", hdr, [[r[k] for k in hdr] for r in cls])

    js = (Path(__file__).parent / "zhou_16s_protocol_patch_template.js").read_text()
    js = js.replace("__PATCHES__", json.dumps([{"id": p["id"], "from": p["from"], "to": p["to"]} for p in patches]))
    (OUT / "scripts/patch_classify_otus_protocols.js").write_text(js)
    (OUT / "reports/patches.json").write_text(json.dumps(patches, indent=1) + "\n")
    files = [f"static/Protocol_additions_{RELEASE}.tsv", f"process/process_16s_sequencing_sso_pilot_time_series_{RELEASE}.tsv",
             f"process/process_classify_otus_sso_pilot_time_series_{RELEASE}.tsv"]
    (OUT / "files_to_import.txt").write_text("\n".join(files) + "\n")
    (OUT / "import_to_coral.py").write_text("\n".join([
        "# Paste into the CORAL import notebook after staging every file in files_to_import.txt",
        f"toolx.update_core('Protocol_additions_{RELEASE}.tsv', 'Protocol')",
        f"toolx.upload_process('16S Sequencing', 'process_16s_sequencing_sso_pilot_time_series_{RELEASE}.tsv')",
        f"toolx.upload_process('Classify OTUs', 'process_classify_otus_sso_pilot_time_series_{RELEASE}.tsv')", ""]))
    print(json.dumps({"protocols": list(PROTOCOLS), "patches": {n: sum(1 for p in patches if p["to"] == n) for n in PROTOCOLS},
                      "pilot_sequencing_rows": len(seq), "pilot_classify_rows": len(cls)}, indent=1))


if __name__ == "__main__":
    main()
