import csv,re,datetime as dt,bisect,statistics as st,openpyxl,warnings,sys,zoneinfo
warnings.simplefilter("ignore")
S,D=sys.argv[1],sys.argv[2]
UTC=dt.timezone.utc
def refseries(table):
    ref=[]
    for r in csv.DictReader(open(f"{S}/cmout/{table}.tsv"),delimiter="\t"):
        if r["air_pressure_inhg"]: ref.append((dt.datetime.fromisoformat(r["time_series_datetime"]).timestamp(), float(r["air_pressure_inhg"])*33.8639))
    ref.sort(); return [x[0] for x in ref],[x[1] for x in ref]
REFS={"WS1":refseries("hazen_hobo_ws1"),"WS3":refseries("hazen_hobo_ws3")}
def lagtest(name,series):
    for rn,(rt,rv) in REFS.items():
        def interp(t):
            i=bisect.bisect_left(rt,t)
            if i==0 or i>=len(rt) or rt[i]-rt[i-1]>3600: return None
            f=(t-rt[i-1])/(rt[i]-rt[i-1]); return rv[i-1]+f*(rv[i]-rv[i-1])
        out=[]
        for lag_h in [x/2 for x in range(-12,13)]:
            d=[v-r for t,v in series[::3] if (r:=interp(t+lag_h*3600)) is not None]
            if len(d)>200: out.append((st.pstdev(d),lag_h,len(d)))
        if not out: continue
        z=[round(s,3) for s,l,n in out if l==0]
        out.sort()
        print(f"{name} vs {rn}: best lag {out[0][1]:+.1f} h (residual SD {out[0][0]:.3f} hPa); next {out[1][1]:+.1f} h ({out[1][0]:.3f}); at 0 h {z}; n={out[0][2]}")
ws=openpyxl.load_workbook(f"{S}/src/EFPW05_09292022_2023-05-09_10-36-20-270.xlsx",data_only=True,read_only=True).worksheets[0]
rows=[r for r in ws.iter_rows(values_only=True)]
i=next(k for k,r in enumerate(rows) if r and r[0]=="Date and Time" and r[1]!="Note")
d=[r for r in rows[i+1:] if isinstance(r[0],dt.datetime) and isinstance(r[16],(int,float))]
start=d[0][0].replace(tzinfo=zoneinfo.ZoneInfo("America/Chicago")).timestamp()
lagtest("EFPW05 direct download, clock read as Central",[(start+(r[1]-d[0][1]), r[16]*1.33322) for r in d])
def brick(ids):
    s=[]
    for b in ids:
        for r in csv.DictReader(open(f"{D}/{b}.tsv"),delimiter="\t"):
            if r["air_pressure_pound_per_square_inch"]: s.append((dt.datetime.fromisoformat(r["time_series_datetime"]).timestamp(), float(r["air_pressure_pound_per_square_inch"])*68.9476))
    return s
lagtest("EFPW02 HydroVu brick as stored",brick(["Brick0001231"]))
lagtest("EFPW03 HydroVu bricks as stored",brick(["Brick0001232","Brick0001233"]))
lagtest("EFPW06 HydroVu brick as stored",brick(["Brick0001362"]))
h=open(f"{S}/src/HydroVu_EFPW01_2022-08-17_02-24-00_Export.htm",errors="ignore").read()
s=[]
for row in re.findall(r"<tr[^>]*>(.*?)</tr>",h,flags=re.S):
    c=[re.sub(r"<[^>]+>","",x).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>",row,flags=re.S)]
    if c and re.match(r"\d{4}-\d\d-\d\d \d\d:",c[0]) and c[-1]:
        s.append((dt.datetime.strptime(c[0][:19],"%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC).timestamp(), float(c[-1])*68.9476))
lagtest("EFPW01 HydroVu export read as UTC",s)
