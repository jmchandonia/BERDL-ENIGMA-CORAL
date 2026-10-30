# Plan: remaining high-priority CORAL imports (well chemistry and ASV data)

Prepared 2026-10-09 after the 2024 SSO geochemistry package
(`coral_import/sso_geochemistry_20261009`) was loaded. The Lakehouse sync is
deferred until the packages below are in CORAL, so that one sync publishes the
whole batch. Every package follows the conventions established today: one
notebook-paste `import_to_coral.py`, static additions before bricks, bricks
before their processes, CheckGeneric on every JSON, and spot checks against
the source workbook recorded in `reports/`.

Status of the sources was verified against the 2026-10-09 CORAL export
(`sync-coral-to-berdl/exports/sync-20261009-134304`).

## Batch A: SSO groundwater chemistry, 2024 (samples already in CORAL)

### A1. Adams ICP-MS metals, 2024 pump test and 2024 pilot time series

| Item | Detail |
| --- | --- |
| Sources | `2024_SSO_Pump Test/Adams_Metals/2024-06-29_…Pump-Test_Metal-Data.xlsm` (17 samples); `2024_SSO_Pilot Time Series/Adams_Metals/2024-10-09_…Pilot-Time-Series_Metal-Data-Final.xlsm` (38 samples, Sept 9 and 18) |
| Sheets to use | `Sample - Blank (uM)` as the reported concentration; `SD (uM)`; `DL (uM)` as detection limit; `BEC (uM)` as background equivalent concentration. The ppb sheets are the same data in mass units and are not imported. |
| Sample mapping | Pump test: `Adams Sample ID` `L8-SZ1-Pre`/`-Post` and the M5-SZ3 `0L/100L/200L` series map to the existing `…METALS1`/`…METALS2` and `…20240329-METALS`/`METALS100`/`METALS200` samples (same PRE = morning rule verified for the IC samples). Time series: `Sample ID` `L7-SZ1-20240909-Metals` maps to `L7-SZ1-20240909-METALS`. |
| Brick model | Same as `adams_metals_27ws` (Brick0000080, `[sample, 52 element]`): dimensions environmental sample × `molecule` (molecule from list, CHEBI element terms as in Brick0000080); variables concentration (µM), standard deviation, detection limit, background equivalent concentration; array context instrument (Agilent 7900 ICP-MS, nebulizer, torch, cones from the Experiment Details sheet), method, personnel Paul Adams lab, run date, comment with the source file. Element-to-CHEBI mapping is copied from Brick0000080's typedef rows so the columns line up with the existing metals tables. |
| Processes | Assay Geochemistry, Adams lab person term, Subsurface Observatory, dated by the run date. |
| Effort | Medium: one generic parser for the Adams workbook layout serves all four metals workbooks. |

### A2. Baliga ammonia and nitrite, 2024 pilot time series

| Item | Detail |
| --- | --- |
| Source | `2024_SSO_Pilot Time Series/Baliga_Ammonia／Nitrite/202111_SSO samples.xlsx`, sheet `Raw data` (the `SSO samples` sheet lacks the location columns). |
| Content | Thermo Gallery discrete analyzer: ammonia (`Ammon H UW`, mg/L), nitrite (`Nitrite KC`), total oxidised nitrogen (`TON L_Wei`), phosphate on a few samples; lab codes `KH1` to `KH38` plus `U1SZ1`/`U1SZ2`, each with Location, Depth zone, Sample date and dilution in the `Raw data` sheet; replicate rows per sample. |
| Sample mapping | `Location` + `Depth` + `Sample date` → `…-NH3NO2` samples (Sept 9, Sept 18 and Oct 14, 2024 all exist in CORAL). |
| Brick model | environmental sample × technical replicate; variables concentration with molecule from list = ammonia/ammonium, nitrite, nitrate+nitrite (TON) and phosphate, mg/L; dilution recorded as a comment; standards and calibrators excluded. |
| Open point | Confirm with the Baliga lab which unit the `U/l` rows carry (the kit output unit) before deciding whether TON and nitrite rows are imported as mg/L. |

### A3. Hazen AODC, 2024 pump test

