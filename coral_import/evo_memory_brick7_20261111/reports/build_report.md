# EVO Memory campaign and Brick0000007 replacement: build report

## hazen_field_post100ws_v2 (replaces Brick0000007)

- samples: 257 (old brick 449); variables: 42 (old 70); values: 4253 (old 5295)

### Cells and rows removed

- 376: January 2015 time-series metals attached to the wrong wells
- 225: Bi, Cs, U floor values, 2014-2015 time series
- 144: samples without values left out
- 48: EVO injection samples (all their measurements are in the EVO geochemistry brick)
- 40: metals copied from another row (log lines 82, 108)
- 24: Be, Sr, U, Zn floor values, 2015-03-31 samples
- 9: nitrate zeros stored as below detection
- 1: implausible specific conductivity (GW456-12-15-14, 1.217 uS/cm)
- 1: DOC equal to DIC (log line 139)

### Precision

- 5240: cells at full precision
- 433: rows matched
- 60: cells kept as exported
- 52: rows without values
- 16: rows without a matching workbook row

### Outliers to review (pH below 4 or above 9; specific conductivity below 20 or above 3000 uS/cm)

- FW106-06-09-14: pH 3.55, conductivity 6575.0, temperature 19.64, DO 0.03, redox 424.0
- FW126-06-10-14: pH 2.87, conductivity 17510.0, temperature 22.35, DO 0.08, redox 234.0
- FW126-06-12-14: pH 2.97, conductivity 17760.0, temperature 19.45, DO 0.02, redox 197.0
- FW021-06-16-14: pH 3.64, conductivity 6208.0, temperature 20.09, DO 0.24, redox 261.0
- FW109-40-08-11-14: pH 3.5, conductivity 1250.0, temperature 22.33, DO 0.32, redox 248.0
- FW410-26-08-11-14: pH 3.57, conductivity 2086.0, temperature 21.69, DO 0.41, redox 269.0
- FW410-26-08-12-14: pH 3.39, conductivity 3035.0, temperature 24.07, DO 1.8, redox 254.0
- FW109-40-08-12-14: pH 3.43, conductivity 1223.0, temperature 21.29, DO 2.97, redox 243.0
- FW109-1-92-08-13-14: pH 3.95, conductivity 2375.0, temperature 21.73, DO 0.22, redox 181.0
- FW410-26-08-13-14: pH 3.47, conductivity 2962.0, temperature 21.55, DO None, redox 263.0
- FW410-26-08-14-14: pH 3.06, conductivity 3148.0, temperature 23.15, DO 3.06, redox 271.0
- FW410-26-08-15-14: pH 3.38, conductivity 3088.0, temperature 18.39, DO None, redox 142.0
- FW410-26-08-18-14: pH 3.72, conductivity 2832.0, temperature 21.66, DO 3.87, redox 277.0
- GW247-050115: pH 5.96, conductivity 27870.0, temperature 20.09, DO 0.08, redox -57.0
- FW021-050115: pH 3.67, conductivity 7295.0, temperature 20.37, DO 1.16, redox 310.0
- FW410-1-050115: pH 3.71, conductivity 2430.0, temperature 24.47, DO 1.19, redox 244.0
- FW104-050115: pH 5.42, conductivity 16120.0, temperature 26.76, DO 0.06, redox 133.0
- FW106-050115: pH 3.8, conductivity 7542.0, temperature 22.38, DO 0.03, redox 416.0
- FW126-050115: pH 3.05, conductivity 21160.0, temperature 24.44, DO 0.08, redox 484.0
- FW106-061015: pH 3.575, conductivity 9152.0, temperature 27.0, DO 0.075, redox 227.5
- FW115-24-02-09-18: pH 3.61, conductivity 12050.0, temperature 17.35, DO -0.14, redox 436.0
- FW115-24-02-09-18-2: pH 3.61, conductivity 12050.0, temperature 17.35, DO -0.14, redox 436.0
- FW115-24-02-09-18-3: pH 3.61, conductivity 12050.0, temperature 17.35, DO -0.14, redox 436.0
- FW115-24-02-09-18-4: pH 3.61, conductivity 12050.0, temperature 17.35, DO -0.14, redox 436.0
- FW106-02-20-18: pH 3.76, conductivity 98.4, temperature 19.93, DO 1.21, redox 144.0
- FW106-02-20-18-2: pH 3.76, conductivity 98.4, temperature 19.93, DO 1.21, redox 144.0
- FW106-02-20-18-3: pH 3.76, conductivity 98.4, temperature 19.93, DO 1.21, redox 144.0
- FW104-02-20-18: pH 5.47, conductivity 10150.0, temperature 18.73, DO -0.08, redox 166.0
- FW104-02-20-18-2: pH 5.47, conductivity 10150.0, temperature 18.73, DO -0.08, redox 166.0
- FW104-02-20-18-3: pH 5.47, conductivity 10150.0, temperature 18.73, DO -0.08, redox 166.0
- FW106-02-20-18-4: pH 3.76, conductivity 98.4, temperature 19.93, DO 1.21, redox 144.0
- FW104-02-20-18-4: pH 5.47, conductivity 10150.0, temperature 18.73, DO -0.08, redox 166.0
- FW106-02-20-18-5: pH 3.76, conductivity 98.4, temperature 19.93, DO 1.21, redox 144.0
- FW104-02-20-18-5: pH 5.47, conductivity 10150.0, temperature 18.73, DO -0.08, redox 166.0
- FW106-02-20-18-6: pH 3.76, conductivity 98.4, temperature 19.93, DO 1.21, redox 144.0
- FW106-02-20-18-7: pH 3.76, conductivity 98.4, temperature 19.93, DO 1.21, redox 144.0
- FW106-02-20-18-8: pH 3.76, conductivity 98.4, temperature 19.93, DO 1.21, redox 144.0
- FW104-02-20-18-6: pH 5.47, conductivity 10150.0, temperature 18.73, DO -0.08, redox 166.0
- FW106-02-20-18-9: pH 3.76, conductivity 98.4, temperature 19.93, DO 1.21, redox 144.0
- FW021-02-23-18: pH 3.76, conductivity 5198.0, temperature 17.83, DO 0.39, redox None
- FW021-02-23-18-2: pH 3.76, conductivity 5198.0, temperature 17.83, DO 0.39, redox None
- FW021-02-23-18-3: pH 3.76, conductivity 5198.0, temperature 17.83, DO 0.39, redox None
- FW021-02-23-18-4: pH 3.76, conductivity 5198.0, temperature 17.83, DO 0.39, redox None
- FW021-02-23-18-5: pH 3.76, conductivity 5198.0, temperature 17.83, DO 0.39, redox None
- FW021-02-23-18-6: pH 3.76, conductivity 5198.0, temperature 17.83, DO 0.39, redox None

