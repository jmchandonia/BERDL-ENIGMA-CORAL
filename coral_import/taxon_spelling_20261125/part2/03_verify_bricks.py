# Run on the CORAL hub: load every brick that has a taxon variable through CORAL; check names against the Taxon table.
import json
from coral.dataprovider import DataProvider
from coral import services
services._init_services()
plan = json.load(open("/home/coral/prod/data_import/data/taxon_plan_20261125.json"))
RETIRED = set(v[0] for v in plan["retire"].values()) | set(v[0] for v in plan["rename"].values())
CURRENT = ['Brick0000011', 'Brick0000012', 'Brick0000016', 'Brick0000511', 'Brick0001483', 'Brick0001486', 'Brick0001608', 'Brick0001611', 'Brick0001614', 'Brick0001617', 'Brick0001670', 'Brick0001671', 'Brick0001672', 'Brick0001673', 'Brick0001743', 'Brick0002132', 'Brick0002135', 'Brick0002138', 'Brick0002141', 'Brick0002144', 'Brick0002148', 'Brick0002149', 'Brick0002168', 'Brick0002170', 'Brick0002184']
WITHDRAWN = ['Brick0000001', 'Brick0000345', 'Brick0000348', 'Brick0000349', 'Brick0000353', 'Brick0000355', 'Brick0000366', 'Brick0000368', 'Brick0000373', 'Brick0000375', 'Brick0000388', 'Brick0000390', 'Brick0000396', 'Brick0000398', 'Brick0000407', 'Brick0000409', 'Brick0000413', 'Brick0000418', 'Brick0000425', 'Brick0000427', 'Brick0000429', 'Brick0000431', 'Brick0000437', 'Brick0000443', 'Brick0000447', 'Brick0000454', 'Brick0000458', 'Brick0000461', 'Brick0000467', 'Brick0000470', 'Brick0000475', 'Brick0000478', 'Brick0000483', 'Brick0000486', 'Brick0000488', 'Brick0000495', 'Brick0000500', 'Brick0000502', 'Brick0000512', 'Brick0000519', 'Brick0000522', 'Brick0000524', 'Brick0000530', 'Brick0001600', 'Brick0001721', 'Brick0001734']
EDITED = set(['Brick0000011', 'Brick0000012', 'Brick0000016', 'Brick0000349', 'Brick0000355', 'Brick0000454', 'Brick0000458', 'Brick0000461', 'Brick0000478', 'Brick0001483', 'Brick0001486', 'Brick0001608', 'Brick0001611', 'Brick0001614', 'Brick0001617', 'Brick0001670', 'Brick0001671', 'Brick0001672', 'Brick0001673', 'Brick0002132', 'Brick0002135', 'Brick0002138', 'Brick0002168', 'Brick0002170', 'Brick0002184'])
taxa = set(services.arango_service.find("FOR t IN SDT_Taxon RETURN t.name", {}, size=100000))
live = taxa - RETIRED
dp = DataProvider()
bad_current = 0
for state, ids in (("current", CURRENT), ("withdrawn", WITHDRAWN)):
    for b in ids:
        br = dp.genx_types.Brick.load(b)
        vals = set()
        for v in br.data_vars:
            if "taxon" in v.type_term.term_name.lower():
                vals |= set(x for x in v.values.flatten().tolist() if x is not None)
        r, miss = len(vals & RETIRED), len(vals - taxa)
        if state == "current" and (r or miss or not vals): bad_current += 1
        print(b, state, "edited" if b in EDITED else "      ", br.name[:60], "shape", [d.size for d in br.dims], "taxa", len(vals), "retired names", r, "not in Taxon", miss)
print("CURRENT BRICKS WITH A PROBLEM:", bad_current)
