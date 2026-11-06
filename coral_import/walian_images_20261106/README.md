# CORAL import package: Walian Lab images and Spring 2019 groundwater EM tallies (20261106)

Built by `tools/build_walian_images_coral_import.py`.

| Content | Count | Source |
| --- | --- | --- |
| CPT sediment TEM images (2021) | 11 | team Drive `2020_Cone Penetrometer Sampling/CPT EM imaging/` |
| Pilot-core micro-CT reconstructions (ALS 8.3.2, 2017-05-17) | 14 stacks + 10 slices | `~/data/enigma/walian/microCT` (HDD from Peter Walian, Dec 2019) |
| Spring 2019 groundwater EM morphotype crops | 51 | team Drive `ENIGMA_Imaging/Images_Groundwater/` (122 method-trial crops not loaded) |
| Spring 2019 AODC micrographs (Hazen Lab) | 45 | team Drive `2019_Spring_Integrated Sampling/Hazen Lab/AODC/` (36 numbered by workbook sample number, 9 named) |
| Brick `walian_em_groundwater_counts_spring2019` | 15 samples x 4 categories | `source/GW_imaging_stats.xlsx` (Peter Walian e-mail, 2020-04-17) |

Static additions: Samples MLSB5-2019-04-16-UF-R11, MLSB5-2019-04-30-UF-R11, MLSB5-2019-05-14-UF-R11; Protocols `walian-tem-cpt-sediment-wash-2021`, `walian-als-832-microct-pilot-core-2017`, `walian-tem-groundwater-spring-2019`; 131 Images.
Processes: Image (Walian Lab) per image, Assay Cell Counts for the brick.

EDR: `images/walian_sediment_em/` (TEM), `images/walian_sediment_microct/<RECON folder>/` (full stacks, rsynced from the local copy),
`images/walian_groundwater_em/`, `images/hazen_aodc_micrograph/` (AODC, with camera XML); manifest rows in `edr_images_manifest_rows_walian_images_20261106.tsv`; hub image files in `images_to_install.txt`.
