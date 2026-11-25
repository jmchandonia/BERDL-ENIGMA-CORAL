# Run on the CORAL hub. Part 2 of the Taxon spelling cleanup: save the affected records, rename 121 in place, copy 6 NCBI ids.
# Preflight checks every record first; nothing is written unless all pass. Each write is guarded by the expected old value.
import json
from coral import services
services._init_services()
A = services.arango_service
DIR = "/home/coral/prod/data_import/data/"
plan = json.load(open(DIR + "taxon_plan_20261125.json"))
keys = sorted(set(plan["rename"]) | set(plan["retire"]) | set(plan["ncbi_copy"]) | {v[2] for v in plan["retire"].values()})
docs = {d["_key"]: d for d in A.find("FOR t IN SDT_Taxon FILTER t._key IN @k RETURN t", {"k": keys}, size=100000)}
names = set(A.find("FOR t IN SDT_Taxon RETURN t.name", {}, size=100000))
problems = []
for k, (old, new) in plan["rename"].items():
    if docs.get(k, {}).get("name") != old: problems.append(("rename: unexpected name", k, old, docs.get(k, {}).get("name")))
    if new in names: problems.append(("rename: new name exists", k, new))
for k, (old, kept, kept_key) in plan["retire"].items():
    if docs.get(k, {}).get("name") != old: problems.append(("retire: unexpected name", k, old))
    if docs.get(kept_key, {}).get("name") != kept: problems.append(("retire: kept record differs", kept_key, kept))
for k, (name, tid, src) in plan["ncbi_copy"].items():
    if docs.get(k, {}).get("ncbi_taxid") not in (None, ""): problems.append(("ncbi: kept already has id", k))
    if docs.get(src, {}).get("ncbi_taxid") != tid: problems.append(("ncbi: source differs", src))
if len(set(v[1] for v in plan["rename"].values())) != len(plan["rename"]): problems.append(("rename: duplicate new names",))
print("records read", len(docs), "of", len(keys), "| problems", len(problems), problems[:10])
if problems or len(docs) != len(keys):
    raise RuntimeError("preflight failed; nothing written")
json.dump(docs, open(DIR + "taxon_records_before_20261125.json", "w"), indent=1, sort_keys=True)
print("saved", len(docs), "records to", DIR + "taxon_records_before_20261125.json")
REN = """LET doc = DOCUMENT(CONCAT("SDT_Taxon/", @key))
LET taken = LENGTH(FOR t IN SDT_Taxon FILTER t.name == @new RETURN 1)
FILTER doc != null AND doc.name == @old AND taken == 0
UPDATE doc WITH { name: @new } IN SDT_Taxon OPTIONS { mergeObjects: true, ignoreRevs: false }
RETURN NEW.name"""
done = 0
for k, (old, new) in plan["rename"].items():
    r = A.find(REN, {"key": k, "old": old, "new": new})
    if r != [new]: raise RuntimeError("rename failed at %s %s -> %s: %r (renamed so far: %d)" % (k, old, new, r, done))
    done += 1
print("renamed", done)
NC = """LET doc = DOCUMENT(CONCAT("SDT_Taxon/", @key))
FILTER doc != null AND doc.name == @name AND (doc.ncbi_taxid == null OR doc.ncbi_taxid == "")
UPDATE doc WITH { ncbi_taxid: @tid } IN SDT_Taxon OPTIONS { mergeObjects: true, ignoreRevs: false }
RETURN [NEW._key, NEW.name, NEW.ncbi_taxid]"""
for k, (name, tid, src) in plan["ncbi_copy"].items():
    r = A.find(NC, {"key": k, "name": name, "tid": tid})
    if len(r) != 1: raise RuntimeError("ncbi copy failed at %s" % k)
    print("ncbi id copied", r[0])
after = {d["_key"]: d["name"] for d in A.find("FOR t IN SDT_Taxon FILTER t._key IN @k RETURN t", {"k": list(plan["rename"])}, size=100000)}
print("renamed records now carrying the new name:", sum(1 for k, v in plan["rename"].items() if after.get(k) == v[1]), "of", len(plan["rename"]), "| Taxon count", A.find("RETURN LENGTH(SDT_Taxon)", {}))