| Item | Detail |
| --- | --- |
| Source | `2024_SSO_Pump Test/Hazen_AODC/AODC_pump test _UTK .xlsx` (17 samples: PRE/POST per port plus M5-SZ3 0/100/200 L). |
| Brick model | Two bricks as for the core pilot: processed (cells per mL, CV %, mean cells per field) with sample dimension, and raw counts `[sample, field 1..10]`; array context microscope ID, objective, filter type, counting person (from the sheet header). |
| Sample mapping | `U2-SZ1 PRE` → `U2-SZ1-20240313-AODC1`, `POST` → `AODC2`, `M5-SZ3 0L/100L/200L` → `M5-SZ3-20240329-AODC`/`AODC100`/`AODC200`. |

## Batch B: SSO 2023 data (needs new static objects)

### B1. 2023 initial well characterization (28 ports, June to August 2023)

| Item | Detail |
| --- | --- |
| Sources | `2023_SSO_Initial Well Characterization/SSO_Initial Well Characterization metadata.xlsx` (field pH, RDO, conductivity, temperature, ORP at pump start and end, pump volumes), `2023-Adams-Metals/…Initial-GW_Metal-Data.xlsm` (28 samples `SSO-1` to `SSO-28`), `2023-Hazen-AODC/2023-Hazen-AODC_SSO_IWC .xlsx` (two counting replicates per port). |
| Static additions | CORAL has no samples between 2023-04 and 2023-08. Add 56 Sample rows (`<WELL>-<ZONE>-<YYYYMMDD>-METALS` and `-AODC` bottle samples (sonde readings keyed by well Location), location `SSO-<well>`, zone depth from the SSO screen table, date and pump start time from the metadata sheet) with one Sampling process per port (Hazen Lab, Subsurface Observatory). Material ground water, env package water. |
| Bricks | Field measurements brick `[sample]` (start and end pH, RDO mg/L and % saturation, specific conductance, temperature, ORP, volume pumped); Adams metals brick as in A1; AODC processed and raw bricks as in A3. |
| Effort | Medium-high because of the sample additions; worth doing together with A1 since the metals parser is shared. |

### B2. 2023 SSO sediment: Adams metals and Northen metabolomics

| Item | Detail |
| --- | --- |
| Metals source | `2023_SSO_Drilling／Sediment Core/2023-Adams-Metals-sediment/…Sediment_Metal-Data.xlsm`: 37 sediment digests, samples `SSO-U1-C3` etc. (all 37 exist as CORAL samples); results in µM of digest and mg per kg dry sediment after the `Well Info` dilution factors. |
| Metals brick | Same model as A1 with units mg/kg (as the core pilot metals bricks); keep the digest µM as a second variable. |
| Metabolomics source | `2023-Northen-Metabolomics-sediment/` GNPS feature tables (two runs, C18 and HILIC): `featuretable_reformated.csv` (feature × sample intensities) and `merged_results_with_gnps.tsv` (annotations). |
| Metabolomics bricks | Feature table brick `[feature, sample]` with intensity, plus a feature annotation brick (m/z, retention time, GNPS compound name, library match score), modeled on `northen_corepilot_raw_metabolomics` (Brick0000068). Sample columns map to `SSO-<well>-C<n>` samples through the `merged_metadata.tsv` filenames. |
| Open point | The GNPS sample filenames must be mapped to CORAL sediment samples by hand once (about 40 names); ask the Northen lab if any are ambiguous. |

## Batch C: Spring 2019 lab data (samples exist, nine wells, biweekly March to June 2019)

CORAL already holds one Sample per lab bottle, named `<well>-<date>-<fraction>-R<n>` with
the recipient encoded in `R<n>`: R91, R92, R93 Adams metals; R3 (unfiltered) and
R13 (0.2 µm) Chakraborty; R5 Elias; R6 and R14 Hazen; R1, R7, R8 Fields; R21 to
R24 and R151 to R153 Stahl. Every brick below maps rows by well, date and the
recipient's R-code.

