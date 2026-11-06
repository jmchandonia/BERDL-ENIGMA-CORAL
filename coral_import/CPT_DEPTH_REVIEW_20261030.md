# CPT sediment sample depths: review before any CORAL correction (2026-10-30)

Seven of the 34 CPT sediment Samples in CORAL have a `depth` that disagrees with the depth
encoded in their own name. Nothing has been changed in CORAL. This note records every source
found for the depths, the verdict per sample and what still needs a human answer.

## Where CORAL's names and depths came from

Both were taken from one Hazen-lab compilation, `2020 CPT Fugro/CPT_SED_full_data_05032021.xlsx`
(identical depths in the 04162021 version): the `Sample Name` column became the CORAL name and the
`Depth.meter` column (= `Depth(decimal ft)` x 0.3048) became the CORAL depth. In that sheet the two
columns disagree for the same seven rows, so CORAL inherited the inconsistency; nothing was
mis-transcribed on our side.

## Sources examined

| Source | Date | Who | Depth information |
| --- | --- | --- | --- |
| Tube labels = sample names (`CPT15SED-ZV-DA335`), as listed in `Shipping/Samples for shipment_10.26.20.xlsx` and `_10.30.20_final.xlsx`, the archive list (12/2021), the Zhou metadata, every lab result sheet | 2020-10-26/30 | Hazen field crew (Putt, Kelly) | depth in cm in the name; decimal names are feet converted (883.9 = 29.0 ft, 1353.3 = 44.4 ft) |
| `CPT_SED_full_data_04162021/05032021.xlsx` `Depth(decimal ft)` | 2021-04/05 | Hazen lab compilation | the only source for CORAL's depth values |
| `CPT Metadata FINAL/CPT_full_data.xlsx` SedimentMetadata (`top/bottom/mid_depth_cm`), unchanged in `CPT_full_data_241122.xlsx` and `CPT_Sediment_full_data_with_distances.xlsx`; readme: "Andrew Putt has completed the metadata file" | 2021-10-28 | Andrew Putt (field sampler) | top/bottom of each subcore |
| Putt dissertation (UTK, 2022), chapter 5 methods, text, Table 5.2, Figure 5.2 (Fugro logs with the sampling intervals drawn and lettered) | 2022 | Andrew Putt | method: "overlying sediments were displaced using the piezocone and then collecting a 45 cm sample in a plastic-lined 3.8 cm diameter core barrel ... sub sectioned"; "the probe hit refusal ... 11.2 m at CPT 47"; "Sixteen samples ... from 274 to 595 cm bgs and three from a depth of 883 to 945 cm bgs"; "a single shallow vadose sample was collected from 274-320 cm bgs"; "CPT47 was the deepest core, and the sample was collected in the material overlying the bedrock"; Table 5.2 mid-depths CPT47S A/B/C = 894/914/934, CPT56CS = 510 |
| Fugro sounding files `CPT_Oct2020_Fugro_Data/CPT-47.csv/.pdf` and `CPT_full_data.xlsx` Location `TotalDepth_M` | 2020-10-24 | Fugro | CPT-47 refusal at 35.29 ft = 10.76 m; CPT-15 4.78 m; CPT-21 4.94 m; CPT-59 2.18 m (59A 9.46 m) |
| Water table: `average gwt` in `CPT_full_data_adding_columns.xlsx` (from the 2020-10 water-level survey of local wells) | 2020-10 | Putt & Kelly | depth to water: CPT15 165 cm, CPT21 202 cm, CPT47 379 cm, CPT56 390 cm, CPT59 362 cm |
| Chakraborty DOC sheet `waterextract_TOC_Northenmethod.xlsx` (depths "as reported by the Hazen lab at distribution, fall 2020") | 2021-11 | Chakraborty lab | follows the names (CPT15 335/366, CPT21 305, CPT59 274/294, CPT56C 549, CPT47 B 1149, C 1353.3) |
| Hazen AODC sheet | 2021-04 | Hazen lab | sample IDs = names |

Not found: a field notebook or field data sheet from October 2020, and the ESS-DIVE copy
(doi:10.15485/1868939; the landing page needs a browser). The Fugro logs do not record sampler pushes.

## How the compilation sheet went wrong

The disputed `Depth(decimal ft)` values are other samples' depths:

| Sheet row | Sheet depth (ft) | Matches |
| --- | --- | --- |
| CPT15S-A, -B | 9.65, 10.01 | CPT59S-B name (9.65 ft) and a 10-ft value |
| CPT59S-A, -B | 10.99, 12.01 | CPT15S-A, -B names (11.0, 12.0 ft) exactly |
| CPT21S-A | 8.99 | CPT59S-A name (9.0 ft) |
| CPT56CS | 2.99 | the CPT56D vadose sample `CPT56DSED-ZV-D91` (91 cm = 2.99 ft) |

