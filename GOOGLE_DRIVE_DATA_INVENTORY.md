# ENIGMA Google Drive data inventory and CORAL import status

Prepared 2026-10-07 from the NFS mirror of the ENIGMA team drive:
`/mnt/net/dipa.jmcnet/data/backup/google-drive/enigma_team_drive_data_enigma_backup`

CORAL status was determined against the live production export taken 2026-10-07
(719 current bricks; 24 campaigns; sample, community, location, strain and
protocol name lists). "In CORAL" means a current brick (or core-type records)
holds the data; it does not mean every column of the source file was captured.

## How to read this document

* **Where the data live** is one of:
  * `in document` — the numbers are in the spreadsheet / docx itself;
  * `files in folder` — the document is a README or metadata sheet, and the
    data are sibling files in the same Drive folder (fastq, csv, pdf, ...);
  * `linked` — the document points to data elsewhere, with the link host
    named (Google Drive, KBase, Arkin lab EDR path on niya/namib, Box,
    Dropbox, GNPS, ESS-DIVE, ...).
* **CORAL status** is one of `in CORAL (brick ...)`, `partly in CORAL`,
  `samples only` (sampling/processes exist but no measurement brick),
  `not in CORAL`, `derived/export from CORAL` (nothing to import),
  `n/a` (planning/meeting documents, no data).
* Rows marked **gap** are the candidates for new CORAL imports.

## Mirror hygiene notes

| Issue | Detail |
| --- | --- |
| Total files in mirror | 25,516 |
| Recursive shortcut copies | 8,517 files under paths containing `Cone Penetrometer Sampling 2020/` are a Drive shortcut mirrored as nested copies of the CPT folder; excluded. |
| Exact duplicate folders | `2023_2024_One-Off Sampliing/` (older copy of `2023_2024_2025_One-Off Sampliing/`), `ENIGMA_Imaging/Atlas_Isolate Images/`, `Data_ComparativeMetagenomics_Pilot/Zhou Lab/{SSO.Sediment.2023,Pilot.ITS…,100_Well_16s_Sequence,Protocols_ZhouLab}/` and `…/Alm Lab/` (copies of `FRC Sequence Data/…`), `2025_EnCom_SSO_sediment_M6_pilot/Baliga_metagenomes/RawTrimmedReads/` (copy of `Enrichments/SSOM6SED/`). |
| Files after de-duplication | 16,325 |
| Documents indexed (xlsx/xlsm/docx/csv/tsv) | 1,559 |
| Links to Arkin lab servers | No `niya` URLs anywhere. EDR paths appear only as `/auto/sahara/namib/home/gtl/enigma-data-repository/...` strings in two isolate workbooks (both already represented in CORAL by `isolate_sequence_and_quality_arkin_260921`). |

Scratch index files (per-document sheets, headers, hyperlinks) are in the
session scratchpad under `gdrive/` (`index.jsonl`, `documents.tsv`,
`dedup_files.tsv`); they are not part of the repo.

---

## 1. Field campaigns, 2017–2020 (FRC wells)

### 2017_Pilot Sediment Campaign (Core Pilot, EB106 / EB271)

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `Pilot Project Data Log.xlsx` | Index of lab results: FvN nitrate respiration (N2O/NH4), Majumder SRB silver-wire assays, others (15 rows) | linked (Google Drive file ids ×10) | partly: Stahl acetylene (`stahl_corepilot_acetylene`), Wall sulfide (`wall_corepilot_sulfide_106/271`) are in CORAL; the linked raw FvN and Majumder files were not resolvable from the mirror. |
| `ENIGMA Field Sample data from Hazen Lab.docx` | Pointer document | linked (enigma.lbl.gov/data/field, Dropbox `ENIGMA_ORNL_FieldSampling`, Drive) | n/a (100WS field data already in `hazen_field_100ws`, `hazen_insitu_100ws`, `hazen_insitu_hach_100ws`) |
| 415 `.tiff`, `.dm4`, 9 `.xls`, 9 `fastq.gz` in folder | EM images and raw amplicon reads for pilot cores | files in folder | images: not in CORAL; reads: Zhou OTU tables in CORAL (`zhou_otu_count_corepilot_106/271`, `zhou_otu_id_corepilot`) |

Core Pilot lab data confirmed in CORAL: Adams metals, Hazen XRF (major/trace/U),
Hazen AODC (raw + processed), Fields DAPI/BONCAT, Northen raw metabolomics,
Chakraborty C/N/moisture, Hazen pH/conductivity, Zhou 16S OTUs.

### FRC_Microarray, FRC Sequence Data, Data_ComparativeMetagenomics_Pilot

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `FRC_Microarray/2017_Pilot_Core_GeoChip_JoeLab/Pilot.core.GeoChip.T5S2.log.RA.csv` + ReadMe | GeoChip 5 functional-gene relative abundance for EB106/EB271 cores | in document (csv) | **not in CORAL (gap)** |
| `FRC Sequence Data/Zhou Lab/Pilot.16S.sequencing.ENIGMA.Version170606/` (OTU tables, treatment csv, Analysis_ArkinLab merged csv) | Pilot core 16S OTUs + Arkin-lab merge with field measurements | in document (csv) + linked (Drive, Box, zhoulab5.rccc.ou.edu) | in CORAL (`zhou_otu_count_corepilot_*`); Arkin merged tables are derived |
| `FRC Sequence Data/Zhou Lab/Pilot.ITS.sequencing.ENIGMA.version171101/` (ITS OTU tables + ReadMe) | Pilot core fungal ITS OTUs | in document (csv) + linked (Dropbox zip) | **not in CORAL (gap)** |
| `FRC Sequence Data/Zhou Lab/100_Well_16s_Sequence/` (`otu.table.txt.gz`, README) | 100 Well Survey OTU table | files in folder | in CORAL (`zhou_otu_count_100ws_v2`, `zhou_otu_id_100ws`, `zhou_otu_repseq_100ws`) |
| `FRC Sequence Data/Alm Lab/` (eotus lineages, README) | 100WS Alm-lab eOTU tables | files in folder | not in CORAL (superseded by Zhou OTUs; low priority) |
| `FRC Sequence Data/Arkin Lab/README.docx` | Email describing 2017 bottom-up analysis | n/a | n/a |
| `FRC Sequence Data/Zhou Lab/SSO.Sediment.2023/` | SSO sediment 16S ASV (v230726, v230906) | in document (csv/xlsx) | in CORAL (`zhou_lab_sso_sediment_ASV_*`) |
| `Data_ComparativeMetagenomics_Pilot/Wall Lab/2017-10-17 SRB 16S abundance…xlsx`, `Core16Srarefied-KD.xlsx` | Wall-lab reworking of Zhou OTUs (SRB relative abundance, alpha diversity) | in document | derived; not needed |

