import sys, json
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, '/data/edr/field_automated_measurements/continuous_monitoring/code')
import cm_build, cm_common as cm
b = cm.builder_module()
root = Path('/data/edr/field_automated_measurements/hydrovu/data')
seq = defaultdict(list)
for p in sorted(root.glob(sys.argv[1])):
    info = b.hydrovu_source_info(p)
    if not info or info[1] not in {'SSO-L8', 'SSO-L9', 'SSO-M6', 'SSO-U3'} or info[0] != 'hydrovu_regular': continue
    obj = json.loads(p.read_text()); series = defaultdict(list)
    for prm in obj['parameters']:
        series[b.hydrovu_parameter_instrument(str(prm['parameterId']))].append([(r['timestamp'], b.parse_float(r.get('value'))) for r in prm['readings']])
    for inst in ('SZ1', 'SZ2'):
        if inst in series:
            f = cm_build.reading_schedule(series[inst])
            seq[(info[1], inst)].append(f"{p.name[2:6]}:{f['interval']}/{f['minute']}" if f else f"{p.name[2:6]}:-")
for k, v in sorted(seq.items()): print(k, ' '.join(v))
