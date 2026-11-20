# Monitoring update 2026-11-17: build report

## hazen_leveltroll400_DP06_20190728_20191206

- 18942 readings, 2019-07-28T00:00:00.000-04:00 to 2019-12-06T12:36:01.000-05:00; intervals (s): {600: 18940, 3361: 1}
- temperature 18.87 to 21.84 C; pressure 1.472 to 2.551 psi; depth to water 11.61 to 14.10 ft

## hazen_pump_log_sso_pump_test_2025

- 242 readings; ports in order pumped: U2-SZ2, U2-SZ1, M4-SZ2, M4-SZ1, L9-SZ2, L9-SZ1, M5-SZ3, M5-SZ2, M5-SZ1
- typing errors corrected: L9-SZ2 08:53 19 L corrected to 08:53 10 L; M5-SZ3 08:21 9 L corrected to 08:31 9 L
- time typed as a number: M4-SZ2 20250924 1155 read as 11:55

## hazen_hobo_WS3_20220509_20230725

- 42409 rows, 2022-05-09T13:15:00.000-04:00 to 2023-07-25T08:15:00.000-04:00; source area3_2022-2024-2025_05_29_13_27_25_EDT_1.csv; battery-only rows dropped: 0

| variable | values | min | max |
|---|---|---|---|
| rainfall_inch | 42409 | 0 | 0.827 |
| rainfall_mathematical_context_cumulative_inch | 41558 | 0 | 2.22 |

## hazen_hobo_WS3_20230725_20240522

- 29032 rows, 2023-07-25T08:30:00.000-04:00 to 2024-05-22T19:45:00.000-04:00; source area3_2022-2024-2025_05_29_13_27_25_EDT_1.csv; battery-only rows dropped: 0

| variable | values | min | max |
|---|---|---|---|
| air_pressure_inhg | 29032 | 28.214 | 29.653 |
| concentration_molecule_from_list_water_physiochemical_state_in_soil_m_3_per_m_3 | 29032 | -0.4206 | 0.7186 |
| dew_point_degree_fahrenheit | 29032 | -5.2 | 82.02 |
| gust_speed_mile_per_hour | 29032 | 0 | 35 |
| rainfall_inch | 29032 | 0 | 0.599 |
| rainfall_mathematical_context_cumulative_inch | 29032 | 0 | 2.65 |
| relative_humidity_percent | 29032 | 14.8 | 100 |
| solar_radiation_watt_per_square_meter | 28938 | 1 | 999 |
| temperature_degree_fahrenheit | 29032 | -3.13 | 96.14 |
| wind_direction_degree | 29032 | 0 | 358 |
| wind_speed_mile_per_hour | 29032 | 0 | 11 |

## hazen_hobo_WS2_20190622_20190723

- 4494 rows, 2019-06-22T15:50:00.000-04:00 to 2019-07-23T20:40:00.000-04:00; source area2_2019-2025_11_25_18_03_16_EST.csv; battery-only rows dropped: 4497

| variable | values | min | max |
|---|---|---|---|
| air_pressure_inhg | 4494 | 28.92 | 29.402 |
| charge_instrument_battery_volt | 4489 | 4.271 | 4.474 |
| concentration_molecule_from_list_water_physiochemical_state_in_soil_m_3_per_m_3 | 4494 | 0.2908 | 0.3822 |
| dew_point_degree_fahrenheit | 4494 | 59 | 82.39 |
| gust_speed_mile_per_hour | 4494 | 0 | 9 |
| rainfall_inch | 4494 | 0 | 0.354 |
| relative_humidity_percent | 4494 | 44 | 100 |
| solar_radiation_watt_per_square_meter | 4326 | 1 | 999 |
| temperature_degree_fahrenheit | 4494 | 58.97 | 96.24 |
| wind_direction_degree | 4494 | 0 | 358 |
| wind_speed_mile_per_hour | 4494 | 0 | 1 |

## EFPW01 Aqua TROLL 600, HydroVu export

- 29665 readings in the export; nitrate sentinels blanked: 0

- hazen_aquatroll600_EFPW01_20220816_20221207: 2710 readings, 2022-08-16T23:00 to 2022-12-07T18:00; intervals (min) {60: 2671, 62: 11, 58: 11}; 16 variables
- hazen_aquatroll600_EFPW01_20221221_20230209: 1220 readings, 2022-12-21T12:54 to 2023-02-09T11:00; intervals (min) {60: 1178, 11: 11, 49: 11}; 16 variables
- hazen_aquatroll600_EFPW01_20230216_20230814: 25735 readings, 2023-02-16T18:30 to 2023-08-14T14:11; intervals (min) {10: 25723, 1: 1, 9: 1}; 16 variables

