import csv,json,re,sys,collections
D,S=sys.argv[1],sys.argv[2]
old=json.load(open("coral_import/taxon_spelling_20261125/taxon_name_map.json"))
T=list(csv.DictReader(open(D+"/coral_export/static_tsv/Taxon.tsv"),delimiter="\t"))
byname={r["name"]:r for r in T}
retire={o:k for o,k in old["map"].items() if o in byname}; done_already={o:k for o,k in old["map"].items() if o not in byname}; assert len(done_already)==4
# user 2026-11-25: keep B-17BO, retire b-17BO
assert retire.pop("B-17BO")=="b-17BO"; retire["b-17BO"]="B-17BO"
live=[r["name"] for r in T if r["name"] not in retire]
def cls(n):
    if n.startswith("Candidatus_") and re.fullmatch(r"Candidatus_[A-Z][a-z]+",n): return "Candidatus"
    if re.search(r"[Ii]ncertae[ _][Ss]edis",n): return "incertae sedis"
    if re.search(r"_(group|clade)$",n): return "group / clade"
    if n=="_Neoptera": return "leading underscore"
    return None
rename={}; kind={}
for n in live:
    k=cls(n)
    if not k: continue
    new=re.sub(r"[Ii]ncertae[ _][Ss]edis","incertae sedis",n.replace("_"," ")).strip() if k!="group / clade" else n.replace("_"," ")
    if new!=n: rename[n]=new; kind[n]=k
# collisions
final=[rename.get(n,n) for n in live]
c=collections.Counter(re.sub(r"\s+"," ",x).lower() for x in final)
bad=[x for x in final if c[re.sub(r"\s+"," ",x).lower()]>1]
assert not bad, bad
assert len(set(final))==len(final)
value_map={o:rename.get(k,k) for o,k in retire.items()}; value_map.update(rename); value_map.update(done_already)   # every old brick value -> final name
ncbi={}
for o,k in retire.items():
    a,b=byname[o]["ncbi_taxid"],byname[k]["ncbi_taxid"]
    if a and not b: ncbi[byname[k]["id"]]=(k,a,byname[o]["id"])
    elif a and b and a!=b: print("CONFLICTING ncbi ids",o,a,k,b)
json.dump({"rename":{byname[o]["id"]:[o,n] for o,n in rename.items()},"retire":{byname[o]["id"]:[o,k,byname[k]["id"]] for o,k in retire.items()},"ncbi_copy":ncbi,"value_map":value_map},open(S+"/taxon_plan.json","w"),indent=1)
print("rename",len(rename),collections.Counter(kind.values()),"| retire",len(retire),"| ncbi copies",len(ncbi),"| brick value map",len(value_map))
for k in ("Candidatus","group / clade","leading underscore","incertae sedis"):
    print("\n==",k)
    for o,n in sorted(rename.items()):
        if kind[o]==k: print("   %-52s -> %s"%(o,n))
print("\nunderscore names left unchanged:",sum(1 for x in final if "_" in x))