### 2017 EVO Injection

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `Zhou - 16S sequencing/ReadMe_EVOinjection2017_16S_v20230222.docx`, `20230222.metadata.csv`, `V230222.zOTU/` (zOTU tables), `Raw sequencing data/{141003,141031,180507,180717,200724}/` (20 fastq, 30 GB) | 16S zOTU tables and raw reads for the 2017 EVO injection time series (71 samples) | in document (csv) + files in folder | **not in CORAL (gap)**: no EVO campaign bricks; samples not present |

### 2019_Spring_Integrated Sampling (Spring 2019 campaign)

CORAL holds 13,982 Spring 2019 processes (sampling, filtering, isolation, 16S)
and the Zhou ASV tables, but **no lab-measurement bricks** for this campaign.

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `Adams Lab/2019_Groundwater_Time_Series_2HNO3_52_Final.xlsm` | ICP-MS metals (combined conc/SD/DL/BEC, ~1000 samples × 52 analytes) | in document | **not in CORAL (gap)** |
| `Chakraborty Lab/C & N analysis_20190801.xlsx`, `Results_Area3.xlsx` | TOC/TN (ppm) by sampling date | in document | **not in CORAL (gap)** |
| `Elias Lab/Ferrozine-ENIGMA-2019.xlsx` | Fe(II)/Fe(III) ferrozine, 94 rows | in document | **not in CORAL (gap)** |
| `Fields Lab/2019SpringSampling_CellCounts_FieldsLab.xlsx` | Cell counts (66 rows) | in document | **not in CORAL (gap)** |
| `Fields Lab/2019SpringSampling_activity_FieldsLab.xlsx` | Per-mL / per-cell activity (ng C/mL/d) | in document | **not in CORAL (gap)** |
| `Fields Lab/2019SpringSampling_18O_2H.xlsx` | Water δ18O / δ2H | in document | **not in CORAL (gap)** |
| `Fields Lab/Spring2019_FieldSampling_DataCompilation.xlsx` | Cross-lab compilation (Fields, Elias, Chakraborty, Adams, Hazen) with STDEV | in document | not in CORAL (derived) |
| `Hazen Lab/AODC/AODC_Active Sampling 2019_*.xlsx` (3 versions) | AODC counts, 905 rows | in document | **not in CORAL (gap)** |
| `Stahl Lab/190618_StableIsotopes_AO_FvN.xlsx` | Ammonia-oxidation stable isotope assays | in document | **not in CORAL (gap)** |
| `Hazen Lab/Field Sheets/2019 Spring Master Spreadsheet(-Metadata).xlsx`, `samples shipped.xlsx` | Sample log incl. DO/ORP/cond/temp field readings | in document | samples in CORAL; field readings not confirmed in a brick |
| `Hazen Lab/Rad Protection Group_Isotope activity analysis/` (Analysis Log + pdf) | Radiological activity reports | files in folder (pdf) | not in CORAL |
| `Zhou Lab/16S_sequencing/V190722*.ESV/` + ReadMes, `SpringSampling_SampleInformation_DNAconcentration_Zhou_20190722.xlsx` | ESV tables (cleaned/resampled/copy-number corrected), DNA concentrations | in document (csv) + linked (Dropbox protocol, zhoulab5 server) | ASVs in CORAL (`zhou_lab_100ws_spring19_*`); DNA concentrations not |
| `Arkin Lab/HighThroughput_{pickingsheet,rearrayconsolidate,noreadwells_sanger}.csv`, `Amplicondata_ht1-12/ht1-12_meta.docx`, `16sblast_October21.docx`, `gDNA concentrations_BarkerHall/*.xlsx` | High-throughput isolation plates, Sanger 16S hits, gDNA | in document | isolates (FHT strains) and 16S in CORAL; plate/gDNA metadata not |
| `Manuscript/*.docx`, `Zhou Lab/SOP_discussion/` | Abstracts, SOP discussion | n/a | n/a |
| 102 pdf, 45 xml, 44 jpg, 9 kmz in folder | Field sheets, gel/images, well maps | files in folder | not in CORAL |

### 2019_Summer／Fall_27-Well Survey

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `Adams - metals/Adams_Metal_Data_27-Well_GW_1-70-Days_…2021-04-26.xlsx` | ICP-MS metals ppb/uM | in document | in CORAL (`adams_metals_27ws`) |
| `Chakraborty - Anions/Anions_Area {1,2,3}*.csv` | IC anions | in document | in CORAL (`chakraborty_anions_27ws`) |
| `Chakraborty - C and N/*.csv,*.tsv` | DOC/TN/DON/DIC | in document | in CORAL (`chakraborty_c_n_27ws`) |
| `Stahl - isotopes/Isotopes/2020_*_Isotopesanalyses_v*.xlsx` | NO3/NO2/N2O/H2O isotopes | in document | in CORAL (`stahl_stable_isotope_27ws`); the later v3 (Dec 2020, Wankel/Bowman N2O data) may be newer than the import |
| `Hazen - Field Log and TROLL data/27Well_2019_Field_Log.xlsx` (Weather, Bug Traps, Master 3243×162) | Field log, HOBO weather, TROLL readings | in document | in CORAL (`hazen_troll_27ws`); weather sheet in `hazen_hobo_WS1/WS2` |
| `27Well_2019_Sample_Log_Master_Limited.xlsx` | Master sample log (DNA, AODC, metals, HPIC, TOC, isotopes columns) | in document | samples in CORAL; AODC column values not confirmed as a brick |
| `Zhou - 16S sequencing/V210407.ASV, V210408.ASV` + ReadMes (0.2 µm and 8 µm) | ASV tables, 1100 fastq.gz | in document (csv) + files in folder | in CORAL (`zhou_otu_count_27ws`, `zhou_27ws_ESV_16S`, `zhou_lab_27_well_survey_ASV_16S`) |
| `Zhou - 16S sequencing Bug trap samples/` (ReadMe v20210507, `27wellBugtrap_metadata_Zhoulab.xlsx`) | Bug-trap 16S ASV tables, 284 samples | in document (csv) + linked (Dropbox protocol) | **not in CORAL (gap)** |
| `Fields - PBR/ReadMe_PBR_Sample_16S_v01252022.docx` + tables | Bug Trap Reactor (PBR) 16S | files in folder | **not in CORAL (gap)** |
| `Hazen - Visual Model/Dixon_Thesis_FINAL.docx`, `Manuscript/*` | Thesis, outlines, FAPROTAX exports from KBase narrative | n/a / derived | n/a |

### 2020_Cone Penetrometer Sampling (CPT)