### Cells repaired or interpreted

- GW460-11-17-14, DIC mg/L: '38.32.41' read as 38.3241
- GW458-12-10-14, DIC mg/L: '37..8576' read as 37.8576
- FW301-050115, AODC: '3.7^4' read as 37000
- FW106-061015, pH: range '3.48-3.67' stored as its midpoint 3.575
- FW106-061015, specific cond. @ 20C (uS/cm): range '8094-10210' stored as its midpoint 9152
- FW106-061015, Temp (°C): range '24-30' stored as its midpoint 27
- FW106-061015, DO (mg/L): range '0.09-0.06' stored as its midpoint 0.075
- FW106-061015, Redox (mV): range '209-246' stored as its midpoint 227.5
- FW106-061015, total uranium via ICPMS mg/L: range '16.62-18.544' stored as its midpoint 17.582
- FW300-102715, Redox (mV): '(-)181' read as -181
- FW300-102715-2, Redox (mV): '(-)181' read as -181
- left blank: 48 non-numeric cells (AODC pending, redox none)

### Values per variable

- pH: 256
- specific cond. @ 20C (uS/cm): 255
- Temp (°C): 256
- DO (mg/L): 253
- Redox (mV): 221
- AODC: 128
- Sulfide (ppm): 112
- Ferrous Iron (mg/L): 133
- CO2: 106
- CH4 umol: 6
- CO umol: 6
- DIC mg/L: 134
- DOC mg/L: 133
- Cl mg/l: 114
- NO3 mg/l: 72
- PO4 mg/l: 27
- SO4 mg/l: 114
- Ag mg/l: 81
- Al mg/l: 112
- As mg/l: 81
- Ba mg/l: 112
- Be mg/l: 37
- Bi mg/l: 4
- Ca mg/l: 106
- Cd mg/l: 27
- Co mg/l: 70
- Cr mg/l: 74
- Cs mg/l: 31
- Cu mg/l: 107
- Fe mg/l: 24
- Ga mg/l: 106
- K mg/l: 112
- Li mg/l: 37
- Mg mg/l: 90
- Mn mg/l: 106
- Na mg/l: 106
- Ni mg/l: 102
- Pb mg/l: 81
- Se mg/l: 77
- Sr mg/l: 106
- U mg/l: 32
- Zn mg/l: 106

