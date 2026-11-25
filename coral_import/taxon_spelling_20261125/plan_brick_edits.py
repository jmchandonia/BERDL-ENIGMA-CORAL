import csv,json,re,collections,sys,os,hashlib
S=sys.argv[1]; X=sys.argv[2]
T=list(csv.DictReader(open(X+"/coral_export/static_tsv/Taxon.tsv"),delimiter="\t"))
g=collections.defaultdict(list)
for r in T: g[re.sub(r"[\s_]+"," ",r["name"]).strip().lower()].append(r)
D={k:v for k,v in g.items() if len(v)>1}
use=collections.Counter(); bricks={}
for b in sorted(os.listdir(S+"/stored")):
    d=json.load(open(S+"/stored/"+b)); bricks[b]=d
    for v in d["typed_values"]:
        if v["values"].get("scalar_type")=="object_ref":
            def walk(x):
                for y in x:
                    if isinstance(y,list): walk(y)
                    elif y is not None: use[y]+=1
            walk(v["values"]["object_refs"])
NCBI_CASE={"Aeromonas veronii bv. sobria","Beet soil-borne mosaic virus","Bovine adenovirus 3","Human picobirnavirus","Methanocaldococcus infernus ME","Methanosarcina barkeri str. Fusaro","Coleoptera"}
keep={}; odd=[]; rename={}
for k,v in D.items():
    names=[r["name"] for r in v]
    pure=len({n.replace("_"," ") for n in names})==1
    if pure: c=min(names,key=lambda n:n.count("_"))
    else:
        c=next((n for n in names if n in NCBI_CASE),None) or max((n for n in names),key=lambda n:(n.count(" "),use[n]))
        odd.append((names,c))
    m=re.fullmatch(r"(\w+) Incertae Sedis",c)
    if m and not pure:
        new=m.group(1)+" incertae sedis"; rename[c]=new; c=new
    for r in v:
        if r["name"]!=c: keep[r["name"]]=c
json.dump({"rename":rename,"map":keep,"ids":{r["name"]:[r["id"],r["ncbi_taxid"]] for v in D.values() for r in v}},open(S+"/taxon_map.json","w"),indent=1)
print("names to retire or rename:",len(keep),"| Taxon records to rename:",rename)
print("other taxa with capital Incertae Sedis, not duplicated:",sorted(r["name"] for r in T if "Incertae Sedis" in r["name"] and r["name"] not in keep)[:40])
print("lower-case incertae sedis taxa:",sorted(r["name"] for r in T if "incertae sedis" in r["name"])[:20])
print("odd pairs (names -> kept, uses in the 20 bricks):")
for names,c in odd: print("   ",[(n,use[n]) for n in names],"->",c)
print("pure pairs where neither is all-space:",[ (k,v) for k,v in keep.items() if "_" in v][:10])
os.makedirs(S+"/new",exist_ok=True)
for b,d in bricks.items():
    n=collections.Counter()
    def fix(x):
        for i,y in enumerate(x):
            if isinstance(y,list): fix(y)
            elif y in keep: n[y]+=1; x[i]=keep[y]
    for v in d["typed_values"]:
        if v["values"].get("scalar_type")=="object_ref": fix(v["values"]["object_refs"])
    if n:
        raw=open(S+"/stored/"+b).read()
        same=json.dumps(json.load(open(S+"/stored/"+b)))==raw
        open(S+"/new/"+b,"w").write(json.dumps(d))
        print("%s %-62s cells changed %7d  distinct names %3d  (stored file is plain json.dumps: %s)"%(b,d["name"],sum(n.values()),len(n),same))