CORAL holds 40 `CPT*` locations, 34 CPT sediment samples, 2,629 CPT-campaign
processes and the CPT ASVs inside the combined Zhou brick. The physical and
geochemical CPT data are **not** in CORAL.

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `CPT Metadata FINAL/CPT_full_data.xlsx` (Location 115, ProbeData 50,036 rows, SedimentMetadata), `CPT_full_data_adding_columns.xlsx`, `Metadata Read Me.docx` | Fugro probe profiles (tip/sleeve/pore pressure vs depth), bore locations, sediment sample metadata | in document + linked (Drive) | **not in CORAL (gap)**: ProbeData and Location tables |
| `CPT_Oct2020_Fugro_Data/CPT-*.csv` (and `CPT Plots and Data 10-*-2020/`), pdf plots | Per-sounding raw Fugro exports (~60 soundings) | in document (csv) | **not in CORAL (gap)** (superset in `CPT_full_data.xlsx`) |
| `2024_0418_Putt's Restored CPT Data…/2020 CPT Fugro/AREA 3/CPT_Fugro_Master_data2020102*.xlsx`, `CPT_Mapped.xlsx`, `CPT_Map.xlsx`, `Y-12 Borings_Lat_Long_All.csv`, `Export01.xlsx`, `RockWorks Sample Import…xlsx` | Daily master sheets, coordinates, RockWorks lithology | in document | partly (locations in CORAL); lithology/stratigraphy not |
| `…/AREA 3/Water Level Master 20201020.xlsx` (+ `Manuscript/…/data_cpt/` copies) | Manual water levels at CPT holes | in document | **not in CORAL (gap)** |
| `…/2020 CPT Fugro/CPT_SED_full_data_0{4162021,5032021}.xlsx`, `Manuscript/Jupyter notebooks/CPT_Sediment_full_data_with_distances.xlsx` | Sediment sample table (33 × 79): coordinates, depth, geochem summary, distances | in document | samples in CORAL; measurements not |
| `AODC 2020 CPT/CPT_sediments_AODC_04062021.xlsx` | AODC on CPT sediments (894 rows) | in document | **not in CORAL (gap)** |
| `Chakraborty CPT DOC data/waterextract_TOC_Northenmethod.xlsx` + README | Water-extractable DOC (32 samples) | in document | **not in CORAL (gap)** |
| `Dataset_Revil_et_al./general_files/Resistivity profiles with coord.xlsx` (+ h5/csv) | Electrical resistivity profiles P1–P4 | in document | **not in CORAL (gap)** |
| `CPT EM imaging/Readme for CPT imaging.docx` + images | EM images of CPT sediments | files in folder (jpg/tif) | not in CORAL |
| `Zhou lab 16S sequencing/V211127ASV/` (+ ReadMes v20210422/0530/1127, `CPT_metadata_Zhoulab.xlsx`) | CPT sediment ASVs, iCAMP/NST/neutral-model outputs | in document (csv) + linked (Dropbox) | ASVs in CORAL (combined brick); ecological-model outputs are derived |
| `…/2020 CPT Fugro/Field Samples_Pilot_Spring_27Well_CPTcor.xlsx` | Cross-campaign sample tracking (Pilot, Spring, 27WS, CPT) | in document + linked (Drive ×25, Docs ×4) | samples in CORAL |
| `…/FTP For SSO Installation/SSO Screens.xlsx`, `Y-12 New Wells.xlsx`, `SSO sediment analysis/SSO Sediment Mastersheet.xlsx`, `SSO_SedimentSampleCollection.xlsx` | SSO well screens, survey coordinates, sediment core inventory | in document | well construction in CORAL (`hazen_oak_ridge_well_construction_data_v3`); core inventory: samples in CORAL |
| `…/tracer tests 20220608/` (FTP, field guide, transmissivity test) | 2022 Area 3/Area 1 tracer test plans | n/a | n/a (no result data in Drive) |
| `…/colloidal borescope-March-12-2021/Colloidal Borescope 31221.docx` | Borescope results FW126/127/128 | in document (text) | not in CORAL |
| `Manuscript/cpt paper data/HydroVu_EFPW0{1,2,3}_2022-08-17_Export.htm` | 2022 AquaTROLL exports for EFPW01–03 | in document (htm) | EFPW02/03 in CORAL (`hazen_aquatroll600_EFPW02/03_*`); **EFPW01 not** |
| `Manuscript/Jupyter notebooks/…`, `MEETING NOTES 2021/`, `FTP: Field Test Plan/`, `CPT Deliverables list.xlsx`, `Putt Dissertation Chapter 4-5.docx` | Notebooks, meeting notes, plans; ESS-DIVE link to published CPT dataset (doi:10.15485/1868939) | n/a / linked (ESS-DIVE) | n/a |
| `List of Measurements10072020.xlsx`, `CPT measurements*.xlsx`, `Shipping/Samples for shipment_*.xlsx`, `CPT Sediment __ARCHIVED SAMPLES/` | Measurement plan, shipping and archive inventories | in document | samples in CORAL; archive inventory not |

### FRC Well Metadata

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `All_Wells_ConstructionData_GoogleEarthTags.xlsx`, `ORNL_Y-12_WellConstruction_GoogleEarthTags.xlsx`, `Oak Ridge well construction data FvN.xlsx`, `FRC_Background_Wells__updated 131108.xlsx`, `bc_select_fmdata.csv` | Well construction, coordinates, screens | in document + linked (OSTI report) | in CORAL (`hazen_oak_ridge_well_construction_data_v3`, locations) |
| `100 Well Survey Original Data/Chandonia Lab/enigma_field_data_hazen_180417.xlsx/.tsv` (also `ENIGMA Public Data/Smith-2015-mBio/`) | 100WS geochemistry (14,664 rows long format) | in document | in CORAL (`hazen_field_100ws`, `hazen_insitu_100ws`, `hazen_insitu_hach_100ws`, `hazen_field_post100ws`) |
| `100 Well Survey Original Data/Alm Lab/{cluster_data,uefpclab_describe,Data dictionary…}.xlsx`, `frc_nonmaip_labdat-1.csv` | Alm-lab 100WS summaries and ORNL lab data dump | in document | derived / historical; not in CORAL |
| `Chain of Custody Sheets/IntegratedGWSampling_AllSheetsandInfo_*.xlsx`, `2019 Spring Master Spreadsheet.xlsx`, `2019 Spring samples shipped.xlsx` | Spring 2019 sampling sheets and chain of custody | in document | samples in CORAL |
| `Core samples/1506_CoreSummary.xlsx`, `Copy of IC Analysis of Core.xlsx`, `Copy of Static Loaded Preprocessed…ORNL+Batch 2.xlsm`, `FW305 Core Depths….xlsx` | 2013–2015 FW305/FW306 core inventory, moisture, Fe(II/III), IC anions, ICP-MS | in document | **not in CORAL (gap)** (FW305/FW306 isolates exist in CORAL; the core geochemistry does not) |
| `FRC well sampling locations ENIGMA.xlsx` | Well lists for Area 3, pH manipulation, Istok, SRS experiments | in document | locations in CORAL |
| `Well monitoring and weather data/*_AT600_*.csv`, `*_LT400_*.csv` (27 files, 2018–2020) | AquaTROLL 600 / LevelTROLL 400 logs | in document (csv) | in CORAL (`hazen_aquatroll600_*`, `hazen_leveltroll400_*`) for 26 of 27; **`DP06_LT400_20190728_20191206.xlsx` not in CORAL (gap)** |
| `Well monitoring and weather data/Area_2_Weather_20180730_20190622.xlsx`, `BGA_Weather_…xlsx`, `old_data/` (49 interim HOBO/TROLL csv) | HOBO weather stations, interim downloads | in document | in CORAL (`hazen_hobo_WS1_20180730_20190622`, `hazen_hobo_WS2_…`); `old_data` superseded |

