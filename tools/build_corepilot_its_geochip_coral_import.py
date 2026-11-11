#!/usr/bin/env python3
"""Build the CORAL import package for the Zhou Lab 2017 Pilot Core fungal ITS OTUs and GeoChip 5.0 data
(Drive inventory item 14).

Sources (team Drive):
* `FRC Sequence Data/Zhou Lab/Pilot.ITS.sequencing.ENIGMA.version171101/` (ReadMe 2017-11-01, Renmao Tian,
  Daliang Ning, Ying Fu ... Jizhong Zhou): UPARSE 97% OTUs of ITS2 amplicons (ITS7F/ITS4R) from 53 pilot core
  sediment samples, RDP Classifier (Warcup fungal ITS trainset, June 2016). The `AllDetectedSamples` tables (raw
  counts, 1,330 OTUs x 53 samples) are loaded; the `SamplesWithEnoughSequences` tables (45 samples rarefied to
  1,250 reads) are derivable and are described in the protocol.
* `FRC_Microarray/2017_Pilot_Core_GeoChip_JoeLab/Pilot.core.GeoChip.T5S2.log.RA.csv` (ReadMe 2017-10-25, Daliang
  Ning, Weiling Shi ... Jizhong Zhou): GeoChip 5.0 180K normalized, log-transformed, total-scaled signal for 105,203
  probes x 49 samples; 0 = probe removed by the detection filters.

Sample IDs EB1060201 = well EB106, section 02, sample 01 = CORAL Sample / Environmental Community EB106-02-01
(all 59 pilot core samples and their communities already exist in CORAL).

Bricks
* zhou_lab_corepilot_2017_OTU_ITS / _OTU_count / _OTU_taxonomy (OTUs named by the MD5 of the representative
  sequence, the source label OTU1.. kept as a dimension variable)
* zhou_lab_corepilot_2017_geochip5 (probe x community, hybridization intensity) and _geochip5_taxonomy (probe x level, NCBI lineage + organism)

Static additions: 53 Reads, new OTU and Taxon names, two Protocols. Processes: ITS Sequencing (53), Classify OTUs
(53), Microarray Hybridization (1). Needs the ontology patch coral_import/ontology_update_20261107_corepilot.

    python tools/build_corepilot_its_geochip_coral_import.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_sso_batch_ab_coral_import as ab  # noqa: E402
import build_sso_oneoff_16s_coral_import as oo  # noqa: E402
from build_sso_batch_ab_coral_import import T, comment, ctx, oterm_value, sval, write_process  # noqa: E402

REPO = ab.REPO
RELEASE = "20261107"
TAG = f"corepilot_its_geochip_{RELEASE}"
OUT = REPO / f"coral_import/{TAG}"
EXPORT = REPO / "sync-coral-to-berdl/exports/sync-20261106-160159/coral_export/static_tsv"
STAGED = Path("/tmp/claude-1000/-scratch-jmc-BERDL-ENIGMA-CORAL/e08931f7-7c7d-4424-a1ff-a5f1bad88ee0/scratchpad/stagedval")
ITS_DIR = ab.DRIVE / "FRC Sequence Data/Zhou Lab/Pilot.ITS.sequencing.ENIGMA.version171101"
GEO_CSV = ab.DRIVE / "FRC_Microarray/2017_Pilot_Core_GeoChip_JoeLab/Pilot.core.GeoChip.T5S2.log.RA.csv"
ITS_FOLDER_LINK = "https://drive.google.com/drive/folders/1YxqcQhgMfSSHIklEnj949kk7scxAR3cV"
ITS_RAW_LINK = "https://drive.google.com/drive/folders/1z1ZqzLe8J-AOXyXW44tUY1rJ_CA-jTil"  # RawSequenceTagged (team drive)
ITS_README_LINK = "https://drive.google.com/file/d/1pukDjwNdih2RWbirQwVa-kEQKdMWXwlT/view"
GEO_FOLDER_LINK = "https://drive.google.com/drive/folders/1JW7sejy245VWo3HGqq3A95LfBu8d-QL0"
GEO_README_LINK = "https://drive.google.com/file/d/1H9K-k2BH2j_8FIpUntZEbt5tC4XPpjbX/view"
CAMPAIGN = "Core Pilot <ENIGMA:0000021>"
ITS_PROTO = "tian-ning-2017-uparse-rdp-warcup-its"
GEO_PROTO = "ning-2017-geochip5-ieg-pipeline"
ITS_SEQ_DATE = "2017-06-23"   # MiSeq run in the raw file names (170623-ITS-P2)
ITS_VERSION = "2017-11-01"
GEO_VERSION = "2017-10-25"
GEO_ASSAY_DATE = "2017-06-14"  # the data file was already on the team Drive (file created 2017-06-14); the ReadMe is dated 2017-10-25
ITS_PROTO_TEXT = (
    "Zhou Lab fungal ITS OTU processing for the ENIGMA 2017 Pilot Core sediment samples (ReadMe_PilotCoreITSMiseq-171101; Renmao Tian, Daliang Ning, Ying Fu, "
    "Daniel J Curtis, Yong Li, Yupeng Fan, Joy D. Van Nostrand, Liyou Wu, Jizhong Zhou). DNA: sediment stored at -80 C, microbial genomic DNA extracted by freeze-grinding "
    "(Zhou et al. 1996) and purified with the DNeasy PowerSoil kit (QIAGEN; bead tubes not used). Library: two-step PCR (Wu et al. 2015), first step with the fungal ITS "
    "primers ITS7F (GTGARTCATCGARTCTTTG) and ITS4R (TCCTCCGCTTATTGATATGC), which amplify the ITS2 region (gITS7/ITS4; our inference from the primers, the ReadMe says only 'the ITS region'), 12 cycles, second step with phasing primers, 25 cycles; Illumina MiSeq 2 x 251 bp. Processing "
    "(IEG Amplicon Sequencing Analysis Pipeline, ASAP 1.3): FastQC 0.11.5; paired ends merged with PEAR 0.9.10 (quality cutoff 20, minimum overlap 40 bp); demultiplexed "
    "with QIIME 1.9.1 split_libraries_fastq.py (zero barcode errors, quality trim 20); primers trimmed; dereplicated with USEARCH 9.2.64 fastx_uniques; OTUs clustered "
    "with UPARSE (-cluster_otus) at 97% identity, singletons and chimeras removed; OTU table by -usearch_global; representative sequences classified with the RDP Classifier "
    "(fungalits_warcup trainset, June 2016) at confidence 0.8; aligned with Clustal Omega and a FastTree phylogeny built. Deliverables: AllDetectedSamples (every sample "
    "with detectable ITS, raw counts: loaded in CORAL) and SamplesWithEnoughSequences (the 45 samples with more than 1,000 sequences, rarefied to 1,250 reads: derivable, "
    "not loaded). Missing samples had too little DNA or sequencing depth. Protocols: http://www.ou.edu/content/ieg/tools/protocols.html")
GEO_PROTO_TEXT = (
    "Zhou Lab GeoChip 5.0 180K functional gene microarray analysis of the ENIGMA 2017 Pilot Core sediment samples (ReadMe_PilotCoreGeoChip-171025-DN; Daliang Ning, "
    "Weiling Shi, Ying Fu, Daniel J Curtis, Yong Li, Yupeng Fan, Joy D. Van Nostrand, Liyou Wu, Jizhong Zhou). Metagenomic DNA (freeze-grinding extraction, DNeasy "
    "PowerSoil purification) was labeled and hybridized following the IEG protocols (Labeling of microbial community DNA 2015-10-20; Hybridizing sample for 180K "
    "2015-09-04). Negative control samples (water) showed no qualified signal. Raw data were preprocessed with the IEG microarray pipeline (http://ieg.ou.edu/microarray/): "
    "spot signals normalized by the mean signal of control spots and then by the sum of all sample spot signals; spots removed when the signal-to-noise ratio was below "
    "2.0 (with a per-slide threshold keeping the detection rate of the thermophilic negative-control probes below 5%), the coefficient of variation above 0.8, or the "
    "normalized signal below 100; remaining signals log-transformed and scaled to the same total per sample (file suffix T5S2.log.RA). 49 of the 59 pilot core samples "
    "yielded enough qualified labeled DNA. Protocols: http://www.ou.edu/content/ieg/tools/protocols.html")
T.update({"GeoChip gene category": "GEOCHIP:0000002", "ITS-2 sequence": "ME:0000194", "metagenomic gene abundance": "DA:0000027", "gene": "ME:0000059", "microarray probe name": "ME:0000522",
          "gene symbol": "ME:0000523", "kingdom": "ME:0000251", "unranked": "ME:0000503", "hybridization intensity": "ME:0000130", "dimensionless unit": "UO:0000186",
          "Core Pilot": "ENIGMA:0000021", "Zhou Lab": "ENIGMA:0000090", "Renmao Tian": "ENIGMA:0000093", "description": "ME:0000202", "category": "ME:0000013"})


ITS_LEVELS = [("Kingdom", "kingdom", "ME:0000251")] + oo.LEVELS[1:]
GEO_LEVELS = [("superkingdom", "taxonomic domain", "ME:0000351"), ("kingdom", "kingdom", "ME:0000251"), ("phylum", "phylum", "ME:0000252"), ("class", "class", "ME:0000253"),
              ("order", "order", "ME:0000254"), ("family", "family", "ME:0000255"), ("genus", "genus", "ME:0000256"), ("species", "species", "ME:0000257"),
              ("organism", "unranked", "ME:0000503")]


def stage_validator() -> None:
    ab.ONTOLOGIES = STAGED / "names"
    cp = (STAGED / "classpath.txt").read_text().strip()

    def run(json_path):
        proc = subprocess.run(["java", "-Xmx12g", "-cp", cp, "gov.lbl.enigma.app.CheckGenericStaged", str(json_path)], capture_output=True, text=True)
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0 and "Generic is OK!" in out, out
    ab.run_checkgeneric = run


def ncbi_ids_extended(names: set[str]) -> tuple[dict[str, str], dict[str, str]]:
    """NCBI taxids for taxon names: a unique exact name match first, then a unique match after normalizing punctuation (the
    Warcup trainset writes 'sp' for 'sp.' and '_' for '-' or ' '), then a unique match among NCBI synonyms (old organism names
    that NCBI has since renamed or merged, which is most of the GeoChip 5.0 design's 2014-era names). Ambiguous matches stay
    unresolved. Returns (name -> taxid, name -> how)."""
    def norm(s):
        return re.sub(r"\s+", " ", re.sub(r"[._\-]", " ", s.lower().replace("sp.", "sp"))).strip()
    exact, normed, syn = {}, {}, {}
    cur = None
    with oo.NCBITAXON.open(errors="ignore") as h:
        for line in h:
            if line.startswith("id: "):
                cur = line[4:].strip()
            elif line.startswith("name: ") and cur:
                n = line[6:].strip()
                exact.setdefault(n, set()).add(cur); normed.setdefault(norm(n), set()).add(cur)
            elif line.startswith("synonym: ") and cur:
                m = re.match(r'synonym: "([^"]+)"', line)
                if m:
                    syn.setdefault(norm(m.group(1)), set()).add(cur)
    ids, how = {}, {}
    for n in names:
        for label, table, key in (("name", exact, n), ("normalized name", normed, norm(n)), ("synonym", syn, norm(n))):
            hits = table.get(key, set())
            if len(hits) == 1:
                ids[n] = next(iter(hits)); how[n] = label; break
            if len(hits) > 1:
                how[n] = f"ambiguous {label}"; break
        else:
            how[n] = "none"
    return ids, how


def coral_name(zid: str) -> str:
    m = re.fullmatch(r"(EB\d{3})(\d\d)(\d\d)", zid)
    if not m:
        raise ValueError(f"unexpected Zhou sample ID {zid}")
    return "-".join(m.groups())


def tsv(name):
    return list(csv.DictReader((EXPORT / name).open(), delimiter="\t"))


# ------------------------------------------------------------------ ITS -----------------------------------------------------------
def read_its():
    d = ITS_DIR / "AllDetectedSamples"
    rows = list(csv.reader((d / "ENITS.V171101.All.OTU.csv").open()))
    if rows[0][0] != "OTU":
        raise ValueError("ITS OTU table header")
    zids = rows[0][1:]
    labels = [r[0] for r in rows[1:]]
    counts = [[int(float(x)) for x in r[1:]] for r in rows[1:]]
    if any(float(x) != int(float(x)) for r in rows[1:] for x in r[1:]):
        raise ValueError("non-integer ITS counts")
    seqs, cur = {}, None
    for line in (d / "ENITS.V171101.All.Rep_Seq.fasta").open():
        line = line.strip()
        if line.startswith(">"):
            cur = line[1:].split()[0]; seqs[cur] = ""
        elif cur:
            seqs[cur] += line.upper()
    if set(seqs) != set(labels):
        raise ValueError("ITS fasta and table OTUs differ")
    cl = list(csv.DictReader((d / "ENITS.V171101.All.Classification.csv").open()))
    if [r["OTU"] for r in cl] != labels:
        raise ValueError("ITS classification order differs from the table")
    taxa, unclassified = [], Counter()
    for r in cl:
        for src, _, _ in ITS_LEVELS:
            v = r[src].strip()
            if v.startswith("unclassified"):
                unclassified[src] += 1; v = None
            taxa.append(v or None)
    md5 = {lab: hashlib.md5(seqs[lab].encode()).hexdigest() for lab in labels}
    if len(set(md5.values())) != len(labels):
        raise ValueError("duplicate ITS representative sequences")
    treat = list(csv.DictReader((d / "ENITS.V171101.All.Treatment.csv").open()))
    if {r["sampleID"] for r in treat} != set(zids):
        raise ValueError("ITS treatment file samples differ from the table")
    # the lab's rarefied subset, for the comment
    k = list(csv.reader((ITS_DIR / "SamplesWithEnoughSequences/ENITS.V171101.1k.OTU.csv").open()))
    k_samples = k[0][1:]
    k_depth = {sum(int(float(r[j])) for r in k[1:]) for j in range(1, len(k[0]))}
    return {"zids": zids, "labels": labels, "counts": counts, "seqs": seqs, "taxa": taxa, "md5": md5, "unclassified": unclassified,
            "k_samples": k_samples, "k_depth": k_depth, "species_not_genus": sum(1 for r in cl if r["Species"] and not r["Species"].startswith("unclassified") and not r["Species"].startswith(r["Genus"]))}


def its_read_counts(zids: list[str]) -> dict[str, int]:
    """Reads per sample = R1 + R2 records whose header ends in --<sample> (the tagged fastq files)."""
    n = Counter()
    for z in sorted((ITS_DIR / "RawSequenceTagged").glob("tagged*_170623-ITS-P2_R*_001.zip")):
        with zipfile.ZipFile(z) as zf:
            names = zf.namelist()
            if len(names) != 1:
                raise ValueError(f"{z.name}: {names}")
            with zf.open(names[0]) as h:
                for i, line in enumerate(h):
                    if i % 4 == 0:
                        if not line.startswith(b"@"):
                            raise ValueError(f"{z.name}: bad fastq record at line {i}")
                        n[line.rstrip().rsplit(b"--", 1)[1].decode()] += 1
    missing = [s for s in zids if s not in n]
    if missing:
        raise ValueError(f"no raw reads tagged for {missing}")
    return {s: n[s] for s in zids}, {s: c for s, c in n.items() if s not in zids}


def its_bricks(its, communities):
    stem = "zhou_lab_corepilot_2017_OTU"
    labels = its["labels"]; names = [its["md5"][l] for l in labels]
    common = [ctx("ENIGMA campaign", oterm_value("Core Pilot")), ctx("personnel", oterm_value("Zhou Lab"))]
    src = f"{ab.DRIVE_LABEL} {ITS_DIR.relative_to(ab.DRIVE)}/AllDetectedSamples"
    otu_dim = {"data_type": oo.term("OTU"), "size": len(names), "typed_values": [
        {"value_type": oo.term("OTU ID"), "values": oo.obj_values(names)},
        {"value_type": oo.term("description"), "values": {"scalar_type": "string", "string_values": labels}, "value_context": [ctx("category", sval("source OTU label"))]}]}
    naming = comment("OTUs are named by the MD5 of their representative sequence (as the Zhou Lab ASV sets are); the lab's labels OTU1..OTU1330 are kept as 'source OTU label'")
    seq = {"name": f"{stem}_ITS.ndarray", "description": "Zhou Lab fungal ITS2 OTU representative sequences, 2017 Pilot Core sediment (UPARSE 97% OTUs, version 171101)",
           "data_type": oo.term("microbial sequence"), "array_context": common + [naming, comment(f"Source: {src}/ENITS.V171101.All.Rep_Seq.fasta")],
           "n_dimensions": 1, "dim_context": [otu_dim],
           "typed_values": [{"value_type": oo.term("sequence"), "values": {"scalar_type": "string", "string_values": [its["seqs"][l] for l in labels]},
                             "value_context": [ctx("sequence type", oterm_value("ITS-2 sequence"))]}]}
    comm_dim = {"data_type": oo.term("community"), "size": len(communities), "typed_values": [{"value_type": oo.term("community ID"), "values": oo.obj_values(communities)}]}
    k = min(its["k_depth"])
    count = {"name": f"{stem}_count.ndarray", "description": "Zhou Lab fungal ITS OTU counts, 2017 Pilot Core sediment: raw counts for the 53 samples with detectable ITS (version 171101)",
             "data_type": oo.term("taxonomic abundance"),
             "array_context": common + [naming,
                 comment("Communities are the existing pilot core sediment communities EB<well>-<section>-<sample> (Zhou sample ID EB1060201 = EB106-02-01); 53 of the 59 "
                         "pilot core samples had detectable ITS. Counts are the lab's AllDetectedSamples table (not rarefied; per-sample totals 1 to 7,256). The lab's "
                         f"analysis table (SamplesWithEnoughSequences) keeps the {len(its['k_samples'])} samples with more than 1,000 sequences rarefied to {k:,} reads; it "
                         "is derivable and not loaded"),
                 comment(f"Source: {src}/ENITS.V171101.All.OTU.csv")],
             "n_dimensions": 2, "dim_context": [otu_dim, comm_dim],
             "typed_values": [{"value_type": oo.term("count"), "value_units": oo.term("count unit"), "values": {"scalar_type": "int", "int_values": [v for row in its["counts"] for v in row]}}]}
    level_dim = {"data_type": oo.term("taxonomic level"), "size": len(ITS_LEVELS), "typed_values": [{"value_type": oo.term("taxonomic level"), "values": {
        "scalar_type": "oterm_ref", "oterm_refs": [i for _, _, i in ITS_LEVELS], "string_values": [n for _, n, _ in ITS_LEVELS]}}]}
    unc = ", ".join(f"{lv} {n}" for lv, n in its["unclassified"].items())
    tax = {"name": f"{stem}_taxonomy.ndarray", "description": "Zhou Lab fungal ITS OTU taxonomy (RDP Classifier, Warcup fungal ITS trainset June 2016, confidence 0.8), 2017 Pilot Core sediment (version 171101)",
           "data_type": oo.term("taxonomic assignment"),
           "array_context": common + [naming,
               comment("Variable: taxon ID (a CORAL Taxon) for kingdom to species as named by the classifier; levels the classifier left as 'unclassified_<parent>' are null "
                       f"(OTUs unclassified at: {unc}). Species are the Warcup binomials as given, {its['species_not_genus']} of which carry a different genus name than the "
                       "genus level (synonyms in the trainset, e.g. genus Pezoloma with species Rhizoscyphus ericae). The source has no per-level confidence values"),
               comment(f"Source: {src}/ENITS.V171101.All.Classification.csv")],
           "n_dimensions": 2, "dim_context": [otu_dim, level_dim],
           "typed_values": [{"value_type": oo.term("taxon ID"), "values": oo.obj_values(its["taxa"])}]}
    return [seq, count, tax]


# ------------------------------------------------------------------ GeoChip -------------------------------------------------------
def norm_label(s: str) -> str:
    s = s.replace("¨C", "-")  # a mangled en dash ("Reductive acetyl¨CCoA pathway")
    return re.sub(r"\s+", " ", s).strip()


def clean_organism(s: str):
    """The file's Organism column is a comma-split fragment for names that contained commas (e.g. 'Influenza A virus (A/.../16])' -> '16]'),
    and 'NA' where unknown: such fragments (unbalanced brackets, HTML entities, not starting with a letter) are not taxon names."""
    s = s.strip()
    if s in ("", "NA") or "&" in s or s.count("[") != s.count("]") or s.count("(") != s.count(")") or not (s[0].isalpha() or s[0] in "'["):
        return None
    return s


SHORT_MERGES = ["Nitoaromatics -> Nitroaromatics (1319 probes)", "Assimilation and N Assimilation -> N assimilation (271)", "Polycyclic aromatics moved under Aromatics (14)",
                "effector -> effector protein (4)", "Other under Aromatics -> Other aromatics (3)", "typr III secretion system -> type III secretion system (1)",
                "adhesion -> adherence (1)", "Sequestration -> Sequester under Multiple metals (1)"]


def merge_path(a: str, b: str, d: str) -> tuple[str, str, str]:
    """Near-duplicate classification paths merged at the user's request (2026-11-09), and two label typos corrected."""
    if a == "Nitrogen" and b in ("N Assimilation", "Assimilation"):
        b = "N assimilation"
    if a == "Organic Remediation" and b == "Polycyclic aromatics":
        b, d = "Aromatics", "Polycyclic aromatics"
    if a == "Organic Remediation" and b == "Aromatics" and d == "Other":
        d = "Other aromatics"  # aromatic_peroxygenase; the subcategory 'Others' holds non-aromatic genes and stays separate
    if b == "typr III secretion system":
        b = "type III secretion system"
    if d == "Nitoaromatics":
        d = "Nitroaromatics"
    if b == "Multiple metals" and d == "Sequestration":
        d = "Sequester"
    if a == "Virulence" and b == "adhesion":
        b = "adherence"
    if a == "Virulence" and b == "effector":
        b = "effector protein"
    return a, b, d


