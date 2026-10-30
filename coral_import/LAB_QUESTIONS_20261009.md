# Lab questions for the pending CORAL imports (revised 2026-10-09)

The first draft of this file listed 35 questions. Re-examining the workbooks
(hidden sheets, formulas, calibration blocks, scanned field sheets, shipping
records, READMEs and FTP documents) answered all but a handful. Section 1 is
what still has to be asked, section 2 lists errors worth reporting to the
uploaders (no reply needed), and section 3 records how each former question
was resolved, with the evidence, so the import packages can cite it.

## 1. Questions that cannot be answered from the files

### Chakraborty lab: Mingfei Chen (mingfeichen@lbl.gov); was addressed to Bri Finley, who has left (resent in RECYCNEC_EMAIL_DRAFT_20261027.md)

**`20241220_IC_results_SSO_timeseries.xlsx`** https://drive.google.com/file/d/1QcKS8yYId740wf3LHO7J0fsEnyty_0Yh/view

1. The pilot time-series metadata registers 19 `…-ICTOC` bottles for each of
   2024-09-09, 2024-09-18 and 2024-10-14, but the IC workbook holds only the
   first two dates and no TOC/TN at all. Were the 2024-10-14 IC samples and
   the time-series TOC/TN run? If so, where are the results?
2. For L8-SZ1 and L8-SZ2 the `sampling_period` label and `Date Sampled`
   disagree in opposite directions (T1 rows dated 09-18, T2 rows dated 09-09).
   The other four date conflicts are provably typos (they would give one port
   two samples on one day), but for L8 nothing in the file shows which column
   is right. We loaded by the T1/T2 label. Is that correct for L8?

### Daliang Ning (dning@lbl.gov), Zhou lab

**`ReadMe_SSO.OneOff.DM_16S_20240916.docx`** (colloid one-off set) https://drive.google.com/file/d/1-_OE4RZJDK-vq9_bm7aiNcT-vLUshYD3/view (folder `2023-Murtazina-Hazen-Zhou_ colloids/`)

3. *Withdrawn 2026-10-20, do not send:* the resampled fasta is in the folder
   (`SSO.OneOff.DM.V240916ASV/ResampData/SSO.DM.16S.Resamp.Seq.fasta`, dated
   2024-10-08); only `Tree.nwk` is absent, and CORAL does not load trees.

### Optional confirmations (low stakes; load proceeds without them)

4. Suzanne Kosina: in the GNPS feature tables every sediment sample appears
   as `…_tr1` and `…_tr2`. We treat these as two technical (extraction or
   injection) replicates of the same core segment.
5. Kristopher Hunt: the Summary sheet note says vials 11145 and 11147 were
   both labelled `U2 SZ2 PRE` and each was diluted two ways. We loaded the
   Summary sheet's own assignment of those N numbers to U2-SZ1-PRE and
   U2-SZ2-PRE, with a comment on the brick.

## 2. Errors to report to the uploaders (no answer needed)

- `2024_Pump Test_ Metadata.xlsx` row 120: the 15:02 sample is
  `M5-SZ3-20240329-ISOTOPES200`, not `ISOTOPES100` (loaded as 200; the
  METALS/AODC/ICTOC rows at 15:02-15:03 and the three Stahl N numbers
  11139/11140/11141 for 0/100/200 L confirm it).
- `20240416_TOC_TN_SSO_pumptest_corrected.xlsx`: `M5_SZ3_POST` replicates 2
  and 3 (TOC 1.531429/2.822857, TN 12.022857/12.942857) and the replicate-1 TN
  (11.834286) are copies of the `M5_SZ3_0L` rows; the IC values for the two
  samples differ, so this is a paste error. Loaded as null with a comment.
- `2019 Spring Master Spreadsheet-Metadata.xlsx` (2025 edit of the 2020
  master): 34 FW101-20/FW102-20 rows collected 2019-03-20 carry IDs dated
  `2019-03-18`; the 2019-04-02 MLSB5 row repeats the 03-19 ID
  `MLSB5-2019-03-19-F01-R161-168`; recipient `Northern`; junk Time cells.
  The 2020 master and the scanned field sheets are right.