### FRC Sample Request Logs

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `ENIGMA_MasterSampleList_5.21.14_jmc.xlsx` | 2014 master sample list (297 × 271), lat/long, shipping | in document | samples from 2014 campaigns in CORAL (100WS era); not re-checked column by column |
| `ORNL Field Sampling Requirements (Responses).xlsx` | Sample request form responses (488 collected samples) | in document | not in CORAL (request log) |
| `1506_CoreSummary.xlsx` | duplicate of FRC Well Metadata copy | in document | see above |

---

## 2. Subsurface Observatory (SSO) era, 2022–2026

### Hazen SSO Continuous Monitoring

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `AQUATROLL DATA/Data Files-Cleaned+Marked/Data Files {START-December 2025, December 2025, March 2026} Downloads/<well>/VuSitu_Log_*.csv/.xlsx` (301 files) | Cleaned AquaTROLL 600 (SZ) and LevelTROLL 500 (VSZ/VZ) logs for all 9 SSO wells, Aug 2024 → Mar 2026 | in document (csv) | in CORAL: every file's log date falls inside a `hazen_aquatroll600_SSO-*` / `hazen_leveltroll500_SSO-*` brick range (283 sensor bricks) |
| `AQUATROLL DATA/Download Zips/` (49 zip, 32 html, csv; `AT600 download_05092023/`, `Level Troll Downloads May 2026/`) | Raw direct downloads | files in folder (zip) | raw of the above; `EFPW03`, `EFPW06` 2022–23 in CORAL; **`EFPW01_08022022…csv` and `EFPW05_09292022…xlsx` not in CORAL (gap)**; May 2026 LevelTROLL zips extend past the last brick (2026-05-04) |
| `README Clean(ed) Aquatroll Files.docx`, `README Direct Troll Downloads.docx` | Documentation | n/a | n/a |

### 2023_SSO_Drilling／Sediment Core

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `SSO Sediment Mastersheet.xlsx` (Sheet1 182×27, shipping, RAD) | Core inventory and sample assignment (metals, metabolomics, 16S, 18S) | in document + linked (FedEx) | samples in CORAL (`SSO-U1-C1-00` … 159 SSO sediment samples) |
| `2023-Adams-Metals-sediment/2024-06-29_Adams-Lab_ENIGMA-SSO-Sediment_Metal-Data.xlsm` | ICP-MS metals on sediment extracts (Well Info 171 rows, runs 506×63) | in document | **not in CORAL (gap)** |
| `2023-Northen-Metabolomics-sediment/` (`GNPS links….xlsx`, `data note….docx`, `Read Me.docx`, 2 × GNPS task folders with feature tables, `merged_results*.tsv`, mgf) | LC-MS metabolomics (C18 and HILIC) feature tables and GNPS annotations | in document (csv/tsv) + linked (gnps2.org tasks ×6, Google Docs/Drive) | **not in CORAL (gap)** |
| `2023-Zhou_16s-sediment/` (ReadMe v20230726b, BarcodeMap, `SSO.Sediment.V230726ASV/`, raw fastq) | SSO sediment 16S ASVs | in document (csv/xlsx) + linked (OU protocol server 129.15.40.254) | in CORAL (`zhou_lab_sso_sediment_ASV_16S/count/taxonomy_v2`) |
| `FTP_SSO Well Installation_20230217.docx` | Field test plan | linked (Smartsheet, enigma.lbl.gov) | n/a |

### 2023_SSO_Initial Well Characterization

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `SSO_Initial Well Characterization metadata.xlsx` | Sample metadata, elevations/TOC (39 rows) | in document | **not in CORAL (gap)**: no 2023 IWC samples found (CORAL 2023 samples are Sept 2023 `20230913-M5-SZ2-*` only) |
| `2023-Adams-Metals/2024-06-29_Adams-Lab_ENIGMA-SSO-Initial-GW_Metal-Data.xlsm` | ICP-MS metals, initial groundwater | in document | **not in CORAL (gap)** |
| `2023-Hazen-AODC/2023-Hazen-AODC_SSO_IWC .xlsx` | AODC counts | in document | **not in CORAL (gap)** |
| `FTP_SSO Well Characterization_20230613.docx` | Plan | n/a | n/a |

### 2024_SSO, 2024_SSO_Borescope Characterization

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `2024_SSO/DTW_ManualMeasurements_SSO.xlsx` | Manual depth-to-water (ft BGS / BTOC) per well-zone, Jan–? 2024 (26 dates) | in document | **not in CORAL (gap)** |
| `Borescope Measurements/2024_SSO_Borescope Characterization_Metadata.xlsx`, `2024020*_<well>.docx` (36 `.log` + 36 `.pdf`) | Colloidal borescope flow-vector results (velocity/direction per depth) | in document (docx tables) + files in folder (log/pdf) + linked (Google Doc) | **not in CORAL (gap)** |
| `FTP_SSO_2024_Borescope and Monitoring Install.docx` | Plan | linked (HydroVu, Drive) | n/a |

### 2024_SSO_Pump Test

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `2024_Pump Test_ Metadata.xlsx` (METADATA 119×24, shipping) | Sample metadata with field measurements | in document + linked (Drive ×9) | in CORAL (`sso_pump_test_2024_environmental_measurements`, 112 rows; samples `20240212-…`) |
| `Adams_Metals/2024-06-29_Adams-Lab_ENIGMA-SSO-Pump-Test_Metal-Data.xlsm` | ICP-MS metals | in document + linked (Google Sheet) | **not in CORAL (gap)** |
| `Chakraborty_IC／TOC/20240412_SSO_pumptest_IC_full_w_rawdata.xlsx`, `20240416_TOC_TN_SSO_pumptest_corrected.xlsx`, ReadMe | IC anions (Cl, SO4, NO3), TOC/TN | in document + linked (Google Doc/Drive) | **not in CORAL (gap)** |
| `Stahl_Isotopes/20240416_TOC_TN_IC_ISOTOPES_SSO_pumptest.xlsx` | Isotope data (35 rows) plus copies of IC/TOC | in document | **not in CORAL (gap)** |
| `Hazen_AODC/AODC_pump test _UTK .xlsx` | AODC counts (30 rows) | in document | **not in CORAL (gap)** |
| `Hazen_Field Data/Manual DTW BGS.xlsx` | Manual DTW during pumping (791 rows) | in document | **not in CORAL (gap)** |
| `Hazen_TROLL Files/TROLL Files_Raw/<well-zone>_2024-04-16_*.csv` (27 files) + README | AquaTROLL/LevelTROLL logs during the April 2024 pump test | in document (csv) | **not in CORAL (gap)**: SSO sensor bricks begin 2024-09-04 (U1 VSZ) / 2024-10-03 (SZ) / 2024-12-20 (VSZ/VZ) |
| `Zhou_16S/` (ReadMe v20240722, DNA info csv, CleanData, DataAnalysisResults) | Pump-test 16S ASVs | in document (csv) + linked (OU protocol server) | in CORAL (`zhou_lab_sso_pump_test_ASV_*`) |
| `2024 FTP 2024 2.0_PumpTests.docx` | Plan | linked (Drive ×6) | n/a |

