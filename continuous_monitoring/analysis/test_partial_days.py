import sys, json, tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, '/data/edr/field_automated_measurements/continuous_monitoring/code')
import cm_build, cm_common as cm
root = Path('/data/edr/field_automated_measurements/hydrovu/data')
tmp = Path(tempfile.mkdtemp(dir='/data/edr/field_automated_measurements/continuous_monitoring/scratch'))
now = datetime.now(timezone.utc)
schedules = {}
stats = Counter(); bad = defaultdict(list); per_table_day = defaultdict(Counter)
for p in sorted(root.glob(sys.argv[1])):
    if not any(f'_{s}_' in p.name or f'_{s}-VZ_' in p.name for s in ('L8', 'L9', 'M6', 'U3')): continue
    obj = json.loads(p.read_text())
    t0 = min(r['timestamp'] for prm in obj['parameters'] for r in prm['readings'])
    cut = int(sys.argv[2]) * 3600
    part = {**obj, 'parameters': [{**prm, 'readings': [r for r in prm['readings'] if r['timestamp'] < t0 + cut]} for prm in obj['parameters']]}
    tp = tmp / p.name; tp.write_text(json.dumps(part))
    bp = cm_build.Builder(None, now); bp.schedules = schedules
    ok_partial = bp.add_hydrovu_file(tp, complete=False)
    bf = cm_build.Builder(None, now); bf.schedules = schedules
    bf.add_hydrovu_file(p, complete=True)
    full = set(bf.cells); partial = set(bp.cells)
    stats['files'] += 1; stats['partial_deferred'] += not ok_partial
    stats['partial_rows'] += len(partial); stats['partial_rows_not_in_full'] += len(partial - full)
    for t, ts in sorted(partial - full)[:3]: bad[t].append((p.name[:6], ts.strftime('%H:%M')))
    for table, ts in full: per_table_day[table][ts.date()] += 1
    stats['schedule_changes'] += len(bf.schedule_changes)
print(dict(stats))
for t, days in sorted(per_table_day.items()):
    c = sorted(days.values()); print(t, 'rows/day median', c[len(c)//2], 'min', c[0], 'max', c[-1])
[print('MISMATCH', t, len(v), v[:8]) for t, v in bad.items()]
print({k: [(e['interval'], e['minute']) for e in v][-3:] for k, v in schedules.items()})
