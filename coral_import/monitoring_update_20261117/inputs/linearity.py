"""Per raw HydroVu file and instrument: how much of the 1-minute series is exactly linear (interpolated) and the spacing of its slope breaks."""
import json,sys,glob,os,collections,re
root=sys.argv[1]; out=open(sys.argv[2],"w")
wells=sys.argv[3].split(",")
files=sorted(f for f in glob.glob(root+"/20*/*/*.json") if not f.endswith(("_coral.json","_coral_a.json")) and re.search(r"_(%s)_"%"|".join(wells),os.path.basename(f)))
for n,f in enumerate(files):
    try: o=json.load(open(f))
    except Exception: continue
    by=collections.defaultdict(list)
    for p in o.get("parameters",[]):
        pid=str(p.get("parameterId"))
        inst=pid.split()[0] if pid[:2] in ("SZ","VZ","VS") else "?"
        r=p.get("readings") or []
        if len(r)<30: continue
        by[inst].append((pid,r))
    for inst,ps in by.items():
        best=None
        for pid,r in ps:
            if not re.search(r"Cond|Temp|ORP|Pressure|Depth",pid): continue
            t=[x["timestamp"] for x in r]; v=[x["value"] for x in r]
            step=collections.Counter(b-a for a,b in zip(t,t[1:])).most_common(1)[0][0]
            n3=lin=0; kinks=[]
            for i in range(1,len(v)-1):
                if t[i+1]-t[i]!=step or t[i]-t[i-1]!=step: continue
                d2=v[i+1]-2*v[i]+v[i-1]; n3+=1
                if abs(d2)<=1e-9*max(1.0,abs(v[i])): lin+=1
                else: kinks.append(t[i])
            rng=max(v)-min(v)
            if n3<20 or rng==0: continue
            gaps=collections.Counter(round((b-a)/60) for a,b in zip(kinks,kinks[1:])).most_common(1)
            cand=(rng,pid,step,n3,lin/n3,gaps[0][0] if gaps else None)
            if best is None or cand[3]>best[3] or (cand[3]==best[3] and cand[0]>best[0]): best=cand
        if best:
            out.write("\t".join(map(str,[os.path.basename(f),inst,best[1],best[2],best[3],round(best[4],3),best[5]]))+"\n")
    if n%500==0: print(n,len(files),flush=True)
