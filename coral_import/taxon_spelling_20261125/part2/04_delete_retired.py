# Run on the CORAL hub. Delete the 252 retired Taxon records (saved beforehand in taxon_records_before_20261125.json).
# Preflight: each record still has the retired name, its kept twin exists, and no process edge touches it.
import json
from coral import services
services._init_services()
A = services.arango_service
DIR = "/home/coral/prod/data_import/data/"
plan = json.load(open(DIR + "taxon_plan_20261125.json"))
before = json.load(open(DIR + "taxon_records_before_20261125.json"))
final_kept = {}
for k, v in plan["retire"].items():
    final_kept[k] = plan["rename"].get(v[2], [None, v[1]])[1]
docs = {d["_key"]: d for d in A.find("FOR t IN SDT_Taxon FILTER t._key IN @k RETURN t", {"k": list(plan["retire"]) + [v[2] for v in plan["retire"].values()]}, size=100000)}
problems = []
for k, v in plan["retire"].items():
    if k not in before: problems.append(("not saved", k))
    if docs.get(k, {}).get("name") != v[0]: problems.append(("name differs", k))
    if docs.get(v[2], {}).get("name") != final_kept[k]: problems.append(("kept twin differs", v[2], final_kept[k], docs.get(v[2], {}).get("name")))
ids = ["SDT_Taxon/" + k for k in plan["retire"]]
edges = A.find("RETURN LENGTH(FOR e IN SYS_ProcessInput FILTER e._from IN @i RETURN 1) + LENGTH(FOR e IN SYS_ProcessOutput FILTER e._to IN @i RETURN 1)", {"i": ids})
print("to delete", len(plan["retire"]), "| problems", len(problems), problems[:5], "| process edges", edges)
if problems or edges != [0]:
    raise RuntimeError("preflight failed; nothing deleted")
n0 = A.find("RETURN LENGTH(SDT_Taxon)", {})[0]
removed = A.find("FOR k IN @keys LET d = DOCUMENT(CONCAT('SDT_Taxon/', k)) FILTER d != null AND d.name == @names[k] REMOVE d IN SDT_Taxon RETURN OLD._key", {"keys": list(plan["retire"]), "names": {k: v[0] for k, v in plan["retire"].items()}}, size=100000)
n1 = A.find("RETURN LENGTH(SDT_Taxon)", {})[0]
print("removed", len(removed), "| Taxon count", n0, "->", n1, "| distinct names", A.find("RETURN LENGTH(UNIQUE(FOR t IN SDT_Taxon RETURN t.name))", {})[0])
print("names still containing an underscore:", A.find("RETURN LENGTH(FOR t IN SDT_Taxon FILTER CONTAINS(t.name, '_') RETURN 1)", {})[0])