| Package | Source | Brick model | Notes |
| --- | --- | --- | --- |
| C1 Adams metals | `Adams Lab/2019_Groundwater_Time_Series_2HNO3_52_Final.xlsm` (`Sample List`, `Combined Conc (uM)`, `Combined SD (uM)`, `Combined DL Conc (uM)`, `Combined BEC Conc (uM)`) | as A1; `ORR Sample ID` `FW100-20_032019` → `FW100-20-2019-03-20-UF-R91` | 1,000-row sheet, 52 elements; samples R91/R92/R93 are three bottles, the workbook reports one combined result per sampling, so map to R91 and note R92/R93 in the comment |
| C2 Chakraborty C/N | `Chakraborty Lab/C & N analysis_20190801.xlsx`, `Results_Area3.xlsx` | as `chakraborty_c_n_27ws`: TN, NO3-N, NO2-N, NH4-N, DON, TC, DOC, DIC (ppm) | map to R3 (unfiltered) samples |
| C3 Elias ferrozine | `Elias Lab/Ferrozine-ENIGMA-2019.xlsx` (`All-05212019`, `Summary`) | `[sample]`: Fe(II), Fe(III), total Fe (mg/L) with method text | sample codes need the well/date decoding from the `Summary` sheet; map to R5 |
| C4 Fields counts, activity, water isotopes | `Fields Lab/2019SpringSampling_CellCounts_FieldsLab.xlsx`, `…_activity_FieldsLab.xlsx`, `…_18O_2H.xlsx` | three bricks: cell counts (cells/mL, SD), activity (ng C per mL per day; per-cell variant as a second variable), water δ18O and δ2H (per mil, with SD) | map to R1 (counts), R7/R8 (activity, isotopes) after confirming which R-code each Fields assay used (the master sheet only says "Fields") |
| C5 Hazen AODC | `Hazen Lab/AODC/AODC_Active Sampling 2019_final timepoint.xlsx` | processed and raw bricks as A3 | map to R6 |
| C6 Stahl ammonia-oxidation isotopes | `Stahl Lab/190618_StableIsotopes_AO_FvN.xlsx` (`Processed`) | `[sample, replicate]`: N concentration (mmol/L), δ18O, δ15N (per mil) with the assay description as method | identifiers `GW821_040119_2` → well, date, bottle; map to R21 to R24 |
| C7 Field readings | `Hazen Lab/Field Sheets/2019 Spring Master Spreadsheet-Metadata.xlsx` (DO, ORP, conductivity, temperature, pH per sampling) | one Environmental Measurement brick `[sampling event]` keyed on the R1 sample of each well-date | only if these are not already in CORAL sample metadata (they are not in a brick today) |

Suggested order inside C: C1 and C2 first (largest analytical value, same
layouts as existing bricks), then C5, C4, C3, C6, C7.

## Batch D: additional ASV data

All Zhou-lab sets use the layout already imported for the SSO pump test and
time series: ASV table, classification table and representative sequences,
yielding three bricks per dataset (`…_ASV_count` `[ASV, community]`,
`…_ASV_taxonomy` `[ASV, rank]`, `…_ASV_16S` `[ASV]`), with communities as the
column dimension (`Community ID <ME:0000233>`). Arkin-lab sets use the demulti
layout imported for 3x5, ORRENR, SSOECT, SSOISO and SSOSTOR.

| Package | Source | Communities | New static objects |
| --- | --- | --- | --- |
| D1 One-off colloids (Murtazina/Hazen/Zhou, 2024-05-29) | `2023_2024_2025_One-Off Sampliing/2023-Murtazina-Hazen-Zhou_ colloids/SSO.OneOff.DM.V240916ASV/` (Clean, Raw, Resamp tables; 8 filter samples: EFP01, L8-SZ2, M5-SZ2, U2-SZ2 × F01/F8) | none exist | 8 Sample rows (`20240529-<port>-F01/F8`; the unfiltered parents `20240529-M5-SZ2` etc. exist) plus 8 Community rows, Sampling and Filter processes |
| D2 One-off FTP6 upper-well AOA (Arkin/Zhou, 2024-08-12) | `2024-FTP6-Arkin_Zhou-UpperWellAOA/CleanData/` (16 samples, `U1SZ1.20240812.F8` style IDs with metadata-table names `20240812-U1-SZ1-F8`) | none exist | 16 Sample and Community rows, processes |
| D3 One-off FTP7 microcalorimetry (Shreve/Fields/Zhou) | `2024-FTP7-Shreve-Field_Zhou-Microcalorimetry/CleanData/` (7 samples) | none exist | 7 Sample and Community rows, processes |
| D4 RecycNec enrichments (Chakraborty, Dec 2025) | `Enrichments/RecycNec/` (`metadata.xlsx` 195 samples, `Bri_1-2.tax.tsv`, wide table) | enrichment communities; parent sample `20251210_L7-SZ2_Isolations` must be checked in CORAL | Community rows from the metadata sheet (as SSOSTOR), Enrichment processes |
| D5 SSOM6SED sediment enrichments (Cooper/Baliga/Chakraborty) | `Enrichments/SSOM6SED/SSOM6SED_metadata.xlsx` (289 rows) plus reads; the ASV tables must be located or generated with demulti | enrichment communities from SSO M6 sediment | Community rows, Enrichment processes; blocked until a count table exists |
| D6 27-well bug traps (Zhou, 2019) | `2019_Summer／Fall_27-Well Survey/Zhou - 16S sequencing Bug trap samples/` (284 samples; `27wellBugtrap_metadata_Zhoulab.xlsx` maps Zhou IDs to ENIGMA and Hazen IDs) | bug-trap communities do not exist | Sample and Community rows for the bug traps (well, deployment and retrieval dates from the 27-well field log), Sampling processes |
| D7 Fields PBR reactor 16S (2022) | `Fields - PBR/` | reactor communities | Community rows (reactor, timepoint); lower priority |
| D8 2017 EVO injection (Zhou) | `2017 EVO Injection/Zhou - 16S sequencing/V230222.zOTU/` (71 samples, 2014 to 2020) | none; no campaign in CORAL | new Campaign term, Location check, Sample and Community rows; do last |
| D9 2022 nitrifying reactor study (Zhou) | `2022_Discovery_Nitrifying_Community/Sequencing_Results/` (16S, 18S, amoA) | none | new campaign, reactor samples; do last |

