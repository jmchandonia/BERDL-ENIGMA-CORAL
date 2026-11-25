# Run on the CORAL hub. Guarded rename of four Taxon records to NCBI's lower-case "incertae sedis".
# A record is written only if it still has the expected old name and the new name is not taken.
from coral import services
services._init_services()
RENAME = {"Taxon0005210": ("Alphaproteobacteria Incertae Sedis", "Alphaproteobacteria incertae sedis"),
          "Taxon0000883": ("Deltaproteobacteria Incertae Sedis", "Deltaproteobacteria incertae sedis"),
          "Taxon0001174": ("Gammaproteobacteria Incertae Sedis", "Gammaproteobacteria incertae sedis"),
          "Taxon0002130": ("Rhizobiales Incertae Sedis", "Rhizobiales incertae sedis")}
AQL = """
LET doc = DOCUMENT(CONCAT("SDT_Taxon/", @key))
LET taken = LENGTH(FOR t IN SDT_Taxon FILTER t.name == @new RETURN 1)
FILTER doc != null AND doc.name == @old AND taken == 0
UPDATE doc WITH { name: @new } IN SDT_Taxon OPTIONS { mergeObjects: true, ignoreRevs: false }
RETURN { id: NEW._key, old_name: OLD.name, new_name: NEW.name }
"""
for key, (old, new) in RENAME.items():
    print(key, services.arango_service.find(AQL, {"key": key, "old": old, "new": new}))
print("after:", services.arango_service.find("FOR t IN SDT_Taxon FILTER t._key IN @k SORT t._key RETURN [t._key, t.name]", {"k": list(RENAME)}))
