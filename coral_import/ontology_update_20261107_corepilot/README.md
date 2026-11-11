# Ontology update: GeoChip and ITS support for the 2017 Pilot Core (2026-11-07)

COMO (`context_measurement_ontology.obo/.txt`):
- `ME:0000522 microarray probe name` (string; under gene): the array designer's name of a probe; for GeoChip the
  GenBank GI number or the IEG in-house identifier of the target gene. A string "name" term, as taxon name and
  strain name are; the "X ID" terms are object references.
- `ME:0000523 gene symbol` (string; under gene): symbol of a gene or gene family (dsrA, nikA). `gene name`
  (ME:0000060) is an object reference into CORAL Gene aliases and cannot hold these.
- `ME:0000130 hybridization intensity` gains `is_microtype` and `is_valid_dimension_variable` (it had only
  `is_valid_data_variable`, which the validator does not accept for a brick data variable).

New ontology `geochip_functional_gene_category.obo/.txt` (prefix GEOCHIP, built by `tools/build_geochip_category_ontology.py`
from the probe annotation of the pilot core GeoChip 5.0 file): root GEOCHIP:0000000, class GEOCHIP:0000001 "GeoChip functional
gene category", microtype GEOCHIP:0000002 "GeoChip gene category" (oterm_ref, xref ORef:GEOCHIP:0000002),
then 12 categories > 123 subcategories > 116 leaves (251 terms, GEOCHIP:0000011 onwards). Labels that still repeat in the tree are
qualified with the parent ("colonization (adherence)") with the bare label as an exact synonym; the designers' "NA"
placeholders are not terms. Near-duplicate paths were merged. Labels that only make sense with their parent are reworded to read on their own ("Arsenic transport", "Cellulose degradation", "Eukaryotic virus replication"), or qualified ("spore (cell wall)") where no natural wording fits, with the source label as a synonym. Terms naming a real compound or element carry a plain `xref: CHEBI:...` (exported to `sys_oterm_links`; CORAL ignores it), elements using the ChEBI atom IDs of the Adams metals bricks. Registration: hub upload_config.json entry `geochip`, CheckGenericProduction.java, the staged
validator, coral_metadata.py CANONICAL_ONTOLOGY_BY_PREFIX + FULL_INCLUDE_ONTOLOGIES, sync_prep.sh copy list.

Process ontology (`process_ontology.obo/.txt`):
- `PROCESS:0000054 Microarray Hybridization` under Assay.

First use: `coral_import/corepilot_its_geochip_20261107` (Zhou Lab pilot core GeoChip 5.0 and fungal ITS).
Baseline = the 2026-11-07 borescope production files (COMO) and the installed process ontology.