Suggested order inside D: D1 to D3 (small, same Zhou layout, samples
collected under existing SSO one-off processes), then D4, D6, D5, D7, D8, D9.

## Execution order and sync points

1. Batch A (A1, A3, then A2 after the unit question) and B1 together: one
   package, because the Adams parser is shared and B1 adds the only new
   samples. Estimated two working sessions.
2. Batch C1, C2, C5 as a second package; the remaining C items as a third.
3. Batch D1 to D3 as one package (shared Zhou-layout builder), then D4 and D6.
4. B2 (sediment metals and metabolomics) once the Northen sample-name
   mapping is confirmed.

Run the Lakehouse sync after step 1 and again after step 3; later steps can
ride on monthly syncs. Each sync re-exports the static tables, so the new
Sample and Community rows are published with their bricks.

## Information to request from the labs

- Baliga lab: unit of the `U/l` rows (nitrite and TON) in the Gallery export.
- Fields lab: which Spring 2019 R-code (R1, R7, R8) belongs to counts, activity and water isotopes.
- Northen lab: GNPS sample filename to core-sample mapping for the two 2023 sediment runs.
- Hazen lab: whether the 2023 initial well characterization port depths should be the screen midpoints used for the 2024 samples.

## Status 2026-10-09: batches A and B packaged

`coral_import/sso_batch_ab_20261009/` (built by
`tools/build_sso_batch_ab_coral_import.py`) holds A1, A2, A3, B1 and B2: 14
bricks, 28 IWC Sample rows with Sampling processes, and five assay process
files, all passing CheckGeneric and spot-checked against the workbooks.
Awaiting owner import into CORAL, then the Lakehouse sync.

## Status 2026-10-16: batch A/B loaded and synced; batch C1 packaged

Batch A/B is in CORAL (56 IWC bottle samples, 14 bricks). The Spring 2019
package for C1, C2 and C5 is `coral_import/spring2019_batch_c1_20261016/`
(built by `tools/build_spring2019_batch_c1_coral_import.py`): Adams metals
[45 x 52] on the R92 bottles, Chakraborty carbon and nitrogen [45] on the
assay-13 VOA bottles (R13; R131 in round 5, not R3 as planned: the shipping
legend shows R3 is a 2 mL dry-ice cryovial and R13 the 0.2 um filtered VOA),
and Hazen AODC processed and raw [45] on R6, plus one missing Adams bottle
sample `MLSB5-2019-04-30-UF-R92`. Next: C3, C4, C6, C7.

## Status 2026-10-19: C1 and nitrate bricks loaded and synced; C3, C4, C6, C7 packaged

The C1 package (14 bricks, including ten `_v2` supersessions) and the 154
corrected Aqua TROLL nitrate bricks are in CORAL and in `enigma.coral` (sync
`sync-20261019-161321`: 175 tables loaded, 164 obsolete brick tables dropped,
row counts, comments, quoting and 268 foreign-key checks passed). The last
Spring 2019 items are packaged in `coral_import/spring2019_batch_c2_20261019/`
(built by `tools/build_spring2019_batch_c2_coral_import.py`): Elias ferrozine
iron [44] on R5, Fields SYBR Gold counts [64] on R7 (field-fixed) and R1
(lab-fixed), Fields 3H-leucine biomass production [46] on R1, Fields water
delta 18O/2H [46] on R8, Stahl ammonia oxidation and natural-abundance
isotopes [14] on R21-R24/R151-R153, and Hazen field readings [33 well visits]
keyed by Location. Four 2019-03-11 pre-campaign Fields bottles are added
(`GW821E/GW822E-2019-03-11-UF-R1/R8`). The package needs ontology update
`coral_import/ontology_update_20261019` (ME:0000513 nanogram per milliliter
per day, ME:0000514 biomass production rate, ME:0000515 time since sample
collection) installed first. It also supersedes the 2023 SSO sonde brick with a
`_v2` (dissolved state on DO, depth reference points). Next: batch D.

