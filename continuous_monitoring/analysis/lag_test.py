import sys, json, csv, glob, statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
man_path, man_col, site, hv_param = sys.argv[1:5]
sys.path.insert(0, '/data/edr/field_automated_measurements/tools')
import build_continuous_monitoring_coral as b
_, start_dt, _, interval, offset = b.extract_manual_metadata(Path(man_path))
rows = list(csv.reader(open(man_path, errors='ignore')))
hi = next(i for i, r in enumerate(rows) if r and r[0].strip('"') == 'Date Time')
ci = next(i for i, h in enumerate(rows[hi]) if h.startswith(man_col))
man = {}
idx = 0
for r in rows[hi+1:]:
    if not r or not r[0]: continue
    t = b.parse_manual_timestamp(r[0], start_dt, interval, idx)
    if t is None: continue
    idx += 1
    try: v = float(r[ci])
    except Exception: continue
    t = t.replace(tzinfo=offset)
    man[int(round(t.timestamp() / 60) * 60)] = v
lo, hi_t = min(man), max(man)
hv = {}
for f in glob.glob(f'/data/edr/field_automated_measurements/hydrovu/data/*/*/*_{site}_0.json'):
    d = datetime.strptime(Path(f).name[:6], '%y%m%d').replace(tzinfo=timezone.utc).timestamp()
    if not (lo - 3*86400 <= d <= hi_t + 3*86400): continue
    for p in json.load(open(f)).get('parameters', []):
        if p['parameterId'] == hv_param:
            for r in p['readings']:
                if r.get('value') is not None: hv[r['timestamp']] = r['value']
print(man_path.split('/')[-1], man_col, 'manual n', len(man), 'offset', offset, 'hydrovu', hv_param, 'n', len(hv))
import bisect
ht = sorted(hv); hvv = [hv[t] for t in ht]
def interp(t):
    i = bisect.bisect_left(ht, t)
    if i == 0 or i >= len(ht): return None
    t0, t1 = ht[i-1], ht[i]
    if t1 - t0 > 1800: return None
    return hvv[i-1] + (hvv[i] - hvv[i-1]) * (t - t0) / (t1 - t0)
for lag_min in range(-360, 361, 30):
    diffs = []
    for t, v in man.items():
        x = interp(t - lag_min * 60)
        if x is not None: diffs.append(abs(v - x))
    if diffs: print(f'  hydrovu time {lag_min/60:+.1f} h: n={len(diffs):6d} median|diff|={statistics.median(diffs):.5f}')