### 2024_SSO_Pilot Time Series

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `2024_Pilot Time Series_ Metadata.xlsx` (METADATA 255×28, Depth to Water 75×8) | Sample metadata, field readings, DTW | in document + linked (Drive ×9) | in CORAL (`sso_pilot_time_series_2024_environmental_measurements`, 211 rows); DTW sheet not confirmed |
| `Adams_Metals/2024-10-09_…Pilot-Time-Series_Metal-Data(-Final).xlsm` (+ Archive, + copy in Pump Test folder) | ICP-MS metals | in document | **not in CORAL (gap)** |
| `Baliga_Ammonia／Nitrite/202111_SSO samples.xlsx` | NH4/NO2 colorimetric assays (550 raw rows) | in document | **not in CORAL (gap)** |
| `Chakraborty_Anions/20241220_IC_results_SSO_timeseries.xlsx` | IC anions | in document | **not in CORAL (gap)** |
| `Zhou_16S/` (ReadMe 20241029, sample info, DNA conc, Clean/Raw/Resamp) | Time-series 16S ASVs | in document (csv) + linked (Drive, OU server) | in CORAL (`zhou_lab_sso_pilot_time_series_ASV_*`) |
| `FTP_Pilot Time Series.docx` | Plan | linked (Drive ×7) | n/a |

### 2023_2024_2025_One-Off Sampliing

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `SSO_Metadata_One Off Sampling.xlsx` (253×42) | One-off sample metadata with field readings | in document + linked (Drive folders ×2, Jira, FedEx) | in CORAL (`oneoff_260609_sample_metadata`, 185 rows) |
| `2023-Murtazina-Hazen-Zhou_ colloids/` (ReadMe 20240916, `Sample.Information.20240916.xlsx`, `SSO.OneOff.DM.V2…/` ASV tables) | Colloid filter-fraction 16S ASVs (11 samples) | in document (csv) | **not in CORAL (gap)** |
| `2024-FTP6-Arkin_Zhou-UpperWellAOA/` (ReadMe, DNA conc, Clean/Raw/Resamp ASV) | Upper-well AOA 16S ASVs (16 samples) | in document (csv) | **not in CORAL (gap)** |
| `2024-FTP7-Shreve-Field_Zhou-Microcalorimetry/` (ReadMe, DNA conc, ASV tables) | Microcalorimetry sample 16S ASVs (7 samples) | in document (csv) | **not in CORAL (gap)** |
| 72 fastq.gz + md5 in folder | Raw reads for the three sets | files in folder | not in CORAL |
| `FTP_One-Off Sampling.docx` | Plan | linked (Google Docs) | n/a |

### 2025_SSO_PumpTest2

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `2025_PumpTest_Metadata.xlsx` (Sample Metadata 131×30, Field Log, Pump Log 243×6) | Sample metadata, field log, pump log | in document + linked (Google Doc) | in CORAL (`pumptest_2025_field_measurements`, 127 rows); Pump Log sheet not confirmed |
| `Fields_activity_cell counts/Fields_CellCounts/2025_PumpTests2_FixedCellCounts_Shreve.xlsx` | Fixed cell counts | in document | in CORAL (`pumptest_2025_fields_cell_counts`) |
| `Hazen - Field Data/TROLL Files - Direct Downloads／Corrected/<well>/VuSitu_Log_2025-08/09-*.xlsx` (31) and `TROLL Files - HydroVu/HydroVu_<well>_2025-09-20_Export.xlsx` (9) | AquaTROLL logs Aug–Sep 2025 | in document | in CORAL (dates fall inside `…_20250819_20251008` bricks) |
| `Hazen - Field Data/Weather Data in Area 3/rain_10-03-25_to_10-30-25…csv` | HOBO rain gauge Oct 2025 | in document | in CORAL (`hazen_hobo_WS3_20250604_20260122`) presumed; rain column not verified |
| `Hazen - Field Data/2025 Pump Test Field Sheets Blank.xlsx` | Blank templates | n/a | n/a |
| `2025 FTP_PumpTests2*.docx` | Plans | linked (Drive, Slides) | n/a |

### 2025_SSO_Tracer Test, 2026_SSO_Tracer Tests

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `2026_SSO_Tracer Tests/U2-SZ1 Injection 20260218/*.csv` (13), `M4-SZ1 Injection 20260310/*.csv` (13) | Bromide tracer breakthrough logs (Seametrics TempHion bromide/temperature probe exports per observation zone; ~173k records per probe for U2, ~59k to 69k for M4) | in document (csv) | **not in CORAL (gap)** |
| `M5-VSZ Injection 20260410/` (12 csv + `M5-VSZ_KBrInjection_20260410_Metadata.xlsx`) — **present only in the My Drive copy, see section 6** | Third injection, Apr 9 to May 11, 2026, ~278k records per probe; DTW during injection | in document (csv/xlsx) | **not in CORAL (gap)** |
| `2026_SSO_Tracer Tests/Simulation_results/test_case/*.h5` (32) | Flow/transport model outputs | files in folder | not in CORAL (model output) |
| `FTP_SSO Tracer Test 2025.docx`, `FTP_SSO Tracer Test 202604 .docx`, `FTP_Tracers.docx` | Plans | linked (Drive, geotechenv.com) | n/a |

### 2025_Green Tag_SSO rad activity, 2025_EnCom_SSO_sediment_M6_pilot

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `2025_Green Tag…/RMAL data_250428/*.pdf`, `NRPD_data_membranes/readme.docx` + pdf | Radiological (LSC) activity reports for 1 L water samples and filter stacks | files in folder (pdf) | not in CORAL |
| `2025_EnCom…/README.docx`, `Baliga_metagenomes/M6_Sed_EnCom_all_sample_info.txt`, `Data_analysis/` (1,742 files, 16 GB: assemblies, bins, annotation html/txt) | Metagenomes of M6 VZ sediment enrichment communities | files in folder | **not in CORAL (gap)**; related SSOM6SED 16S metadata under Enrichments (below) |

### SSO Sample Requests

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `SSO Sample Request／Metadata／Field Work Sheet.xlsx` | Sample request form responses (7) | in document + linked (Drive) | not in CORAL (request log) |

---

## 3. Enrichment and reactor studies

### Enrichments (Arkin-lab 16S amplicon campaigns, `demulti` pipeline)