## Addendum 2026-10-09: loading decisions settled from the source files

The provenance review recorded in `LAB_QUESTIONS_20261009.md` section 3
fixes these choices for the batches above:

- A1 Adams 2024 metals: load `Sample - Blank (uM)` with SD and DL as slices;
  zeros stay 0 (template auto-zeroes negatives); join the `-Final`
  time-series workbook to samples by tube number (HNO3-3000..3037); Fe in the
  time series is semi-quantitative (1.2x only). IWC metals: either workbook
  version is identical; record the unacidified-at-receipt caveat.
- A2 Baliga NH3/NO2: units µg N/L (`U/l`) and mg N/L; report `Ammon H UW`
  undiluted rows (or the 1+4 re-run where over range), never the 1+9 rows;
  one sample per KH code, all 57 already CORAL samples.
- A3 Hazen AODC 2024: labels map directly to AODC1/AODC2 and
  AODC/AODC100/AODC200; dates from the metadata workbook.
- B1 IWC 2023: register `<WELL>-<ZONE>-<YYYYMMDD>-METALS` and `-AODC` bottle samples (sonde readings keyed by well Location) (56 samples, one Sampling process per port) with Pump
  End as the sampling time (crosswalk in the questions file); AODC first row
  per port only.
- C Spring 2019: Fields R1 = leucine activity (ng C/mL/day), R7 = SYBR Gold
  counts (cells/mL, field-fixed rows), R8 = δ18O/δ2H; the 2019-03-11 GW821 and
  GW822 pre-campaign samples need new Sample objects; Adams values link to the
  R92 (HNO3) bottle; Stahl identifiers decode to R21-R24 and R151-R153; field
  DO/ORP/cond/temp/pH load once per well and date (conductivity µS/cm).
- D ASV sets: load the resampled tables (as the existing bricks do), add the
  28 one-off filter samples with date-first names; colloid set has no fasta
  (asked); SSOM6SED is metagenome bins, not amplicons.
- Northen sediment metabolomics: four feature tables (C18 and HILIC, pos and
  neg), peak area, `tr1/tr2` as a replicate dimension, GNPS M4 and L9 map to
  `SSO-M4A` and `SSO-L9B`.

## Status 2026-10-20: batch C2 synced; SSO hydrology packaged

Batch C2 is in CORAL and `enigma.coral` (sync `sync-20261020-124617`). The SSO
hydrology package `coral_import/sso_hydrology_20261020/` holds the 2024 manual
depth-to-water surveys, the March 2024 pump-test manual depth to water and the
35 bromide-probe logs of the three 2026 tracer tests. The raw April 2024
pump-test TROLL logs are held back (the readme says not to use them raw).

## Status 2026-10-27: D1-D3 loaded and synced; Zhou 16S protocols corrected

The one-off 16S package `coral_import/sso_oneoff_16s_20261020/` (D1-D3: 9 bricks,
Brick0002130-0002138, 24 samples and communities) is in CORAL. The Zhou Lab
pump-test and sediment Classify OTUs processes now cite protocols matching
their ReadMes, and the 2024 pilot time series has its sequencing and
classification processes (`coral_import/zhou_16s_protocol_fix_20261027/`).
Both are in `enigma.coral` (sync `sync-20261027-134534`). Next: D4, then D6.

## Status 2026-10-29: D6 and D7 loaded (with the Adams bug-trap metals)

`coral_import/27ws_bug_traps_20261027/` (built by `tools/build_27ws_bug_trap_coral_import.py`) is in
CORAL as Brick0002139-0002145: bug-trap 16S sequences, counts and taxonomy, Adams bug-trap metals,
and the Fields packed-bed reactor 16S sequences, counts and taxonomy. COMO gained `time elapsed` as a
dimension variable and the new term `baseline control` (ME:0000516) for it. D4 waits on Mingfei Chen;
the bug-trap starting sediment's FRC source is a question for Katie Walker. Lakehouse sync pending.