- `2019SpringSampling_activity_FieldsLab.xlsx`, `Per Cell - Area 2` D22/D29:
  the MLSB 04-02 cell counts are MLSF's values (32.4e6 / 3.88e6 instead of
  12.80e6 ± 0.85e6), so D37/D43 are wrong; `Per Cell - Background` E30 holds
  the count instead of its standard deviation.
- `2019SpringSampling_18O_2H.xlsx`: five rows have analysis date 2018-03-21
  (2019 intended); the δ18O "std dev" of the 2019-06-03 batch is -0.1 × δ
  (negative), unlike the 0.10-0.12 ‰ of the other batches.
- `AODC_pump test _UTK .xlsx`: the Date-Time column (C13:C30) is empty; times
  were taken from the metadata workbook.
- `2024-10-09_…Pilot-Time-Series_Metal-Data-Final.xlsm`: `Sample Name` reads
  `HN03-3000…` (zero for O) and the Sample Info sheet is re-sorted, so the
  data rows must be joined by tube number, not by row position.

## 3. Former questions and how they were resolved

### Baliga lab, `202111_SSO samples.xlsx` (Katie Walker)

- **`U/l` = µg N/L; `mg/l` = mg N/L.** The `SSO samples` sheet converts
  `U/l` results with `/14` and `mg/l` results with `/0.014` into columns
  headed `micromolar` (AA12:AG68). Check standards named in N units read back
  at face value: `1000ugNNO2` gives Nitrite KC 995.65, `7.78Nnh3` gives
  NH4 L Tri 7777.7 U/l and Ammon H UW 8.67-10.06 mg/l.
- **Reportable ammonia = `Ammon H UW`.** The lab's `Ammonium mean/std`
  columns average only Ammon H UW (range 0.04-2 mg N/L, calibrated
  2024-10-07). `NH4 L Tri` (0-200 µg N/L, calibration dated 2021-03-09) went
  over range (error 19, status AR) for 8 samples and is negative for many
  low samples.
- **Dilution is already applied by the instrument.** `Dilution+1` equals the
  Gallery `Dilution 1 +` field on all 353 rows and diluted standards read
  nominal. But the 1+9 rows carry a 10×-amplified blank offset (Ammon H UW
  about +0.08-0.10 mg/L on every sample; NH4 L Tri -80 to -120 U/l; Nitrite
  KC mostly error 30 below range). Load the undiluted rows, or the 1+4 re-run
  where the undiluted row was over range; do not average the 1+9 rows as the
  lab's `Ammonium mean` does.
- **One field sample per KH code.** 57 codes = 19 ports × 3 dates (KH1-19 on
  2024-09-09, KH20-38 on 09-18, port-named codes on 10-14); the extra rows per
  code are the instrument's auto-dilution series, not replicates. The
  metadata registers exactly one 20 mL `…-NH3NO2` bottle per port and date,
  and all 57 are already CORAL samples (for example `U1-SZ1-20240909-NH3NO2`).
- **Method text** for the Protocol: "measured for ammonia and nitrite with a
  spectrophotometer (Thermo Fisher Gallery) … kits Ammonia R1, R2 and TON R1
  and R2" (`Method` sheet).

### Hazen field readings, `2019 Spring Master Spreadsheet-Metadata.xlsx`

- **One reading per well and date.** Across 45 well × date groups (757
  bottle rows) the DO/ORP/conductivity/temperature/pH values never differ
  within a group. Nine round-5 groups (2019-05-01 FW100/101/102-20, 05-13
  GW821E/822E/823D, 05-14 MLSB5/D5/F5) have no values ("Technical issues in
  field"). The value is the last pre-sampling stabilization reading (the
  10:01 row of `GW-821-E_031819_Sonde_Stablization.pdf` matches).
  Conductivity is µS/cm despite the mS/cm header (23.9-672 is only plausible
  in µS/cm, and the sampling-sheet template says µS/cm).

### Fields lab, 2019 workbooks (Katherine Davis)