| Folder / document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `3x5/` (`working_meta_3X5.xlsx`, `ORNL_100_5.new.tax.tsv`, wide tables, Readme) | 3X5 enrichment 16S zOTU counts/taxonomy | in document + linked (Google Docs/Sheets, GitHub demulti) | in CORAL (`3x5_asv_counts/sequences/taxonomy`) |
| `ORRENR/` (`meta_data2_transformed2.xlsx`, `OR_enrich_wide2.csv`, Readme) | ORRENR enrichment 16S | in document | in CORAL (`orrenr_asv_*`) |
| `SSOECT/` (`ISB_Enrichment_meta.xlsx`, `…gDNA_Metafile.xlsx`, `SSOECT_wide_renamed.xlsx`, `Seattle_25.xlsx`, mapping tsv) | SSOECT (Baliga/ISB) enrichment 16S | in document | in CORAL (`ssoect_asv_*`) |
| `SSOISO/` (`SSOISO_meta.xlsx`, `FHT01-6.tax.tsv`, …) | SSOISO isolation-plate 16S | in document | in CORAL (`ssoiso_asv_*`) |
| `SSOSTOR/1/`, `SSOSTOR/2/` (`metadata.xlsx`, `Jen_25_2.tax.xlsx`, mapping) | SSOSTOR storage-experiment 16S | in document | in CORAL (`ssostor1_asv_*`, `ssostor2_asv_*`) |
| `RecycNec/` (`metadata.xlsx`, `Bri_1-2_meta.xlsx`, `Bri_1-2.tax.xlsx/.tsv`, Readme) | RecycNec (Chakraborty/Hasan) enrichment 16S, 195 samples, sequenced after Dec 2025 | in document | **not in CORAL (gap)** |
| `SSOM6SED/` (`SSOM6SED_metadata.xlsx` 289 rows, README; reads duplicated under 2025_EnCom) | M6 sediment enrichment 16S metadata and raw reads | in document + files in folder | **not in CORAL (gap)** |
| `FW106ENR/1,2/Copy of Blank_metadata.xlsx`, `Blank_metadata.xlsx`, `Readme template.docx` | Empty templates | n/a | n/a |
| 288 `.fastq`, 1,344 `.txt` (demulti outputs) | Raw and demultiplexed reads | files in folder | not in CORAL (reads are not bricked) |

### 2022_Discovery_Nitrifying_Community

| Folder / document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `Sequencing_Results/16S.V4Primer/{DADA2,UPARSE}/` (Alpha, Beta, Composition, Rarefaction, Treatment csv) | Reactor 16S (V4) ASV/OTU analyses, samples SD1… | in document (csv) | **not in CORAL (gap)** |
| `Sequencing_Results/16S18S/{UNOISE,UPARSE}/` | 16S+18S zOTU tables, sample information (Reactor, Type, Date, Day) | in document (csv) | **not in CORAL (gap)** |
| `Sequencing_Results/Archaeal_amoA/`, `Bacterial_amoA/` (UNOISE/UPARSE × FrameBot) | amoA functional-gene zOTU tables | in document (csv) | **not in CORAL (gap)** |
| 3,610 fastq.gz (10 GB) | Raw reads | files in folder | not in CORAL |

No CORAL campaign or sample names correspond to this reactor study.

---

## 4. Isolate, imaging, PPI and reference collections

### ENIGMA Isolate List and Sequences

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `260924_ENIGMA_Isolates.xlsx`, `260225_…`, `old_versions/*` (64 dated versions 2017–2025) | Isolate master list (3,152 × 23) | in document + linked (KBase narrative `ws.41372` objects in older versions) | derived/export from CORAL (isolate bricks `isolate_classification_260205`, `isolation_conditions_251112`, `isolate_availability_260205`, `isolate_publication_260213`, `isolate_16S_sanger_260917`, …) |
| `ENIGMA isolate data exported from CORAL.xlsx` (3,152 × 51), `…legacy spreadsheet format.xlsx`, `ENIGMA sample data exported from CORAL.xlsx`, `ENIGMA samples used for Isolation.xlsx` | CORAL exports | in document + linked (EDR paths `/auto/sahara/namib/.../genome_processing/...` ×60) | derived/export from CORAL |
| `GenomeBatches/GenomeSamples_metadata.xlsx` (Alternate_Sequencing 67×27, Lauren_genome_information 94×8, from_Jen_2022) | Genome sequencing batch metadata | in document + linked (EDR paths ×60, genomics.lbl.gov ×5) | in CORAL (`isolate_sequence_and_quality_arkin_260921`, Genome records); batch/plate metadata not |
| `Metal Resistant Genomes/genome_seq_data_8metals_strains.xlsx` | 17 metal-resistant strains: FastQ paths, TnSeq/BarSeq gDNA, plates | in document | strains and TnSeq fitness in CORAL (`feba_tnseq_fitness_*`); plate metadata not |
| `ENIGMA_Isolate_Sanger_16S_Traces/` (2,159 `.ab1`, `Missing Fasta.xlsx` 159 rows) | Sanger traces | files in folder | sequences in CORAL (`isolate_16S_sanger_260917`); traces not bricked; `Missing Fasta.xlsx` lists 159 isolates without a FASTA |
| 524 `.fna`, 261 `.gbk`, 261 `.sintax` | Genome assemblies and annotations (`Isolate Genome Sequences - obsolete, use kbase instead/`) | files in folder + linked (morgannprice.org strains page, KBase) | genomes in CORAL/KBase; folder marked obsolete |
| `ENIGMA Isolate Submission Checklist (Responses).xlsx` | Submission form responses (15) | in document + linked (Drive ×7) | not in CORAL (form log) |
| `README.txt.docx` | Pointer | linked (KBase `ws.41372.obj.1`) | n/a |

### ENIGMA Public Data

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `Public Isolate Data/isolate_table_public_export_230829.tsv`, `isolate_table_samples_public_export_231011.tsv` | Public isolate exports | in document | derived/export from CORAL |
| `Smith-2015-mBio/enigma_field_data_hazen_180417.tsv` | 100WS geochemistry | in document | in CORAL (100WS bricks) |

### ENIGMA_Imaging

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `Walian_EM_isolates.xlsx` (List_All 119×28, Ongoing, Experiments), `Walian_EM_isolates_JMC.xlsx` | EM morphology per isolate (shape, size, S-layer, flagella, …) with image links | in document + linked (Google Drive image files ×110) | partly in CORAL (`isolate_image_data_221011_v2`, 94 rows); 25 newer rows and the image files not |
| `Images_Subfolders_Intermediate spreadsheets/Isolate Atlas Listing*.xlsx` | Atlas listing (163 rows) | in document + linked (Google Sheet) | partly (same brick) |
| `Images_Groundwater/<category>/*.tif` (277) | EM images of groundwater cells/viruses by morphotype | files in folder | not in CORAL |

### PPI data

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `TAP/Supplemental Datasets S1-S2*.xlsx`, `final_list_of_interacting_pairs_tap.txt` | TAP protein-protein interaction strains (1,499) and MS data | in document + linked (MassIVE, PanoramaWeb, Matrix Science) | **not in CORAL (gap)** |
| `Tagless/Dataset S1 MS peptides.xlsx`, `final_list_of_interacting_pairs_tagless.txt` | Tagless PPI MS peptide dataset | in document | **not in CORAL (gap)** |

