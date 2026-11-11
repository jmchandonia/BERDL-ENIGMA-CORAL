#!/usr/bin/env python3
"""Build geochip_functional_gene_category.obo/.txt (prefix GEOCHIP) from the GeoChip 5.0 probe classification columns
(Gene category, Sub-category1, Sub-category2) of the pilot core GeoChip file, after the label normalization used by
tools/build_corepilot_its_geochip_coral_import.py. The three levels nest strictly (each subcategory-1 label has one
category; a subcategory-2 label is a leaf of one (category, subcategory-1) pair and repeats across pairs, e.g.
'Transport' under 24 metals, so repeated leaf names are qualified '<leaf> (<subcategory 1>)'). 'NA' placeholders are
not terms: a probe whose subcategory-2 is NA points at its subcategory-1 term, and the three 'NA <category>'
subcategory-1 placeholders point at the category.

Writes to coral_import/ontology_update_20261107_corepilot/production/ and prints the term count.
    python tools/build_geochip_category_ontology.py
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_corepilot_its_geochip_coral_import as cp  # noqa: E402

OUT = cp.REPO / "coral_import/ontology_update_20261107_corepilot/production"
PREFIX = "GEOCHIP"
SOURCE = ("GeoChip 5.0 180K functional gene array probe classification (Institute for Environmental Genomics, University of Oklahoma; "
          "Zhou Lab), as given in the probe annotation of the ENIGMA 2017 Pilot Core GeoChip data file Pilot.core.GeoChip.T5S2.log.RA.csv")


# Term names that read on their own (user review 2026-11-09): a label that only makes sense with its parent is reworded, naturally where English allows
# ("Arsenic transport"); labels that do not reword well keep the fallback "<label> (<parent>)". The source label stays as an exact synonym.
_M = "Metal Homeostasis"
_MW = {"Cadmium,Cobalt,Zinc": "Cadmium, cobalt and zinc", "Cobalt,Nickel": "Cobalt and nickel", "Cobalt/Magnesium": "Cobalt and magnesium", "Multiple metals": "Multiple metal"}
_MV = {"Transport": "transport", "Detoxification": "detoxification", "Sequester": "sequestration", "oxidation": "oxidation", "storage": "storage", "Biosynthesis": "biosynthesis"}
_CD = ("Carbon Cycling", "Carbon degradation")
_OR = "Organic Remediation"
NATURAL = {
    **{(_CD[0], _CD[1], k): f"{k} degradation" for k in ("Camphor", "Cellulose", "Chitin", "Cutin", "Hemicellulose", "Inulin", "Lactose", "Lignin", "Pectin", "Starch")},
    (*_CD, "Phospholipids"): "Phospholipid degradation", (*_CD, "Tannins"): "Tannin degradation", (*_CD, "Terpenes"): "Terpene degradation", (*_CD, "protein"): "Protein degradation",
    (*_CD, "Vanillin/Lignin"): "Vanillin and lignin degradation", (*_CD, "Other"): "Other carbon degradation",
    ("Carbon Cycling", "Carbon fixation", "multiple systems"): "Multiple carbon fixation systems",
    ("Carbon Cycling", "Methane"): "Methane metabolism", ("Carbon Cycling", "major biomolecule"): "Major biomolecule synthesis",
    (_OR, "Aromatics"): "Aromatic remediation", (_OR, "Chlorinated solvents"): "Chlorinated solvent remediation", (_OR, "Herbicides related compound"): "Herbicide remediation",
    (_OR, "Pesticides related compound"): "Pesticide remediation", (_OR, "Other Hydrocarbons"): "Other hydrocarbon remediation", (_OR, "halogenated compounds"): "Halogenated compound remediation",
    (_OR, "Others"): "Other organic remediation",
    **{(_OR, "Aromatics", k): v for k, v in (("Aromatic alpha hydroxy acid", "Aromatic alpha hydroxy acid remediation"), ("Aromatic carboxylic acid", "Aromatic carboxylic acid remediation"),
       ("BTEX and related aromatics", "BTEX and related aromatic remediation"), ("Chlorinated aromatics", "Chlorinated aromatic remediation"), ("Heterocyclic aromatics", "Heterocyclic aromatic remediation"),
       ("Nitroaromatics", "Nitroaromatic remediation"), ("Other aromatics", "Other aromatic remediation"), ("Polycyclic aromatics", "Polycyclic aromatic remediation"))},
    ("Other", "Movement"): "Cell movement", ("Other", "Phylogenetic"): "Phylogenetic marker",
    ("Secondary metabolism", "Other"): "Other secondary metabolism", ("Secondary metabolism", "antibiotic"): "Antibiotic biosynthesis",
    ("Stress", "RNA-binding protein"): "Stress RNA-binding protein", ("Stress", "stress other"): "Other stress",
    ("Sulfur", "Reduction"): "Sulfur reduction", ("Sulfur", "sulfur other"): "Other sulfur metabolism",
    ("Virulence", "Antibiotic resistance", "Degradation"): "Antibiotic degradation", ("Virulence", "Antibiotic resistance", "subunit modification"): "Antibiotic resistance subunit modification",
    ("Virulence", "Antibiotic resistance", "transporter"): "Antibiotic resistance transporter", ("Virulence", "Toxin"): "Virulence toxin", ("Virulence", "Toxin", "ergot"): "Ergot toxin",
    ("Virulence", "Toxin", "oomycete"): "Oomycete toxin", ("Virulence", "effector protein", "oomycete"): "Oomycete effector protein", ("Virulence", "elicitor", "oomycete"): "Oomycete elicitor",
    ("Virulence", "regulation"): "Virulence regulation", ("Virulence", "protease"): "Virulence protease", ("Virulence", "invasion"): "Host invasion", ("Virulence", "unclassified"): "Unclassified virulence",
    ("Virulence", "degradation"): "degradation (Virulence)", ("Virulence", "cell wall", "spore"): "spore (cell wall)", ("Virulence", "intracellular survival", "stress"): "stress (intracellular survival)",
    ("Virulence", "virulence c degradation", "Cyanide"): "Cyanide degradation",
    ("Virus", "Eukaryotic"): "Eukaryotic virus", ("Virus", "Prokaryotic"): "Prokaryotic virus",
    ("Virus", "Eukaryotic", "Infection"): "Eukaryotic virus infection", ("Virus", "Eukaryotic", "RNA silencing"): "Eukaryotic virus RNA silencing", ("Virus", "Eukaryotic", "Replication"): "Eukaryotic virus replication",
    ("Virus", "Eukaryotic", "Structural"): "Eukaryotic virus structural protein", ("Virus", "Eukaryotic", "Toxin"): "Eukaryotic virus toxin", ("Virus", "Eukaryotic", "movement protein"): "Eukaryotic virus movement protein",
    ("Virus", "Prokaryotic", "HOST RECOGNITION/STRUCTURAL"): "Prokaryotic virus host recognition and structure", ("Virus", "Prokaryotic", "LYSIS"): "Prokaryotic virus lysis",
    ("Virus", "Prokaryotic", "Replication"): "Prokaryotic virus replication", ("Virus", "Prokaryotic", "Structural"): "Prokaryotic virus structural protein",
}


def natural_name(path, fallback):
    if path[0] == _M and len(path) >= 2:
        word = _MW.get(path[1], path[1])
        return f"{word} homeostasis" if len(path) == 2 else f"{word} {_MV[path[2]]}"
    return NATURAL.get(path, fallback)


# ChEBI cross-references: only terms naming a real compound or element. Elements use the ChEBI atom IDs of the Adams metals bricks (ELEMENTS) so that
# sys_oterm_links joins to their molecule columns. They are xrefs, not is_a: 'Arsenic' here means arsenic-related genes, not the element.
METALS = {"Aluminum": ["Al"], "Arsenic": ["As"], "Boron": ["B"], "Cadmium": ["Cd"], "Cadmium,Cobalt,Zinc": ["Cd", "Co", "Zn"], "Calcium": ["Ca"], "Chromium": ["Cr"],
          "Cobalt": ["Co"], "Cobalt,Nickel": ["Co", "Ni"], "Cobalt/Magnesium": ["Co", "Mg"], "Copper": ["Cu"], "Iron": ["Fe"], "Lead": ["Pb"], "Magnesium": ["Mg"],
          "Manganese": ["Mn"], "Mercury": ["Hg"], "Nickel": ["Ni"], "Potassium": ["K"], "Selenium": ["Se"], "Silicon": ["Si"], "Silver": ["Ag"], "Sodium": ["Na"],
          "Tellurium": ["Te"], "Zinc": ["Zn"]}
ELEMENT_FALLBACK = {"Si": "CHEBI:27573", "Te": "CHEBI:30452", "Ag": "CHEBI:30512", "Se": "CHEBI:27568", "Hg": "CHEBI:16170", "Pb": "CHEBI:27889", "Cd": "CHEBI:22977"}
COMPOUNDS = {"Cellulose": ["CHEBI:18246"], "Aromatic carboxylic acid": ["CHEBI:33859"], "Bacteriochlorophyll": ["CHEBI:38201"], "Bilin": ["CHEBI:35799"], "Camphor": ["CHEBI:36773"], "Carotenoid": ["CHEBI:23044"],
             "Chitin": ["CHEBI:17029"], "Chlorophyll": ["CHEBI:28966"], "Cyanide": ["CHEBI:17514"], "Enniatin": ["CHEBI:64648"], "Hemicellulose": ["CHEBI:61266"], "Inulin": ["CHEBI:15443"],
             "Lactose": ["CHEBI:17716"], "Lignin": ["CHEBI:6457"], "Melanin": ["CHEBI:89634"], "Methane": ["CHEBI:16183"], "Pectin": ["CHEBI:17309"], "Pyoluteorin": ["CHEBI:156453"],
             "Saxitoxin": ["CHEBI:34970"], "Starch": ["CHEBI:28017"], "Terpenes": ["CHEBI:35186"], "trichodiene": ["CHEBI:15861"], "Tannins": ["CHEBI:26848"], "Phospholipids": ["CHEBI:16247"],
             "Vanillin/Lignin": ["CHEBI:18346", "CHEBI:6457"], "Polycyclic aromatics": ["CHEBI:33848"]}
CHEBI_OBO = Path("/home/coral/prod/data_import/ontologies/chebi.obo")


def chebi_xrefs() -> dict[str, list[str]]:
    el = {e[0]: e[1] for e in cp.ab.ELEMENTS} | {}
    for k, v in ELEMENT_FALLBACK.items():
        el.setdefault(k, v)
    out = {name: [el[s] for s in syms] for name, syms in METALS.items()} | COMPOUNDS
    known = {}
    cur = None
    with CHEBI_OBO.open(errors="ignore") as h:
        for line in h:
            if line.startswith("id: "):
                cur = line[4:].strip()
            elif line.startswith("name: ") and cur:
                known[cur] = line[6:].strip()
    bad = sorted({i for v in out.values() for i in v if i not in known})
    if bad:
        raise ValueError(f"ChEBI IDs not in chebi.obo: {bad}")
    return out, known


def is_na(label):
    return label is None or label == "NA" or label.startswith("NA ")


def main() -> None:
    geo = cp.read_geochip(resolve_terms=False)
    c1, c2, c3 = geo["cats"]["Gene category"], geo["cats"]["Sub-category1"], geo["cats"]["Sub-category2"]
    triples = collections.Counter(zip(c1, c2, c3))
    cats = sorted(set(c1))
    sub1 = sorted({(a, b) for a, b, _ in triples if not is_na(b)})
    leaves = sorted({(a, b, d) for a, b, d in triples if not is_na(b) and not is_na(d)})
    leaf_global = collections.Counter(d for _, _, d in leaves)
    # consistency: a subcategory-1 label under one category only; a leaf label unique within its pair
    by_sub1 = collections.defaultdict(set)
    for a, b in sub1:
        by_sub1[b].add(a)
    if any(len(v) > 1 for v in by_sub1.values()):
        raise ValueError("a subcategory-1 label occurs under more than one category")
    # term names: the label itself; a subcategory or leaf label that also occurs elsewhere in the tree (at any level) is
    # qualified with its parent label, e.g. 'Transport (Arsenic)', 'Other (Stress)', so every term name is unique
    labels = collections.Counter([a for a in cats] + [b for _, b in sub1] + [d for _, _, d in leaves])
    terms = []  # (id, name, parent_id, def, synonyms)
    ids = {}
    n = 10
    def new_id():
        nonlocal n
        n += 1
        return f"{PREFIX}:{n:07d}"
    for a in cats:
        i = new_id(); ids[(a,)] = i
        terms.append((i, a, f"{PREFIX}:0000002", f"GeoChip 5.0 gene category '{a}'.", [], a))
    for a, b in sub1:
        i = new_id(); ids[(a, b)] = i
        name = natural_name((a, b), f"{b} ({a})" if labels[b] > 1 else b)
        terms.append((i, name, ids[(a,)], f"GeoChip 5.0 gene subcategory '{b}' of category '{a}'.", [b] if name != b else [], b))
    for a, b, d in leaves:
        i = new_id(); ids[(a, b, d)] = i
        name = natural_name((a, b, d), f"{d} ({b})" if labels[d] > 1 else d)
        terms.append((i, name, ids[(a, b)], f"GeoChip 5.0 gene subcategory '{d}' of '{b}' (category '{a}').", [d] if name != d else [], d))
    extra = {"N assimilation": ["Assimilation", "N Assimilation"], "Nitroaromatic remediation": ["Nitoaromatics"], "type III secretion system": ["typr III secretion system"],
             "Multiple metal sequestration": ["Sequestration"], "adherence (Virulence)": ["adhesion"], "effector protein": ["effector"]}  # merged or corrected source labels
    terms = [(i, name, parent, d, syns + extra.get(name, []), label) for i, name, parent, d, syns, label in terms]
    names = collections.Counter(t[1] for t in terms)
    dup = [k for k, v in names.items() if v > 1]
    if dup:
        raise ValueError(f"duplicate term names {dup}")
    # the deepest real term of each probe path, for the brick builder
    path_term = {}
    for a, b, d in triples:
        key = (a, b, d) if (a, b, d) in ids else (a, b) if (a, b) in ids else (a,)
        path_term[(a, b, d)] = ids[key]
    obo = ["format-version: 1.4", "ontology:geochip", "date: 09:11:2026 12:00", "saved-by: jmc",
           "auto-generated-by: tools/build_geochip_category_ontology.py (coral_import/ontology_update_20261107_corepilot)",
           "import: context_measurement_ontology.obo", "",
           "[Term]", f"id: {PREFIX}:0000000", "name: term", "namespace: geochip.ontology", 'def: "Root of the GeoChip functional gene category ontology." []', "",
           "[Term]", f"id: {PREFIX}:0000001", "name: GeoChip functional gene category", "namespace: geochip.ontology",
           f'def: "Functional classification of the genes targeted by GeoChip probes: a category (e.g. Carbon Cycling), a subcategory (e.g. Carbon degradation) and, where the array designers gave one, a finer subcategory (e.g. Cellulose). Source: {SOURCE}." []',
           f"is_a: {PREFIX}:0000000 ! term", "is_a: ME:0000001", "",
           "[Term]", f"id: {PREFIX}:0000002", "name: GeoChip gene category", "namespace: geochip.ontology",
           'property_value: data_type "oterm_ref" xsd:string', 'property_value: is_microtype "true" xsd:boolean', 'property_value: is_valid_data_variable "true" xsd:boolean',
           'property_value: is_valid_dimension "true" xsd:boolean', 'property_value: is_valid_dimension_variable "true" xsd:boolean', 'property_value: is_valid_property "true" xsd:boolean',
           'def: "GeoChip functional gene category assigned to a probe or gene; the value is the deepest category term the array designers gave." []',
           f"xref: ORef:{PREFIX}:0000002", f"is_a: {PREFIX}:0000001 ! GeoChip functional gene category", ""]
    parent_name = {t[0]: t[1] for t in terms} | {f"{PREFIX}:0000002": "GeoChip gene category"}
    xrefs, chebi_names = chebi_xrefs()
    missing = sorted(set(xrefs) - {t[5] for t in terms})
    if missing:
        raise ValueError(f"xrefs for terms not in the ontology: {missing}")
    for i, name, parent, d, syns, label in terms:
        obo += ["[Term]", f"id: {i}", f"name: {name}", "namespace: geochip.ontology", f'def: "{d}" []'] + [f'synonym: "{s}" EXACT []' for s in syns] + \
               [f"xref: {x}" for x in xrefs.get(label, [])] + [f"is_a: {parent} ! {parent_name[parent]}", ""]
    (OUT / "geochip_functional_gene_category.obo").write_text("\n".join(obo))
    # the .txt tree in the style of the other CORAL ontology .txt files
    kids = collections.defaultdict(list)
    for i, name, parent, _, syns, _label in terms:
        kids[parent].append((i, name, syns))
    lines = ["GeoChip functional gene category", "  is_a: ME:0000001", "  *GeoChip gene category:"]
    def walk(parent, depth):
        for i, name, syns in kids[parent]:
            lines.append("  " * depth + name)
            for s in syns:
                lines.append("  " * (depth + 1) + f"alias: {s}")
            walk(i, depth + 1)
    walk(f"{PREFIX}:0000002", 2)
    (OUT / "geochip_functional_gene_category.txt").write_text("\n".join(lines) + "\n")
    (OUT / "geochip_path_terms.json").write_text(json.dumps({" | ".join(k): v for k, v in sorted(path_term.items())}, indent=1) + "\n")
    print("ChEBI xrefs:", len(xrefs), "terms,", sum(map(len, xrefs.values())), "links")
    for name, ids_ in sorted(xrefs.items()):
        print(f"  {name}: " + ", ".join(f"{x} {chebi_names[x]}" for x in ids_))
    print(f"terms: {len(cats)} categories + {len(sub1)} subcategories + {len(leaves)} leaves = {len(terms)} (+ root, class, microtype); paths {len(path_term)}")


if __name__ == "__main__":
    main()