That is a row-misalignment pattern (CPT15 and CPT59 crossed; two cells copied from neighbours),
not independent measurements. The names, by contrast, were written on the tubes in the field and
are reproduced identically in every later document.

## Verdicts

| CORAL sample | CORAL depth (m) | Name says (cm) | Putt metadata top-bottom (cm) | Verdict | Confidence |
| --- | --- | --- | --- | --- | --- |
| CPT15SED-ZV-DA335 | 2.94 | 335 | 335.28-349.9 | CORAL depth wrong; 3.35 m | high (name, Putt, swap pattern) |
| CPT15SED-ZC-DB366 | 3.05 | 366 | 349.9-365.7 | CORAL depth wrong; 3.50-3.66 m (366 is the subcore bottom) | high |
| CPT21SED-ZU-DA305 | 2.74 | 305 | 305-323 | CORAL depth wrong; 3.05 m | high |
| CPT59SED-ZC-DA274 | 3.35 | 274 | 274-294 | CORAL depth wrong; 2.74 m. Dissertation: the one shallow vadose sample, 274-320 cm; Figure 5.2 draws it at 2.7-3.3 m; the water table is at 362 cm, so 335-366 cm would not be vadose | high |
| CPT59SED-ZC-DB294 | 3.66 | 294 | 294-320 | CORAL depth wrong; 2.94 m | high |
| CPT56CSED-ZS-549 | 0.91 | 549 | 505.5-515.5 (Table 5.2 mid 510) | CORAL depth certainly wrong (0.91 m is the 56D vadose sample; a ZS = saturated sample must be below 390 cm). Correct value is either 549 (name, 18 ft) or about 505-515 (Putt) | 0.91 wrong: high; which replacement: ask |
| CPT47SED-ZS-DB115 | 11.491 | "114.9" (garbled; sheet 1149.1 = 37.7 ft) | 904.2-924.5 (mid 914) | CORAL depth physically impossible: refusal at CPT-47 was 10.76-11.2 m, the method is one 45 cm core per hole, Figure 5.2 draws A/B/C together at 8.6-9.5 m, dissertation says 883-945 cm. Correct about 9.04 m | 11.49 wrong: high; 9.04: Putt's subdivision |
| CPT47SED-ZS-DC1353 | 13.533 | 1353.3 (= 44.4 ft) | 924.5-944.8 (mid 934) | As above; correct about 9.25 m. The tube label itself carries the impossible value, so the name will stay and the description must explain it | 13.53 wrong: high |

Consistency check on the others: for the 27 undisputed samples the name, the compilation sheet and
CORAL agree, and Putt's tops agree with the names for the A subcores (B and C tops are the A top
plus an assumed subcore length, so they differ from the names by up to 30 cm; that is a modelling
choice, not an error).

## Recommendation

1. Do not edit CORAL yet. Send the table above to Andrew Putt (aputt@vols.utk.edu, author of the
   metadata and dissertation) and Katie Walker (field crew) and ask them to confirm: (a) the five
   CPT15/21/59 depths, (b) what CPT56C's depth is (549 or about 510 cm), (c) that CPT47 B and C are
   subcores of the single 883-945 cm core and how the 1149/1353 labels arose.
2. After confirmation, correct only the `depth` field (and add a description note) of the seven
   Samples; keep the names, which are the keys every brick and process references.
3. The CPT AODC and DOC package is unaffected: it joins on sample names, and each row is the same
   physical sample whatever its depth. Its DOC "depth typos" (CPT10 C 605, CPT63 B 387.35) are
   separate, within-sheet slips.

## Independent physical test: lab texture and Fugro soil behaviour type (added 2026-10-30)