### ENIGMA Dashboard Source Files, 2018-10-07-Pilot Project Analysis- Arkin

| Document | Data type | Where the data live | CORAL status |
| --- | --- | --- | --- |
| `2022_12_08_df_asvRankMatrix.xlsx` (111,831 × 68) | ASV rank matrix with FAPROTAX traits, correlates, isolate matches | in document | derived from CORAL ASV bricks; not needed |
| `ESVMasterTable.tsv`, `ProcessMasterTable.tsv`, PCA pdfs | 2018 CORAL exports and PCA plots | in document | derived/export from CORAL |

---

## 5. Summary of gaps (candidates for CORAL import)

Ordered roughly by how self-contained the source tables are.

| # | Data | Source document(s) | Campaign in CORAL? |
| --- | --- | --- | --- |
| 1 | Spring 2019 lab geochemistry and biology: Adams ICP-MS, Chakraborty C/N, Elias ferrozine, Fields cell counts / activity / δ18O-δ2H, Hazen AODC, Stahl isotopes | `2019_Spring_Integrated Sampling/<Lab>/…` | yes (samples exist) |
| 2 | 2024 SSO Pump Test lab data: Adams metals, Chakraborty IC + TOC/TN, Stahl isotopes, Hazen AODC, manual DTW, April 2024 TROLL logs (27 files) | `2024_SSO_Pump Test/…` | yes (samples exist) |
| 3 | 2024 SSO Pilot Time Series lab data: Adams metals, Baliga NH4/NO2, Chakraborty IC | `2024_SSO_Pilot Time Series/…` | yes |
| 4 | 2023 SSO sediment: Adams ICP-MS metals; Northen LC-MS metabolomics (GNPS) | `2023_SSO_Drilling／Sediment Core/2023-Adams-…`, `2023-Northen-…` | yes (sediment samples exist) |
| 5 | 2023 SSO Initial Well Characterization: metadata, Adams metals, Hazen AODC | `2023_SSO_Initial Well Characterization/` | no samples found |
| 6 | 2024 manual DTW and 2024 colloidal borescope results | `2024_SSO/DTW_ManualMeasurements_SSO.xlsx`, `2024_SSO_Borescope Characterization/` | locations exist |
| 7 | 2026 bromide tracer breakthrough logs (26 csv) | `2026_SSO_Tracer Tests/` | locations exist |
| 8 | CPT physical data: Fugro probe profiles (50k rows), lithology, water levels, resistivity; CPT sediment AODC and water-extractable DOC | `2020_Cone Penetrometer Sampling/CPT Metadata FINAL/`, `…/AREA 3/`, `AODC 2020 CPT/`, `Chakraborty CPT DOC data/`, `Dataset_Revil_et_al./` | yes (CPT locations/samples) |
| 9 | 27-Well bug-trap 16S and Fields PBR 16S | `2019_Summer／Fall_27-Well Survey/Zhou - 16S sequencing Bug trap samples/`, `Fields - PBR/` | yes |
| 10 | 2017 EVO Injection 16S zOTUs (71 samples) | `2017 EVO Injection/Zhou - 16S sequencing/` | no |
| 11 | 2022 Discovery nitrifying-community reactor amplicons (16S, 18S, amoA) | `2022_Discovery_Nitrifying_Community/Sequencing_Results/` | no |
| 12 | One-off SSO 16S ASV sets (colloids, FTP6 AOA, FTP7 microcalorimetry) | `2023_2024_2025_One-Off Sampliing/2023-…`, `2024-FTP6-…`, `2024-FTP7-…` | yes (one-off samples exist) |
| 13 | RecycNec and SSOM6SED enrichment 16S; EnCom M6 metagenomes | `Enrichments/RecycNec/`, `Enrichments/SSOM6SED/`, `2025_EnCom_SSO_sediment_M6_pilot/` | partly (SSO communities exist) |
| 14 | Pilot core GeoChip and fungal ITS | `FRC_Microarray/…`, `FRC Sequence Data/Zhou Lab/Pilot.ITS…` | yes |
| 15 | PPI datasets (TAP, tagless) | `PPI data/` | strains exist |
| 16 | Sensor files missing from the troll series: `DP06_LT400_20190728_20191206.xlsx`, `EFPW01_08022022…`, `EFPW05_09292022…`, EFPW01 2022 HydroVu export; LevelTROLL downloads after 2026-05-04 | `FRC Well Metadata/Well monitoring…`, `Hazen SSO Continuous Monitoring/AQUATROLL DATA/Download Zips/` | yes |
| 17 | 2013–2015 FW305/FW306 core geochemistry | `FRC Well Metadata/Core samples/` | strains exist |
| 18 | Walian EM isolate list rows added after 2022 and the linked image files | `ENIGMA_Imaging/Walian_EM_isolates.xlsx` | yes |
| 19 | 2026 M5-VSZ bromide tracer injection: 12 probe logs (Apr 9 to May 11, 2026) and injection DTW metadata. **Only in the My Drive copy** | `My Drive …/2026_SSO_Tracer Tests/M5-VSZ Injection 20260410/` | locations exist |
| 20 | Five Plasmidsaurus long-read isolate sequencing runs (Oct 2026) added to the genome batch sheet; two strains (GW821-FHT14H06, EU05-FHT14E09) exist in CORAL, three (GW821-HT13G08, GW821-HT20B11, GW821-FHT1410) do not. **Newer version only in the My Drive copy** | `My Drive …/ENIGMA Isolate List and Sequences/GenomeBatches/GenomeSamples_metadata.xlsx` (2026-10-05) | partly |
| 21 | CPT flow-model inputs: `CPT_full_data_{Location,ProbeData,Sediment}.csv`, Revil resistivity profile interpolations, `Water Level Master 20201020_final4.xlsx` (same source data as item 8, in model-ready form). **Only in the My Drive copy** | `My Drive …/Cone Penetrometer Sampling 2020/Manuscript/Jupyter notebooks/source_overlapping/data_cpt/` | yes |

Not import candidates: planning documents (FTPs, meeting notes, manuscripts),
CORAL exports stored on Drive, raw sequence reads (fastq, ab1), PDFs of
radiological reports and field sheets, and derived analysis outputs
(iCAMP/NST, PCA, dashboards).

---

## 6. Second mirror: My Drive › `DataManagement_ENIGMA/ENIGMA Data`

Checked 2026-10-08:
`/mnt/net/dipa.jmcnet/data/backup/google-drive/my_drive/DataManagement_ENIGMA/ENIGMA Data`
(31,263 files). This is an older copy of the same campaign tree, kept in the
owner's My Drive, with some folders under their pre-migration names
(`27 Well Survey - Summer Fall 2019`, `Integrated Sampling - Spring 2019`,
`Pilot Sediment Campaign`, `Cone Penetrometer Sampling 2020`,
`2023_One-Off Sampliing`). It lacks the team-drive-only folders
`Enrichments`, `ENIGMA_Imaging`, `Hazen SSO Continuous Monitoring` and
`SSO Sample Requests`.