## EFPW05 Aqua TROLL 600, direct download

- hazen_aquatroll600_EFPW05_20230301_20230509: 9894 readings, 2023-03-01T15:08 to 2023-05-09T08:58; intervals (min) {10: 9893}; 15 variables

## HydroVu Level TROLL bricks, timestamps 4 hours later (fix 1)

| replaces | new brick | rows | first reading | last reading | depth relabelled |
|---|---|---|---|---|---|
| Brick0001367 hazen_leveltroll500_SSO-L7_VZ_20241220_20250716 | hazen_leveltroll500_SSO-L7_VZ_20241220_20250716_v2 | 4982 | 2024-12-20T17:00 | 2025-07-16T08:00 | no |
| Brick0001411 hazen_leveltroll500_SSO-U1_VSZ_20240904_20241002 | hazen_leveltroll500_SSO-U1_VSZ_20240905_20241002_v2 | 2646 | 2024-09-05T00:45 | 2024-10-02T14:00 | yes |
| Brick0001420 hazen_leveltroll500_SSO-U2_VSZ_20241220_20250807 | hazen_leveltroll500_SSO-U2_VSZ_20241220_20250807_v2 | 21949 | 2024-12-20T13:00 | 2025-08-07T13:00 | yes |
| Brick0001594 hazen_leveltroll500_SSO-U3_VSZ_20251213_20251216_v2 | hazen_leveltroll500_SSO-U3_VSZ_20251213_20251216_v3 | 328 | 2025-12-13T04:05 | 2025-12-16T13:50 | no |
| Brick0001598 hazen_leveltroll500_SSO-U3_VZ_20251213_20251216_v2 | hazen_leveltroll500_SSO-U3_VZ_20251213_20251216_v3 | 328 | 2025-12-13T04:05 | 2025-12-16T13:50 | no |

Fix 2 (interpolated values at L8, L9, M6, U3) is withdrawn (user, 2026-11-19): the API's minute series there is not an interpolation of the instrument's log (compared with the L8-SZ2 manual log of 2025-09-10 it scatters about the logged values, and it is a straight line on only 18 of about 4,700 instrument-days), so the 19 Aqua TROLL bricks listed for it stay as loaded.

## WS3 bricks with the dead anemometer (fix 5)

| replaces | new brick | rows | wind speed / gust speed |
|---|---|---|---|
| Brick0001359 hazen_hobo_WS3_20240522_20250408 | hazen_hobo_WS3_20240522_20250408_v2 | 30139 | 1886 zero values blanked |
| Brick0001360 hazen_hobo_WS3_20250416_20250530 | hazen_hobo_WS3_20250416_20250530_v2 | 4192 | 8384 zero values blanked; variables removed: gust_speed_mile_per_hour, wind_speed_mile_per_hour |
| Brick0001361 hazen_hobo_WS3_20250604_20260122 | hazen_hobo_WS3_20250604_20260122_v2 | 21852 | 43704 zero values blanked; variables removed: gust_speed_mile_per_hour, wind_speed_mile_per_hour |

## Total dissolved solids unit (109 bricks)

The unit term changes from parts per trillion to parts per thousand; no value changes. In every brick TDS divided by specific conductivity (uS/cm) is 0.00065, the instruments' factor of 0.65 mg/L per uS/cm expressed in g/L.

