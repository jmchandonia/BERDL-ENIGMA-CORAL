#!/usr/bin/env python3
"""Build replacement bricks with corrected ChEBI molecule terms (review: coral_import/CHEBI_MIXUP_REVIEW_20261112.md).

Each affected current brick is rebuilt from the JSON the CORAL hub stores for it (data_store/<BrickID>, copied read-only
to --stored), with only the wrong or imprecise molecule terms replaced, a new version name, and an Update Data process
from the old brick. Nothing else in a brick changes.

Group A (wrong compound, an element symbol resolved to another term): Brick0000059, 62, 72, 73, 81.
Group B (right compound, imprecise form): phosphorus(.), uranium(0), L-valine / L-asparagine / L-histidine / glycine residue.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import build_sso_batch_ab_coral_import as ab  # noqa: E402
import build_sso_oneoff_16s_coral_import as oo  # noqa: E402
from build_sso_batch_ab_coral_import import comment, write_process  # noqa: E402

OUT = REPO / "coral_import" / "chebi_term_fix_20261112"
EXPORT = REPO / "sync-coral-to-berdl/exports/sync-20261112-152215/berdl_upload/data"
TODAY = "2026-11-12"

# imprecise form -> intended term, wherever it occurs in an affected brick
COMMON = {"CHEBI:30207": "CHEBI:28659",   # phosphorus(.) -> phosphorus atom
          "CHEBI:49936": "CHEBI:27214",   # uranium(0) -> uranium atom
          "CHEBI:29947": "CHEBI:15428",   # glycine residue -> glycine
          "CHEBI:50347": "CHEBI:17196",   # L-asparagine residue -> L-asparagine
          "CHEBI:29979": "CHEBI:15971",   # L-histidine residue -> L-histidine
          "CHEBI:30015": "CHEBI:16414"}   # L-valine residue -> L-valine (growth plates)
# element symbols that were resolved to another compound
ELEMENT = {"CHEBI:25094": "CHEBI:26216",  # lysine -> potassium atom (K)
           "CHEBI:50342": "CHEBI:28659",  # L-proline residue -> phosphorus atom (P)
           "CHEBI:30015": "CHEBI:27698",  # L-valine residue -> vanadium atom (V)
           "CHEBI:29954": "CHEBI:27998",  # L-tryptophan residue -> tungsten (W)
           "CHEBI:30000": "CHEBI:27214",  # L-selenocysteine residue -> uranium atom (U)
           "CHEBI:73891": "CHEBI:49631",  # Gly-D-Ala -> gallium atom (Ga)
           "CHEBI:47217": "CHEBI:27563",  # arsane -> arsenic atom (As)
           "CHEBI:17909": "CHEBI:27007",  # polysulfur -> tin atom (Sn)
           "CHEBI:49807": "CHEBI:25016",  # lead(2+) -> lead atom (Pb)
           "CHEBI:9141": "CHEBI:30512",   # silver(0) -> silver atom (Ag)
           "CHEBI:16170": "CHEBI:25195"}  # mercury(0) -> mercury atom (Hg)
FIELD_100WS = {"CHEBI:23116": "CHEBI:17996",  # chlorine atom -> chloride
               "CHEBI:22972": "CHEBI:15858"}  # butyryl group -> bromide (Br)
ALT: dict[str, str] = {}  # secondary ChEBI ID -> primary ID (filled in main); older bricks still carry some secondary IDs

SPECIAL = {b: dict(COMMON, **ELEMENT) for b in ("Brick0000059", "Brick0000062", "Brick0000072", "Brick0000073")}
SPECIAL["Brick0000081"] = dict(COMMON, **ELEMENT, **FIELD_100WS)
SPECIAL["Brick0000081"].pop("CHEBI:30015")


def new_name(name):
    stem, ext = name.rsplit(".", 1)
    m = re.fullmatch(r"(.*)_v(\d+)", stem)
    return f"{m.group(1)}_v{int(m.group(2)) + 1}.{ext}" if m else f"{stem}_v2.{ext}"


def flatten(v):
    while v and isinstance(v[0], list):
        v = [x for sub in v for x in sub]
    return v


def convert(stored, mapping, names_used):
    """Stored brick JSON -> upload JSON with the mapped terms; returns (object, {old id: new id} actually replaced)."""
    replaced = collections.Counter()
    mapping = collections.ChainMap(mapping, ALT)

    def term(t):
        ref = t["oterm_ref"]
        if ref.startswith("CHEBI:") and ref in mapping:
            replaced[ref] += 1
            ref = mapping[ref]
        name = ab.NAMES.get(ref, t.get("oterm_name"))
        return {"term_name": name, "oterm_ref": ref, "oterm_name": name}

    def scalar(v):
        v = dict(v)
        if v.get("scalar_type") == "oterm_ref":
            ref = v["oterm_ref"]
            if ref in mapping:
                replaced[ref] += 1
                ref = mapping[ref]
            v["oterm_ref"] = ref
            v["string_value"] = ab.NAMES[ref]
        return v

    def context(lst):
        out = []
        for c in lst or []:
            v = scalar(c["value"])
            # older heterogeneous bricks mark their data variables with a measurement term; the marker is now the brick's data type
            if c["value_type"]["oterm_ref"] == "ME:0000293" and not v.get("oterm_ref", "").startswith("DA:"):
                v = {"scalar_type": "oterm_ref", "oterm_ref": stored["data_type"]["oterm_ref"], "string_value": ab.NAMES[stored["data_type"]["oterm_ref"]]}
            out.append(dict({"value_type": term(c["value_type"]), "value": v}, **({"value_units": term(c["value_units"])} if c.get("value_units") else {})))
        return out

    def typed(t):
        vals = dict(t["values"])
        for k in list(vals):
            if k.endswith("_values") or k in ("object_refs", "oterm_refs"):
                vals[k] = flatten(vals[k])
        if "oterm_refs" in vals:
            refs = []
            for r in vals["oterm_refs"]:
                if r in mapping:
                    replaced[r] += 1
                    r = mapping[r]
                refs.append(r)
            vals["oterm_refs"] = refs
            vals["string_values"] = [None if r is None else ab.NAMES[r] for r in refs]
        if "object_refs" in vals:
            vals["string_values"] = list(vals["object_refs"])
        out = {"value_type": term(t["value_type"]), "values": vals}
        if t.get("value_units"):
            out["value_units"] = term(t["value_units"])
        if t.get("value_context"):
            out["value_context"] = context(t["value_context"])
        return out

    obj = {"name": new_name(stored["name"]), "description": stored["description"], "data_type": term(stored["data_type"]),
           "array_context": context(stored["array_context"]), "n_dimensions": len(stored["dim_context"]),
           "dim_context": [{"data_type": term(d["data_type"]), "size": d["size"], "typed_values": [typed(t) for t in d["typed_values"]]} for d in stored["dim_context"]],
           "typed_values": [typed(t) for t in stored["typed_values"]]}
    if obj["name"] in names_used:
        raise ValueError(f"{obj['name']} already exists")
    # a corrected term must not collide with one already on the same dimension
    for d in obj["dim_context"]:
        for t in d["typed_values"]:
            refs = t["values"].get("oterm_refs")
            if refs and len(set(refs)) != len(refs) and len(set(flatten(next(x for x in stored["dim_context"] if x["size"] == d["size"])["typed_values"][0]["values"].get("oterm_refs", [])))) == d["size"]:
                dup = [r for r, n in collections.Counter(refs).items() if n > 1]
                raise ValueError(f"{stored['name']}: duplicate molecule after correction {dup}")
    return obj, replaced


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stored", required=True, help="directory with the hub's data_store files of the affected bricks")
    args = ap.parse_args()
    oo.stage_validator()
    ab.load_ontology_names()
    # names for every ChEBI ID, including secondary (alt_id) IDs that older bricks still use
    cur = name = None
    with open("/home/coral/prod/data_import/ontologies/chebi.obo", errors="ignore") as h:
        for line in h:
            line = line.rstrip("\n")
            if line == "[Term]":
                cur = name = None
            elif line.startswith("id: "):
                cur = line[4:]
            elif line.startswith("name: ") and cur:
                name = line[6:]
                ab.NAMES.setdefault(cur, name)
            elif line.startswith("alt_id: ") and name:
                ab.NAMES.setdefault(line[8:], name)
                ALT[line[8:]] = cur
    if OUT.exists():
        raise FileExistsError(OUT)
    ab.OUT = OUT
    ab.JSON_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT = (OUT / d for d in ("json", "process", "check", "reports"))
    for d in (ab.JSON_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT):
        d.mkdir(parents=True)
    csv.field_size_limit(10 ** 9)
    nd = {r["ddt_ndarray_id"]: r for r in csv.DictReader((EXPORT / "ddt_ndarray.tsv").open(), delimiter="\t")}
    names_used = {r["ddt_ndarray_name"] for r in nd.values()}
    campaign = {}
    for r in csv.DictReader((EXPORT / "sys_process.tsv").open(), delimiter="\t"):
        for b in re.findall(r"Brick\d{7}", r["output_objects"]):
            campaign.setdefault(b, f"{r['campaign_sys_oterm_name']} <{r['campaign_sys_oterm_id']}>")
    rows, report, failed = [], ["# ChEBI term corrections: replacement bricks (2026-11-12)", "", "| Old brick | Old name | New name | Terms replaced |", "| --- | --- | --- | --- |"], []
    for path in sorted(Path(args.stored).glob("Brick*")):
        bid = path.name
        r = nd[bid]
        if r["withdrawn_date"] or r["superceded_by_ddt_ndarray_id"]:
            continue
        stored = json.loads(path.read_text())
        mapping = SPECIAL.get(bid, COMMON)
        obj, replaced = convert(stored, mapping, names_used)
        if not replaced:
            raise ValueError(f"{bid}: nothing to replace")
        full = collections.ChainMap(mapping, ALT)
        what = "; ".join((f"{ab.NAMES.get(a, a)} -> {ab.NAMES[full[a]]}" if a in mapping else f"secondary ID {a} -> {full[a]} ({ab.NAMES[full[a]]})")
                         for a in sorted(replaced, key=lambda x: (x not in mapping, ab.NAMES.get(x, x))))
        obj["array_context"].append(comment(f"Replaces {stored['name']} ({bid}): molecule terms corrected ({what}); nothing else changed"))
        try:
            (ab.write_brick if obj["name"].endswith(".hndarray") else oo.write_brick)(obj)
        except Exception as e:  # report every brick that does not validate, then stop
            failed.append((bid, stored["name"], str(e)[-600:]))
            continue
        names_used.add(obj["name"])
        rows.append({"process": "Update Data <PROCESS:0000053>", "person": "John-Marc Chandonia <ENIGMA:0000057>", "campaign": campaign[bid], "protocol": "null",
                     "date_start": TODAY, "date_end": TODAY, "input_objects": f"Generic: {stored['name']}", "output_objects": f"Generic: {obj['name']}"})
        report.append(f"| {bid} | {stored['name']} | {obj['name']} | {what} |")
    (ab.REPORT_OUT / "build_report.md").write_text("\n".join(report) + "\n")
    if failed:
        for f in failed:
            print("FAILED", f[0], f[1], "\n   ", f[2].replace("\n", " ")[-400:])
        raise SystemExit(f"{len(failed)} bricks failed validation; {len(rows)} built")
    write_process(ab.PROCESS_OUT / "process_update_data_chebi_term_fix_20261112.tsv", rows)
    files = [f"json/{r['output_objects'].replace('Generic: ', '').rsplit('.', 1)[0]}.json" for r in rows] + ["process/process_update_data_chebi_term_fix_20261112.tsv"]
    (OUT / "files_to_import.txt").write_text("\n".join(files) + "\n")
    (OUT / "import_to_coral.py").write_text("\n".join([f"toolx.upload_brick('{Path(f).name}')" for f in files[:-1]]
                                                      + ["toolx.upload_process('Update Data', 'process_update_data_chebi_term_fix_20261112.tsv')"]) + "\n")
    print(f"built {len(rows)} replacement bricks")


if __name__ == "__main__":
    main()