### Comparison method

Every file was matched to the team drive by relative path, then by
basename plus byte size anywhere in the team drive. Google-native documents
(Docs, Sheets, Slides) export with slightly different byte counts on each
mirror, so same-path files whose size differs by under 5 kB with the same
modification date were treated as identical (177 files). The remaining
differences were opened and compared sheet by sheet.

| Category | Files |
| --- | --- |
| Identical path and size | 22,490 |
| Same path, Google-export size drift only | 177 |
| Same path, different content | 10 (listed below) |
| Different path, identical basename and size (renamed folders) | 3,673 |
| **Not present anywhere in the team drive** | **4,913** (listed below) |

### Files that exist only in the My Drive copy — **copy these to the team drive**

| Location in My Drive copy | Contents | Data type | CORAL status |
| --- | --- | --- | --- |
| `2026_SSO_Tracer Tests/M5-VSZ Injection 20260410/` (13 files, 133 MB) | 12 TempHion bromide-probe csv logs (`L7-SZ1`, `L8-SZ1`, `L8-SZ2`, `L9-SZ1`, `L9-SZ2`, `M4-SZ1`, `M5-SZ1`, `M5-SZ2`, `M5-SZ3`, `M5-VSZ`, `M6-SZ1`, `M6-SZ2`, each ~278k records, 2026-04-09 to 2026-05-11) and `M5-VSZ_KBrInjection_20260410_Metadata.xlsx` (depth to water in M5-VSZ and M5-SZ3 every minute during the 0.5 L/min injection). Note: `M5-SZ2_20260511.csv` is byte-identical to `M5-SZ1_20260511.csv` (sensor name M5-SZ1 inside), so the M5-SZ2 log appears to be missing. | Tracer breakthrough time series; in document | **not in CORAL (gap 19)**. The team drive holds only the U2-SZ1 and M4-SZ1 injections. |
| `2026_Timeseries/Fall 2026 Gantt Chart.xlsx` (30 MB, 2026-10-07) | Fall 2026 time-series planning workbook: `Schedule` (Sept to Dec 2026 Gantt: AquaTROLL calibration, Picarro install, sampling timepoints), `Assays` (21 assays × timepoints × 18 wells: 16S and MAG 0.1/8 µm filters, pH, metals, …, responsible person, PI, shipments), `Sample Metadata` (template with one example row `20261006-U1-SZ1-Metals` and ~10,000 placeholder rows). | Campaign plan and sample-ID template; no measurements yet | n/a now; will become the sample metadata source for the Fall 2026 time series. Not in team drive. |
| `Cone Penetrometer Sampling 2020/Manuscript/Jupyter notebooks/source_overlapping/` (412 files) | `data_cpt/`: `CPT_full_data_Location.csv` (108 bores), `CPT_full_data_ProbeData.csv` (50,035 rows), `CPT_full_data_Sediment.csv` (32 samples with moisture and pH), four `Revil_Fig-9_P{1..4}_…kernel=30.tsv` resistivity interpolations, `Water Level Master 20201020_final4.xlsx`, `cpt_raw/` (daily Fugro exports); `data_rwpt/` (random-walk particle-tracking domain, velocity ensemble, 398 snapshot `.npy`); `8.rwpt_results_shekhar.ipynb`, `cpt_utils.py`. | Model-ready CPT tables (in document) plus model outputs | CPT tables: **not in CORAL (gap 8 / 21)**; RWPT outputs: derived |
| `Cone Penetrometer Sampling 2020/Manuscript/cpt paper data/` (new items: 4 notebooks, `MAD_cpt.py`, 2 `.dill` states, `sub_pflotran_initial/` with 300 PFLOTRAN run files and `sub_data/` 4,140 `.h5`, ~54 GB) | PFLOTRAN Richards-flow / nitrate-transport ensemble for Area 3 (`reference.in`, `run_N.in/.h5/.out`), tracer location outputs, MCMC/MAD calibration notebooks | Model inputs and outputs | derived; not a CORAL candidate, but only copy of the calibration ensemble |
| `Cone Penetrometer Sampling 2020/Manuscript/Conference abstracts/Abstract_AGU2026_{Bayesian,Connection}_Im et al.docx` | Two AGU 2026 abstracts (Bayesian CPT inversion; RWPT as a neutral model of microbial connectivity) | n/a | n/a |

### Same path, newer or different content in the My Drive copy

| File | Difference | CORAL status |
| --- | --- | --- |
| `ENIGMA Isolate List and Sequences/GenomeBatches/GenomeSamples_metadata.xlsx` (My Drive 2026-10-05 vs team 2025-12-11) | `Alternate_Sequencing` gains five Plasmidsaurus long-read runs (`GW821-HT13G08`, `GW821-HT20B11`, `GW821-FHT14H06`, `EU05-FHT14E09`, `GW821-FHT1410`; reads under `/usr2/people/kuehl/Plasmidsaurus/2026100…`); `information` gains three note rows. **Copy to team drive.** | Two of the five strains are CORAL strains; three are not; none of the five runs are in `isolate_sequence_and_quality_arkin_260921` (gap 20) |
| `2023_2024_2025_One-Off Sampliing/SSO_Metadata_One Off Sampling.xlsx` and `2023_One-Off Sampliing/…` (2026-02-16 vs team 2025-12-08) | Three added rows: `20260216-M5-SZ3-UF-Activity1`, `-Activity2`, `-Count`. | already in CORAL as samples (`20260216-M5-SZ3-UF-ACTIVITY1` …); team drive copy is stale |
| `2025_SSO_PumpTest2/Hazen - Field Data/TROLL Files - HydroVu/HydroVu_U2_2025-09-20_04-00-00_Export.xlsx` | Same header and rows; formatting only | in CORAL |
| `2023_SSO_Drilling／Sediment Core/SSO Sediment Mastersheet.xlsx`, `…/SSO.Sediment.16S.BarcodeMapping-MiSeq20230714.20230818.xlsx`, `2023_SSO_Initial Well Characterization/2023-Adams-Metals/…Metal-Data.xlsm`, `Cone Penetrometer Sampling 2020/CPT Metadata FINAL/CPT_full_data*.xlsx`, `MEETING NOTES 2021/CPT MEETING NOTES INDEX.xlsx` | Same sheets and non-empty row counts; size/mtime differ only | as in sections 1 and 2 |
| `FRC Well Metadata/All_Wells_ConstructionData_GoogleEarthTags.xlsx`, `ENIGMA Isolate List and Sequences/ENIGMA isolate data exported from CORAL*.xlsx`, `ENIGMA samples used for Isolation.xlsx`, `2019_Summer／Fall_27-Well Survey/Stahl - isotopes/Isotopes/README.txt` | **Team drive copy is newer** (2026-07 to 2026-09); My Drive copy is stale | in CORAL / exports |

Everything else in the My Drive copy is a byte-identical or export-drift
duplicate of the team drive.