## FWB-306 sediment: hazen_sediment_extractable_fwb306_2015 and hazen_sediment_soil_properties_fwb306_2015

- samples: FWB306-01, FWB306-02, FWB306-03, FWB306-04, FWB306-05, FWB306-06, FWB306-07, FWB306-08; 2 replicates
- extractable: 20 analytes; below-limit cells: Cr 8 of 16; Pb 2 of 16; nitrate 15 of 16; sulfate 8 of 16
- never detected (kept, all blank): Cd (Mehlich 1; limit 0.04 to 0.06 mg/kg); Mo (Mehlich 1; limit 0.04 to 0.06 mg/kg); fluoride (water extract; limit 0.7 mg/kg); phosphate (water extract; limit 4 mg/kg); U (water extract; limit 1 mg/kg)
- soil properties: 10 variables

## hazen_geochemistry_evo_injection_2017

- samples: 58 (15 new: FW215-03-01-18, FW216-19-03-01-18, MLSB3-03-01-18, GP01-18-03-01-18, GP03-19-03-01-18, FW215-03-29-18, FW216-19-03-29-18, MLSB3-03-29-18, GP01-18-03-29-18, GP03-19-03-29-18, FW215-04-26-18, FW216-19-04-26-18, MLSB3-04-26-18, GP01-18-04-26-18, GP03-19-04-26-18)
- variables: 23; below-detection cells: element Fe 10, nitrate 4, acetate 23, ammonium 12
- chloride values 29, phosphate values 11

## 16S: samples, communities, reads, zOTU bricks

- samples: 105 referenced, 76 new (53 of 2009)
- communities: 136 new; reads: 169 (100 libraries with 133 SRA runs; 36 libraries on Drive only)
- zOTUs: 10216 (2086 new OTU records); taxa: 1415 distinct, 58 new (37 with an NCBI taxid; name 34, none 21, normalized name 3)
- unassigned per level: Family 5244, Genus 6949, Species 10088, Order 2626, Phylum 847, Class 1288, Kingdom 17
- protocols added: michael-ning-2023-unoise3-silva138, 0.1 micron filter

## Sample moves (hub scripts in hub/)

| Sample | New name | Location | Depth m |
| --- | --- | --- | --- |
| GP01-033115 | (unchanged) | GP01-30 -> GP01-18 | 7.391 -> 4.01 |
| GP01-30-01-04-18 | GP01-18-01-04-18 | GP01-30 -> GP01-18 | 7.391 -> 4.01 |
| GP01-30-02-01-18 | GP01-18-02-01-18 | GP01-30 -> GP01-18 | 7.391 -> 4.01 |
| GP01-30-12-07-17 | GP01-18-12-07-17 | GP01-30 -> GP01-18 | 7.391 -> 4.01 |
| GP01-30-12-14-17 | GP01-18-12-14-17 | GP01-30 -> GP01-18 | 7.391 -> 4.01 |
| GP01-30-12-21-17 | GP01-18-12-21-17 | GP01-30 -> GP01-18 | 7.391 -> 4.01 |
| GP01-30-12-28-17 | GP01-18-12-28-17 | GP01-30 -> GP01-18 | 7.391 -> 4.01 |
| GP03-033115 | (unchanged) | GP03-29 -> GP03-19 | 7.303 -> 4.255 |
| GP03-29-01-04-18 | GP03-19-01-04-18 | GP03-29 -> GP03-19 | 7.303 -> 4.255 |
| GP03-29-02-01-18 | GP03-19-02-01-18 | GP03-29 -> GP03-19 | 7.303 -> 4.255 |
| GP03-29-12-07-17 | GP03-19-12-07-17 | GP03-29 -> GP03-19 | 7.303 -> 4.255 |
| GP03-29-12-14-17 | GP03-19-12-14-17 | GP03-29 -> GP03-19 | 7.303 -> 4.255 |
| GP03-29-12-21-17 | GP03-19-12-21-17 | GP03-29 -> GP03-19 | 7.303 -> 4.255 |
| GP03-29-12-28-17 | GP03-19-12-28-17 | GP03-29 -> GP03-19 | 7.303 -> 4.255 |

