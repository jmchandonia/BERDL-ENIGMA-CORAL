# Read-only verification of FEBa update bricks and processes.
from coral.dataprovider import DataProvider
from coral import toolx
from coral import services
import json
services._init_services()
A = services.arango_service
NEW = json.loads('["feba_tnseq_condition_metadata_20261111.ndarray", "feba_tnseq_fitness_GW456-12-10-14-TSB1.4.ndarray", "feba_tnseq_fitness_GW460-12-10-14-LB2.4_v3.ndarray", "feba_tnseq_fitness_GW822-FHT05C05.3_v3.ndarray", "feba_tnseq_fitness_GW823-FHT01H08.4_v3.ndarray", "feba_tnseq_fitness_MT49.4_v3.ndarray", "feba_tnseq_fitness_MT58.3_v3.ndarray"]')
OLD = json.loads('["feba_tnseq_fitness_GW460-12-10-14-LB2.4_v2.ndarray", "feba_tnseq_fitness_GW822-FHT05C05.3_v2.ndarray", "feba_tnseq_fitness_GW823-FHT01H08.4_v2.ndarray", "feba_tnseq_fitness_MT49.4_v2.ndarray", "feba_tnseq_fitness_MT58.3_v2.ndarray", "feba_tnseq_condition_metadata_20260813.ndarray"]')
def q(aql, b=None):
    return list(A.find(aql, b or {}))
out = {}
bricks = q("FOR b IN DDT_Brick FILTER b.name IN @n RETURN {id: b._key, name: b.name, shape: b.shape, dim_sizes: b.dim_sizes, attrs: ATTRIBUTES(b)}", {"n": NEW + OLD})
out["attrs"] = sorted(bricks[0]["attrs"]) if bricks else []
out["bricks"] = [{k: b.get(k) for k in ("id", "name", "shape", "dim_sizes")} for b in bricks]
ids = {b["name"]: "DDT_Brick/" + b["id"] for b in bricks}
out["producing"] = q("FOR e IN SYS_ProcessOutput FILTER e._to IN @ids LET p = DOCUMENT(e._from) RETURN {brick: e._to, process: p._key, term: p.process_term_name, inputs: p.input_objects}", {"ids": [ids[n] for n in NEW if n in ids]})
out["consuming_old"] = q("FOR e IN SYS_ProcessInput FILTER e._from IN @ids LET p = DOCUMENT(e._to) RETURN {brick: e._from, process: p._key, term: p.process_term_name, outputs: p.output_objects}", {"ids": [ids[n] for n in OLD if n in ids]})
print("STAGE2_JSON " + json.dumps(out))
