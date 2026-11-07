# Ontology update: velocity, azimuth, micrometer per second (2026-11-07)

- `ME:0000519 velocity` (synonym speed; speed/velocity units): generic magnitude of a rate of movement.
  `wind speed` (ME:0000316, with `gust speed` beneath it) is now its child.
- `ME:0000520 azimuth` (degree): horizontal angle clockwise from north, the direction of a vector such as
  groundwater flow. `wind direction` (ME:0000320) is now its child, its def noting the meteorological "from" convention.
- `ME:0000521 micrometer per second` (um/s) under "units not in UO", a speed/velocity unit.

- `median` (ME:0000153), `minimum` (ME:0000151) and `maximum` (ME:0000152) gain `is_valid_dimension_variable`, as `average` and
  `standard deviation` already have, so a statistic can be the primary term of a data variable in a heterogeneous brick
  (the data variables of such a brick are validated as a dimension).

First use: the 2024 SSO colloidal-borescope bricks (`coral_import/sso_borescope_20261107`).

| File | Before (baseline/) | After (production/) |
| --- | --- | --- |
| context_measurement_ontology.obo | 2b046c334b7092bd6147f2ad243ee2890a0761441eec57159c85e1dd3265109e | 5f5fa175de3ad6ff61ea64f8416f1fff4e3b3b24621edb0db9ded526db83f63f |
| context_measurement_ontology.txt | b1160df71aaa220f776720454df7efc1859f9b2139855bb9f6d01a3425f3dacc | e4ffc508c6e496408617982833f248f5cc3248292fcfc6ae58e051885284e0ea |

Installed 2026-11-07 on stout (`/home/coral/prod/data_import/ontologies/`) and coral-enigma (same path), sha256
obo 5f5fa175…, txt e4ffc508…; reloaded with `toolx.upload_ontologies()` (three benign UBERON errors only); the eight
affected terms verified in `OTerm`. Copied to `~/src/CORAL/example/enigma/ontologies/`.
