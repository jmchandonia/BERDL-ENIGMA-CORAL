# ENIGMA image collection: EDR layout plan (2026-11-02, draft for review)

Goal: one folder `dipa:/data/edr/images/` holding every image file that a CORAL Image object links
to (and the image sets still to be imported), in subfolders named `<lab>_<subject>_<technique>`,
with a manifest that the CORAL-to-BERDL sync uses to turn CORAL's flat `/images/<name>` links into
`enigma-data-repository/images/<folder>/<name>`. CORAL's own store stays flat.

## Inventory of image data on the team Drive (mirror scan 2026-11-02, 1,170 files, 13.8 GB)

Excluded as derived figures or scans of documents, not data images: Zhou analysis plots (tiff),
Sampling Mission Control figures, Adams scratch plots, HydroVu screenshots, SSOM6SED bin summaries,
Revil figure bitmaps, the SSO-installation daily-log photos (scans of paper logs) and paper figures,
Hazen 3D-model gifs.

| Set | Files, size | Source on Drive | In CORAL today | Proposed folder |
| --- | --- | --- | --- | --- |
| Walian Lab isolate electron micrographs | 95 TIFF, 572 MB (+17 newer and some renamed duplicates in the Atlas folder of 112) | `ENIGMA_Imaging/Atlas_Isolate_Images_renamed_JMC` (= EDR `isolate_images`); newer ones in `ENIGMA Isolate List and Sequences/Atlas_Isolate Images` | yes: 95 Image objects, `Image` processes, `isolate_image_data_221011_v2` brick | `walian_isolate_em` |
| Walian Lab groundwater cell and virus electron micrographs, by morphotype | 173 TIFF, ~0.5 GB | `ENIGMA_Imaging/Images_Groundwater/<morphotype>/` (29 morphotype folders; wells MLS*, GW821, FW215 in the names) | no | `walian_groundwater_em` (morphotype recorded in the manifest and the future brick, not as folders) |
| Walian Lab TEM of CPT sediment washes | 11 JPEG, 4 MB (+ readme, pptx) | `2020_Cone Penetrometer Sampling/CPT EM imaging` | no | `walian_sediment_em` |
| Pilot-core sediment thin-section TEM | 1 Gatan .dm4, 65 MB | `2017_Pilot Sediment Campaign/PilotSediment micro-CT imaging/Sediment thin-sections` | no | `walian_sediment_em` (confirm it is Walian's) |
| Hazen Lab AODC epifluorescence micrographs | 66 JPEG now in CORAL; 4 CPT (2020); 45 Spring 2019 (`2019_Spring_Integrated Sampling/Hazen Lab/AODC`, 2560x1920, same camera) | core pilot, 100WS/2016-17, CPT, Spring 2019 | 66 yes (corepilot_aodc bricks); 4 CPT in the pending package; 45 Spring 2019 no (the batch C1 AODC brick has no images) | `hazen_aodc_micrograph` |
| Hazen Lab pilot core segment photos | 57 PNG, 1 MB | CORAL store only (not found on Drive) | yes (`corepilot_pm_106/271` bricks) | `hazen_core_photo` |
| Pilot-core micro-CT | 10 selected slices (2560x2560 float TIFF, 262 MB) and one full reconstruction stack of 405 slices (10.6 GB) for FW106 section 7-6 | `2017_Pilot Sediment Campaign/PilotSediment micro-CT imaging` | no | `hazen_sediment_microct`; the full stack as `hazen_sediment_microct/EB106-07-06_recon/` (decide whether CORAL gets one Image per slice or one object for the stack) |
| CPT 2020 campaign field photographs (Y-12 cleared, photographer Bret Pate) | 101 JPEG, 570 MB (duplicated in part under `2020 CPT Fugro/AREA 3/CPT photo session 3 of 3`) | `2020_Cone Penetrometer Sampling/CPT Y-12 Cleared Pictures Photographer Bret Pate` | no | `hazen_field_photo` (campaign and date in the manifest) |

Not on the team Drive but worth asking about: borescope images (only logs/pdf on Drive), SSO
drilling photos, EM of SSO sediments.

## Folder and file conventions

- `images/<lab>_<subject>_<technique>/<file>`: one level of subfolders; lab = CORAL lab term
  (walian, hazen, zhou, ...), subject = isolate | groundwater | sediment | core | field,
  technique = em | aodc_micrograph | microct | photo. New categories are added by appending to
  this list; the manifest, not the folder, carries morphotype, well, date and campaign.
- File names are the CORAL Image names, unique across the whole collection (CORAL's Image.name
  is a unique key, so this is guaranteed for imported files). Files imported later keep their
  source names unless they collide or contain spaces, in which case they are renamed at import and
  the original name is recorded in the manifest.
- `images/manifest.tsv` columns: `path` (relative to images/), `coral_image_name`, `lab`,
  `subject`, `technique`, `mime_type`, `size_bytes`, `source_drive_path`, `original_name`,
  `coral_objects` (sample/strain/community the image belongs to), `status` (in_coral | pending).
- `images/scripts/`: the existing isolate copy script, log and process TSV, plus the future
  builder that adds files and manifest rows.
- The old `edr/isolate_images/` is removed after its 95 files are in place; `index.html` is
  updated; `sync_berdl.sh`'s delete stage drops the old MinIO paths.

## Sync rule

`sdt_image.link` in the Lakehouse = `enigma-data-repository/images/` + manifest `path` for the row
whose `coral_image_name` equals the Image name. The sync fails if an Image has no manifest row or
the file is absent from `edr/images/`; after `sync_berdl.sh` a check lists the MinIO objects under
`images/` and compares them with the manifest.

## Order of work

1. Build `images/` with the three existing sets (95 + 70 + 57 files), the manifest and scripts;
   remove `isolate_images/`; run the EDR sync; add the sync rule and check.
2. Load the CPT AODC/DOC package (its 4 micrographs are rows 1-4 of the pending list).
3. Import the pending sets one at a time, each as a CORAL package with Image objects and the
   process or brick that links them: Spring 2019 AODC micrographs (need the sample mapping from
   the Hazen AODC workbook/pptx), Walian groundwater EM (173; morphotype brick), CPT field photos,
   Walian CPT sediment TEM, micro-CT, newer Atlas isolate images (with the isolate update).
