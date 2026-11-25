"""Check what CORAL serves after the in-place edits: the Taxon table and the edited bricks as downloaded by the sync.
usage: 05_check_downloads.py <new run dir> <previous run dir> <plan json> <plan_bricks.out> <force_bricks.txt>"""
import csv, json, re, sys, collections
csv.field_size_limit(10**9)
NEW, PREV, PLAN, PB, FORCE = sys.argv[1:6]
plan = json.load(open(PLAN)); vm = plan["value_map"]
old_names = set(vm)
ok = True
# 1. Taxon table: previous download + plan must equal the new download exactly
prev = {r["id"]: r for r in csv.DictReader(open(PREV + "/coral_export/static_tsv/Taxon.tsv"), delimiter="\t")}
new = {r["id"]: r for r in csv.DictReader(open(NEW + "/coral_export/static_tsv/Taxon.tsv"), delimiter="\t")}
exp = {k: dict(v) for k, v in prev.items() if k not in plan["retire"]}
for k, (o, n) in plan["rename"].items():
    assert exp[k]["name"] == o; exp[k]["name"] = n
for k, (name, tid, src) in plan["ncbi_copy"].items():
    assert exp[k]["name"] == name and not exp[k]["ncbi_taxid"]; exp[k]["ncbi_taxid"] = tid
diff = [k for k in set(exp) | set(new) if exp.get(k) != new.get(k)]
names = [r["name"] for r in new.values()]
print("Taxon: previous %d -> new %d (expected %d); records differing from expectation: %d; duplicate names: %d; old names still present: %d; renamed %d, ncbi ids set %d, deleted %d"
      % (len(prev), len(new), len(exp), len(diff), len(names) - len(set(names)), len(set(names) & old_names),
         sum(1 for k, v in plan["rename"].items() if new.get(k, {}).get("name") == v[1]), sum(1 for k, v in plan["ncbi_copy"].items() if new.get(k, {}).get("ncbi_taxid") == v[1]),
         sum(1 for k in plan["retire"] if k not in new)))
ok &= not diff and len(names) == len(set(names)) and not (set(names) & old_names)
low = collections.Counter(re.sub(r"[\s_]+", " ", n).strip().lower() for n in names)
print("Taxon: spelling-duplicate groups left:", sum(1 for v in low.values() if v > 1))
taxa = set(names)
# 2. each edited current brick: raw download == previous raw download with the value map applied, cell by cell
planned = {}
for l in open(PB):
    m = re.match(r"(Brick\d+) .*cells changed\s+(\d+)", l)
    if m: planned[m.group(1)] = int(m.group(2))
for b in open(FORCE).read().split():
    a = list(csv.reader(open(PREV + "/coral_export/brick_csv/%s.csv" % b)))
    n = list(csv.reader(open(NEW + "/coral_export/brick_csv/%s.csv" % b)))
    same_shape = len(a) == len(n) and all(len(x) == len(y) for x, y in zip(a, n))
    changed = wrong = left = 0
    if same_shape:
        for x, y in zip(a, n):
            for p, q in zip(x, y):
                if p != q:
                    changed += 1
                    mp = re.fullmatch(r"(.*) <(.*)>", p)   # the download writes an object reference as "name <name>"
                    if not (mp and mp.group(1) == mp.group(2) and mp.group(1) in vm and q == "%s <%s>" % (vm[mp.group(1)], vm[mp.group(1)])): wrong += 1
                mq = re.fullmatch(r"(.*) <(.*)>", q)
                if q in old_names or (mq and (mq.group(1) in old_names or mq.group(2) in old_names)): left += 1
    # converted Lakehouse table
    t = csv.reader(open(NEW + "/berdl_upload/data/%s.tsv" % b), delimiter="\t"); hdr = next(t)
    idx = [i for i, c in enumerate(hdr) if "taxon" in c.lower() and "level" not in c.lower()]
    vals = set()
    for row in t:
        for i in idx: vals.add(row[i])
    vals.discard("")
    good = same_shape and wrong == 0 and left == 0 and changed == planned[b] and not (vals & old_names) and not (vals - taxa)
    ok &= good
    print("%s %s rows %d  cells changed %6d (planned %6d)  unexpected changes %d  old names left %d | lakehouse table: taxa %d, old names %d, not in Taxon %d  %s"
          % (b, "same layout" if same_shape else "LAYOUT DIFFERS", len(n), changed, planned[b], wrong, left, len(vals), len(vals & old_names), len(vals - taxa), "OK" if good else "PROBLEM"))
print("ALL CHECKS PASSED" if ok else "CHECKS FAILED")
