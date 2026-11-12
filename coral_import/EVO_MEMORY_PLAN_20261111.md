# EVO injection (Memory campaign, 2009 and 2017): import plan and decisions (2026-11-11)

Source: team Drive `2017 EVO Injection/Zhou - 16S sequencing/` (processed zOTU table, classification, rep seqs,
`20230222.metadata.csv`), paper Michael et al. 2024 Water Research doi:10.1016/j.watres.2024.121460.
Keys saved in `coral_import/evo_memory_2017_source/`: SRA BioSamples of PRJNA1084851 (`biosamples.json`, `ena.tsv`),
the sample table of the paper's GitHub R object (`github_ps.EVO_all_sample_data.tsv`, jpmichael93/Publications),
text of the B. Adams 2019 thesis tables, text of the Watson et al. 2013 supporting information.

## Library-to-sample key
* 136 libraries in the processed table (all rarefied to 10,448 reads; replicate filters already combined).
* EMR1-45 = 2017 experiment, 0.2 um filter, five wells x nine visits (days -6..134; GP01 day 1 missing). SRA + GitHub agree.
* APEVO55/56/60/61 = 0.2 um, day 372 (2018-12-20), FW215/FW216/GP01/GP03.
* 35 other APEVO = 0.1 um filter fraction (GitHub table only; not in SRA). Their day labels 2, 81, 107 are the visits of
  days 1, 78, 106 (Thursday visits only per thesis; community similarity). Day 246 (2018-08-16) is a separate visit.
  APEVO28 (labelled FW215 day 81, a duplicate of APEVO24) is the day 106 visit: numbering block 28-32, FW215 otherwise
  missing on day 107, closest 0.2 um community is day 106.
* W1-W8 = 2009 experiment: MLSG4, FW216, MLSA3, GP01, MLSB3, FW202, GP03, FW215; days -28, 4, 17, 31, 80, 140, 269
  (2009-01-12 .. 2009-11-05; injection 2009-02-09). W7D80 (GP03 2009-04-30) is not in SRA.
* 2017 injection 2017-12-13; day -6 = 2017-12-07.

## Ports (user decisions 2026-11-11)
| Well | Port | Evidence |
| --- | --- | --- |
| GP01 | GP01-18 (upper), all years | Watson 2013 SI Table S4 depth 5.46 m; thesis 2.56-5.46 m |
| GP03 | GP03-19 (upper), all years | Watson SI 5.69 m; thesis 2.82-5.69 m |
| FW216 | FW-216-19 (lower), all years | Watson SI "FW216-2" 5.81 m; thesis says 4.09-4.67 m (upper) - treated as a lookup error, note it |
| FW202 (2009) | FW-202-19 | assumption (level of the other wells) |
The existing ports GP01-30 / GP03-29 came from hard-coded mappings in DumpFieldSamplesTSV3/DumpFieldDataJSON5.

## Corrections to existing CORAL objects
* Rename and move 12 samples: `GP01-30-<date>` -> `GP01-18-<date>`, `GP03-29-<date>` -> `GP03-19-<date>` (six dates
  2017-12-07 .. 2018-02-01), Location and depth with them. FW216-19-* unchanged.
* Move (no rename) `GP01-033115` -> GP01-18 and `GP03-033115` -> GP03-19 (2015; GP01-033115 is the isolation source
  of 18 strains: the isolate bricks carry the Location and must follow at the next isolate update).
* Brick0000007 (hazen_field_post100ws, from the ORNL FRC sample log tab `sample_spreadsheet_tab3.tsv`) needs a
  corrected superseding brick, as a separate task: (a) ChEBI terms resolved from element symbols are wrong for
  K (lysine), P (L-proline residue), F (L-phenylalanine residue), U (L-selenocysteine residue), Ga (Gly-D-Ala),
  As (arsane), Ag (silver(0)) for all 449 rows; (b) the 48 EVO rows have chloride/nitrate/phosphate/sulfate under
  As/Ba/Be/Ca in the source log, acetate (uM) under "Sulfide (ppm)", and unidentified values (probably other organic
  acids) under ferrous iron, CO2, total uranium, CH4, CO: move the anions, drop or relabel the rest.

