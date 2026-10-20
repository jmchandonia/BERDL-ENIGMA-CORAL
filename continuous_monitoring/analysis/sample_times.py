import sys, json, statistics
from pathlib import Path
from collections import Counter, defaultdict
sys.path.insert(0, '/data/edr/field_automated_measurements/tools')
import build_continuous_monitoring_coral as b
root = Path('/data/edr/field_automated_measurements/hydrovu/data')
gapc = defaultdict(Counter); minute_c = defaultdict(Counter); examples = {}
for p in sorted(root.glob(sys.argv[1])):
    info = b.hydrovu_source_info(p)
    if not info or info[1] not in {'SSO-L8','SSO-L9','SSO-M6','SSO-U3'}: continue
    obj = json.loads(p.read_text())
    for prm in obj['parameters']:
        pid = str(prm['parameterId']); r = prm['readings']
        if len(r) < 1000: continue
        v = [b.parse_float(x['value']) for x in r]; t = [b.utc_epoch_to_eastern(x['timestamp']) for x in r]
        sd = [abs(v[i+1]-2*v[i]+v[i-1]) if None not in (v[i-1],v[i],v[i+1]) else 0 for i in range(1, len(v)-1)]
        nz = sorted(x for x in sd if x > 0)
        if len(nz) < 20: continue
        thr = 10 * statistics.median(nz)
        kinks = [t[i+1] for i, x in enumerate(sd) if x > thr]
        key = (info[1], pid)
        for a, c in zip(kinks, kinks[1:]): gapc[key][min(int((c-a).total_seconds()//60), 61)] += 1
        for k in kinks: minute_c[key][k.minute % 15] += 1
        if key not in examples: examples[key] = [k.strftime('%H:%M') for k in kinks[:14]]
for key in sorted(gapc):
    g = gapc[key]; tot = sum(g.values())
    print(key, 'kinks', tot, 'top gaps(min)', g.most_common(5), 'minute%15 top', minute_c[key].most_common(3))
    print('    first kinks', examples[key])
