# Example brick-like structure: `enigma.sso_staging.toc_tn_anions`

One row per **ANIONS sample**: the Chakraborty lab's total organic carbon /
total nitrogen and ion-chromatography anion results for the campaign's
0.2 µm syringe-filtered, 4 °C vial. Source: every workbook in the campaign
folder's `TOC_TN_Anions_Chakraborty/` subfolder (first file
`SSO_timeseries_102626`, 144 rows = 18 well-zones × 8 timepoints, 2026-11-04).
**Upsert (MERGE) by `sdt_sample_name`**: all rows are re-staged every run, so
rows the lab adds are inserted and rows it edits are updated; a newer workbook
(by mtime) supersedes an older one for the same sample.

This is the first *assay result* table, i.e. the staged form of a CORAL
Chemical Measurement brick keyed on `sdt_sample`. Microtypes are the same ones
the lab's 2024 SSO bricks used (`coral_import/sso_geochemistry_20261009`:
`chakraborty_toc_tn_sso_pump_test_2024`, `chakraborty_ic_anions_*`), so the
campaign-end conversion is mechanical.

## Columns

| Source (lab sheet) | Column | type | role / comment |
|---|---|---|---|
| `SampleID` (mapped) | `sdt_sample_name` | STRING | **FK** → `sample_registry.sdt_sample_name` (upsert key); lab id `L7-SZ1-100626` (`<well>-<zone>-MMDDYY`) → `20261006-L7-SZ1-ANIONS` |
| `SampleID` (raw) | `source_sample_id` | STRING | verbatim lab id |
| — (registry) | `timepoint` | INT | campaign timepoint, looked up from the registry row |
| `Date Sampled` | `sample_date` | STRING | `YYYY-MM-DD` (CORAL date form; from the lab id's `MMDDYY`, checked against the sheet's numeric `MMDDYY`) |
| `Well`/`Zone` | `sdt_location_name` | STRING | FK → enigma.coral.sdt_location; `SSO-<well>` |
| `Well`/`Zone` | `well_port` / `zone` | STRING | `L7-SZ1` / `SZ1` (the well itself is `sdt_location_name` = `SSO-L7`) |
| `Preservation` | `preservation` | STRING | e.g. `0.2um syringe filter` |
| `Storage` | `storage_condition` | STRING | e.g. `4C` |
| `ORDER` | `analysis_order` | INT | lab run order |
| `TOC_ppm` | `concentration_molecule_from_list_elemental_carbon_organic_1_parts_per_million` | DOUBLE | concentration, molecule from list=elemental carbon (CHEBI:33415), organic=1; ppm (UO:0000169) |
| `TN_ppm` | `concentration_molecule_from_list_nitrogen_atom_parts_per_million` | DOUBLE | concentration, molecule from list=nitrogen atom (CHEBI:25555); ppm |
| `Chloride_ppm` | `concentration_molecule_from_list_chloride_parts_per_million` | DOUBLE | chloride CHEBI:17996; ppm |
| `Sulfate_ppm` | `concentration_molecule_from_list_sulfate_parts_per_million` | DOUBLE | sulfate CHEBI:16189; ppm |
| `Nitrate_ppm` | `concentration_molecule_from_list_nitrate_parts_per_million` | DOUBLE | nitrate CHEBI:17632 (as NO3⁻); ppm |
| — | `provenance` / `source_file` / `ingest_run_id` / `ingested_at` | | bookkeeping |

## Decisions

- **Which sample.** TOC/TN and anions share one row per lab id and the lab's
  preservation/storage match the registry's `Anions` assay (Chakraborty, 4C,
  30 mL VOA vial, every timepoint); the registry's `Carbon` assay is a
  different, every-third-timepoint sample. So every row attaches to the
  `...-ANIONS` sample. A lab id with no such registry row is **held** and
  reported (manifest lag or a typo), never loaded as an orphan.
- **`organic_1` stays in the TOC column name** even though it is context:
  coral's `concentration_molecule_from_list_elemental_carbon_parts_per_million`
  is *total* carbon, so the bare name would collide in meaning (NAMING rule:
  a context token is added only to break a lakehouse collision).
- **Units as reported (ppm)**, not converted to mg/L; same as the 2024 bricks.
  Values are stored as the lab reports them (no below-detection nulling at
  this stage; none are zero in the first file).
- **Method / instrument context is not asserted** — the sheet does not state
  it (the 2024 bricks recorded a Dionex Integrion HPIC and a Lotix TOC-TN
  analyzer); add it when the lab confirms.
- Held reasons: id not `<well>-<zone>-MMDDYY`; id contradicts the sheet's own
  Well/Zone/Date Sampled; illegal CORAL id; duplicate id within one file; no
  matching ANIONS sample in the manifest.