def read_geochip(resolve_terms: bool = True):
    with GEO_CSV.open(encoding="latin-1", newline="") as h:
        rows = list(csv.DictReader(h))
    hdr = list(rows[0].keys())
    if hdr[:7] != ["Genbank ID", "Gene name", "Gene category", "Sub-category1", "Sub-category2", "Organism", "Lineage"]:
        raise ValueError(f"GeoChip header {hdr[:7]}")
    zids = hdr[7:]
    ids = [r["Genbank ID"].strip() for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate GeoChip probe IDs")
    # category spellings: trim, fix the mangled dash, merge case variants to the most frequent spelling
    cols = {"Gene category": [], "Sub-category1": [], "Sub-category2": []}
    mapping = {}
    for col in cols:
        c = Counter(norm_label(r[col]) for r in rows)
        by = defaultdict(list)
        for k, n in c.items():
            by[k.lower()].append((n, k))
        # prefer a spelling with a capital first letter that is not all caps (the file's usual style), then the most frequent
        canon = {k: max(v, key=lambda x: (x[1][:1].isupper() and not x[1].isupper(), x[0]))[1] for k, v in by.items()}
        for r in rows:
            raw = r[col]; v = canon[norm_label(raw).lower()] if norm_label(raw) else None
            cols[col].append(v)
            if raw != v:
                mapping.setdefault(col, Counter())[(raw, v)] += 1
    path_merges = Counter()
    for i, old in enumerate(zip(cols["Gene category"], cols["Sub-category1"], cols["Sub-category2"])):
        new = merge_path(*old)
        if new != old:
            path_merges[(" > ".join(old), " > ".join(new))] += 1
            cols["Gene category"][i], cols["Sub-category1"][i], cols["Sub-category2"][i] = new
    values = [[float(r[z]) for z in zids] for r in rows]
    # functional category: the deepest real term of the probe's (category, subcategory 1, subcategory 2) path in the GEOCHIP ontology
    path_terms = json.loads((REPO / "coral_import/ontology_update_20261107_corepilot/production/geochip_path_terms.json").read_text()) if resolve_terms else {}
    term_name = {}
    cur = None
    for line in (REPO / "coral_import/ontology_update_20261107_corepilot/production/geochip_functional_gene_category.obo").open():
        if line.startswith("id: "):
            cur = line[4:].strip()
        elif line.startswith("name: ") and cur:
            term_name[cur] = line[6:].strip()
    cat_terms = [path_terms[" | ".join((a, b, d))] for a, b, d in zip(cols["Gene category"], cols["Sub-category1"], cols["Sub-category2"])] if resolve_terms else []
    cat_names = [term_name[i] for i in cat_terms]
    # taxonomy: the NCBI lineage string "superkingdom:Bacteria;phylum:...;species:X;" plus the organism (NCBI strain-level name) as the unranked level
    taxa, odd, na, dropped_org = [], Counter(), 0, Counter()
    for r in rows:
        lin = r["Lineage"].strip()
        d = {}
        for part in lin.strip(";").split(";"):
            if not part:
                continue
            if ":" not in part:
                odd[part] += 1; continue
            k, v = part.split(":", 1); d[k] = clean_organism(v)
            if d[k] is None and v.strip():
                dropped_org[f"{k}:{v.strip()}"] += 1
        if lin == "NA":
            na += 1
        org = clean_organism(r["Organism"])
        if org is None and r["Organism"].strip() not in ("", "NA"):
            dropped_org[r["Organism"].strip()] += 1
        for src, _, _ in GEO_LEVELS:
            taxa.append(org if src == "organism" else d.get(src))
    return {"zids": zids, "ids": ids, "genes": [r["Gene name"].strip() for r in rows], "cats": cols, "cat_terms": cat_terms, "cat_names": cat_names, "values": values, "mapping": mapping, "path_merges": path_merges, "taxa": taxa,
            "lineage_na": na, "odd_lineage_parts": dict(odd), "organism_blank": sum(1 for r in rows if r["Organism"].strip() in ("", "NA")), "dropped_organism": dict(dropped_org),
            "nonzero": sum(1 for row in values for v in row if v != 0.0), "nonnumeric_ids": [i for i in ids if not i.isdigit()]}


def geochip_bricks(geo, communities):
    src = f"{ab.DRIVE_LABEL} {GEO_CSV.relative_to(ab.DRIVE)}"
    probe_dim = {"data_type": oo.term("gene"), "size": len(geo["ids"]), "typed_values": [
        {"value_type": oo.term("microarray probe name"), "values": {"scalar_type": "string", "string_values": geo["ids"]}},
        {"value_type": oo.term("gene symbol"), "values": {"scalar_type": "string", "string_values": geo["genes"]}},
        {"value_type": oo.term("GeoChip gene category"), "values": {"scalar_type": "oterm_ref", "oterm_refs": geo["cat_terms"], "string_values": geo["cat_names"]}},
    ]}
    key_dim = {"data_type": oo.term("gene"), "size": len(geo["ids"]), "typed_values": [probe_dim["typed_values"][0]]}
    comm_dim = {"data_type": oo.term("community"), "size": len(communities), "typed_values": [{"value_type": oo.term("community ID"), "values": oo.obj_values(communities)}]}
    fixes = "; ".join(f"{col}: " + ", ".join(f"'{a}' -> '{b}' ({n})" for (a, b), n in sorted(c.items(), key=lambda x: -x[1])) for col, c in geo["mapping"].items())
    fixes += "; near-duplicate paths merged and typos corrected: " + ", ".join(f"'{a}' -> '{b}' ({n})" for (a, b), n in geo["path_merges"].most_common())
    expect = {"Nitoaromatics": 1319, "Assimilation": 271, "Polycyclic aromatics": 14, "effector ": 4, "Other ": 3, "typr": 1, "adhesion": 1, "Sequestration": 1}
    got = Counter()
    for (a, b), n in geo["path_merges"].items():
        key = "Nitoaromatics" if "Nitoaromatics" in a else "Assimilation" if "ssimilation" in a else "Polycyclic aromatics" if "Polycyclic" in a else "effector " if "effector" in a \
            else "Other " if a.endswith("> Other") else "typr" if "typr" in a else "adhesion" if "adhesion" in a else "Sequestration"
        got[key] += n
    if got != Counter(expect):
        raise ValueError(f"merge counts changed: {dict(got)}")
    n_cells = len(geo["ids"]) * len(communities)
    brick = {"name": "zhou_lab_corepilot_2017_geochip5.ndarray",
             "description": "Zhou Lab GeoChip 5.0 functional gene array signal (normalized, log-transformed, total-scaled), 2017 Pilot Core sediment, 105,203 probes x 49 samples (version 171025)",
             "data_type": oo.term("metagenomic gene abundance"),
             "array_context": [ctx("ENIGMA campaign", oterm_value("Core Pilot")), ctx("personnel", oterm_value("Zhou Lab")), ctx("instrument", sval("GeoChip 5.0 180K")),
                 comment("Value: the IEG pipeline's processed signal of each probe in each sample (normalized by control spots and by the sample's total, filtered by "
                         "signal-to-noise ratio 2.0, coefficient of variation 0.8 and normalized signal 100, log-transformed and scaled to the same total per sample; file "
                         f"suffix T5S2.log.RA); dimensionless. A value of 0 means the probe did not pass the detection filters in that sample ({n_cells - geo['nonzero']:,} "
                         f"of {n_cells:,} cells; {geo['nonzero']:,} detections). The array has about 180,000 spots and every one of the 105,203 probes listed here is detected in at least one sample, so a probe absent from this brick was most likely not detected in any sample (inferred; the ReadMe does not say). The ReadMe does not state the log base; other papers using the IEG GeoChip pipeline describe a natural log. Because each sample is rescaled to a common total after the log step, the stored values do not depend on the base"),
                 comment("Probe dimension: microarray probe name = the designer's GenBank GI number of the target gene, or an IEG in-house identifier for "
                         f"{len(geo['nonnumeric_ids'])} probes (e.g. {', '.join(geo['nonnumeric_ids'][:3])}); gene symbol = the gene or gene family; GeoChip gene "
                         "category = the deepest term of the probe's category / subcategory 1 / subcategory 2 path in the GEOCHIP ontology (a path "
                         "whose finer levels the designers left 'NA' maps to its category or subcategory term). The taxonomy of each probe's target sequence is in "
                         "zhou_lab_corepilot_2017_geochip5_taxonomy, keyed by the same probe name"),
                 comment("The ontology term names are the file's category labels, reworded where a label only makes sense with its parent (the source label is kept as a "
                         "synonym), after trimming whitespace, merging case variants to one spelling and restoring a mangled dash ('acetyl¨CCoA' -> 'acetyl-CoA'). Near-duplicate "
                         "paths were merged and typos corrected: " + "; ".join(SHORT_MERGES)),
                 comment("Communities are the existing pilot core sediment communities EB<well>-<section>-<sample> (Zhou sample ID EB1060201 = EB106-02-01); 49 of the 59 "
                         "pilot core samples yielded qualified labeled DNA"),
                 comment(f"Source: {src} (ReadMe_PilotCoreGeoChip-171025-DN.docx in the same folder)")],
             "n_dimensions": 2, "dim_context": [probe_dim, comm_dim],
             "typed_values": [{"value_type": oo.term("hybridization intensity"), "value_units": oo.term("dimensionless unit"),
                               "values": {"scalar_type": "float", "float_values": [v for row in geo["values"] for v in row]}}]}
    level_dim = {"data_type": oo.term("taxonomic level"), "size": len(GEO_LEVELS), "typed_values": [{"value_type": oo.term("taxonomic level"), "values": {
        "scalar_type": "oterm_ref", "oterm_refs": [i for _, _, i in GEO_LEVELS], "string_values": [n for _, n, _ in GEO_LEVELS]}}]}
    tax = {"name": "zhou_lab_corepilot_2017_geochip5_taxonomy.ndarray",
           "description": "Zhou Lab GeoChip 5.0 probe taxonomy: NCBI lineage and organism of each probe's target sequence, 2017 Pilot Core sediment (version 171025)",
           "data_type": oo.term("taxonomic assignment"),
           "array_context": [ctx("ENIGMA campaign", oterm_value("Core Pilot")), ctx("personnel", oterm_value("Zhou Lab")), ctx("instrument", sval("GeoChip 5.0 180K")),
               comment("Variable: taxon ID (a CORAL Taxon) for the ranks of the file's Lineage column (superkingdom as taxonomic domain, kingdom, phylum, class, order, "
                       "family, genus, species; a rank absent from the lineage is null) and, as the unranked level, the file's Organism column (the NCBI organism name "
                       f"of the target sequence, often strain-level). {geo['lineage_na']:,} probes have lineage NA, {geo['organism_blank']} no organism, and "
                       f"{sum(geo['dropped_organism'].values())} an organism or lineage fragment left by a comma split or an HTML entity in the file (e.g. '16]', 'Ostreococcus &apos'), stored as null. Probes are "
                       "the same 105,203 as in zhou_lab_corepilot_2017_geochip5, keyed by microarray probe name"),
               comment(f"Source: {src}, columns Organism and Lineage")],
           "n_dimensions": 2, "dim_context": [key_dim, level_dim],
           "typed_values": [{"value_type": oo.term("taxon ID"), "values": oo.obj_values(geo["taxa"])}]}
    return [brick, tax]


# ------------------------------------------------------------------ main ----------------------------------------------------------
def main() -> None:
    stage_validator()
    ab.load_ontology_names()
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    ab.OUT = OUT
    ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT = (OUT / d for d in ("json", "static", "process", "check", "reports"))
    for d in (ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT):
        d.mkdir(parents=True)
    samples = {r["name"] for r in tsv("Sample.tsv")}
    communities = {r["name"]: r for r in tsv("Community.tsv")}
    reads = {r["name"] for r in tsv("Reads.tsv")}
    otus = {r["name"] for r in tsv("OTU.tsv")}
    taxa = {r["name"] for r in tsv("Taxon.tsv")}
    protocols = {r["name"] for r in tsv("Protocol.tsv")}
    if {ITS_PROTO, GEO_PROTO} & protocols:
        raise ValueError("protocol exists")

    def comm_names(zids):
        out = []
        for z in zids:
            n = coral_name(z)
            c = communities.get(n)
            if n not in samples or c is None or c["sample_id"] != n or not c["community_type"].startswith("Environmental Community"):
                raise ValueError(f"{z}: no pilot core sample/environmental community {n}")
            out.append(n)
        return out

    its = read_its()
    its_comm = comm_names(its["zids"])
    counts, extra_tags = its_read_counts(its["zids"])
    geo = read_geochip()
    geo_comm = comm_names(geo["zids"])

    bricks = its_bricks(its, its_comm) + geochip_bricks(geo, geo_comm)
    for b in bricks:
        oo.write_brick(b)

    new_otus = [its["md5"][l] for l in its["labels"] if its["md5"][l] not in otus]
    new_taxa = sorted({t for t in its["taxa"] + geo["taxa"] if t is not None and t not in taxa})
    ids, how = ncbi_ids_extended(set(new_taxa))
    reads_rows = []
    for z, n in zip(its["zids"], its_comm):
        name = f"{n}.ITS.reads"
        if name in reads:
            raise ValueError(f"{name} exists")
        reads_rows.append([name, str(counts[z]), "Paired End Read <ME:0000113>", "Illumina <ME:0000117>", ITS_RAW_LINK])

    def write(name, header, rows):
        with (ab.STATIC_OUT / name).open("w", newline="") as h:
            w = csv.writer(h, delimiter="\t", lineterminator="\n"); w.writerow(header); w.writerows(rows)
    write(f"Protocol_additions_{TAG}.tsv", ["name", "description", "link"], [[ITS_PROTO, ITS_PROTO_TEXT, ITS_README_LINK], [GEO_PROTO, GEO_PROTO_TEXT, GEO_README_LINK]])
    write(f"Taxon_additions_{TAG}.tsv", ["name", "ncbi_taxid"], [[t, ids.get(t, "null")] for t in new_taxa])
    write(f"OTU_additions_{TAG}.tsv", ["name"], [[a] for a in new_otus])
    write(f"Reads_additions_{TAG}.tsv", ["name", "read_count", "read_type", "sequencing_technology", "link"], reads_rows)
    its_out = ", ".join(f"Generic: {b['name']}" for b in bricks[:3])
    seqp = [{"process": "ITS Sequencing <PROCESS:0000019>", "person": "Ying Fu <ENIGMA:0000168>", "campaign": CAMPAIGN, "protocol": "null", "date_start": ITS_SEQ_DATE,
             "date_end": ITS_SEQ_DATE, "input_objects": f"Sample: {n}", "output_objects": f"Reads: {n}.ITS.reads"} for n in its_comm]
    clsp = [{"process": "Classify OTUs <PROCESS:0000031>", "person": "Renmao Tian <ENIGMA:0000093>", "campaign": CAMPAIGN, "protocol": ITS_PROTO, "date_start": ITS_VERSION,
             "date_end": ITS_VERSION, "input_objects": f"Reads: {n}.ITS.reads", "output_objects": its_out} for n in its_comm]
    geop = [{"process": "Microarray Hybridization <PROCESS:0000054>", "person": "Daliang Ning <ENIGMA:0000092>", "campaign": CAMPAIGN, "protocol": GEO_PROTO,
             "date_start": GEO_ASSAY_DATE, "date_end": GEO_ASSAY_DATE, "input_objects": ", ".join(f"Sample: {n}" for n in geo_comm), "output_objects": ", ".join(f"Generic: {b['name']}" for b in bricks[3:])}]
    p1, p2, p3 = (ab.PROCESS_OUT / f"process_{k}_{TAG}.tsv" for k in ("its_sequencing", "classify_otus", "microarray_hybridization"))
    write_process(p1, seqp); write_process(p2, clsp); write_process(p3, geop)
    files = [f"static/{n}" for n in (f"Protocol_additions_{TAG}.tsv", f"Taxon_additions_{TAG}.tsv", f"OTU_additions_{TAG}.tsv", f"Reads_additions_{TAG}.tsv")] + \
            [f"process/{p1.name}"] + [f"json/{b['name'].replace('.ndarray', '.json')}" for b in bricks] + [f"process/{p2.name}", f"process/{p3.name}"]
    (OUT / "files_to_import.txt").write_text("\n".join(files) + "\n")
    (OUT / "import_to_coral.py").write_text("\n".join([
        "# Run on the CORAL hub after staging files_to_import.txt in data_import/data and reloading the ontologies (coral_import/ontology_update_20261107_corepilot)",
        f"toolx.update_core('Protocol_additions_{TAG}.tsv', 'Protocol')", f"toolx.update_core('Taxon_additions_{TAG}.tsv', 'Taxon')",
        f"toolx.update_core('OTU_additions_{TAG}.tsv', 'OTU')", f"toolx.update_core('Reads_additions_{TAG}.tsv', 'Reads')",
        f"toolx.upload_process('ITS Sequencing', '{p1.name}')"] + [f"toolx.upload_brick('{b['name'].replace('.ndarray', '.json')}')" for b in bricks] +
        [f"toolx.upload_process('Classify OTUs', '{p2.name}')", f"toolx.upload_process('Microarray Hybridization', '{p3.name}')", ""]))
    summary = {"release": RELEASE, "its": {"samples": len(its_comm), "otus": len(its["labels"]), "new_otus": len(new_otus), "reads_per_sample": counts,
                                           "raw_tags_not_in_table": extra_tags, "unclassified_by_level": dict(its["unclassified"]), "species_not_matching_genus": its["species_not_genus"],
                                           "rarefied_subset": {"samples": len(its["k_samples"]), "depth": sorted(its["k_depth"]) or None}},
               "geochip": {"samples": len(geo_comm), "probes": len(geo["ids"]), "nonzero": geo["nonzero"], "nonnumeric_probe_ids": geo["nonnumeric_ids"],
                           "lineage_na": geo["lineage_na"], "odd_lineage_parts": geo["odd_lineage_parts"], "organism_blank": geo["organism_blank"], "dropped_organism": geo["dropped_organism"],
                           "distinct_taxa": len({t for t in geo["taxa"] if t}), "its_distinct_taxa": len({t for t in its["taxa"] if t}),
                           "label_fixes": {col: {f"{a} -> {b}": n for (a, b), n in c.items()} for col, c in geo["mapping"].items()}},
               "new_taxa": len(new_taxa), "new_taxa_with_ncbi": len(ids), "ncbi_match_method": dict(Counter(how.values())),
               "taxa_without_ncbi": {t: how[t] for t in new_taxa if t not in ids}, "ncbi_match_by_name": how, "bricks": [b["name"] for b in bricks]}
    (ab.REPORT_OUT / "build_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("its", "ncbi_match_by_name", "taxa_without_ncbi")} | {"its": {k: v for k, v in summary["its"].items() if k != "reads_per_sample"}}, indent=1))


if __name__ == "__main__":
    main()