## Modelling decisions
* Communities: one per sample and filter, 100-well style: `<sample> 0.2 micron filter`, `<sample> 0.1 micron filter`.
* Counts: the processed (rarefied, combined) table. Raw table not loaded (62 of 198 libraries unidentified).
* Geochemistry brick: all Drive metadata columns for the 44 well-visits, including the four derived categories
  (oxygen content, nitrate reduction, sulfate reduction, phase). 2009 geochemistry not available (Gihring 2011 only).
* Known data caveats to state in comments: thesis acetate table is one visit earlier than the Drive/published values;
  Drive uranium at day -6 is exactly 2x the thesis's relative to later visits (32 of 38 well-visits).
* Not loaded: the 27 injection-well metadata rows (no data); 62 unlabelled raw libraries.

## People
Jonathan Michael appears to have left OU (personal address by Dec 2024); Daliang Ning manages the lab's data.

## Brick0000007 replacement and EVO data discrepancies (research 2026-11-11, decisions so far)

Sources compared: sample log `sample_spreadsheet_tab3.tsv` (= "Collected Samples" sheet, updated 2019-02-08) and its
2015-2016 versions in `FRC Sample Request Logs/older_versions` (identical for all shared samples); Rocha poster
2015-02-23 Table 1; Jagadamma seminar 2015-09-02; 100-well survey (`enigma_field_data_hazen_180417.tsv`);
Hazen-lab slides "Area 2 EVO Injection.pptx" (May 2018, chart data); Adams thesis 2019; Putt dissertation (methods);
paper Table S1 (= Drive `20230222.metadata.csv`); Watson 2013 SI.

Decided by the user (2026-11-11):
- One update: superseding Brick0000007 (no campaign/personnel array context), sample renames, EVO package.
- Brick 7 replacement drops every measurement that is in the new EVO brick.
- Drop the 25 metal columns for the 18 January 2015 time-series rows (log lines 135-152; metals attached to the
  wrong wells), the copied metals on lines 82 and 108, and DOC on line 139 (copy of DIC).
- Drop floor values: Bi, Cs, U for the 2014-2015 time series; Be, Sr, U, Zn for the six 2015-03-31 samples.
- Keep 2013 DOC as reported with a comment (same DOC-tracks-DIC behaviour in the 100-well survey).
- Sediment mg/kg block (16 Natural Organic Matter rows) becomes its own brick.
- EVO brick: correct the FW215/FW216 day-15 nitrate and sulfate swap in the Drive table (log and slides agree:
  FW215 1.49 / 60.29 mg/L, FW216 17.74 / 67.56 mg/L).

Findings still awaiting a decision:
- EVO rows in the log: Cl (col 30) and PO4 (col 32) identities supported; five columns (16, 18, 19, 20, 21) not
  identifiable from their values -> proposed drop.
- Drive metals: U confirmed mg/L and day -6 confirmed doubled (thesis: MLSB3 1111.5 ug/L before injection, Drive
  2.223; FW215 day 8 1174.7 ug/L, Drive 1.175). Mn consistent with mg/L. Mg, K, Ca cannot be mg/L (numerically
  consistent with mmol/L). Al flat 6-8.6 in every well and visit (not a plausible analyte signal). Fe is Fe-54,
  erratic.
- Drive GP01 day 106 nitrate 17.63 vs slides 1.76 (unresolved). Thesis acetate table is one visit early for days
  1-22 (log, slides, Drive agree with each other); thesis has day-134 acetate that Drive lacks.

## Follow-ups noted during the brick review (2026-11-11)
- Clean up spelling duplicates in the Taxon table (space vs underscore, capitalization); the EVO taxonomy brick
  references existing records for five such names and adds no new variants.
- Inspect other bricks from the same Java dumpers (e.g. Brick0000081 hazen_field_100ws) for the ChEBI mix-ups
  found in Brick0000007 (element symbols resolved to amino-acid or wrong-species terms).
