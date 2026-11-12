# The CORAL name index (SYS_ObjectTypeID: type_name, upk_id -> pk_id) still held the old names of the twelve renamed EVO samples,
# so processes could not find them by their new names. Update the index entries, guarded on the expected state.
from coral.dataprovider import DataProvider
from coral import toolx
from coral import services
import json
services._init_services()
A = services.arango_service
REN = json.loads("""[{"key": "Sample0002886", "old_name": "GP01-30-01-04-18", "new_name": "GP01-18-01-04-18", "old_loc": "GP01-30", "new_loc": "GP01-18", "old_loc_id": "Location0000408", "new_loc_id": "Location0000407", "old_depth": 7.3914, "new_depth": 4.01}, {"key": "Sample0002906", "old_name": "GP01-30-02-01-18", "new_name": "GP01-18-02-01-18", "old_loc": "GP01-30", "new_loc": "GP01-18", "old_loc_id": "Location0000408", "new_loc_id": "Location0000407", "old_depth": 7.3914, "new_depth": 4.01}, {"key": "Sample0002854", "old_name": "GP01-30-12-07-17", "new_name": "GP01-18-12-07-17", "old_loc": "GP01-30", "new_loc": "GP01-18", "old_loc_id": "Location0000408", "new_loc_id": "Location0000407", "old_depth": 7.3914, "new_depth": 4.01}, {"key": "Sample0002862", "old_name": "GP01-30-12-14-17", "new_name": "GP01-18-12-14-17", "old_loc": "GP01-30", "new_loc": "GP01-18", "old_loc_id": "Location0000408", "new_loc_id": "Location0000407", "old_depth": 7.3914, "new_depth": 4.01}, {"key": "Sample0002870", "old_name": "GP01-30-12-21-17", "new_name": "GP01-18-12-21-17", "old_loc": "GP01-30", "new_loc": "GP01-18", "old_loc_id": "Location0000408", "new_loc_id": "Location0000407", "old_depth": 7.3914, "new_depth": 4.01}, {"key": "Sample0002878", "old_name": "GP01-30-12-28-17", "new_name": "GP01-18-12-28-17", "old_loc": "GP01-30", "new_loc": "GP01-18", "old_loc_id": "Location0000408", "new_loc_id": "Location0000407", "old_depth": 7.3914, "new_depth": 4.01}, {"key": "Sample0002887", "old_name": "GP03-29-01-04-18", "new_name": "GP03-19-01-04-18", "old_loc": "GP03-29", "new_loc": "GP03-19", "old_loc_id": "Location0000412", "new_loc_id": "Location0000411", "old_depth": 7.303008, "new_depth": 4.255}, {"key": "Sample0002907", "old_name": "GP03-29-02-01-18", "new_name": "GP03-19-02-01-18", "old_loc": "GP03-29", "new_loc": "GP03-19", "old_loc_id": "Location0000412", "new_loc_id": "Location0000411", "old_depth": 7.303008, "new_depth": 4.255}, {"key": "Sample0002855", "old_name": "GP03-29-12-07-17", "new_name": "GP03-19-12-07-17", "old_loc": "GP03-29", "new_loc": "GP03-19", "old_loc_id": "Location0000412", "new_loc_id": "Location0000411", "old_depth": 7.303008, "new_depth": 4.255}, {"key": "Sample0002863", "old_name": "GP03-29-12-14-17", "new_name": "GP03-19-12-14-17", "old_loc": "GP03-29", "new_loc": "GP03-19", "old_loc_id": "Location0000412", "new_loc_id": "Location0000411", "old_depth": 7.303008, "new_depth": 4.255}, {"key": "Sample0002871", "old_name": "GP03-29-12-21-17", "new_name": "GP03-19-12-21-17", "old_loc": "GP03-29", "new_loc": "GP03-19", "old_loc_id": "Location0000412", "new_loc_id": "Location0000411", "old_depth": 7.303008, "new_depth": 4.255}, {"key": "Sample0002879", "old_name": "GP03-29-12-28-17", "new_name": "GP03-19-12-28-17", "old_loc": "GP03-29", "new_loc": "GP03-19", "old_loc_id": "Location0000412", "new_loc_id": "Location0000411", "old_depth": 7.303008, "new_depth": 4.255}]""")
PRE = """
FOR m IN @ren
  LET old = (FOR x IN SYS_ObjectTypeID FILTER x.type_name == "Sample" AND x.upk_id == m.old_name RETURN x)
  LET new = (FOR x IN SYS_ObjectTypeID FILTER x.type_name == "Sample" AND x.upk_id == m.new_name RETURN x)
  LET s = DOCUMENT("SDT_Sample", m.key)
  RETURN LENGTH(old) == 1 AND old[0].pk_id == m.key AND LENGTH(new) == 0 AND s.name == m.new_name"""
pre = A.find(PRE, {"ren": REN})
print("index entries as expected:", sum(1 for x in pre if x), "of", len(pre))
if len(pre) == 12 and all(pre):
    r = A.find("""
FOR m IN @ren
  FOR x IN SYS_ObjectTypeID FILTER x.type_name == "Sample" AND x.upk_id == m.old_name AND x.pk_id == m.key
    UPDATE x WITH { upk_id: m.new_name } IN SYS_ObjectTypeID
    RETURN { pk_id: NEW.pk_id, old: OLD.upk_id, new: NEW.upk_id }""", {"ren": REN})
    print("index entries updated:", len(r))
    for x in r: print("  ", x)
    v = A.find("""FOR m IN @ren RETURN LENGTH(FOR x IN SYS_ObjectTypeID FILTER x.type_name == "Sample" AND x.upk_id == m.new_name AND x.pk_id == m.key RETURN 1) == 1
      AND LENGTH(FOR x IN SYS_ObjectTypeID FILTER x.type_name == "Sample" AND x.upk_id == m.old_name RETURN 1) == 0""", {"ren": REN})
    print("verified:", sum(1 for x in v if x), "of", len(v))
else:
    print("NOT APPLIED")
