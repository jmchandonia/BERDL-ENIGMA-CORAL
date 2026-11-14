# FW305 sediment core (2013) and FWB-306 Chakraborty Lab sediment properties

Built by `tools/build_fw305_core_coral_import.py` from the workbooks in `coral_import/fw305_core_2013_source/`
(ENIGMA Google Drive). Loaded on the CORAL hub 2026-11-13.

| object | CORAL ID | content |
|---|---|---|
| 54 Samples `FW305-01-00` … `FW305-08-00` | | Location FW-305, 0.1524 to 7.9502 m (bottom of each core section), dated 2013-05-29 (well completion), one Sampling process each (Elias Lab, Natural and Synthetic Ecologies) |
| `elias_sediment_anions_iron_fw305_core_2013` | Brick0002346 | 54 samples x 33 variables: moisture, iron(2+), iron(3+), 15 anions and organic acids (µM), one below flag per anion/organic acid |
| `adams_metals_fw305_core_2013` | Brick0002347 | 54 samples x 64 isotopes x 3 instrument runs: concentration (mg/kg dry soil) and below |
| `chakraborty_sediment_properties_fwb306_2015` | Brick0002348 | 8 existing FWB306 samples x 8 variables: pH and nitrate (mean, SD), nitrate below, organic carbon, freeze-dry moisture replicates 1 and 2 |

Decisions (user review 2026-11-13):

- Sample names are the lab's core IDs; depth is the depth sheet's value (bottom of the section, judged from section
  lengths). `FW305-06-54` (22.4167 ft) is kept as given although it is 1 inch above `FW305-06-48`.
- Empty anion/organic acid cells are non-detects (every section has values from the same run): blank concentration
  with below = true. The workbook's formate of `FW305-01-36` (6969) is a typing error: blank, below = false.
  Butyrate and citrate (never detected) are kept.
- Metals: the three instrument runs are stored (no averages); zero readings are blank with below = true; ng/g
  converted to mg/kg as in the other Adams Lab sediment bricks; isotope mass as molecular weight and gas mode as
  presence of helium, as in the core pilot bricks (the workbook says only "Gas Mode (ORS)"); the unlabelled masses
  15, 33 and 44 (44 tracks calcium-43 at 2.1 to 2.8 times its value) and the internal standards are not stored;
  dry soil mass is on the sample dimension.
- FWB-306: the summary sheet's sulfate and moisture columns are the UGA values already in Brick0002185 and
  Brick0002180 and are not stored; freeze-dry moisture of FWB306-03 and -04 (about 0.2 percent) is kept.
- Not loaded: the "Dwayne" subset sheet, the FW306 inventory allocations and the boring log.