| replaces | new brick | rows | TDS / specific conductivity |
|---|---|---|---|
| Brick0001322 hazen_aquatroll600_SSO-U1_SZ2_20241003_20241009 | hazen_aquatroll600_SSO-U1_SZ2_20241003_20241009_v2 | 901 | 0.00065 |
| Brick0001487 hazen_aquatroll600_SSO-L7_SZ1_20241003_20250716_v2 | hazen_aquatroll600_SSO-L7_SZ1_20241003_20250716_v3 | 41172 | 0.00065 |
| Brick0001502 hazen_aquatroll600_SSO-L9_SZ1_20251219_20251220_v2 | hazen_aquatroll600_SSO-L9_SZ1_20251219_20251220_v3 | 122 | 0.00065 |
| Brick0001930 hazen_aquatroll600_EU05_20190604_20190607_v3 | hazen_aquatroll600_EU05_20190604_20190607_v4 | 410 | 0.00065 |
| Brick0001931 hazen_aquatroll600_EU05_20190607_20191004_v3 | hazen_aquatroll600_EU05_20190607_20191004_v4 | 17112 | 0.00065 |
| Brick0001932 hazen_aquatroll600_EU05_20191004_20191206_v3 | hazen_aquatroll600_EU05_20191004_20191206_v4 | 9075 | 0.00065; 1 floor conductivity readings blanked |
| Brick0001933 hazen_aquatroll600_FW-106_20190604_20190607_v3 | hazen_aquatroll600_FW-106_20190604_20190607_v4 | 373 | 0.00065 |
| Brick0001934 hazen_aquatroll600_FW-106_20190607_20200104_v3 | hazen_aquatroll600_FW-106_20190607_20200104_v4 | 30427 | 0.00065; 1 floor conductivity readings blanked |
| Brick0001935 hazen_aquatroll600_FW-126_20190207_20190604_v3 | hazen_aquatroll600_FW-126_20190207_20190604_v4 | 15862 | 0.00065 |
| Brick0001936 hazen_aquatroll600_GW-835_20190606_20191002_v3 | hazen_aquatroll600_GW-835_20190606_20191002_v4 | 17022 | 0.00065 |
| Brick0001937 hazen_aquatroll600_GW-835_20191004_20191206_v3 | hazen_aquatroll600_GW-835_20191004_20191206_v4 | 9076 | 0.00065 |
| Brick0001939 hazen_aquatroll600_SSO-L7_SZ1_20250826_20250905_v3 | hazen_aquatroll600_SSO-L7_SZ1_20250826_20250905_v4 | 1395 | 0.00065 |
| Brick0001940 hazen_aquatroll600_SSO-L7_SZ1_20250908_20251008_v3 | hazen_aquatroll600_SSO-L7_SZ1_20250908_20251008_v4 | 4299 | 0.00065 |
| Brick0001941 hazen_aquatroll600_SSO-L7_SZ1_20251015_20251208_v4 | hazen_aquatroll600_SSO-L7_SZ1_20251015_20251208_v5 | 7743 | 0.00065 |
| Brick0001942 hazen_aquatroll600_SSO-L7_SZ1_20251209_20260121_v3 | hazen_aquatroll600_SSO-L7_SZ1_20251209_20260121_v4 | 6203 | 0.00065; 9 floor conductivity readings blanked |
| Brick0001943 hazen_aquatroll600_SSO-L7_SZ1_20260122_20260122_v4 | hazen_aquatroll600_SSO-L7_SZ1_20260122_20260122_v5 | 60 | 0.00065 |
| Brick0001944 hazen_aquatroll600_SSO-L7_SZ1_20260123_20260309_v3 | hazen_aquatroll600_SSO-L7_SZ1_20260123_20260309_v4 | 6555 | 0.00065; 43 floor conductivity readings blanked |
| Brick0001945 hazen_aquatroll600_SSO-L7_SZ2_20241003_20250610_v4 | hazen_aquatroll600_SSO-L7_SZ2_20241003_20250610_v5 | 35997 | 0.00065 |
| Brick0001946 hazen_aquatroll600_SSO-L7_SZ2_20250610_20250815_v3 | hazen_aquatroll600_SSO-L7_SZ2_20250610_20250815_v4 | 9514 | 0.00065 |
| Brick0001948 hazen_aquatroll600_SSO-L7_SZ2_20250903_20251008_v3 | hazen_aquatroll600_SSO-L7_SZ2_20250903_20251008_v4 | 5018 | 0.00065 |
| Brick0001949 hazen_aquatroll600_SSO-L7_SZ2_20251015_20251208_v4 | hazen_aquatroll600_SSO-L7_SZ2_20251015_20251208_v5 | 7743 | 0.00065 |
| Brick0001950 hazen_aquatroll600_SSO-L7_SZ2_20251209_20260122_v4 | hazen_aquatroll600_SSO-L7_SZ2_20251209_20260122_v5 | 6402 | 0.00065; 36 floor conductivity readings blanked |
| Brick0001951 hazen_aquatroll600_SSO-L7_SZ2_20260123_20260309_v3 | hazen_aquatroll600_SSO-L7_SZ2_20260123_20260309_v4 | 6554 | 0.00065; 141 floor conductivity readings blanked |
| Brick0001953 hazen_aquatroll600_SSO-L8_SZ1_20241003_20250815_v4 | hazen_aquatroll600_SSO-L8_SZ1_20241003_20250815_v5 | 45502 | 0.00065 |
| Brick0001954 hazen_aquatroll600_SSO-L8_SZ1_20250819_20251008_v3 | hazen_aquatroll600_SSO-L8_SZ1_20250819_20251008_v4 | 7210 | 0.00065 |
| Brick0001956 hazen_aquatroll600_SSO-L8_SZ1_20251020_20251104_v4 | hazen_aquatroll600_SSO-L8_SZ1_20251020_20251104_v5 | 2168 | 0.00065 |
| Brick0001958 hazen_aquatroll600_SSO-L8_SZ1_20251106_20251208_v3 | hazen_aquatroll600_SSO-L8_SZ1_20251106_20251208_v4 | 4580 | 0.00065 |
| Brick0001959 hazen_aquatroll600_SSO-L8_SZ1_20251210_20260122_v4 | hazen_aquatroll600_SSO-L8_SZ1_20251210_20260122_v5 | 6270 | 0.00065 |
| Brick0001960 hazen_aquatroll600_SSO-L8_SZ1_20260123_20260217_v3 | hazen_aquatroll600_SSO-L8_SZ1_20260123_20260217_v4 | 3666 | 0.00065 |
| Brick0001961 hazen_aquatroll600_SSO-L8_SZ2_20241003_20241015_v3 | hazen_aquatroll600_SSO-L8_SZ2_20241003_20241015_v4 | 1745 | 0.00065 |
| Brick0001962 hazen_aquatroll600_SSO-L8_SZ2_20241015_20250808_v4 | hazen_aquatroll600_SSO-L8_SZ2_20241015_20250808_v5 | 42750 | 0.00065 |
| Brick0001963 hazen_aquatroll600_SSO-L8_SZ2_20250819_20250928_v3 | hazen_aquatroll600_SSO-L8_SZ2_20250819_20250928_v4 | 5833 | 0.00065 |
| Brick0001965 hazen_aquatroll600_SSO-L8_SZ2_20251016_20251031_v3 | hazen_aquatroll600_SSO-L8_SZ2_20251016_20251031_v4 | 2145 | 0.00065 |
| Brick0001966 hazen_aquatroll600_SSO-L8_SZ2_20251114_20251208_v3 | hazen_aquatroll600_SSO-L8_SZ2_20251114_20251208_v4 | 3436 | 0.00065 |
| Brick0001967 hazen_aquatroll600_SSO-L8_SZ2_20251210_20260122_v4 | hazen_aquatroll600_SSO-L8_SZ2_20251210_20260122_v5 | 6270 | 0.00065 |
| Brick0001968 hazen_aquatroll600_SSO-L8_SZ2_20260123_20260217_v3 | hazen_aquatroll600_SSO-L8_SZ2_20260123_20260217_v4 | 3665 | 0.00065 |
| Brick0001969 hazen_aquatroll600_SSO-L9_SZ1_20241003_20250815_v4 | hazen_aquatroll600_SSO-L9_SZ1_20241003_20250815_v5 | 45491 | 0.00065 |
| Brick0001970 hazen_aquatroll600_SSO-L9_SZ1_20250819_20251008_v3 | hazen_aquatroll600_SSO-L9_SZ1_20250819_20251008_v4 | 7209 | 0.00065 |
| Brick0001971 hazen_aquatroll600_SSO-L9_SZ1_20251016_20251208_v4 | hazen_aquatroll600_SSO-L9_SZ1_20251016_20251208_v5 | 7630 | 0.00065 |
| Brick0001972 hazen_aquatroll600_SSO-L9_SZ1_20251210_20251217_v4 | hazen_aquatroll600_SSO-L9_SZ1_20251210_20251217_v5 | 1031 | 0.00065 |
| Brick0001973 hazen_aquatroll600_SSO-L9_SZ1_20260113_20260122_v4 | hazen_aquatroll600_SSO-L9_SZ1_20260113_20260122_v5 | 1353 | 0.00065 |
| Brick0001974 hazen_aquatroll600_SSO-L9_SZ1_20260123_20260217_v3 | hazen_aquatroll600_SSO-L9_SZ1_20260123_20260217_v4 | 3665 | 0.00065; 143 floor conductivity readings blanked |
| Brick0001975 hazen_aquatroll600_SSO-L9_SZ2_20241003_20250809_v4 | hazen_aquatroll600_SSO-L9_SZ2_20241003_20250809_v5 | 44688 | 0.00065 |
| Brick0001977 hazen_aquatroll600_SSO-L9_SZ2_20251016_20251208_v4 | hazen_aquatroll600_SSO-L9_SZ2_20251016_20251208_v5 | 7632 | 0.00065 |
| Brick0001978 hazen_aquatroll600_SSO-L9_SZ2_20251210_20260122_v4 | hazen_aquatroll600_SSO-L9_SZ2_20251210_20260122_v5 | 6269 | 0.00065 |
| Brick0001979 hazen_aquatroll600_SSO-L9_SZ2_20260123_20260217_v3 | hazen_aquatroll600_SSO-L9_SZ2_20260123_20260217_v4 | 3665 | 0.00065 |
| Brick0001980 hazen_aquatroll600_SSO-M4_SZ1_20241003_20250322_v4 | hazen_aquatroll600_SSO-M4_SZ1_20241003_20250322_v5 | 24495 | 0.00065 |
| Brick0001984 hazen_aquatroll600_SSO-M4_SZ1_20251015_20251103_v4 | hazen_aquatroll600_SSO-M4_SZ1_20251015_20251103_v5 | 2728 | 0.00065 |
| Brick0001985 hazen_aquatroll600_SSO-M4_SZ1_20251104_20251212_v3 | hazen_aquatroll600_SSO-M4_SZ1_20251104_20251212_v4 | 5453 | 0.00065 |
| Brick0001986 hazen_aquatroll600_SSO-M4_SZ1_20251216_20260122_v4 | hazen_aquatroll600_SSO-M4_SZ1_20251216_20260122_v5 | 5389 | 0.00065; 5034 floor conductivity readings blanked |
| Brick0001987 hazen_aquatroll600_SSO-M4_SZ1_20260123_20260309_v3 | hazen_aquatroll600_SSO-M4_SZ1_20260123_20260309_v4 | 6553 | no conductivity above 5 uS/cm to compare; 6553 floor conductivity readings blanked; variables removed: concentration_phase_solid_physiochemical_state_dissolved_parts_per_trillion, conductivity_microsiemen_per_centimeter, specific_conductivity_microsiemen_per_centimeter |
| Brick0001989 hazen_aquatroll600_SSO-M4_SZ2_20250819_20250825_v3 | hazen_aquatroll600_SSO-M4_SZ2_20250819_20250825_v4 | 880 | 0.00065 |
| Brick0001992 hazen_aquatroll600_SSO-M4_SZ2_20251015_20251212_v4 | hazen_aquatroll600_SSO-M4_SZ2_20251015_20251212_v5 | 8334 | 0.00065 |
| Brick0001993 hazen_aquatroll600_SSO-M4_SZ2_20251216_20260122_v4 | hazen_aquatroll600_SSO-M4_SZ2_20251216_20260122_v5 | 5389 | 0.00065; 314 floor conductivity readings blanked |
| Brick0001994 hazen_aquatroll600_SSO-M4_SZ2_20260123_20260309_v3 | hazen_aquatroll600_SSO-M4_SZ2_20260123_20260309_v4 | 6551 | 0.00065; 1739 floor conductivity readings blanked |
| Brick0001996 hazen_aquatroll600_SSO-M5_SZ1_20241003_20250808_v4 | hazen_aquatroll600_SSO-M5_SZ1_20241003_20250808_v5 | 44493 | 0.00065 |
| Brick0001997 hazen_aquatroll600_SSO-M5_SZ1_20250818_20251008_v3 | hazen_aquatroll600_SSO-M5_SZ1_20250818_20251008_v4 | 7343 | 0.00065 |
| Brick0001998 hazen_aquatroll600_SSO-M5_SZ1_20251015_20251212_v4 | hazen_aquatroll600_SSO-M5_SZ1_20251015_20251212_v5 | 8341 | 0.00065 |
| Brick0001999 hazen_aquatroll600_SSO-M5_SZ1_20251216_20260102_v4 | hazen_aquatroll600_SSO-M5_SZ1_20251216_20260102_v5 | 2440 | 0.00065 |
| Brick0002001 hazen_aquatroll600_SSO-M5_SZ2_20241003_20250808_v4 | hazen_aquatroll600_SSO-M5_SZ2_20241003_20250808_v5 | 44488 | 0.00065 |
| Brick0002002 hazen_aquatroll600_SSO-M5_SZ2_20250818_20251008_v3 | hazen_aquatroll600_SSO-M5_SZ2_20250818_20251008_v4 | 7345 | 0.00065 |
| Brick0002003 hazen_aquatroll600_SSO-M5_SZ2_20251015_20251209_v4 | hazen_aquatroll600_SSO-M5_SZ2_20251015_20251209_v5 | 7909 | 0.00065 |
| Brick0002004 hazen_aquatroll600_SSO-M5_SZ2_20251216_20260122_v4 | hazen_aquatroll600_SSO-M5_SZ2_20251216_20260122_v5 | 5391 | 0.00065 |
| Brick0002005 hazen_aquatroll600_SSO-M5_SZ2_20260123_20260217_v3 | hazen_aquatroll600_SSO-M5_SZ2_20260123_20260217_v4 | 3665 | 0.00065 |
| Brick0002006 hazen_aquatroll600_SSO-M5_SZ3_20250928_20251003_v4 | hazen_aquatroll600_SSO-M5_SZ3_20250928_20251003_v5 | 728 | 0.00065 |
| Brick0002007 hazen_aquatroll600_SSO-M5_SZ3_20251117_20251209_v3 | hazen_aquatroll600_SSO-M5_SZ3_20251117_20251209_v4 | 3071 | 0.00065 |
| Brick0002008 hazen_aquatroll600_SSO-M5_SZ3_20251216_20260122_v4 | hazen_aquatroll600_SSO-M5_SZ3_20251216_20260122_v5 | 5390 | 0.00065 |
| Brick0002009 hazen_aquatroll600_SSO-M5_SZ3_20260123_20260309_v3 | hazen_aquatroll600_SSO-M5_SZ3_20260123_20260309_v4 | 6565 | 0.00065 |
| Brick0002012 hazen_aquatroll600_SSO-M6_SZ1_20250825_20250829_v4 | hazen_aquatroll600_SSO-M6_SZ1_20250825_20250829_v5 | 582 | 0.00065 |
| Brick0002013 hazen_aquatroll600_SSO-M6_SZ1_20250829_20250911_v4 | hazen_aquatroll600_SSO-M6_SZ1_20250829_20250911_v5 | 1872 | 0.00065 |
| Brick0002014 hazen_aquatroll600_SSO-M6_SZ1_20250912_20250918_v4 | hazen_aquatroll600_SSO-M6_SZ1_20250912_20250918_v5 | 878 | 0.00065 |
| Brick0002016 hazen_aquatroll600_SSO-M6_SZ1_20251016_20251209_v4 | hazen_aquatroll600_SSO-M6_SZ1_20251016_20251209_v5 | 7790 | 0.00065 |
| Brick0002017 hazen_aquatroll600_SSO-M6_SZ1_20251216_20260122_v4 | hazen_aquatroll600_SSO-M6_SZ1_20251216_20260122_v5 | 5391 | 0.00065 |
| Brick0002018 hazen_aquatroll600_SSO-M6_SZ1_20260123_20260217_v3 | hazen_aquatroll600_SSO-M6_SZ1_20260123_20260217_v4 | 3666 | 0.00065 |
| Brick0002023 hazen_aquatroll600_SSO-M6_SZ2_20250826_20250829_v3 | hazen_aquatroll600_SSO-M6_SZ2_20250826_20250829_v4 | 449 | 0.00065 |
| Brick0002024 hazen_aquatroll600_SSO-M6_SZ2_20250829_20251008_v3 | hazen_aquatroll600_SSO-M6_SZ2_20250829_20251008_v4 | 5746 | 0.00065 |
| Brick0002025 hazen_aquatroll600_SSO-M6_SZ2_20251016_20251209_v4 | hazen_aquatroll600_SSO-M6_SZ2_20251016_20251209_v5 | 7790 | 0.00065 |
| Brick0002026 hazen_aquatroll600_SSO-M6_SZ2_20251216_20260122_v4 | hazen_aquatroll600_SSO-M6_SZ2_20251216_20260122_v5 | 5392 | 0.00065 |
| Brick0002027 hazen_aquatroll600_SSO-M6_SZ2_20260123_20260217_v3 | hazen_aquatroll600_SSO-M6_SZ2_20260123_20260217_v4 | 3665 | 0.00065 |
| Brick0002028 hazen_aquatroll600_SSO-U1_SZ1_20241003_20250111_v4 | hazen_aquatroll600_SSO-U1_SZ1_20241003_20250111_v5 | 14338 | 0.00065 |
| Brick0002031 hazen_aquatroll600_SSO-U1_SZ1_20251014_20251017_v4 | hazen_aquatroll600_SSO-U1_SZ1_20251014_20251017_v5 | 422 | 0.00065 |
| Brick0002033 hazen_aquatroll600_SSO-U1_SZ1_20251028_20251107_v4 | hazen_aquatroll600_SSO-U1_SZ1_20251028_20251107_v5 | 1454 | 0.00065 |
| Brick0002034 hazen_aquatroll600_SSO-U1_SZ1_20251110_20251126_v3 | hazen_aquatroll600_SSO-U1_SZ1_20251110_20251126_v4 | 2272 | 0.00065 |
| Brick0002035 hazen_aquatroll600_SSO-U1_SZ1_20251126_20251216_v3 | hazen_aquatroll600_SSO-U1_SZ1_20251126_20251216_v4 | 2901 | 0.00065 |
| Brick0002039 hazen_aquatroll600_SSO-U1_SZ2_20241010_20250308_v4 | hazen_aquatroll600_SSO-U1_SZ2_20241010_20250308_v5 | 21397 | 0.00065 |
| Brick0002042 hazen_aquatroll600_SSO-U1_SZ2_20251014_20251110_v4 | hazen_aquatroll600_SSO-U1_SZ2_20251014_20251110_v5 | 3897 | 0.00065 |
| Brick0002043 hazen_aquatroll600_SSO-U1_SZ2_20251110_20251216_v4 | hazen_aquatroll600_SSO-U1_SZ2_20251110_20251216_v5 | 5176 | 0.00065 |
| Brick0002047 hazen_aquatroll600_SSO-U2_SZ1_20241003_20250205_v4 | hazen_aquatroll600_SSO-U2_SZ1_20241003_20250205_v5 | 18033 | 0.00065; 806 floor conductivity readings blanked |
| Brick0002050 hazen_aquatroll600_SSO-U2_SZ1_20251014_20251023_v4 | hazen_aquatroll600_SSO-U2_SZ1_20251014_20251023_v5 | 1218 | 0.00065 |
| Brick0002052 hazen_aquatroll600_SSO-U2_SZ1_20251217_20260122_v4 | hazen_aquatroll600_SSO-U2_SZ1_20251217_20260122_v5 | 5239 | 0.00065; 4384 floor conductivity readings blanked |
| Brick0002053 hazen_aquatroll600_SSO-U2_SZ1_20260123_20260217_v3 | hazen_aquatroll600_SSO-U2_SZ1_20260123_20260217_v4 | 3666 | no conductivity above 5 uS/cm to compare; 3666 floor conductivity readings blanked; variables removed: concentration_phase_solid_physiochemical_state_dissolved_parts_per_trillion, conductivity_microsiemen_per_centimeter, specific_conductivity_microsiemen_per_centimeter |
| Brick0002055 hazen_aquatroll600_SSO-U2_SZ2_20241004_20241015_v3 | hazen_aquatroll600_SSO-U2_SZ2_20241004_20241015_v4 | 1570 | 0.00065 |
| Brick0002056 hazen_aquatroll600_SSO-U2_SZ2_20241015_20250501_v4 | hazen_aquatroll600_SSO-U2_SZ2_20241015_20250501_v5 | 28477 | 0.00065 |
| Brick0002059 hazen_aquatroll600_SSO-U2_SZ2_20250825_20251008_v3 | hazen_aquatroll600_SSO-U2_SZ2_20250825_20251008_v4 | 4207 | 0.00065 |
| Brick0002060 hazen_aquatroll600_SSO-U2_SZ2_20251014_20251216_v4 | hazen_aquatroll600_SSO-U2_SZ2_20251014_20251216_v5 | 9071 | 0.00065 |
| Brick0002061 hazen_aquatroll600_SSO-U2_SZ2_20251217_20260122_v4 | hazen_aquatroll600_SSO-U2_SZ2_20251217_20260122_v5 | 5239 | 0.00065 |
| Brick0002062 hazen_aquatroll600_SSO-U2_SZ2_20260123_20260217_v3 | hazen_aquatroll600_SSO-U2_SZ2_20260123_20260217_v4 | 3666 | 0.00065; 129 floor conductivity readings blanked |
| Brick0002064 hazen_aquatroll600_SSO-U3_SZ1_20241003_20250429_v4 | hazen_aquatroll600_SSO-U3_SZ1_20241003_20250429_v5 | 29971 | 0.00065 |
| Brick0002065 hazen_aquatroll600_SSO-U3_SZ1_20250515_20250522_v3 | hazen_aquatroll600_SSO-U3_SZ1_20250515_20250522_v4 | 1023 | 0.00065 |
| Brick0002066 hazen_aquatroll600_SSO-U3_SZ1_20250523_20250610_v3 | hazen_aquatroll600_SSO-U3_SZ1_20250523_20250610_v4 | 2579 | 0.00065 |
| Brick0002069 hazen_aquatroll600_SSO-U3_SZ1_20250826_20250911_v3 | hazen_aquatroll600_SSO-U3_SZ1_20250826_20250911_v4 | 2368 | 0.00065 |
| Brick0002071 hazen_aquatroll600_SSO-U3_SZ1_20251014_20251212_v4 | hazen_aquatroll600_SSO-U3_SZ1_20251014_20251212_v5 | 8480 | 0.00065 |
| Brick0002073 hazen_aquatroll600_SSO-U3_SZ1_20251217_20260122_v4 | hazen_aquatroll600_SSO-U3_SZ1_20251217_20260122_v5 | 5239 | 0.00065; 61 floor conductivity readings blanked |
| Brick0002074 hazen_aquatroll600_SSO-U3_SZ1_20260123_20260217_v3 | hazen_aquatroll600_SSO-U3_SZ1_20260123_20260217_v4 | 3665 | 0.00065; 471 floor conductivity readings blanked |
| Brick0002077 hazen_aquatroll600_SSO-U3_SZ2_20250819_20250825_v3 | hazen_aquatroll600_SSO-U3_SZ2_20250819_20250825_v4 | 876 | 0.00065 |
| Brick0002078 hazen_aquatroll600_SSO-U3_SZ2_20250825_20251008_v3 | hazen_aquatroll600_SSO-U3_SZ2_20250825_20251008_v4 | 6326 | 0.00065 |
| Brick0002079 hazen_aquatroll600_SSO-U3_SZ2_20251014_20251212_v4 | hazen_aquatroll600_SSO-U3_SZ2_20251014_20251212_v5 | 8484 | 0.00065 |
| Brick0002081 hazen_aquatroll600_SSO-U3_SZ2_20251217_20260122_v4 | hazen_aquatroll600_SSO-U3_SZ2_20251217_20260122_v5 | 5238 | 0.00065 |
| Brick0002082 hazen_aquatroll600_SSO-U3_SZ2_20260123_20260217_v3 | hazen_aquatroll600_SSO-U3_SZ2_20260123_20260217_v4 | 3666 | 0.00065 |

