# Run on the CORAL hub. Guarded update of the description of two Sample records (nothing else changes).
from coral import services
services._init_services()
A = services.arango_service
COMMON = ("Material from Fields Lab laboratory biofilm reactors (CDC reactors) fed FW-305 groundwater, with nonporous 30 micrometer glass beads in coupons as the "
          "biofilm matrix; water or beads from the reactors were the inoculum for isolations (Kothari et al. 2021, mSystems, PMID 34184913). ")
TAIL = ("The location is the source of the groundwater; the depth equals that of the FW-305 groundwater samples (5.62 m) and presumably refers to the groundwater "
        "that fed the reactors. The material and package terms are as originally recorded; no natural sediment was involved. How the reactors were sampled is not "
        "recorded. Contacts named in the original record: ")
NEW = {
    "Sample0002966": ("Matthew Fields Bioreactor", "Dwayne Elias or Matt Fields should have more details",
                      COMMON + "Of the 25 isolates linked to this sample, 9 are described as from fulvic acid or humic acid coupons and 16 as from bulk groundwater "
                      "(top or bottom). " + TAIL + "Dwayne Elias, Matt Fields."),
    "Sample0002965": ("Bioreactor Coupon", "Dwayne Elias should have more details",
                      COMMON + "All 27 isolates linked to this sample are described as from bulk groundwater (top or bottom) through an anaerobic enrichment with "
                      "fulvic acid or AQDS; none is described as from a coupon. The recorded date, 2014-12-24, could not be verified (the reactors of the other "
                      "sample from this source, Matthew Fields Bioreactor, are dated 2014-06-10). " + TAIL + "Dwayne Elias."),
}
AQL = """LET doc = DOCUMENT(CONCAT("SDT_Sample/", @key))
FILTER doc != null AND doc.name == @name AND doc.description == @old
UPDATE doc WITH { description: @new } IN SDT_Sample OPTIONS { mergeObjects: true, ignoreRevs: false }
RETURN { id: NEW._key, name: NEW.name, old: OLD.description, new: NEW.description, unchanged: [NEW.depth == OLD.depth, NEW.date == OLD.date, NEW.material_term_id == OLD.material_term_id] }"""
for key, (name, old, new) in NEW.items():
    print(A.find(AQL, {"key": key, "name": name, "old": old, "new": new}))
