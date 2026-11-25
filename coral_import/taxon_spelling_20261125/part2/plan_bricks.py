import json,sys,os,csv,hashlib,collections,gc
S,D=sys.argv[1],sys.argv[2]
plan=json.load(open(S+"/taxon_plan.json")); vm=plan["value_map"]
nd={r["ddt_ndarray_id"]:r for r in csv.DictReader(open(D+"/berdl_upload/data/ddt_ndarray.tsv"),delimiter="\t")}
T={r["name"] for r in csv.DictReader(open(D+"/coral_export/static_tsv/Taxon.tsv"),delimiter="\t")}
final=(T-{v[0] for v in plan["rename"].values()}-{v[0] for v in plan["retire"].values()})|{v[1] for v in plan["rename"].values()}
os.makedirs(S+"/new",exist_ok=True); out=[]; used=collections.Counter()
def walk(x,fn):
    for i,y in enumerate(x):
        if isinstance(y,list): walk(y,fn)
        else: fn(x,i,y)
for b in sorted(os.listdir(S+"/stored")):
    raw=open(S+"/stored/"+b,"rb").read(); d=json.loads(raw)
    assert json.dumps(d).encode()==raw, b+" is not plain json.dumps output"
    n=collections.Counter(); missing=set(); other=collections.Counter(); ntax=0
    vars_=[("data",v) for v in d["typed_values"]]+[("dim%d"%i,v) for i,dm in enumerate(d["dim_context"]) for v in dm["typed_values"]]
    for where,v in vars_:
        if v["values"].get("scalar_type")!="object_ref": continue
        tname=(v["value_type"].get("oterm_name") or "")
        if "taxon" in tname.lower():
            ntax+=1
            def fix(x,i,y):
                if y in vm: n[y]+=1; used[y]+=1; x[i]=vm[y]
                elif y is not None and y not in final: missing.add(y)
            walk(v["values"]["object_refs"],fix)
        else:
            def chk(x,i,y):
                if y in vm: other[tname]+=1
            walk(v["values"]["object_refs"],chk)
    r=nd.get(b,{}); state="withdrawn" if r.get("withdrawn_date") or r.get("superceded_by_ddt_ndarray_id") else "current"
    if n:
        new=json.dumps(d).encode(); open(S+"/new/"+b,"wb").write(new)
        out.append((b,hashlib.md5(raw).hexdigest(),hashlib.md5(new).hexdigest()))
    print("%s %-9s %-64s taxon vars %d  cells changed %7d  names %3d  %s%s"%(b,state,d["name"][:64],ntax,sum(n.values()),len(n),"NOT-IN-TAXON %d %s "%(len(missing),sorted(missing)[:3]) if missing else "","OTHER-REF %s"%dict(other) if other else ""))
    del d,raw; gc.collect()
open(S+"/md5.txt","w").write("".join("%s %s %s\n"%x for x in out))
print("bricks to edit:",len(out),"| value-map names used by some brick:",len(used),"of",len(vm))