Jinwoo Im's CPT model notebooks (`Manuscript/Jupyter notebooks/`) log their inputs:
`CPT_full_data_241122.xlsx` (identical to Putt's final metadata) and `data_sediment_part_05M.csv`
(Putt's top/bottom elevations). They add no independent depth measurement, but they point to a
test that is independent of the compilation sheet: the dissertation's Table 5.2 gives a laboratory
particle-size analysis for each of the 19 subsite samples, and the Fugro probe gives a soil
behaviour type (SBT) every 1-2 cm at each hole. A sample's measured texture should match the SBT
at its true depth. Fugro soundings used: CPT-15, CPT-21, CPT-47, CPT-56B, CPT-59A (the successful
pushes). Full table in the scratchpad file `sbt_test.txt`.

| Sample | Lab texture (coarse/fine, clay) | Fugro SBT at the name depth | Fugro SBT at the sheet (CORAL) depth | Favours |
| --- | --- | --- | --- | --- |
| CPT59S-A | 19/81, clay 47 % | 274-294: **clay** (3), tip 43 TSF | 335-355: very stiff fine grained (11), tip 108 | name |
| CPT59S-B | 39/61, clay 32 % | 294-320: stiff fine grained / sandy silt mix | 366-386: clay-clayey silt | name (mixed texture) |
| CPT56CS | 31/69, clay 24 % | 549-560: **sandy silt-clayey silt** (6) | 91-101: silty clay-clay | name (549); Putt's 505-515 is "very stiff fine grained" (ambiguous) |
| CPT56DS-A/B/C (not disputed; CORAL uses the names) | 47/53, 59/41 with 25 % gravel, 60/40 | 548-607: sandy silt, sand-clayey sand (6, 12) | Putt's 488-549: very stiff fine grained (11) throughout | names, i.e. CORAL as is |
| CPT47S-A, -B, -C | 17/83, 16/84, 37/63 | 884-945: stiff fine grained then sand-clayey sand | 1149 and 1353 cm: below refusal, no data | A and B nearly identical in texture and geochemistry (adjacent subcores); C sandier where the log turns sandy at 925-945 |
| CPT15S-A, -B | no lab texture; Putt's hand-assigned SBT 6, 6 | 335-366: clayey silt-sandy silt (5, 6) | 294-320: soft clay (3), tip 16-24 | name |
| CPT21S-A | no lab texture; Putt's SBT 11 | 305-323: very stiff fine grained (11), tip 144 | 274-292: clay (3), tip 27 | name |

Where the test can speak it supports the names every time and the compilation-sheet depths
never. It also supports the name depth (549) over Putt's 505-515 for CPT56C.

## Recommendation (revised)

Putt has left the project and Walker cannot be reached, so the decision rests on the record above:
field labels, Putt's own metadata and dissertation, the refusal depths, the misalignment pattern in
the compilation sheet, and the texture test all agree. Proposed corrections to the `depth` field
only (names unchanged; add a description note citing this review):

| Sample | Current | Proposed | Basis |
| --- | --- | --- | --- |
| CPT15SED-ZV-DA335 | 2.94 | 3.35 | name, Putt top 335.28 |
| CPT15SED-ZC-DB366 | 3.05 | 3.66 | name (CORAL uses the name depth for every other B/C subcore, e.g. CPT26S-B 5.48) |
| CPT21SED-ZU-DA305 | 2.74 | 3.05 | name, Putt top 305 |
| CPT59SED-ZC-DA274 | 3.35 | 2.74 | name, Putt, dissertation, texture |
| CPT59SED-ZC-DB294 | 3.66 | 2.94 | name, Putt |
| CPT56CSED-ZS-549 | 0.91 | 5.49 | name, texture, saturated zone; Putt's 5.05 is the alternative |
| CPT47SED-ZS-DB115 | 11.491 | 9.042 | Putt's subcore top; label impossible (refusal 10.76-11.2 m) |
| CPT47SED-ZS-DC1353 | 13.533 | 9.245 | Putt's subcore top; label impossible |

CPT47 B/C and CPT56C should be described as best estimates with the alternatives named.

## Revision 2026-11-02: evidence independent of Putt, and CPT47 withdrawn

How the compilation sheet's depth cells were entered settles the CPT15/21/59 block without
reference to Putt. In `CPT_SED_full_data_05032021.xlsx` the rows CPT21S-A, CPT15S-A, CPT15S-B,
CPT59S-A, CPT59S-B are consecutive. Their label depths are 305, 335, 366, 274, 294 cm; the sheet's
depth cells for those rows are 274, 294, 305, 335, 366: the same five numbers sorted ascending and
attached to the wrong rows (typed as whole cm, with the "decimal feet" column derived from them,
hence 8.99, 9.65, 10.01, 10.99, 12.01 ft). The CPT56C cell (91 cm) is the depth of
`CPT56DSED-ZV-D91`, which has no row in that sheet. So those six sheet values are not measurements.

For CPT47 B and C the position is different and the earlier recommendation is withdrawn. The two
field-derived records agree with each other: the tube labels (883.9, "114.9" for 1149, 1353.3 cm)
and the sheet, where the CPT47 depths were typed in feet (29.0, 37.7, 44.4). Only Putt's metadata
and dissertation (one 61 cm core at 883.9-944.8 cm) disagree. The physical objection, the Fugro
cone refusal at 35.3 ft, is weakened by the well-construction data: the wells within 5 m of CPT47
(FW115, FW122, FW127, FW129, FW130) were bored to 47-51 ft and are screened at 37-50 ft, so
saprolite does extend to the labelled depths. CORAL keeps 11.491 and 13.533 m for CPT47 B and C
until a field participant confirms; a description note records the conflict.

Proposed corrections now: CPT15SED-ZV-DA335 2.94 -> 3.35; CPT15SED-ZC-DB366 3.05 -> 3.66;
CPT21SED-ZU-DA305 2.74 -> 3.05; CPT59SED-ZC-DA274 3.35 -> 2.74; CPT59SED-ZC-DB294 3.66 -> 2.94;
CPT56CSED-ZS-549 0.91 -> 5.49. Jinwoo Im asked about CPT47 (email 2026-11-02).