- **R1 = activity, R7 = cell counts, R8 = water isotopes.** The scanned
  field sheet `GW-821-E_031819_Sampling_Sheet.pdf` ("Integrated Sampling
  Plan" table) and `Hazen Lab/samples shipped.xlsx` rows 4/13/14: assay 1 =
  1 L sterile glass, unfiltered (BONCAT planned, realised as 3H-leucine
  activity); assay 7 = 10 mL pipetted from the 1 L bottle, formaldehyde
  (SYBR Gold counts); assay 8 = amber glass, 0.2 µm filtered, no headspace
  (EEMs/δ18O). Registry volumes agree (1000/10/120 mL).
- **2019-03-11 was a pre-campaign shakedown**, GW821 and GW822 only (no
  GW823), with activity started 48 h after collection
  (`Spring2019_FieldSampling_DataCompilation.xlsx` Measurement!F60; the
  Fields slide deck; a 3-13-19 rad-screening request for nine 1 L samples).
  It is absent from both master spreadsheets, the Hazen sheets and CORAL, so
  it needs its own Sample objects (or exclusion) and must not be merged
  with 03-18.
- **Activity units ng C mL⁻¹ day⁻¹** (sheet headers); **Per Cell = Per mL ÷
  field-fixed count** (formula `=D4/D20`, standard deviation by error
  propagation), verified on all 48 cells. The `-48hr` rows on 04-01 and
  04-02 are re-measurements of the same sample at 48 h (1.74× and 1.79×),
  a method test, not time points.
- **Count IDs:** `<well> <date>-Sample & Fixed` = fixed in the field (R7);
  `<well> <date>-Sample <date+1>-Fixed` = fixed in the lab a day later when
  the activity assay started (only rounds 04-29/05-01, 05-13/15 and 03-11).
  Only field-fixed counts feed Per Cell and the compilation. `Count total`
  is cells per mL (same numbers headed "cell/mL" in the activity workbook
  and on the slide axis). The raw fields-counted formula is not in Drive but
  is not needed to load cells/mL.
- FW102 2019-03-20 has registered bottles but no Fields data ("FW102 not
  shipped").

### Chakraborty lab (Bri Finley)

- **Nitrate is mg/L as NO3⁻.** The Stahl workbook's Summary sheet divides
  `Nitrate_ppm` by 62 (`=AVERAGE(IC_data!N2,N19,N36)/62`), chloride by
  35.453, sulfate by 96.06, and TN by 14; its IC_data sheet is a
  value-identical copy of the Chakraborty workbook.
- **Date conflicts:** every saturated-zone port, including L8, was sampled
  on both 2024-09-09 and 09-18 (metadata lists 19 ICTOC bottles per date;
  Adams tube numbers HNO3-3000..3018 on 09-09 and 3019..3037 on 09-18). The
  `Date Sampled` column gives L9-SZ1 two 09-18 samples and U2-SZ1 two 09-09
  samples, which is impossible, so the T1/T2 labels were used; the run
  `ORDER` column is randomized and does not help with L8 (question 2 above).
- **Chloride 0 = no integrated peak.** No standards or peak areas are in the
  workbooks; the smallest non-zero diluted reading is 0.0005, so exact zeros
  are Chromeleon "n.a." values. Replicate scatter puts the practical floor
  near 0.05 in the diluted sample, about 2-3 mg/L after the 1:50 dilution,
  for chloride and nitrate; sulfate is never near it. Loaded as null with a
  below-detection-limit flag.
- **TOC zeros are instrument readings of 0.000.** The "corrected" file and
  the Stahl copy agree on all 51 rows; all non-zero values are multiples of
  0.001 × 40/7 (7 mL in 40 mL, per the ReadMe), so zeros are analyzer zeros.
  No calibration range exists, so no detection limit can be derived; values
  below about 0.5 mg/L are not quantitative. Loaded as null with a flag.
- Pump-test IC technical replicate 1 came from a different run or
  calibration than replicates 2-3 (U2_SZ2_PRE nitrate 666.8 vs 431.1/451.9
  ppm); recorded as a brick comment.

### Hazen lab (Dominique Joyner)

- **ISOTOPES100 at 15:02 is the 200 L sample** (see section 2).
- **`…1` and `…2` samples:** the 2024 FTP (section 5.3, Table 3) defines
  the first set as "after 3 L purge and before in-line filtration" and the
  second as "after filtration, using the 25th L"; metadata times are 3-4 h
  apart. Adams, Chakraborty, Stahl and the AODC workbook call them PRE and
  POST. They are start-of-pumping and end-of-pumping samples, not samples
  before and after a separate pump test.
- **2023 IWC crosswalk:** Adams `Sample Info` A4:F31 follows the metadata
  sheet row order, Adams lab ID = `<port> SSO-n`:
  SSO-1..3 L7 SZ2/SZ1/VSZ 2023-06-26; 4..6 L8 06-27; 7..9 L9 06-28; 10..12
  M4 06-29; 13..15 M5 SZ3/SZ2/SZ1 07-11; 16 M5-VSZ 08-09; 17..18 M6 SZ2/SZ1
  07-13; 19 M6-VSZ 08-09; 20..21 U1 SZ2/SZ1 07-03; 22 U1-VSZ 07-11; 23..24 U2
  SZ2/SZ1 07-05; 25 U2-VSZ 07-11; 26..28 U3 SZ2/SZ1/VSZ 07-11. No separate
  sample-time column exists; the AODC Date-Time equals Pump End for 23 of 28
  ports (Pump Start for M4-SZ2, M5-SZ3, M5-SZ1, U2-VSZ, U3-VSZ), so Pump End
  is the sampling time. CORAL has no 2023 groundwater samples; the import
  will register them as `<WELL>-<ZONE>-<YYYYMMDD>-METALS` and `-AODC` bottle samples (56 in all; the sonde readings are keyed by well Location). The metals were
  received unacidified and run after three months at 4 °C (Experiment
  Details A26), to be recorded as a caveat.
- **The 2026-03-27 IWC metals workbook is a Google re-save:** all 16
  sheets, all values and the VBA project are identical to the 2024-07-20
  file; only Excel metadata, printer settings and chart XML differ.
- **AODC second rows are empty templates:** the tally strings in T:AC are
  blank, so the field-count formulas return `#DIV/0!`. Only U1-VSZ row 14
  has a hand-typed partial second count. Load the first row per port
  (cells/mL = mean per field × 11,815 fields ÷ 1 mL) plus the blank
  (42,533 cells/mL).
- **AODC pump-test labels** map one-to-one to the metadata AODC1/AODC2 and
  AODC/AODC100/AODC200 rows (rows are ordered 0L, 200L, 100L); the workbook
  has no dates, so dates come from the metadata.
- **The `-Final` time-series metals workbook supersedes** the October 2024
  draft: "10/9/2024 (Updated 09/17/2025)", Na/Mg/Al/K/Ca/Mn/Sr/U re-run at
  600× (values and DLs change for all 38 samples), 74→52 element columns,
  "DRAFT" removed. Fe was not re-run and remains semi-quantitative at 1.2×.
  The copy under `2024_SSO_Pump Test/Adams_Metals/` is the same Final file.
- **Sediment metals:** every data sheet is mg/kg dry weight; reportable is
  `Sample - Blank (mg per Kg)`; dry mass (col A `Dry Weight (g)`), digest
  volume (col B `Resusp. Vol. (L)`, 0.01 L) and MH dilution (col D) are in
  the data sheets themselves, not in Well Info. DL/BEC use a nominal 0.5 g.

### Adams lab (Farris Poole)

- **2019 time series: one bottle per sampling, the HNO3 bottle R92.** The
  legend is `Hazen Lab/samples shipped.xlsx` A15:E17 (9.1 = 50 mL in-field
  incubation, 9.2 = 10 mL HNO3, 9.3 = 10 mL HCl). Every Combined sheet has
  45 rows, all `_9.2`, one UGA tube each. "Combined" merges the 1.2× and
  100× dilutions per element (Readme.txt and the `Combined Dilution` sheet).
- **`Combined Conc (uM)` is reportable**; `Combined DL Conc` = instrument DL
  × dilution and `Combined BEC Conc` = background-equivalent concentration ×
  dilution (verified numerically: Na 2278.33 ppb / 22.99 = 99.06 µM; DL
  0.2116 × 100 = 21.16).
- **2024 workbooks: `Sample - Blank (uM)` is reportable** (Experiment
  Details A84 in all four files). The template auto-zeroes negatives, so
  zeros mean below DL or blank-dominated; there are no negatives. The sheet
  title says "(ppb)" but values are µM. Earlier CORAL Adams bricks kept
  zeros as 0.0; the new bricks will store value, SD and DL as slices and
  keep zeros, with the DL available for flagging.

### Northen lab (Suzanne Kosina)

- **GNPS names map 37 of 37** to CORAL `-00` sediment subsamples:
  `soil-<well>-<zone>-C<core>_tr<n>`; zone tokens V/VSZ1/SZ1/SZ2/SZ3 agree
  with the mastersheet "screen Zone" column for every core. Two well-code
  renames: GNPS `M4` → `SSO-M4A-…`, GNPS `L9` → `SSO-L9B-…`. Four extraction
  blanks and one QC standard per run.
- **Four feature tables** (C18 pos/neg, HILIC pos/neg), one GNPS2 FBMN job
  each (770/136/303/220 features × 79 files); the intensity column is MZmine
  `Peak area` (`intensity_measure = area`, `normalization: None`).

### Stahl lab (Kristopher Hunt)

- **Two rows per N number are analytical replicates** (different peak
  heights, same dilution; the Summary sheet averages them with
  `AVERAGEIF`/`STDEV`). For 11144-11147 the pairs are two dilution
  preparations (note in Summary!A26). The blank δ cells (11144 row 1,
  11147 row 2) have peak heights of 0.13 and 0.09 nA against 7.7-58.9 nA
  elsewhere and are yellow-filled: failed injections, left null.
- **`Identifier 1` = well_MMDDYY_assay.bottle.** `GW821_040119_2.1` is
  GW821E, 2019-04-01, assay 2 bottle 1; the R-code is "R" + assay number
  (R21-R24 = 2.1-2.4, 120 mL serum bottle, 15N ammonia-oxidation incubation,
  .4 = azide kill; R151-R153 = 15.1-15.3, 30 mL, 0.1 µm filtered, natural
  abundance NO3⁻/NO2⁻ and N2O isotopes). 14 identifiers = 14 registered
  bottles (GW821E and MLSB5 only; FW100-20 had no rad approval).
- **`Processed` sheet:** columns A-K pass through the IRMS report (denitrifier
  method N2O from the NO3⁻+NO2⁻ pool, dissolved N2O, δ18O VSMOW, δ15N Air);
  the computed finals are oxidized NH3 (nM) per bottle and the mean ± SEM
  over the three live bottles (GW821 2.9 ± 1.3, MLSB 0.95 ± 0.47 nM per
  24 h), plus natural-abundance δ15N/δ18O of nitrate and N2O for MLSB (GW821
  too low). The `Isotope fractionation 3(FvN-UW)` sheet is a separate
  2016-2017 dataset and is not part of the 2019 campaign.

### Zhou lab (Daliang Ning) and SSOM6SED (Zac Cooper)

- **Load the resampled tables, not CleanData.** The existing pump-test and
  time-series bricks match the `4_resampled_ASV.Table.csv` (9432 ASVs, every
  sample 55,286 reads) and `SSOPilotTimeSeries.Resamp.ASVTable.csv` (9398
  ASVs, 23,313 reads), not the clean tables. One-off sets: FTP6 4513 × 12
  (25,181 reads), FTP7 3457 × 4 (25,181), colloids 5273 × 8 (37,579).
- **FTP7 sample IDs are complete** in every copy of the csv: the only `NA`
  rows are the C3 and H2O controls. All four samples resolve to field rows
  145-148 of `SSO_Metadata_One Off Sampling.xlsx` (2024-08-20, U1-VSZ and
  M4-SZ1, 8 µm and 0.1 µm, 1.2 L). FTP6 carries two lab-inferred identities
  (tubes arrived broken) to copy into sample comments.
- **SSOM6SED has no amplicon tables because it is long-read shotgun
  metagenomics** (Nanopore, metaFlye, anvi'o manual bins). Loadable now: the
  288-well enrichment metadata, the 41-bin summary with GTDB taxonomy, and
  the bin abundance/coverage/detection matrices. The parent samples
  `SSO-M6-C2-00/-16` exist in CORAL.
- None of the 28 one-off filter samples exist in CORAL yet (only the four
  2024-05-29 parent samples); they will be added with the ASV bricks.