Floor conductivity readings blanked in this group: 23531

## Conductivity at the sensor floor, bricks not otherwise replaced

| replaces | new brick | rows | readings blanked | variables removed |
|---|---|---|---|---|
| Brick0001952 hazen_aquatroll600_SSO-L7_SZ2_20260409_20260501_v4 | hazen_aquatroll600_SSO-L7_SZ2_20260409_20260501_v5 | 2089 | 2089 | conductivity_microsiemen_per_centimeter |
| Brick0001957 hazen_aquatroll600_SSO-L8_SZ1_20251105_20251106_v4 | hazen_aquatroll600_SSO-L8_SZ1_20251105_20251106_v5 | 69 | 1 | none |
| Brick0001988 hazen_aquatroll600_SSO-M4_SZ2_20241003_20250313_v4 | hazen_aquatroll600_SSO-M4_SZ2_20241003_20250313_v5 | 15027 | 2 | none |
| Brick0002000 hazen_aquatroll600_SSO-M5_SZ1_20260103_20260106_v4 | hazen_aquatroll600_SSO-M5_SZ1_20260103_20260106_v5 | 266 | 5 | none |
| Brick0002011 hazen_aquatroll600_SSO-M6_SZ1_20250610_20250808_v4 | hazen_aquatroll600_SSO-M6_SZ1_20250610_20250808_v5 | 5439 | 9 | none |
| Brick0002049 hazen_aquatroll600_SSO-U2_SZ1_20250828_20251008_v4 | hazen_aquatroll600_SSO-U2_SZ1_20250828_20251008_v5 | 3919 | 25 | none |

## Air pressure unit in the 2018-19 weather bricks

The variable labelled millimetres of mercury holds inches of mercury (it equals the brick's millibar value / 33.8639); only the unit term changes.

| replaces | new brick | rows | largest difference from millibar / 33.8639 (inHg) |
|---|---|---|---|
| Brick0000046 hazen_hobo_WS2_20180730_20190622 | hazen_hobo_WS2_20180730_20190622_v2 | 36886 | 0.00009 over 36886 readings |
| Brick0000047 hazen_hobo_WS1_20180730_20190622 | hazen_hobo_WS1_20180730_20190622_v2 | 43436 | 0.00009 over 43436 readings |

