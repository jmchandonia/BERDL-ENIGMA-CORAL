# Database Schema: enigma_coral

Total Tables: 45

---

## Table: ddt_ndarray

**Table Description:** Dynamic Data Types (N-Dimensional Arrays)

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| ddt_ndarray_id | string | Yes | {"description": "Primary key for dynamic data type (N-dimensional array)", "type": "primary_key"} |
| ddt_ndarray_name | string | Yes | {"description": "Name of the data brick (N-dimensional array)", "type": "unique_key"} |
| ddt_ndarray_description | string | Yes | {"description": "Description of the data brick (N-dimensional array)"} |
| ddt_ndarray_metadata | string | Yes | {"description": "Metadata for the data brick (N-dimensional array)"} |
| ddt_ndarray_type_sys_oterm_id | string | Yes | {"description": "Data type for this data brick, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| ddt_ndarray_type_sys_oterm_name | string | Yes | {"description": "Data type for this data brick"} |
| ddt_ndarray_shape | string | Yes | {"description": "Shape of the N-dimensional array, array with one integer per dimension", "example": "[10,10]"} |
| ddt_ndarray_dimension_types_sys_oterm_id | string | Yes | {"description": "Array of dimension data types, ontology term CURIEs", "type": "foreign_key", "references": "[sys_oterm.sys_oterm_id]"} |
| ddt_ndarray_dimension_types_sys_oterm_name | string | Yes | {"description": "Array of dimension data types"} |
| ddt_ndarray_dimension_variable_types_sys_oterm_id | string | Yes | {"description": "Array of dimension variable types, ontology term CURIEs", "type": "foreign_key", "references": "[sys_oterm.sys_oterm_id]"} |
| ddt_ndarray_dimension_variable_types_sys_oterm_name | string | Yes | {"description": "Array of dimension variable types"} |
| ddt_ndarray_variable_types_sys_oterm_id | string | Yes | {"description": "Array of variable types, ontology term CURIEs", "type": "foreign_key", "references": "[sys_oterm.sys_oterm_id]"} |
| ddt_ndarray_variable_types_sys_oterm_name | string | Yes | {"description": "Array of variable types"} |
| withdrawn_date | string | Yes | {"description": "Date when this dataset was withdrawn, or null if the dataset is currently valid"} |
| superceded_by_ddt_ndarray_id | string | Yes | {"description": "Dataset that supercedes this one, if the dataset was withdrawn and replaced, or null if the dataset is currently valid", "type": "foreign_key", "references": "ddt_ndarray.ddt_ndarray_id"} |

### Sample Data (5 rows)

| ddt_ndarray_id | ddt_ndarray_name | ddt_ndarray_description | ddt_ndarray_metadata | ddt_ndarray_type_sys_oterm_id | ddt_ndarray_type_sys_oterm_name | ddt_ndarray_shape | ddt_ndarray_dimension_types_sys_oterm_id | ddt_ndarray_dimension_types_sys_oterm_name | ddt_ndarray_dimension_variable_types_sys_oterm_id | ddt_ndarray_dimension_variable_types_sys_oterm_name | ddt_ndarray_variable_types_sys_oterm_id | ddt_ndarray_variable_types_sys_oterm_name | withdrawn_date | superceded_by_ddt_ndarray_id |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Brick0000010 | adams_metals_100ws.ndarray | Adams Lab Metals Measurements for 100 Well Survey | [] | DA:0000005 | Chemical Measurement | [209, 52, 3, 3] | "[""DA:0000042"" |  ""ME:0000027"" |  ""ME:0000037"" |  ""ME:0000005""]" | "[""Environmental Sample"" |  ""molecule"" |  ""physiochemical state"" |  ""replicate series""]" |
| Brick0000072 | adams_metals_corepilot_271.ndarray | Adams Lab Metals Measurements from Core Pilot | [] | DA:0000005 | Chemical Measurement | [3, 2, 9, 35] | "[""ME:0000037"" |  ""ME:0000146"" |  ""ME:0000100"" |  ""ME:0000027""]" | "[""physiochemical state"" |  ""statistic"" |  ""environmental sample"" |  ""molecule""]" |
| Brick0000073 | adams_metals_corepilot_106.ndarray | Adams Lab Metals Measurements from Core Pilot | [] | DA:0000005 | Chemical Measurement | [3, 2, 18, 33] | "[""ME:0000037"" |  ""ME:0000146"" |  ""ME:0000100"" |  ""ME:0000027""]" | "[""physiochemical state"" |  ""statistic"" |  ""environmental sample"" |  ""molecule""]" |
| Brick0000080 | adams_metals_27ws.hndarray | Adams Lab Metals Measurements from 27 Well Survey | "[[""Instrument <ME:0000012>"" |  ""Nebulizer |  Concentric Quartz; Torch |  Quartz; Cones |  Pt""] |  [""Method <ME:0000007>"" |  ""Samples are diluted 1.2x for final acid conc of 2% HNO3.  Tubes were rinsed thoroughly after receiving them from ORNL due shipping contamination.""] |  [""Comment <ME:0000011>"" |  ""Inorganic Ventures 71A and 71B standards where used plus individual standards of Al |  Mg |  K |  Ca |
| Brick0000452 | zhou_lab_100ws_spring19_corepilot_27ws_cpt_ASV_16S.ndarray | Zhou Lab 100WS Spring19 CorePilot 27WS CPT ASV 16S Sequences | [] | DA:0000064 | Microbial Sequence | [113741] | "[""ME:0000184""]" | "[""ASV""]" | "[[""ME:0000222""]]" | "[[""ASV ID""]]" | "[""ME:0000282""]" | "[""sequence""]" | NULL | NULL |

---

## Table: sys_ddt_typedef

**Table Description:** Typedefs for Dynamic Data Types (N-Dimensional Arrays)

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| ddt_ndarray_id | string | Yes | {"description": "Key for dynamic data type (N-dimensional array)", "type": "foreign_key", "references": "ddt_ndarray.ddt_ndarray_id"} |
| berdl_column_name | string | Yes | {"description": "BERDL column name"} |
| berdl_column_data_type | string | Yes | {"description": "BERDL column data type, variable or dimension_variable"} |
| scalar_type | string | Yes | {"description": "Scalar type"} |
| foreign_key | string | Yes | {"description": "Foreign key reference"} |
| comment | string | Yes | {"description": "Column comment"} |
| unit_sys_oterm_id | string | Yes | {"description": "Unit, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| unit_sys_oterm_name | string | Yes | {"description": "Unit"} |
| dimension_number | int | Yes | {"description": "Dimension number, starting at 1, for dimension variables"} |
| dimension_oterm_id | string | Yes | {"description": "Dimension data type, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| dimension_oterm_name | string | Yes | {"description": "Dimension data type"} |
| variable_number | int | Yes | {"description": "Variable number within a dimension, numbered starting at 1"} |
| variable_oterm_id | string | Yes | {"description": "Dimension variable data type, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| variable_oterm_name | string | Yes | {"description": "Dimension variable data type"} |
| original_csv_string | string | Yes | {"description": "Original representation of this variable in the CORAL data dump CSV"} |

### Sample Data (5 rows)

| ddt_ndarray_id | berdl_column_name | berdl_column_data_type | scalar_type | foreign_key | comment | unit_sys_oterm_id | unit_sys_oterm_name | dimension_number | dimension_oterm_id | dimension_oterm_name | variable_number | variable_oterm_id | variable_oterm_name | original_csv_string |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Brick0000010 | concentration_micromolar | variable | float | NULL | concentration | UO:0000064 | micromolar | NULL | NULL | NULL | 1 | ME:0000129 | concentration | values,Concentration <ME:0000129>,micromolar <UO:0000064> |
| Brick0000010 | sdt_sample_name | dimension_variable | object_ref | sdt_sample.sdt_sample_name | environmental sample ID | NULL | NULL | 1 | DA:0000042 | Environmental Sample | 1 | ME:0000102 | environmental sample ID | dmeta,1,Environmental Sample <DA:0000042>,Environmental Sample ID <ME:0000102> |
| Brick0000010 | molecule_from_list_sys_oterm_id | dimension_variable | oterm_ref | sys_oterm.sys_oterm_id | molecule from list, ontology term CURIE | NULL | NULL | 2 | ME:0000027 | molecule | 1 | ME:0000381 | molecule from list | dmeta,2,Molecule <ME:0000027>,Molecule from list <ME:0000381> |
| Brick0000010 | molecule_from_list_sys_oterm_name | dimension_variable | oterm_ref | NULL | molecule from list | NULL | NULL | 2 | ME:0000027 | molecule | 1 | ME:0000381 | molecule from list | dmeta,2,Molecule <ME:0000027>,Molecule from list <ME:0000381> |
| Brick0000010 | molecule_molecular_weight_dalton | dimension_variable | float | NULL | molecular weight | UO:0000221 | dalton | 2 | ME:0000027 | molecule | 2 | ME:0000350 | molecular weight | dmeta,2,Molecule <ME:0000027>,Molecular Weight <ME:0000350>,dalton <UO:0000221> |

---

## Table: ddt_brick0000010

**Table Description:** DDT Brick table: Brick0000010

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_sample_name | string | Yes | {"description": "environmental sample ID", "type": "foreign_key", "references": "sdt_sample.sdt_sample_name"} |
| molecule_from_list_sys_oterm_id | string | Yes | {"description": "molecule from list, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| molecule_from_list_sys_oterm_name | string | Yes | {"description": "molecule from list"} |
| molecule_molecular_weight_dalton | double | Yes | {"description": "molecular weight", "unit": "dalton"} |
| molecule_algorithm_parameter | string | Yes | {"description": "algorithm parameter"} |
| molecule_detection_limit_micromolar | double | Yes | {"description": "detection limit", "unit": "micromolar"} |
| physiochemical_state | string | Yes | {"description": "physiochemical state"} |
| replicate_series_count_unit | int | Yes | {"description": "replicate series", "unit": "count unit"} |
| concentration_micromolar | double | Yes | {"description": "concentration", "unit": "micromolar"} |

### Sample Data (5 rows)

| sdt_sample_name | molecule_from_list_sys_oterm_id | molecule_from_list_sys_oterm_name | molecule_molecular_weight_dalton | molecule_algorithm_parameter | molecule_detection_limit_micromolar | physiochemical_state | replicate_series_count_unit | concentration_micromolar |
|---|---|---|---|---|---|---|---|---|
| GW773-35-2-4-13 | CHEBI:27214 | uranium atom | 238.0 | Collision mode 0 | NULL | Suspension | 3 | 0.0006932770000000001 |
| GW773-35-2-4-13 | CHEBI:27214 | uranium atom | 238.0 | Collision mode 0 | NULL | Pellet | 1 | 0.000159664 |
| GW773-35-2-4-13 | CHEBI:27214 | uranium atom | 238.0 | Collision mode 0 | NULL | Pellet | 2 | 0.00013025200000000003 |
| GW773-35-2-4-13 | CHEBI:27214 | uranium atom | 238.0 | Collision mode 0 | NULL | Pellet | 3 | 0.000142857 |
| GW198-41-2-11-13 | CHEBI:17632 | nitrate | NULL | NULL | 2.5 | Supernatant | 1 | 81.85473439968399 |

---

## Table: ddt_brick0000072

**Table Description:** DDT Brick table: Brick0000072

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| physiochemical_state | string | Yes | {"description": "physiochemical state"} |
| statistic_sys_oterm_id | string | Yes | {"description": "statistic, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| statistic_sys_oterm_name | string | Yes | {"description": "statistic"} |
| sdt_sample_name | string | Yes | {"description": "environmental sample ID", "type": "foreign_key", "references": "sdt_sample.sdt_sample_name"} |
| molecule_from_list_sys_oterm_id | string | Yes | {"description": "molecule from list, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| molecule_from_list_sys_oterm_name | string | Yes | {"description": "molecule from list"} |
| molecule_molecular_weight_dalton | double | Yes | {"description": "molecular weight", "unit": "dalton"} |
| molecule_presence_molecule_from_list_helium_0 | boolean | Yes | {"description": "presence, Molecule from list=helium(0)"} |
| concentration_milligram_per_kilogram | double | Yes | {"description": "concentration", "unit": "milligram per kilogram"} |

### Sample Data (5 rows)

| physiochemical_state | statistic_sys_oterm_id | statistic_sys_oterm_name | sdt_sample_name | molecule_from_list_sys_oterm_id | molecule_from_list_sys_oterm_name | molecule_molecular_weight_dalton | molecule_presence_molecule_from_list_helium_0 | concentration_milligram_per_kilogram |
|---|---|---|---|---|---|---|---|---|
| Acid | ME:0000147 | Average | EB271-02-02 | CHEBI:25107 | magnesium atom | 24.0 | True | 791.7 |
| Acid | ME:0000147 | Average | EB271-02-02 | CHEBI:28984 | aluminium atom | 27.0 | True | 101.7 |
| Acid | ME:0000147 | Average | EB271-02-02 | CHEBI:50342 | L-proline residue | 31.0 | False | 0.0 |
| Acid | ME:0000147 | Average | EB271-02-02 | CHEBI:50342 | L-proline residue | 31.0 | True | 0.0 |
| Acid | ME:0000147 | Average | EB271-02-02 | CHEBI:25094 | lysine | 39.0 | True | 83.0 |

---

## Table: ddt_brick0000073

**Table Description:** DDT Brick table: Brick0000073

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| physiochemical_state | string | Yes | {"description": "physiochemical state"} |
| statistic_sys_oterm_id | string | Yes | {"description": "statistic, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| statistic_sys_oterm_name | string | Yes | {"description": "statistic"} |
| sdt_sample_name | string | Yes | {"description": "environmental sample ID", "type": "foreign_key", "references": "sdt_sample.sdt_sample_name"} |
| molecule_from_list_sys_oterm_id | string | Yes | {"description": "molecule from list, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| molecule_from_list_sys_oterm_name | string | Yes | {"description": "molecule from list"} |
| molecule_molecular_weight_dalton | double | Yes | {"description": "molecular weight", "unit": "dalton"} |
| molecule_presence_molecule_from_list_helium_0 | boolean | Yes | {"description": "presence, Molecule from list=helium(0)"} |
| concentration_milligram_per_kilogram | double | Yes | {"description": "concentration", "unit": "milligram per kilogram"} |

### Sample Data (5 rows)

| physiochemical_state | statistic_sys_oterm_id | statistic_sys_oterm_name | sdt_sample_name | molecule_from_list_sys_oterm_id | molecule_from_list_sys_oterm_name | molecule_molecular_weight_dalton | molecule_presence_molecule_from_list_helium_0 | concentration_milligram_per_kilogram |
|---|---|---|---|---|---|---|---|---|
| Acid | ME:0000147 | Average | EB106-02-01 | CHEBI:25107 | magnesium atom | 24.0 | True | 2609.57890976744 |
| Acid | ME:0000147 | Average | EB106-02-01 | CHEBI:28984 | aluminium atom | 27.0 | True | 95.4801055222215 |
| Acid | ME:0000147 | Average | EB106-02-01 | CHEBI:50342 | L-proline residue | 31.0 | False | 0.799307315611935 |
| Acid | ME:0000147 | Average | EB106-02-01 | CHEBI:50342 | L-proline residue | 31.0 | True | 0.601571442761929 |
| Acid | ME:0000147 | Average | EB106-02-01 | CHEBI:25094 | lysine | 39.0 | True | 142.371843456069 |

---

## Table: ddt_brick0000080

**Table Description:** DDT Brick table: Brick0000080

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_sample_name | string | Yes | {"description": "environmental sample ID", "type": "foreign_key", "references": "sdt_sample.sdt_sample_name"} |
| molecule_from_list_sys_oterm_id | string | Yes | {"description": "molecule from list, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| molecule_from_list_sys_oterm_name | string | Yes | {"description": "molecule from list"} |
| molecule_molecular_weight_dalton | double | Yes | {"description": "molecular weight", "unit": "dalton"} |
| molecule_presence_molecule_from_list_helium_0 | boolean | Yes | {"description": "presence, Molecule from list=helium(0)"} |
| concentration_statistic_average_parts_per_billion | double | Yes | {"description": "concentration, Statistic=Average", "unit": "parts per billion"} |
| concentration_statistic_standard_deviation_parts_per_billion | double | Yes | {"description": "concentration, Statistic=Standard Deviation", "unit": "parts per billion"} |
| detection_limit_parts_per_billion | double | Yes | {"description": "detection limit", "unit": "parts per billion"} |

### Sample Data (5 rows)

| sdt_sample_name | molecule_from_list_sys_oterm_id | molecule_from_list_sys_oterm_name | molecule_molecular_weight_dalton | molecule_presence_molecule_from_list_helium_0 | concentration_statistic_average_parts_per_billion | concentration_statistic_standard_deviation_parts_per_billion | detection_limit_parts_per_billion |
|---|---|---|---|---|---|---|---|
| ED04-D01 | CHEBI:30501 | beryllium atom | 9.0 | False | 0.001562349753452 | 0.000366941008739 | 0.000469808553261 |
| ED04-D01 | CHEBI:27560 | boron atom | 11.0 | False | 33.7619347281608 | 0.191036459932015 | 0.023132926454591 |
| ED04-D01 | CHEBI:26708 | sodium atom | 23.0 | False | 5696.39023311947 | 32.3566930281299 | 0.894455712265924 |
| ED04-D01 | CHEBI:25107 | magnesium atom | 24.0 | False | 17678.0757968573 | 297.141974133571 | 0.079527218969207 |
| ED04-D01 | CHEBI:28984 | aluminium atom | 27.0 | True | 1.63612631792486 | 0.078702157706031 | 0.03413258127732 |

---

## Table: ddt_brick0000452

**Table Description:** DDT Brick table: Brick0000452

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_asv_name | string | Yes | {"description": "ASV ID", "type": "foreign_key", "references": "sdt_asv.sdt_asv_name"} |
| sequence_sequence_type_16s_sequence | string | Yes | {"description": "sequence, Sequence Type=16S Sequence"} |

### Sample Data (5 rows)

| sdt_asv_name | sequence_sequence_type_16s_sequence |
|---|---|
| 8596cf3f138f9a1eb8b88cfedb4188ea | TACGGAGGTGGCAAGCGTTACTCGGATTTATTGGGTGTAAAGGGCAGGTAGGTGGTCTTGTAAGTTGGGAGTGAAATCCCCCGGCTCAACCGGGGAACTGCTTTCAAAACTGCAAGACTTGGGACTAGAAGAGGAGAACGGAATTCCCGGTGTAAGGGTGAAATCTGTAGATATCGGGAGGAACACCAGTAGCGAAGGCGGTTCTCTGGGCTAGTTCTGACACTGAGCTGCGAAAGCTAGGGGAGCAAACAGG |
| 8597b02df0861a148003228718227162 | TACAGAGGGGGCAAGCGTTGTTCGGAATTATTGGGCGTAAAGGGTGTGTAGGCGGCTTGACAAGTCAGTGGTGAAATCCCCCGGCTTAACCGGGGACGTGCCTTTGATACTGTCAGGCTTGAGTACGGAAGAGGAGAGTGGAATTCCCAGTGTAGCGGTGAAATGCGTAGATATTGGGAAGAACACCGGCGGCGAAGGCGGCTCTCTGGTCCGTTACTGACGCTGAGACACGAAAGCCAGGGTAGCAAACGGG |
| 8597b8c50a71f8ab34d326d3b4b4068c | AACGTAGGAGGCGAGCGTTATCCGGATTTACTGGGCGTAAAGCGCGTGCAGGTGGTACGGTTAGTTGGATGTGAAAGCTCCTGGCTTAACTGGGAGAGGTCGTTCAATACTGCCGAACTGGAGTATGGGAGAGGGAGGTGGAATTCCGAGTGTAGTGGTGAAATGCGTAGATATTCGGAGGAACACCAGTGGCGAAAGCGGCCTCCTGGCCCATTACTGACACTCAGACGCGAAAGCTAGGGGAGCGAACGGG |
| 85984a4ef5ce3ceaf718c8fb20b09721 | TACGTAGGGTGCAAGCGTTGTTCGGAATTACTGGGCGTAAAGGGCGCGTAGGCGGGCGCGTAAGTCGGCTGTGAAAGCCCTGGGCTTAACCCGGGAATTGCAGTTGAAACTGCGTGTCTTGAGTGTTTGAGAGGGTGGTGGAATTCCTGGTGTAGAGGTGAAATTCGTAGATATCAGGAGGAACACCGGAGGCGAAGGCGGCCACCTGGCAATACACTGACGCTGAGGCGCGAAAGCGTGGGGAGCAAACAGG |
| 85985b3f96eefb54d7dfef9beb107f8b | TACGGGGGGGGCAAGCGTTGTTCGGAATTACTGGGCGTAAAGGGTGCGTAGGCGGTGCTCTAAGTCGGATGTGAAAACTCTGGGCTCAACCCAGAGCCTGCATCCGAAACTGGAGTGCTGGAGTTCTGGAGGGGGTAGCGGAATTCCTGGTGTAGCGGTGAAATGCGTAGATATCAGGAGGAACACCGGTGGCGAAGGCGGCTACCTGGACAGAAACTGACGCTGAGGCACGAAAGCTAGGGGAGCAAACAGG |

---

## Table: ddt_brick0000454

**Table Description:** DDT Brick table: Brick0000454

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_asv_name | string | Yes | {"description": "ASV ID", "type": "foreign_key", "references": "sdt_asv.sdt_asv_name"} |
| taxonomic_level_sys_oterm_id | string | Yes | {"description": "taxonomic level, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| taxonomic_level_sys_oterm_name | string | Yes | {"description": "taxonomic level"} |
| sdt_taxon_name | string | Yes | {"description": "taxon ID", "type": "foreign_key", "references": "sdt_taxon.sdt_taxon_name"} |

### Sample Data (5 rows)

| sdt_asv_name | taxonomic_level_sys_oterm_id | taxonomic_level_sys_oterm_name | sdt_taxon_name |
|---|---|---|---|
| 4716d5b2f4559853424c60c46689a288 | ME:0000253 | Class | Omnitrophia |
| 4716d5b2f4559853424c60c46689a288 | ME:0000254 | Order | Omnitrophales |
| 4716d5b2f4559853424c60c46689a288 | ME:0000255 | Family | Omnitrophaceae |
| 4716d5b2f4559853424c60c46689a288 | ME:0000256 | Genus | Candidatus_Omnitrophus |
| 4719c3ac824b9bc042d678e923a01d4c | ME:0000351 | Taxonomic Domain | Bacteria |

---

## Table: ddt_brick0000457

**Table Description:** DDT Brick table: Brick0000457

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_asv_name | string | Yes | {"description": "ASV ID", "type": "foreign_key", "references": "sdt_asv.sdt_asv_name"} |
| sequence_sequence_type_16s_sequence | string | Yes | {"description": "sequence, Sequence Type=16S Sequence"} |

### Sample Data (5 rows)

| sdt_asv_name | sequence_sequence_type_16s_sequence |
|---|---|
| 0001d123420b59585627edf5a1292ae8 | TACGAAGGGGGCTAGCGTTGTTCGGAATCACTGGGCGTAAAGGGCGCGTAGGCGGCTTTGTAAGTCGGGGGTGAAAGCCTGTGGCTCAACCACAGAATTGCCTTCGATACTGCATGGCTTGAGACCGGAAGAGGTAAGTGGAACTGCGAGTGTAGAGGTGAAATTCGTAGATATTCGCAAGAACACCAGTGGCGAAGGCGGCTTACTGGTCCGGTTCTGACGCTGAGGCGCGAAAGCGTGGGGAGCAAACAGG |
| 00075a89460c8f6f09b52d9a8439cc3b | GACGGAGGGAGCTAGCGTTGTTCGGAATGACTGGGCGTAAAGGGCGCGTAGGCGGTTTTTTAAGTGAGGCGTGAAAGCCCTGGGCTTAACCCAGGAGGTGCGTTTCATACTGGAAGACTTGAGTGCGAGAGAGGAAAGTGGAATTCCTAGTGTAGAGGTGAAATTCGTAGATATTAGGAAGAACACCAGAGGCGAAGGCGGCTTTCTGGCTCGCAACTGACGCTGAGGCGCGAAAGCGTGGGGAGCAAACAGG |
| 000d07f2a82557601686d86686203205 | AACGTAGGGGGCGAGCGTTGTCCGGAATTACTGGGCGTAAAGGGCGTGTAGGTGGCCTGTGAAGTCGAGAGTGAAAACCTGGGGCTCAACCCCGGGCCTGCTTTCGAAACCAGCAGGCTTGAGGACAGGAGAGGGAAGCGGAATTCCCAGTGTAGCGGTGAAATGCGTAGATATTGGGAGGAACACCAGTGGCGAAAGCGGCTTTCTGGCCTGTAACTGACACTGAGGCGCGAAAGCGTGGGGAGCAAACAGG |
| 000dd512be8bcd3ee3f14a5996fa08ed | TACGTAGGGAGCTAGCGTTGTTCGGAATCACTGGGCGTAAAGGGAGTGTAGGCGGATAGATAAGTTAGGAGTGAAATGTACAGGCTTAACCTGTGACCTGCTTCTAATACTGTCAGTCTGGAGTATGGGAGAGGAAGATGGAATTCCAGGTGTAGTGGTAAAATACGTAGATATCTGGAAGAACACCAGTTGCGAAGGCGGTCTTCTGGCCCAATACTGACGCTGAGGCTCGAAAGCTAGGGGAGCAAACAGG |
| 00110df9ef266a6900a52bc9ab3b9692 | CACCAGCGCCACAAGTGGTGACCACAATTATTGGGCCTAAAGCGTCCGTAGCCGGTCTAATAAATCTTTTGTGAAATCGTTGTGCTTAACTCAACGACGTGCAGAAGAGACTGTTAGACTTGGAACCGGGAGGAGTCAGAGGTATTCCGTGGGGAGCGGTAAAATGTTATAATCCTCGGAGGACCACCTGTGGCGAAGGCGTCTGACTATAACGGTTTCGACGGTGAGGGACGAAAGCTAGGGGAGCAATCCGG |

---

## Table: ddt_brick0000458

**Table Description:** DDT Brick table: Brick0000458

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_asv_name | string | Yes | {"description": "ASV ID", "type": "foreign_key", "references": "sdt_asv.sdt_asv_name"} |
| taxonomic_level_sys_oterm_id | string | Yes | {"description": "taxonomic level, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| taxonomic_level_sys_oterm_name | string | Yes | {"description": "taxonomic level"} |
| sdt_taxon_name | string | Yes | {"description": "taxon ID", "type": "foreign_key", "references": "sdt_taxon.sdt_taxon_name"} |

### Sample Data (5 rows)

| sdt_asv_name | taxonomic_level_sys_oterm_id | taxonomic_level_sys_oterm_name | sdt_taxon_name |
|---|---|---|---|
| 0001d123420b59585627edf5a1292ae8 | ME:0000351 | Taxonomic Domain | Bacteria |
| 0001d123420b59585627edf5a1292ae8 | ME:0000252 | Phylum | Proteobacteria |
| 0001d123420b59585627edf5a1292ae8 | ME:0000253 | Class | Alphaproteobacteria |
| 0001d123420b59585627edf5a1292ae8 | ME:0000254 | Order | Rhizobiales |
| 0001d123420b59585627edf5a1292ae8 | ME:0000255 | Family | Beijerinckiaceae |

---

## Table: ddt_brick0000459

**Table Description:** DDT Brick table: Brick0000459

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_asv_name | string | Yes | {"description": "ASV ID", "type": "foreign_key", "references": "sdt_asv.sdt_asv_name"} |
| sdt_community_name | string | Yes | {"description": "community ID", "type": "foreign_key", "references": "sdt_community.sdt_community_name"} |
| count_count_unit | int | Yes | {"description": "count", "unit": "count unit"} |

### Sample Data (5 rows)

| sdt_asv_name | sdt_community_name | count_count_unit |
|---|---|---|
| 8c7237d4628046aae33addc398333dcf | SSO-L8-C10-00 | 0 |
| 8c7237d4628046aae33addc398333dcf | SSO-L9B-C3-00 | 0 |
| 8c7237d4628046aae33addc398333dcf | SSO-L9B-C5-00 | 0 |
| 8c7237d4628046aae33addc398333dcf | SSO-L9B-C7-00 | 0 |
| 8c7237d4628046aae33addc398333dcf | SSO-L9B-C10-00 | 0 |

---

## Table: ddt_brick0000460

**Table Description:** DDT Brick table: Brick0000460

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_asv_name | string | Yes | {"description": "ASV ID", "type": "foreign_key", "references": "sdt_asv.sdt_asv_name"} |
| sequence_sequence_type_16s_sequence | string | Yes | {"description": "sequence, Sequence Type=16S Sequence"} |

### Sample Data (5 rows)

| sdt_asv_name | sequence_sequence_type_16s_sequence |
|---|---|
| e9d6145e68007c14026e66332ae3ee96 | TACCAGCACCTCGAGTGGTCAGGACGTTTATTGGGCCTAAAGCATCCGTAGCCGGCTTTGCAAGTCTTCGGTTAAATCCACCTGCTCAACAGATGGGCCGCTGGAGATACTACAAAGCTAGGGAGTGGGAGAGGCAGACGGTATTCAGTGGGTAGGGGTAAAATCCTCTGATCCATTGAGGACCACCAGTGGCGAAGGCGGTCTGCCAGAACACGTTCGACGGTGAGGGATGAAAGCTGGGGGAGCAAACCGG |
| d1bf18ef6f6781169da0ad132a3068b2 | TACGTAGGGTGCAAGCGTTAATCGGAATTACTGGGCGTAAAGCGTGCGCAGGCGGTTATATAAGTCAGATGTGAAATCCCTGGGCTCAACCTAGGAACTGCATTTGAGACTGTATGGCTAGAGTGTGTCAGAGGGGGGTAGAATTCCACGTGTAGCAGTGAAATGCGTAGAGATGTGGAGGAATACCGATGGCGAAGGCAGCCCCCTGGGATAACACTGACGCTCATGCACGAAAGCGTGGGGAGCAAACAGG |
| d12833fed8673a8d32d1adc368a01538 | TACGAAGGGTGCAAGCGTTAATCGGAATTACTGGGCGTAAAGGGTGCGTAGGCGGTTGTTTAAGTCTGTCGTGAAATCCCCGGGCTCAACCTGGGAATGGCGATGGATACTGGGCAGCTAGAGTGTGTCAGAGGATGGTGGAATTCCCGGTGTAGCGGTGAAATGCGTAGAGATCGGGAGGAACATCAGTGGCGAAGGCGGCCATCTGGGACAACACTGACGCTGAAGCACGAAAGCGTGGGGAGCAAACAGG |
| 5525695dd844200b911fec57dbf4a5d6 | TACGTAGGGTGCGAGCGTTAATCGGAATTACTGGGCGTAAAGCGTGCGCAGGCGGCGACATAAGACAGATGTGAAATCCCCGGGCTCAACCTGGGAACTGCGTTTGTGACTGTGTTGCTAGAGTGTAGCAGAGGGGGGTGGAATTCCACGTGTAGCAGTGAAATGCGTAGAGATGTGGAGGAACACCGATGGCGAAGGCAGCCCCCTGGGTTAACACTGACGCTCATGCACGAAAGCGTGGGGAGCAAACAGG |
| f34cdcd73e535507d29c29b19d01f658 | TACGTAGGGTGCGAGCGTTAATCGGAATTACTGGGCGTAAAGCGTGCGCAGGCGGTTATATAAGACAGATGTGAAATCCCCGGGCTCAACCTGGGACCTGCATTTGTGACTGTATAGCTAGAGTACGGTAGAGGGGGATGGAATTCCGCGTGTAGCAGTGAAATGCGTAGATATGCGGAGGAACACCGATGGCGAAGGCAATCCCCTGGACCTGTACTGACGCTCATGCACGAAAGCGTGGGGAGCAAACAGG |

---

## Table: ddt_brick0000461

**Table Description:** DDT Brick table: Brick0000461

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_asv_name | string | Yes | {"description": "ASV ID", "type": "foreign_key", "references": "sdt_asv.sdt_asv_name"} |
| taxonomic_level_sys_oterm_id | string | Yes | {"description": "taxonomic level, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| taxonomic_level_sys_oterm_name | string | Yes | {"description": "taxonomic level"} |
| sdt_taxon_name | string | Yes | {"description": "taxon ID", "type": "foreign_key", "references": "sdt_taxon.sdt_taxon_name"} |
| confidence_confidence_unit | double | Yes | {"description": "confidence", "unit": "confidence unit"} |

### Sample Data (5 rows)

| sdt_asv_name | taxonomic_level_sys_oterm_id | taxonomic_level_sys_oterm_name | sdt_taxon_name | confidence_confidence_unit |
|---|---|---|---|---|
| e9d6145e68007c14026e66332ae3ee96 | ME:0000351 | Taxonomic Domain | Archaea | 1.0 |
| e9d6145e68007c14026e66332ae3ee96 | ME:0000252 | Phylum | Crenarchaeota | 1.0 |
| e9d6145e68007c14026e66332ae3ee96 | ME:0000253 | Class | Nitrososphaeria | 1.0 |
| e9d6145e68007c14026e66332ae3ee96 | ME:0000254 | Order | Nitrosotaleales | 1.0 |
| e9d6145e68007c14026e66332ae3ee96 | ME:0000255 | Family | Nitrosotaleaceae | 1.0 |

---

## Table: ddt_brick0000462

**Table Description:** DDT Brick table: Brick0000462

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_asv_name | string | Yes | {"description": "ASV ID", "type": "foreign_key", "references": "sdt_asv.sdt_asv_name"} |
| sdt_community_name | string | Yes | {"description": "community ID", "type": "foreign_key", "references": "sdt_community.sdt_community_name"} |
| count_count_unit | int | Yes | {"description": "count", "unit": "count unit"} |

### Sample Data (5 rows)

| sdt_asv_name | sdt_community_name | count_count_unit |
|---|---|---|
| e9d6145e68007c14026e66332ae3ee96 | L8-SZ1-20240314-F01 | 214 |
| e9d6145e68007c14026e66332ae3ee96 | L8-SZ1-20240314-F8 | 8 |
| e9d6145e68007c14026e66332ae3ee96 | L8-SZ2-20240320-F01 | 60 |
| e9d6145e68007c14026e66332ae3ee96 | L8-SZ2-20240320-F8 | 1009 |
| e9d6145e68007c14026e66332ae3ee96 | M5-SZ1-20240318-F01 | 303 |

---

## Table: ddt_brick0000477

**Table Description:** DDT Brick table: Brick0000477

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_asv_name | string | Yes | {"description": "ASV ID", "type": "foreign_key", "references": "sdt_asv.sdt_asv_name"} |
| sequence_sequence_type_16s_sequence | string | Yes | {"description": "sequence, Sequence Type=16S Sequence"} |

### Sample Data (5 rows)

| sdt_asv_name | sequence_sequence_type_16s_sequence |
|---|---|
| 000b67fd460465b2285c0932b352aee2 | TACAGAGGGTGCAAGCGTTAATCGGAATTACTGGGCGTAAAGAGCACGTAGGTGGTTAGGTGAGTCAGATGTGAAATCCCCGGGCTTAACCTGGGAACTGCATTTGATACTGCCTGGCTAGAGTTTGGTAGAGGGAAGTGGAATTCCACATGTAGCGGTGAAATGCGTAGAGATGTGGAGGAACACCAGTGGCGAAGGCGGCTTCCTGGACCAAAACTGACACTGAGGTGCGAAAGCGTGGGTAGCAAACAGG |
| 0016e5c5e6aba81612fdd8d45d47e671 | AACGTAGGAGGCAAGCGTTATCCGGATTTACTGGGCGTAAAGGGCGTGCAGGTGGCTGTGTAAGTGGTGCGTGAAAGCGCTCGGCTCAACCGGGCGAGGGCGTGCCAAACTGCACAACTAGAAACAGACAGAGGCAAGTGGAATTCGGGGTGTAGTGGTGAAATGCGTAGAGATCCCGAGGAACTCCTGTGGCGAAGGCGACTTGCTGGGTCTGGTTTGACACTCAGACGCGAAAGCATGGGGAGCGAACGGG |
| 001f37e240ec76cca0576c56ac384c2b | GACAGAGGGTGCAAACGTTGTTCGGAATTACTGGGCGTAAAGCGCGTGTAGGCGGCGATGCAAGTCGGATGTGAAAGCCCTCGGCTCAACCCAGAGAGGCCACCCGATACTGCCGTGACTGGAGTGCGGTAGGGGAGTGGGGAATTCCTGGTGTAGCGGTGAAATGCGCAGATATCAGGAGGAACACCAGTGGCGAAGGCGCCACTCTGGGCCGTAACTGACGCTGAGGCACGAAGGCCAGGGGAGCAAACGGG |
| 0023af8d2bea3fe12ceb48d32a172e20 | TACGAAGGCCCCAAGCGTTATCCGGATTTATTGGGCGTAAAGCGTGCGTAGGAGGTTTAGTAAGTCTGTTGTTAAATTTCGCTGCTTAACGGCGGAGCCGCAACAGATACTACTAGACTAGAGTGTGTGAGAGGCTAATAGAACTCACGGTGTAGGGGTGAAATCCGTTGATATCGTGGGGAATACCAAAGGCGAAGGCATTTAGCTAGCGCATTACTGACTCTAAGGCACGAAAGCGTGGGGAGCAAAAAGG |
| 002a1665d74eb41002fde4fa32f51d93 | TACAGAGGGTGCGAGCGTTAATCGGAATTACTGGGCGTAAAGCGCACGTAGGCGGCTTCGTAAGTCGGATGTGAAATCCCCGGGCTCAACCTGGGAACTGCATTCGAGACTGCGATGCTCGAGTATGGGAGAGGACAGCGGAATTCCGGGTGTAGCGGTGAAATGCGTAGATATCCGGAGGAACATCAGTGGCGAAGGCGGCTGTCTGGCCCAATACTGACGCTCAGGTGCGAAAGCGTGGGGAGCAAACAGG |

---

## Table: ddt_brick0000478

**Table Description:** DDT Brick table: Brick0000478

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_asv_name | string | Yes | {"description": "ASV ID", "type": "foreign_key", "references": "sdt_asv.sdt_asv_name"} |
| taxonomic_level_sys_oterm_id | string | Yes | {"description": "taxonomic level, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| taxonomic_level_sys_oterm_name | string | Yes | {"description": "taxonomic level"} |
| sdt_taxon_name | string | Yes | {"description": "taxon ID", "type": "foreign_key", "references": "sdt_taxon.sdt_taxon_name"} |
| confidence_confidence_unit | double | Yes | {"description": "confidence", "unit": "confidence unit"} |

### Sample Data (5 rows)

| sdt_asv_name | taxonomic_level_sys_oterm_id | taxonomic_level_sys_oterm_name | sdt_taxon_name | confidence_confidence_unit |
|---|---|---|---|---|
| 000b67fd460465b2285c0932b352aee2 | ME:0000351 | Taxonomic Domain | Bacteria | 1.0 |
| 000b67fd460465b2285c0932b352aee2 | ME:0000252 | Phylum | Proteobacteria | 1.0 |
| 000b67fd460465b2285c0932b352aee2 | ME:0000253 | Class | Gammaproteobacteria | 1.0 |
| 000b67fd460465b2285c0932b352aee2 | ME:0000254 | Order | Acidiferrobacterales | 0.9 |
| 000b67fd460465b2285c0932b352aee2 | ME:0000255 | Family | Acidiferrobacteraceae | 0.9 |

---

## Table: ddt_brick0000479

**Table Description:** DDT Brick table: Brick0000479

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_asv_name | string | Yes | {"description": "ASV ID", "type": "foreign_key", "references": "sdt_asv.sdt_asv_name"} |
| sdt_community_name | string | Yes | {"description": "community ID", "type": "foreign_key", "references": "sdt_community.sdt_community_name"} |
| count_count_unit | int | Yes | {"description": "count", "unit": "count unit"} |

### Sample Data (5 rows)

| sdt_asv_name | sdt_community_name | count_count_unit |
|---|---|---|
| 97d95ee93b0d992e190508d16a66eb65 | M6-SZ1-20240918-F01 | 0 |
| 97d95ee93b0d992e190508d16a66eb65 | M6-SZ2-20240918-F8 | 0 |
| 97d95ee93b0d992e190508d16a66eb65 | M6-SZ2-20240918-F01 | 0 |
| 97d95ee93b0d992e190508d16a66eb65 | L7-SZ1-20240918-F8 | 0 |
| 97d95ee93b0d992e190508d16a66eb65 | L7-SZ1-20240918-F01 | 0 |

---

## Table: sys_oterm

**Table Description:** Ontology terms used in CORAL

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sys_oterm_id | string | Yes | {"description": "Term identifier, aka CURIE (Primary key)", "type": "primary_key"} |
| parent_sys_oterm_id | string | Yes | {"description": "Parent term identifier", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| sys_oterm_ontology | string | Yes | {"description": "Ontology that each term is from"} |
| sys_oterm_name | string | Yes | {"description": "Term name"} |
| sys_oterm_synonyms | array<string> | Yes | {"description": "List of synonyms for a term"} |
| sys_oterm_definition | string | Yes | {"description": "Term definition"} |
| sys_oterm_links | array<string> | Yes | {"description": "Indicates that values are links to other tables (Ref) or ontological terms (ORef)"} |
| sys_oterm_properties | map<string,string> | Yes | {"description": "Semicolon-separated map of properties to values for terms that are CORAL microtypes, including scalar data_type, is_valid_data_variable, is_valid_dimension, is_valid_data_variable, is_valid_dimension_variable, is_valid_property, valid_units, and valid_units_parent"} |

### Sample Data (5 rows)

| sys_oterm_id | parent_sys_oterm_id | sys_oterm_ontology | sys_oterm_name | sys_oterm_synonyms | sys_oterm_definition | sys_oterm_links | sys_oterm_properties |
|---|---|---|---|---|---|---|---|
| ME:0000000 | NULL | context_measurement_ontology | term | [] | Root of all ontological terms. | NULL | NULL |
| ME:0000001 | ME:0000000 | context_measurement_ontology | context | [] | Root of all Context and Measurement Terms. | ["ORef:ME:0000001"] | {"data_type": "oterm_ref", "is_hidden": "true", "is_microtype": "true", "is_valid_data_variable": "true", "is_valid_property": "true"} |
| ME:0000002 | ME:0000001 | context_measurement_ontology | experimental context | [] | Context describing experimental design. | ["ORef:ME:0000002"] | {"data_type": "oterm_ref", "is_microtype": "true", "is_valid_data_variable": "true", "is_valid_property": "true"} |
| ME:0000003 | ME:0000002 | context_measurement_ontology | series type | [] | Context describing the purpose of a series. | ["ORef:ME:0000003"] | {"data_type": "oterm_ref", "is_microtype": "true", "is_valid_data_variable": "true", "is_valid_property": "true"} |
| ME:0000004 | ME:0000003 | context_measurement_ontology | time series | [] | A time series, in which a series of measurements was taken at different timepoints. | NULL | {"data_type": "float", "is_microtype": "true", "is_valid_data_variable": "true", "is_valid_dimension": "true", "is_valid_dimension_variable": "true", "is_valid_property": "true", "valid_units_parent": "UO:0000003"} |

---

## Table: sys_process_input

**Table Description:** Process Inputs

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sys_process_id | string | Yes | {"description": "Foreign key to sys_process", "type": "foreign_key", "references": "sys_process.sys_process_id"} |
| sdt_assembly_id | string | Yes | {"description": "Input object from sdt_assembly", "type": "foreign_key", "references": "sdt_assembly.sdt_assembly_id"} |
| sdt_bin_id | string | Yes | {"description": "Input object from sdt_bin", "type": "foreign_key", "references": "sdt_bin.sdt_bin_id"} |
| sdt_community_id | string | Yes | {"description": "Input object from sdt_community", "type": "foreign_key", "references": "sdt_community.sdt_community_id"} |
| sdt_genome_id | string | Yes | {"description": "Input object from sdt_genome", "type": "foreign_key", "references": "sdt_genome.sdt_genome_id"} |
| sdt_location_id | string | Yes | {"description": "Input object from sdt_location", "type": "foreign_key", "references": "sdt_location.sdt_location_id"} |
| sdt_reads_id | string | Yes | {"description": "Input object from sdt_reads", "type": "foreign_key", "references": "sdt_reads.sdt_reads_id"} |
| sdt_sample_id | string | Yes | {"description": "Input object from sdt_sample", "type": "foreign_key", "references": "sdt_sample.sdt_sample_id"} |
| sdt_strain_id | string | Yes | {"description": "Input object from sdt_strain", "type": "foreign_key", "references": "sdt_strain.sdt_strain_id"} |
| sdt_tnseq_library_id | string | Yes | {"description": "Input object from sdt_tnseq_library", "type": "foreign_key", "references": "sdt_tnseq_library.sdt_tnseq_library_id"} |

### Sample Data (5 rows)

| sys_process_id | sdt_assembly_id | sdt_bin_id | sdt_community_id | sdt_genome_id | sdt_location_id | sdt_reads_id | sdt_sample_id | sdt_strain_id | sdt_tnseq_library_id |
|---|---|---|---|---|---|---|---|---|---|
| Process0009812 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | Strain0001421 | NULL |
| Process0009813 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | Strain0001422 | NULL |
| Process0009814 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | Strain0001423 | NULL |
| Process0009815 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | Strain0001424 | NULL |
| Process0009816 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | Strain0001425 | NULL |

---

## Table: sys_process_output

**Table Description:** Process Outputs

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sys_process_id | string | Yes | {"description": "Foreign key to sys_process", "type": "foreign_key", "references": "sys_process.sys_process_id"} |
| ddt_ndarray_id | string | Yes | {"description": "Output object from ddt_ndarray", "type": "foreign_key", "references": "ddt_ndarray.ddt_ndarray_id"} |
| sdt_assembly_id | string | Yes | {"description": "Output object from sdt_assembly", "type": "foreign_key", "references": "sdt_assembly.sdt_assembly_id"} |
| sdt_bin_id | string | Yes | {"description": "Output object from sdt_bin", "type": "foreign_key", "references": "sdt_bin.sdt_bin_id"} |
| sdt_community_id | string | Yes | {"description": "Output object from sdt_community", "type": "foreign_key", "references": "sdt_community.sdt_community_id"} |
| sdt_dubseq_library_id | string | Yes | {"description": "Output object from sdt_dubseq_library", "type": "foreign_key", "references": "sdt_dubseq_library.sdt_dubseq_library_id"} |
| sdt_genome_id | string | Yes | {"description": "Output object from sdt_genome", "type": "foreign_key", "references": "sdt_genome.sdt_genome_id"} |
| sdt_image_id | string | Yes | {"description": "Output object from sdt_image", "type": "foreign_key", "references": "sdt_image.sdt_image_id"} |
| sdt_reads_id | string | Yes | {"description": "Output object from sdt_reads", "type": "foreign_key", "references": "sdt_reads.sdt_reads_id"} |
| sdt_sample_id | string | Yes | {"description": "Output object from sdt_sample", "type": "foreign_key", "references": "sdt_sample.sdt_sample_id"} |
| sdt_strain_id | string | Yes | {"description": "Output object from sdt_strain", "type": "foreign_key", "references": "sdt_strain.sdt_strain_id"} |
| sdt_tnseq_library_id | string | Yes | {"description": "Output object from sdt_tnseq_library", "type": "foreign_key", "references": "sdt_tnseq_library.sdt_tnseq_library_id"} |

### Sample Data (5 rows)

| sys_process_id | ddt_ndarray_id | sdt_assembly_id | sdt_bin_id | sdt_community_id | sdt_dubseq_library_id | sdt_genome_id | sdt_image_id | sdt_reads_id | sdt_sample_id | sdt_strain_id | sdt_tnseq_library_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Process0201007 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | Reads0015944 | NULL | NULL | NULL |
| Process0201008 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | Reads0015945 | NULL | NULL | NULL |
| Process0201009 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | Reads0015946 | NULL | NULL | NULL |
| Process0201010 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | Reads0015947 | NULL | NULL | NULL |
| Process0201011 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | Reads0015948 | NULL | NULL | NULL |

---

## Table: ddt_brick0000476

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_asv_name | string | Yes | {"description": "ASV ID", "type": "foreign_key", "references": "sdt_asv.sdt_asv_name"} |
| sdt_community_name | string | Yes | {"description": "community ID", "type": "foreign_key", "references": "sdt_community.sdt_community_name"} |
| replicate_series_count_unit | int | Yes | {"description": "replicate series", "unit": "count unit"} |
| count_count_unit | int | Yes | {"description": "count", "unit": "count unit"} |

### Sample Data (5 rows)

| sdt_asv_name | sdt_community_name | replicate_series_count_unit | count_count_unit |
|---|---|---|---|
| 1b885550c8fe9c5305ef38efd64f8762 | GW621-21-12-17-12 0.2 micron filter | 1 | 0 |
| 1b885550c8fe9c5305ef38efd64f8762 | GW621-21-12-17-12 10 micron filter | 1 | 0 |
| 1b885550c8fe9c5305ef38efd64f8762 | GW631-98-12-11-12 0.2 micron filter | 1 | 0 |
| 1b885550c8fe9c5305ef38efd64f8762 | GW631-98-12-11-12 10 micron filter | 1 | 0 |
| 1b885550c8fe9c5305ef38efd64f8762 | GW636-32-1-28-13 0.2 micron filter | 1 | 0 |

---

## Table: sys_process

**Table Description:** CDM table for CORAL type `Process`

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sys_process_id | string | Yes | {"description": "Unique identifier for each process record (Primary key)", "type": "primary_key"} |
| process_sys_oterm_id | string | Yes | {"description": "Reference to the specific process type used to generate the outputs, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| process_sys_oterm_name | string | Yes | {"description": "Reference to the specific process type used to generate the outputs"} |
| person_sys_oterm_id | string | Yes | {"description": "Reference to the person or lab that performed the process, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| person_sys_oterm_name | string | Yes | {"description": "Reference to the person or lab that performed the process"} |
| campaign_sys_oterm_id | string | Yes | {"description": "Reference to the ENIGMA campaign under which the data were generated, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| campaign_sys_oterm_name | string | Yes | {"description": "Reference to the ENIGMA campaign under which the data were generated"} |
| sdt_protocol_name | string | Yes | {"description": "Protocol used in this process (foreign key to Protocol.name)", "type": "foreign_key", "references": "sdt_protocol.sdt_protocol_name"} |
| date_start | string | Yes | {"description": "YYYY[-MM[-DD]]"} |
| date_end | string | Yes | {"description": "YYYY[-MM[-DD]]"} |
| input_objects | array<string> | Yes | {"description": "List of references to data that were input to this process"} |
| output_objects | array<string> | Yes | {"description": "List of references to data that were produced by this process"} |

### Sample Data (5 rows)

| sys_process_id | process_sys_oterm_id | process_sys_oterm_name | person_sys_oterm_id | person_sys_oterm_name | campaign_sys_oterm_id | campaign_sys_oterm_name | sdt_protocol_name | date_start | date_end | input_objects | output_objects |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Process0000001 | PROCESS:0000006 | Assay Growth | ENIGMA:0000032 | Michael Thorgersen | ENIGMA:0000013 | Metal Metabolism | NULL | NULL | NULL | ["Strain:Strain0000672"] | ["Brick-0000019:Brick0000003"] |
| Process0000002 | PROCESS:0000006 | Assay Growth | ENIGMA:0000032 | Michael Thorgersen | ENIGMA:0000013 | Metal Metabolism | NULL | NULL | NULL | ["Strain:Strain0000669"] | ["Brick-0000019:Brick0000004"] |
| Process0000003 | PROCESS:0000006 | Assay Growth | ENIGMA:0000032 | Michael Thorgersen | ENIGMA:0000013 | Metal Metabolism | NULL | NULL | NULL | ["Strain:Strain0000672"] | ["Brick-0000019:Brick0000005"] |
| Process0000004 | PROCESS:0000006 | Assay Growth | ENIGMA:0000032 | Michael Thorgersen | ENIGMA:0000013 | Metal Metabolism | NULL | NULL | NULL | ["Strain:Strain0000666"] | ["Brick-0000019:Brick0000005"] |
| Process0000005 | PROCESS:0000006 | Assay Growth | ENIGMA:0000032 | Michael Thorgersen | ENIGMA:0000013 | Metal Metabolism | NULL | NULL | NULL | ["Strain:Strain0000668"] | ["Brick-0000019:Brick0000005"] |

---

## Table: sdt_enigma

**Table Description:** CDM table for CORAL type `ENIGMA`

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_enigma_id | string | Yes | {"description": "Primary key for table `sdt_enigma`", "type": "primary_key"} |

### Sample Data (5 rows)

| sdt_enigma_id |
|---|
| NULL |

---

## Table: sdt_location

**Table Description:** CDM table for CORAL type `Location`

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_location_id | string | Yes | {"description": "Unique identifier for the location (Primary key)", "type": "primary_key"} |
| sdt_location_name | string | Yes | {"description": "Unique name of the location", "type": "unique_key"} |
| latitude_degree | double | Yes | {"description": "Latitude of the location in decimal degrees", "unit": "degree"} |
| longitude_degree | double | Yes | {"description": "Longitude of the location in decimal degrees", "unit": "degree"} |
| continent_sys_oterm_id | string | Yes | {"description": "Continent where the location is situated, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| continent_sys_oterm_name | string | Yes | {"description": "Continent where the location is situated"} |
| country_sys_oterm_id | string | Yes | {"description": "Country of the location, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| country_sys_oterm_name | string | Yes | {"description": "Country of the location"} |
| region | string | Yes | {"description": "Specific local region name(s)"} |
| biome_sys_oterm_id | string | Yes | {"description": "Biome classification of the location, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| biome_sys_oterm_name | string | Yes | {"description": "Biome classification of the location"} |
| feature_sys_oterm_id | string | Yes | {"description": "Environmental or geographic feature at the location, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| feature_sys_oterm_name | string | Yes | {"description": "Environmental or geographic feature at the location"} |

### Sample Data (5 rows)

| sdt_location_id | sdt_location_name | latitude_degree | longitude_degree | continent_sys_oterm_id | continent_sys_oterm_name | country_sys_oterm_id | country_sys_oterm_name | region | biome_sys_oterm_id | biome_sys_oterm_name | feature_sys_oterm_id | feature_sys_oterm_name |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Location0000151 | GW-220 | 35.993381 | -84.236976 | CONTINENT:0000007 | North America | COUNTRY:0000263 | USA | Tennessee (TN), Oak Ridge Reservation (ORR), Area Y-12 East, Cluster 50 | ENVO:01000221 | temperate woodland biome | ENVO:01000002 | water well |
| Location0000152 | GW-750 | 35.994376 | -84.235312 | CONTINENT:0000007 | North America | COUNTRY:0000263 | USA | Tennessee (TN), Oak Ridge Reservation (ORR), Area Y-12 East, Cluster 28 | ENVO:01000221 | temperate woodland biome | ENVO:01000002 | water well |
| Location0000153 | GW-800 | 35.968949 | -84.28178 | CONTINENT:0000007 | North America | COUNTRY:0000263 | USA | Tennessee (TN), Oak Ridge Reservation (ORR), Area Y-12 West, Cluster 70 | ENVO:01000221 | temperate woodland biome | ENVO:01000002 | water well |
| Location0000154 | GW-737 | 35.97079 | -84.280741 | CONTINENT:0000007 | North America | COUNTRY:0000263 | USA | Tennessee (TN), Oak Ridge Reservation (ORR), Area Y-12 West, Cluster 64 | ENVO:01000221 | temperate woodland biome | ENVO:01000002 | water well |
| Location0000155 | GW-704 | 35.96353 | -84.290837 | CONTINENT:0000007 | North America | COUNTRY:0000263 | USA | Tennessee (TN), Oak Ridge Reservation (ORR), Area NT3-NT8, Cluster 5 | ENVO:01000221 | temperate woodland biome | ENVO:01000002 | water well |

---

## Table: sdt_sample

**Table Description:** CDM table for CORAL type `Sample`

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_sample_id | string | Yes | {"description": "Unique identifier for the sample (Primary key)", "type": "primary_key"} |
| sdt_sample_name | string | Yes | {"description": "Unique name of the sample", "type": "unique_key"} |
| sdt_location_name | string | Yes | {"description": "Location where the sample was collected (Foreign key)", "type": "foreign_key", "references": "sdt_location.sdt_location_name"} |
| depth_meter | double | Yes | {"description": "For below-ground samples, the average distance below ground level in meters where the sample was taken", "unit": "meter"} |
| elevation_meter | double | Yes | {"description": "For above-ground samples, the average distance above ground level in meters where the sample was taken", "unit": "meter"} |
| date | string | Yes | {"description": "YYYY[-MM[-DD]]"} |
| time | string | Yes | {"description": "HH[:MM[:SS]] [AM|PM]"} |
| timezone | string | Yes | {"description": "ISO8601 compliant format, ie. UTC-7"} |
| material_sys_oterm_id | string | Yes | {"description": "Material type of the sample, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| material_sys_oterm_name | string | Yes | {"description": "Material type of the sample"} |
| env_package_sys_oterm_id | string | Yes | {"description": "MIxS environmental package classification of the sample, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| env_package_sys_oterm_name | string | Yes | {"description": "MIxS environmental package classification of the sample"} |
| sdt_sample_description | string | Yes | {"description": "Free-form description or notes about the sample"} |

### Sample Data (5 rows)

| sdt_sample_id | sdt_sample_name | sdt_location_name | depth_meter | elevation_meter | date | time | timezone | material_sys_oterm_id | material_sys_oterm_name | env_package_sys_oterm_id | env_package_sys_oterm_name | sdt_sample_description |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Sample0000001 | EU02-D01 | EU02 | 5.401056 | NULL | 2019-07-29 | 6:59 | UTC-04 | ENVO:00002041 | ground water | MIxS:0000017 | water | 1 L purged |
| Sample0000002 | EU03-D01 | EU03 | 4.605528 | NULL | 2019-07-29 | 8:09 | UTC-04 | ENVO:00002041 | ground water | MIxS:0000017 | water | 1 L purged |
| Sample0000003 | ED04-D01 | ED04 | 4.7625 | NULL | 2019-07-29 | 8:58 | UTC-04 | ENVO:00002041 | ground water | MIxS:0000017 | water | 1 L purged |
| Sample0000004 | EU05-D01 | EU05 | 4.639056 | NULL | 2019-07-29 | 6:43 | UTC-04 | ENVO:00002041 | ground water | MIxS:0000017 | water | 3 L purged, 5 L filtered |
| Sample0000005 | ED06-D01 | ED06 | 5.4483 | NULL | 2019-07-29 | 8:41 | UTC-04 | ENVO:00002041 | ground water | MIxS:0000017 | water | 1 L purged |

---

## Table: sdt_taxon

**Table Description:** CDM table for CORAL type `Taxon`

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_taxon_id | string | Yes | {"description": "Unique identifier for a taxon record (Primary key)", "type": "primary_key"} |
| sdt_taxon_name | string | Yes | {"description": "Unique taxon name, typically the scientific name", "type": "unique_key"} |
| ncbi_taxid | string | Yes | {"description": "NCBI taxonomy identifier for the taxon, if available"} |

### Sample Data (5 rows)

| sdt_taxon_id | sdt_taxon_name | ncbi_taxid |
|---|---|---|
| Taxon0000842 | Cytophagales | NCBITaxon:768507 |
| Taxon0000843 | Cytophaga | NCBITaxon:978 |
| Taxon0000844 | Cytophagia | NCBITaxon:768503 |
| Taxon0000845 | Dactylosporangium | NCBITaxon:35753 |
| Taxon0000846 | Dadabacteriales | NULL |

---

## Table: sdt_asv

**Table Description:** CDM table for CORAL type `OTU`

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_asv_id | string | Yes | {"description": "Unique identifier for each ASV/OTU (Primary key)", "type": "primary_key"} |
| sdt_asv_name | string | Yes | {"description": "Unique name assigned to the ASV/OTU, usually md5sum", "type": "unique_key"} |

### Sample Data (5 rows)

| sdt_asv_id | sdt_asv_name |
|---|---|
| ASV0106523 | 2e56bda85383e9058b038f24e7266e0f |
| ASV0106524 | 2e57aec929df910d3c2b55b86bf9ef1d |
| ASV0106525 | 2e59dc23020840844b142289a792c14c |
| ASV0106526 | 2e59e241bdb04cf8408be0d5c48eee12 |
| ASV0106527 | 2e5b1764668375892d88df73711f8033 |

---

## Table: sdt_condition

**Table Description:** CDM table for CORAL type `Condition`

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_condition_id | string | Yes | {"description": "Unique identifier for the condition (Primary key)", "type": "primary_key"} |
| sdt_condition_name | string | Yes | {"description": "Unique text name describing the condition", "type": "unique_key"} |

### Sample Data (5 rows)

| sdt_condition_id | sdt_condition_name |
|---|---|
| Condition0000785 | Anaerobic = 0; media addition = fulvic acid; media name = Basal Media; media name = Bulk groundwater BOTTOM; media name = TSA; temperature = 30.0 (degree Celsius) |
| Condition0000786 | Anaerobic = 0; media name = Casamino Acids; media name = R2A, concentration = 10.0 (fold dilution); temperature = 30.0 (degree Celsius) |
| Condition0000787 | Anaerobic = 1; media addition = sodium pyruvate, concentration = 73.3 (mM); media addition = yeast extract, concentration = 0.1 (mass volume percentage); media name = MO Basal Medium; temperature = 18.0 (degree Celsius) |
| Condition0000788 | Eugon Broth |
| Condition0000789 | Anaerobic = 1; media addition = fumarate; media addition = lactate; media addition = sulfate, concentration = 20.0 (mM); media name = Metal Mixture; pH = 5.5 (pH) |

---

## Table: sdt_strain

**Table Description:** CDM table for CORAL type `Strain`

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_strain_id | string | Yes | {"description": "Unique identifier for each strain (Primary key)", "type": "primary_key"} |
| sdt_strain_name | string | Yes | {"description": "Unique name of the strain", "type": "unique_key"} |
| sdt_strain_description | string | Yes | {"description": "Free-text description of the strain"} |
| sdt_genome_name | string | Yes | {"description": "Genome object for sequenced, wild type strains", "type": "foreign_key", "references": "sdt_genome.sdt_genome_name"} |
| derived_from_sdt_strain_name | string | Yes | {"description": "Name of the parent strain from which this strain was derived, if created by genetic modification or similar process", "type": "foreign_key", "references": "sdt_strain.sdt_strain_name"} |
| sdt_gene_names_changed | array<string> | Yes | {"description": "List of gene identifiers that have been altered in this strain, if created by genetic modification, if known", "type": "foreign_key", "references": "sdt_gene.sdt_gene_name"} |

### Sample Data (5 rows)

| sdt_strain_id | sdt_strain_name | sdt_strain_description | sdt_genome_name | derived_from_sdt_strain_name | sdt_gene_names_changed |
|---|---|---|---|---|---|
| Strain0000789 | EB106-05-01-XG146 | NULL | NULL | NULL | [] |
| Strain0000790 | EB106-05-01-XG147 | NULL | NULL | NULL | [] |
| Strain0000791 | EB106-07-01-XG149 | NULL | NULL | NULL | [] |
| Strain0000792 | EB106-07-01-XG150 | NULL | NULL | NULL | [] |
| Strain0000793 | EB106-08-01-XG153 | NULL | NULL | NULL | [] |

---

## Table: sdt_community

**Table Description:** CDM table for CORAL type `Community`

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_community_id | string | Yes | {"description": "Unique internal identifier for the community (Primary key)", "type": "primary_key"} |
| sdt_community_name | string | Yes | {"description": "Unique name of the community", "type": "unique_key"} |
| community_type_sys_oterm_id | string | Yes | {"description": "Type of community, e.g., isolate or enrichment, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| community_type_sys_oterm_name | string | Yes | {"description": "Type of community, e.g., isolate or enrichment"} |
| sdt_sample_name | string | Yes | {"description": "Reference to the Sample from which the community was obtained.", "type": "foreign_key", "references": "sdt_sample.sdt_sample_name"} |
| parent_sdt_community_name | string | Yes | {"description": "Reference to the name of a parent community, establishing hierarchical relationships", "type": "foreign_key", "references": "sdt_community.sdt_community_name"} |
| sdt_condition_name | string | Yes | {"description": "Reference to the experimental or environmental condition associated with the community", "type": "foreign_key", "references": "sdt_condition.sdt_condition_name"} |
| defined_sdt_strain_names | array<string> | Yes | {"description": "List of strains that comprise the community, if the community is defined", "type": "foreign_key", "references": "sdt_strain.sdt_strain_name"} |
| sdt_community_description | string | Yes | {"description": "Free-text field providing additional details or notes about the community"} |

### Sample Data (5 rows)

| sdt_community_id | sdt_community_name | community_type_sys_oterm_id | community_type_sys_oterm_name | sdt_sample_name | parent_sdt_community_name | sdt_condition_name | defined_sdt_strain_names | sdt_community_description |
|---|---|---|---|---|---|---|---|---|
| Community0000001 | EB106-02-01 BONCAT community | ME:0000237 | Active Fraction | EB106-02-01 | EB106-02-01 | NULL | [] | NULL |
| Community0000002 | EB106-02-02 BONCAT community | ME:0000237 | Active Fraction | EB106-02-02 | EB106-02-02 | NULL | [] | NULL |
| Community0000003 | EB106-02-03 BONCAT community | ME:0000237 | Active Fraction | EB106-02-03 | EB106-02-03 | NULL | [] | NULL |
| Community0000004 | EB106-03-01 BONCAT community | ME:0000237 | Active Fraction | EB106-03-01 | EB106-03-01 | NULL | [] | NULL |
| Community0000005 | EB106-03-02 BONCAT community | ME:0000237 | Active Fraction | EB106-03-02 | EB106-03-02 | NULL | [] | NULL |

---

## Table: sdt_reads

**Table Description:** CDM table for CORAL type `Reads`

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_reads_id | string | Yes | {"description": "Unique identifier for each reads dataset (Primary key)", "type": "primary_key"} |
| sdt_reads_name | string | Yes | {"description": "Unique name for the reads", "type": "unique_key"} |
| read_count_count_unit | int | Yes | {"description": "Number of reads", "unit": "count unit"} |
| read_type_sys_oterm_id | string | Yes | {"description": "Category of reads (e.g., single-end, paired-end), ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| read_type_sys_oterm_name | string | Yes | {"description": "Category of reads (e.g., single-end, paired-end)"} |
| sequencing_technology_sys_oterm_id | string | Yes | {"description": "Sequencing technology used (e.g., Illumina), ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| sequencing_technology_sys_oterm_name | string | Yes | {"description": "Sequencing technology used (e.g., Illumina)"} |
| link | string | Yes | {"description": "Link to the reads file (e.g., fastq)"} |

### Sample Data (5 rows)

| sdt_reads_id | sdt_reads_name | read_count_count_unit | read_type_sys_oterm_id | read_type_sys_oterm_name | sequencing_technology_sys_oterm_id | sequencing_technology_sys_oterm_name | link |
|---|---|---|---|---|---|---|---|
| Reads0017831 | GW823-FHT01F02/reads/illumina/GW823-FHT01F02_2020-03-23_raw_unpaired_R2.fastq.gz | 1202663 | ME:0000113 | Paired End Read | ME:0000117 | Illumina | enigma-data-repository/genome_processing/GW823-FHT01F02/reads/illumina/GW823-FHT01F02_2020-03-23_raw_unpaired_R2.fastq.gz |
| Reads0017832 | GW821-FHT01H02/reads/illumina/GW821-FHT01H02_2020-03-23_raw_unpaired_R1.fastq.gz | 31423 | ME:0000113 | Paired End Read | ME:0000117 | Illumina | enigma-data-repository/genome_processing/GW821-FHT01H02/reads/illumina/GW821-FHT01H02_2020-03-23_raw_unpaired_R1.fastq.gz |
| Reads0017833 | GW821-FHT01H02/reads/illumina/GW821-FHT01H02_2020-03-23_raw_unpaired_R2.fastq.gz | 31423 | ME:0000113 | Paired End Read | ME:0000117 | Illumina | enigma-data-repository/genome_processing/GW821-FHT01H02/reads/illumina/GW821-FHT01H02_2020-03-23_raw_unpaired_R2.fastq.gz |
| Reads0017834 | GW821-FHT05G01/reads/illumina/GW821-FHT05G01_2020-03-23_raw_unpaired_R1.fastq.gz | 395152 | ME:0000113 | Paired End Read | ME:0000117 | Illumina | enigma-data-repository/genome_processing/GW821-FHT05G01/reads/illumina/GW821-FHT05G01_2020-03-23_raw_unpaired_R1.fastq.gz |
| Reads0017835 | GW821-FHT05G01/reads/illumina/GW821-FHT05G01_2020-03-23_raw_unpaired_R2.fastq.gz | 395152 | ME:0000113 | Paired End Read | ME:0000117 | Illumina | enigma-data-repository/genome_processing/GW821-FHT05G01/reads/illumina/GW821-FHT05G01_2020-03-23_raw_unpaired_R2.fastq.gz |

---

## Table: sdt_assembly

**Table Description:** CDM table for CORAL type `Assembly`

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_assembly_id | string | Yes | {"description": "Unique text identifier for the assembly (Primary key)", "type": "primary_key"} |
| sdt_assembly_name | string | Yes | {"description": "Unique name for the assembly", "type": "unique_key"} |
| sdt_strain_name | string | Yes | {"description": "Strain name from which the assembly was derived (foreign key to Strain.name).", "type": "foreign_key", "references": "sdt_strain.sdt_strain_name"} |
| n_contigs_count_unit | int | Yes | {"description": "Number of contigs in the assembly", "unit": "count unit"} |
| link | string | Yes | {"description": "Reference to the actual assembly data"} |

### Sample Data (5 rows)

| sdt_assembly_id | sdt_assembly_name | sdt_strain_name | n_contigs_count_unit | link |
|---|---|---|---|---|
| Assembly0002571 | 154265/GW821-FHT12B10.contigs | GW821-FHT12B10 | 6 | https://narrative.kbase.us/#dataview/154265/GW821-FHT12B10.contigs |
| Assembly0002572 | 154265/FW101-FHT12H10.contigs | FW101-FHT12H10 | 17 | https://narrative.kbase.us/#dataview/154265/FW101-FHT12H10.contigs |
| Assembly0002573 | 154265/GW821-FHT09A05.contigs | GW821-FHT09A05 | 72 | https://narrative.kbase.us/#dataview/154265/GW821-FHT09A05.contigs |
| Assembly0002574 | 154265/GW821-FHT10C11.contigs | GW821-FHT10C11 | 22 | https://narrative.kbase.us/#dataview/154265/GW821-FHT10C11.contigs |
| Assembly0002575 | 154265/GW821-FHT12F11.contigs | GW821-FHT12F11 | 16 | https://narrative.kbase.us/#dataview/154265/GW821-FHT12F11.contigs |

---

## Table: sdt_genome

**Table Description:** CDM table for CORAL type `Genome`

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_genome_id | string | Yes | {"description": "Unique identifier for the genome (Primary key)", "type": "primary_key"} |
| sdt_genome_name | string | Yes | {"description": "Unique name of the genome", "type": "unique_key"} |
| sdt_strain_name | string | Yes | {"description": "Name of the microbial strain associated with the genome (foreign key)", "type": "foreign_key", "references": "sdt_strain.sdt_strain_name"} |
| n_contigs_count_unit | int | Yes | {"description": "Number of contigs in the genome assembly", "unit": "count unit"} |
| n_features_count_unit | int | Yes | {"description": "Number of annotated features (e.g., genes) in the genome", "unit": "count unit"} |
| link | string | Yes | {"description": "Link to where the genome itself is actually stored"} |

### Sample Data (5 rows)

| sdt_genome_id | sdt_genome_name | sdt_strain_name | n_contigs_count_unit | n_features_count_unit | link |
|---|---|---|---|---|---|
| Genome0000001 | FW305-37-reassembled.genome | FW305-37 | 149 | 5866 | https://narrative.kbase.us/#dataview/41372/FW305-37-reassembled.genome |
| Genome0000002 | FW507-29LB-reassembled.genome | FW507-29LB | 220 | 7535 | https://narrative.kbase.us/#dataview/41372/FW507-29LB-reassembled.genome |
| Genome0000003 | MPR-WIN1-reassembled.genome | MPR-WIN1 | 2373 | 8294 | https://narrative.kbase.us/#dataview/41372/MPR-WIN1-reassembled.genome |
| Genome0000004 | MPR-TSA4-reassembled.genome | MPR-TSA4 | 101 | 3172 | https://narrative.kbase.us/#dataview/41372/MPR-TSA4-reassembled.genome |
| Genome0000005 | MT42-reassembled.genome | MT42 | 856 | 4958 | https://narrative.kbase.us/#dataview/41372/MT42-reassembled.genome |

---

## Table: sdt_gene

**Table Description:** CDM table for CORAL type `Gene`

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_gene_id | string | Yes | {"description": "Unique internal identifier for the gene (Primary key)", "type": "primary_key"} |
| sdt_gene_name | string | Yes | {"description": "Unique external identifier for the gene", "type": "unique_key"} |
| sdt_genome_name | string | Yes | {"description": "Name of the genome to which the gene belongs (foreign key)", "type": "foreign_key", "references": "sdt_genome.sdt_genome_name"} |
| aliases | array<string> | Yes | {"description": "List of alternative names or identifiers for the gene"} |
| contig_number_count_unit | int | Yes | {"description": "Contigs are indexed starting at 1, as in KBase", "unit": "count unit"} |
| strand | string | Yes | {"description": "DNA strand of the gene (+ for forward, - for reverse)"} |
| start_base_pair | int | Yes | {"description": "Genomic start coordinate on the contig, indexed starting at 1 as in KBase", "unit": "base pair"} |
| stop_base_pair | int | Yes | {"description": "Genomic stop coordinate in base pairs", "unit": "base pair"} |
| function | string | Yes | {"description": "Annotated biological function of the gene"} |

### Sample Data (5 rows)

| sdt_gene_id | sdt_gene_name | sdt_genome_name | aliases | contig_number_count_unit | strand | start_base_pair | stop_base_pair | function |
|---|---|---|---|---|---|---|---|---|
| Gene0000001 | MEPIHFMG_04711 | FW300-N2A2.genome | [] | 91 | + | 12032 | 13033 | Glyceraldehyde-3-phosphate dehydrogenase 1 |
| Gene0000002 | MEPIHFMG_04712 | FW300-N2A2.genome | [] | 91 | + | 13173 | 13637 | Methylglyoxal synthase |
| Gene0000003 | MEPIHFMG_04713 | FW300-N2A2.genome | [] | 91 | + | 13715 | 14233 | ECF RNA polymerase sigma factor SigE |
| Gene0000004 | MEPIHFMG_04714 | FW300-N2A2.genome | [] | 91 | + | 14315 | 15280 | hypothetical protein |
| Gene0000005 | MEPIHFMG_04715 | FW300-N2A2.genome | [] | 91 | + | 15403 | 17994 | Hemin receptor |

---

## Table: sdt_bin

**Table Description:** CDM table for CORAL type `Bin`

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_bin_id | string | Yes | {"description": "Unique identifier for the bin (Primary key)", "type": "primary_key"} |
| sdt_bin_name | string | Yes | {"description": "Human-readable, unique name for the bin", "type": "unique_key"} |
| sdt_assembly_name | string | Yes | {"description": "Identifier of the metagenomic assembly that the bin belongs to (foreign key to Assembly.name)", "type": "foreign_key", "references": "sdt_assembly.sdt_assembly_name"} |
| contigs | array<string> | Yes | {"description": "Array of contig identifiers included in the bin"} |

### Sample Data (5 rows)

| sdt_bin_id | sdt_bin_name | sdt_assembly_name | contigs |
|---|---|---|---|
| Bin0000001 | FW215_bin_47 | FW215.contigs | ["FW215_contig_1948", "FW215_contig_3592", "FW215_contig_4370", "FW215_contig_5127", "FW215_contig_5247", "FW215_contig_5390", "FW215_contig_5505", "FW215_contig_5607", "FW215_contig_5821", "FW215_contig_5833", "FW215_contig_5917", "FW215_contig_6337", "FW215_contig_6498", "FW215_contig_6778", "FW215_contig_6883", "FW215_contig_7526", "FW215_contig_8063", "FW215_contig_8142", "FW215_contig_8164", "FW215_contig_8239", "FW215_contig_8279", "FW215_contig_8516", "FW215_contig_8530", "FW215_contig_8632", "FW215_contig_9346", "FW215_contig_9508", "FW215_contig_9659", "FW215_contig_9760", "FW215_contig_9994", "FW215_contig_10117", "FW215_contig_10299", "FW215_contig_10392", "FW215_contig_10702", "FW215_contig_10981", "FW215_contig_11090", "FW215_contig_11187", "FW215_contig_11255", "FW215_contig_11666", "FW215_contig_11691", "FW215_contig_11745", "FW215_contig_11802", "FW215_contig_11832", "FW215_contig_12111", "FW215_contig_12122", "FW215_contig_12152", "FW215_contig_12231", "FW215_contig_12270", "FW215_contig_12354", "FW215_contig_12467", "FW215_contig_12635", "FW215_contig_12719", "FW215_contig_12829", "FW215_contig_13018", "FW215_contig_13277", "FW215_contig_13533", "FW215_contig_13626", "FW215_contig_13802", "FW215_contig_13848", "FW215_contig_13893", "FW215_contig_13967", "FW215_contig_13979", "FW215_contig_13985", "FW215_contig_14100", "FW215_contig_14333", "FW215_contig_14340", "FW215_contig_14556", "FW215_contig_14659", "FW215_contig_14669", "FW215_contig_14722", "FW215_contig_14755", "FW215_contig_15099", "FW215_contig_15298", "FW215_contig_15510", "FW215_contig_15829", "FW215_contig_15843", "FW215_contig_16049", "FW215_contig_16326", "FW215_contig_16598", "FW215_contig_16885", "FW215_contig_17109", "FW215_contig_17503", "FW215_contig_17609", "FW215_contig_17718", "FW215_contig_17735", "FW215_contig_17858", "FW215_contig_18022", "FW215_contig_18106", "FW215_contig_18113", "FW215_contig_18323", "FW215_contig_18356", "FW215_contig_18558", "FW215_contig_18624", "FW215_contig_18723", "FW215_contig_18860", "FW215_contig_18926", "FW215_contig_18956", "FW215_contig_18974", "FW215_contig_19259", "FW215_contig_19521", "FW215_contig_19591", "FW215_contig_19619", "FW215_contig_19668", "FW215_contig_20050", "FW215_contig_20111", "FW215_contig_20377", "FW215_contig_20391", "FW215_contig_20585", "FW215_contig_20634", "FW215_contig_20688", "FW215_contig_20862", "FW215_contig_20883", "FW215_contig_20910", "FW215_contig_21051", "FW215_contig_21292", "FW215_contig_21584", "FW215_contig_21610", "FW215_contig_21708", "FW215_contig_21755", "FW215_contig_21957", "FW215_contig_22263", "FW215_contig_22317", "FW215_contig_22413", "FW215_contig_22430", "FW215_contig_22643", "FW215_contig_22886", "FW215_contig_23132", "FW215_contig_23260", "FW215_contig_23366", "FW215_contig_23379", "FW215_contig_23521", "FW215_contig_23643", "FW215_contig_23739", "FW215_contig_23793", "FW215_contig_23913", "FW215_contig_24051", "FW215_contig_24106", "FW215_contig_24228", "FW215_contig_24321", "FW215_contig_24514", "FW215_contig_24614", "FW215_contig_24889", "FW215_contig_24935", "FW215_contig_25335", "FW215_contig_25584", "FW215_contig_25760", "FW215_contig_25852", "FW215_contig_26127", "FW215_contig_26502", "FW215_contig_26537", "FW215_contig_26587", "FW215_contig_26650", "FW215_contig_26677", "FW215_contig_27359", "FW215_contig_27436", "FW215_contig_27473", "FW215_contig_27673", "FW215_contig_27695", "FW215_contig_27919", "FW215_contig_28103", "FW215_contig_28240", "FW215_contig_29060"] |
| Bin0000002 | FW215_bin_1 | FW215.contigs | ["FW215_contig_4", "FW215_contig_6", "FW215_contig_7", "FW215_contig_8", "FW215_contig_9", "FW215_contig_17", "FW215_contig_30", "FW215_contig_31", "FW215_contig_32", "FW215_contig_39", "FW215_contig_43", "FW215_contig_45", "FW215_contig_50", "FW215_contig_53", "FW215_contig_55", "FW215_contig_60", "FW215_contig_62", "FW215_contig_84", "FW215_contig_92", "FW215_contig_96", "FW215_contig_108", "FW215_contig_119", "FW215_contig_123", "FW215_contig_133", "FW215_contig_134", "FW215_contig_137", "FW215_contig_151", "FW215_contig_161", "FW215_contig_164", "FW215_contig_176", "FW215_contig_177", "FW215_contig_187", "FW215_contig_202", "FW215_contig_240", "FW215_contig_299", "FW215_contig_334", "FW215_contig_367", "FW215_contig_410", "FW215_contig_412", "FW215_contig_435", "FW215_contig_502", "FW215_contig_507", "FW215_contig_533", "FW215_contig_603", "FW215_contig_717", "FW215_contig_762", "FW215_contig_773", "FW215_contig_783", "FW215_contig_827", "FW215_contig_1151", "FW215_contig_1319", "FW215_contig_1338", "FW215_contig_1669", "FW215_contig_2013", "FW215_contig_2377", "FW215_contig_2385", "FW215_contig_3179", "FW215_contig_4398", "FW215_contig_5032", "FW215_contig_5216", "FW215_contig_6214", "FW215_contig_6349", "FW215_contig_9491", "FW215_contig_10616", "FW215_contig_21984", "FW215_contig_28548"] |
| Bin0000003 | FW215_bin_48 | FW215.contigs | ["FW215_contig_204", "FW215_contig_243", "FW215_contig_501", "FW215_contig_757", "FW215_contig_769", "FW215_contig_829", "FW215_contig_845", "FW215_contig_971", "FW215_contig_1036", "FW215_contig_1257", "FW215_contig_1273", "FW215_contig_1401", "FW215_contig_1880", "FW215_contig_2044", "FW215_contig_2047", "FW215_contig_2160", "FW215_contig_2168", "FW215_contig_2197", "FW215_contig_2284", "FW215_contig_2445", "FW215_contig_2729", "FW215_contig_2844", "FW215_contig_2883", "FW215_contig_3215", "FW215_contig_3251", "FW215_contig_3551", "FW215_contig_3853", "FW215_contig_4222", "FW215_contig_4672", "FW215_contig_4681", "FW215_contig_4925", "FW215_contig_6032", "FW215_contig_6486", "FW215_contig_6845", "FW215_contig_7358", "FW215_contig_7366", "FW215_contig_7413", "FW215_contig_7449", "FW215_contig_7931", "FW215_contig_8736", "FW215_contig_8808", "FW215_contig_8815", "FW215_contig_9108", "FW215_contig_9910", "FW215_contig_9989", "FW215_contig_10868", "FW215_contig_10969", "FW215_contig_11037", "FW215_contig_11244", "FW215_contig_11767", "FW215_contig_12510", "FW215_contig_13488", "FW215_contig_14765", "FW215_contig_15376", "FW215_contig_15403", "FW215_contig_17510", "FW215_contig_18221", "FW215_contig_20077", "FW215_contig_20461", "FW215_contig_23640", "FW215_contig_23811", "FW215_contig_28525", "FW215_contig_29745"] |
| Bin0000004 | FW215_bin_10 | FW215.contigs | ["FW215_contig_232", "FW215_contig_241", "FW215_contig_292", "FW215_contig_297", "FW215_contig_315", "FW215_contig_330", "FW215_contig_459", "FW215_contig_460", "FW215_contig_493", "FW215_contig_564", "FW215_contig_571", "FW215_contig_671", "FW215_contig_687", "FW215_contig_727", "FW215_contig_738", "FW215_contig_774", "FW215_contig_775", "FW215_contig_858", "FW215_contig_1060", "FW215_contig_1167", "FW215_contig_1172", "FW215_contig_1178", "FW215_contig_1214", "FW215_contig_1249", "FW215_contig_1255", "FW215_contig_1296", "FW215_contig_1503", "FW215_contig_1695", "FW215_contig_2035", "FW215_contig_2266", "FW215_contig_2515", "FW215_contig_2569", "FW215_contig_2929", "FW215_contig_3023", "FW215_contig_3198", "FW215_contig_3495", "FW215_contig_4581", "FW215_contig_5683", "FW215_contig_5686", "FW215_contig_6180", "FW215_contig_6520", "FW215_contig_6971", "FW215_contig_7613", "FW215_contig_8859", "FW215_contig_10631", "FW215_contig_10845", "FW215_contig_14092", "FW215_contig_20010", "FW215_contig_25256"] |
| Bin0000005 | FW215_bin_5 | FW215.contigs | ["FW215_contig_1374", "FW215_contig_1770", "FW215_contig_2320", "FW215_contig_2347", "FW215_contig_2431", "FW215_contig_2474", "FW215_contig_2609", "FW215_contig_2864", "FW215_contig_3072", "FW215_contig_3096", "FW215_contig_3115", "FW215_contig_3298", "FW215_contig_3505", "FW215_contig_3630", "FW215_contig_3641", "FW215_contig_4332", "FW215_contig_4380", "FW215_contig_5029", "FW215_contig_5270", "FW215_contig_5396", "FW215_contig_5428", "FW215_contig_5539", "FW215_contig_5768", "FW215_contig_5839", "FW215_contig_5940", "FW215_contig_6051", "FW215_contig_6262", "FW215_contig_6309", "FW215_contig_6356", "FW215_contig_6375", "FW215_contig_6434", "FW215_contig_6544", "FW215_contig_6685", "FW215_contig_6707", "FW215_contig_6737", "FW215_contig_6888", "FW215_contig_8085", "FW215_contig_8285", "FW215_contig_8471", "FW215_contig_8489", "FW215_contig_8554", "FW215_contig_8650", "FW215_contig_8904", "FW215_contig_8971", "FW215_contig_9067", "FW215_contig_9460", "FW215_contig_9487", "FW215_contig_9595", "FW215_contig_9644", "FW215_contig_9931", "FW215_contig_9951", "FW215_contig_10053", "FW215_contig_10314", "FW215_contig_10339", "FW215_contig_10624", "FW215_contig_10649", "FW215_contig_10947", "FW215_contig_11428", "FW215_contig_11528", "FW215_contig_12017", "FW215_contig_12392", "FW215_contig_12588", "FW215_contig_13398", "FW215_contig_13443", "FW215_contig_13698", "FW215_contig_14055", "FW215_contig_14170", "FW215_contig_14367", "FW215_contig_14904", "FW215_contig_15034", "FW215_contig_15154", "FW215_contig_15276", "FW215_contig_15370", "FW215_contig_15703", "FW215_contig_15810", "FW215_contig_15895", "FW215_contig_16504", "FW215_contig_16539", "FW215_contig_17528", "FW215_contig_17666", "FW215_contig_17675", "FW215_contig_18474", "FW215_contig_18649", "FW215_contig_18981", "FW215_contig_19168", "FW215_contig_19199", "FW215_contig_19483", "FW215_contig_19530", "FW215_contig_19554", "FW215_contig_19781", "FW215_contig_19918", "FW215_contig_19974", "FW215_contig_20157", "FW215_contig_20369", "FW215_contig_20392", "FW215_contig_20568", "FW215_contig_20782", "FW215_contig_21428", "FW215_contig_21905", "FW215_contig_22011", "FW215_contig_22283", "FW215_contig_22732", "FW215_contig_23075", "FW215_contig_23485", "FW215_contig_23635", "FW215_contig_23696", "FW215_contig_24155", "FW215_contig_24451", "FW215_contig_24636", "FW215_contig_24914", "FW215_contig_25162", "FW215_contig_25295", "FW215_contig_25343", "FW215_contig_25565", "FW215_contig_26095", "FW215_contig_28300", "FW215_contig_28871", "FW215_contig_29205"] |

---

## Table: sdt_protocol

**Table Description:** CDM table for CORAL type `Protocol`

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_protocol_id | string | Yes | {"description": "Unique identifier for the protocol (Primary key)", "type": "primary_key"} |
| sdt_protocol_name | string | Yes | {"description": "Unique, human-readable name of the protocol", "type": "unique_key"} |
| sdt_protocol_description | string | Yes | {"description": "Detailed description of the protocol"} |
| link | string | Yes | {"description": "URL linking to additional documentation of the protocol, such as protocols.io"} |

### Sample Data (5 rows)

| sdt_protocol_id | sdt_protocol_name | sdt_protocol_description | link |
|---|---|---|---|
| Protocol0000026 | ning-2020-matchseq | The forward and reverse sequences are matched according to coordinate of each sequence. Matched sequences are ranked in the same order in [Sample ID]_m_R1.fastq and [Sample ID]_m_R2.fastq, while unmatched sequences were removed. | NULL |
| Protocol0000027 | ning-lui-2021-qiime2 | QIIME2 (version 2021.2) was used to generate ASV table. After barcode and primer sequences were trimmed with zero error, sequencing data were processed by DADA2 to identify exact amplicon sequence variants (ASV). The method ‘consensus’ was used to remove chimeras; samples are denoised independently; forward and reverse truncate positions are 163 and 130, respectively, after quality trim with a quality score 2; maximal expected error score is 2.0 when combining forward and reverse sequences. The ASVs were identified taxonomically based on the Silva 138 dataset using QIIME2 pre-fitted sklearn-based taxonomy classifier with the default confidence (0.7). After classification, ASVs identified as Chloroplast, Mitochondria, Eukaryota, or unclassified kingdom were removed. The prokaryotic ASV sequences were aligned using MAFFT in QIIME2, without mask. Then, aligned sequences were used to build phylogenetic tree by FastTree (4, 5).  November 16, 2021:  Lauren Lui dereplicated the ASV table from Adam Arkin and combined it with taxonomy. The taxonomy was called by loading the sequences into QIIME2 and using the Naive Bayes classifier trained on the SILVA138 database.  Lauren removed any ASVs with “Mitochondria” or “Chloroplast” in the taxonomy before calculating relative abundance.   | NULL |
| Protocol0000028 | chandonia-2020-cutadapt | "kb_cutadapt 1.0.8 (cutadapt 1.18) with options: {<br>                    "input_reads": name,<br>                    "output_object_name": cut_name,<br>                    "5P": None,<br>                    "3P": {<br>                        "adapter_sequence_3P": "CTGTCTCTTATACACATCT",<br>                        "anchored_3P": 0<br>                    },<br>                    "error_tolerance": 0.1,<br>                    "min_overlap_length": 3,<br>                    "min_read_length": 50,<br>                    "discard_untrimmed": "0"<br>                }," | NULL |
| Protocol0000029 | lui-nielsen-2020-flye-canu | We reassembled these genomes using Flye v1.7 and CANU v1.9 for assembly | NULL |
| Protocol0000030 | lui-2020-spades | "Valentine sequenced some ENIGMA genomes that were problematic in the previous batch of sequencing.<br>These nextera sequencing libraries were made by Valentine.<br><br>A single index was used.<br><br>Sequencing was done on novaseq machine at UC Berkeley (SP 250PE)<br><br>2 x 250bp paired end reads<br>Lauren assembled them outside KBase using SPAdes in late 2020." | NULL |

---

## Table: sdt_image

**Table Description:** CDM table for CORAL type `Image`

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_image_id | string | Yes | {"description": "Unique identifier for each image (Primary key)", "type": "primary_key"} |
| sdt_image_name | string | Yes | {"description": "Unique name (e.g., filename) for the image.", "type": "unique_key"} |
| sdt_image_description | string | Yes | {"description": "Textual description of the image"} |
| mime_type | string | Yes | {"description": "MIME type specifying the image file format (e.g., image/jpeg)"} |
| size_byte | int | Yes | {"description": "File size of the image measured in bytes", "unit": "byte"} |
| dimensions | string | Yes | {"description": "Image dimensions (e.g., width \u00d7 height) expressed in pixels", "unit": "image resolution unit"} |
| link | string | Yes | {"description": "URL or file path linking to the stored image"} |

### Sample Data (5 rows)

| sdt_image_id | sdt_image_name | sdt_image_description | mime_type | size_byte | dimensions | link |
|---|---|---|---|---|---|---|
| Image0000164 | GW821-FHT03E03_Sphingobacterium.tif | GW821-FHT03E03_Sphingobacterium isolate image | image/tiff | 1863672 | 682,683 | /images/GW821-FHT03E03_Sphingobacterium.tif |
| Image0000165 | GW821-FHT03G07_Serratia.tif | GW821-FHT03G07_Serratia isolate image | image/tiff | 2693336 | 820,821 | /images/GW821-FHT03G07_Serratia.tif |
| Image0000166 | GW821-FHT04A06_Chryseobacterium.tif | GW821-FHT04A06_Chryseobacterium isolate image | image/tiff | 3062980 | 875,875 | /images/GW821-FHT04A06_Chryseobacterium.tif |
| Image0000167 | GW821-FHT04A12_Delftia.tif | GW821-FHT04A12_Delftia isolate image | image/tiff | 2693336 | 820,821 | /images/GW821-FHT04A12_Delftia.tif |
| Image0000168 | GW821-FHT04C08_Delftia_acidovorans.tif | GW821-FHT04C08_Delftia_acidovorans isolate image | image/tiff | 3226096 | 897,899 | /images/GW821-FHT04C08_Delftia_acidovorans.tif |

---

## Table: sdt_tnseq_library

**Table Description:** CDM table for CORAL type `TnSeq_Library`

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_tnseq_library_id | string | Yes | {"description": "Unique TnSeq library identifier (Primary key)", "type": "primary_key"} |
| sdt_tnseq_library_name | string | Yes | {"description": "Unique, human-readable name of the TnSeq library", "type": "unique_key"} |
| sdt_genome_name | string | Yes | {"description": "Foreign key to the associated genome (Genome.name) from which the library was derived", "type": "foreign_key", "references": "sdt_genome.sdt_genome_name"} |
| primers_model | string | Yes | {"description": "Type of primers used to generate the library"} |
| n_mapped_reads_count_unit | int | Yes | {"description": "Number of reads that mapped to the reference genome", "unit": "count unit"} |
| n_barcodes_count_unit | int | Yes | {"description": "Total number of distinct barcode sequences detected in the library", "unit": "count unit"} |
| n_usable_barcodes_count_unit | int | Yes | {"description": "Number of barcodes deemed usable after quality filtering", "unit": "count unit"} |
| n_insertion_locations_count_unit | int | Yes | {"description": "Number of distinct transposon insertion sites identified in the library", "unit": "count unit"} |
| hit_rate_essential_ratio_unit | double | Yes | {"description": "Proportion of essential genes with at least one transposon insertion", "unit": "ratio unit"} |
| hit_rate_other_ratio_unit | double | Yes | {"description": "Proportion of non-essential (other) genes with at least one transposon insertion", "unit": "ratio unit"} |

### Sample Data (5 rows)

| sdt_tnseq_library_id | sdt_tnseq_library_name | sdt_genome_name | primers_model | n_mapped_reads_count_unit | n_barcodes_count_unit | n_usable_barcodes_count_unit | n_insertion_locations_count_unit | hit_rate_essential_ratio_unit | hit_rate_other_ratio_unit |
|---|---|---|---|---|---|---|---|---|---|
| TnSeq_Library0000001 | FW300-N2E2.tnseq_library | FW300-N2E2-reassembled.genome | model_pKMW7 | NULL | NULL | NULL | NULL | NULL | NULL |

---

## Table: sdt_dubseq_library

**Table Description:** CDM table for CORAL type `DubSeq_Library`

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_dubseq_library_id | string | Yes | {"description": "Unique DubSeq library identifier (Primary key)", "type": "primary_key"} |
| sdt_dubseq_library_name | string | Yes | {"description": "Unique, human-readable name of the DubSeq library", "type": "unique_key"} |
| sdt_genome_name | string | Yes | {"description": "Foreign key to the associated genome (Genome.name) from which the library was derived", "type": "foreign_key", "references": "sdt_genome.sdt_genome_name"} |
| n_fragments_count_unit | int | Yes | {"description": "Number of unique DNA fragments in the library", "unit": "count unit"} |

### Sample Data (5 rows)

| sdt_dubseq_library_id | sdt_dubseq_library_name | sdt_genome_name | n_fragments_count_unit |
|---|---|---|---|
| DubSeq_Library0000002 | Pseudomonas-putida-KT2440.dubseq_library | Pseudomonas-putida-KT2440.genome | NULL |
| DubSeq_Library0000003 | Bacteroides-thetaiotaomicron-VPI-5482.dubseq_library | Bacteroides-thetaiotaomicron-VPI-5482.genome | NULL |
| DubSeq_Library0000001 | Escherichia-coli-BW25113.dubseq_library | Escherichia-coli-BW25113.genome | NULL |

---

## Table: sys_typedef

**Table Description:** CORAL type definitions

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| type_name | string | Yes |  |
| field_name | string | Yes |  |
| cdm_column_name | string | Yes |  |
| scalar_type | string | Yes |  |
| is_required | boolean | Yes |  |
| is_pk | boolean | Yes |  |
| is_upk | boolean | Yes |  |
| fk | string | Yes |  |
| constraint | string | Yes |  |
| comment | string | Yes |  |
| units_sys_oterm_id | string | Yes |  |
| units_sys_oterm_name | string | Yes | {"description": "Term name"} |
| type_sys_oterm_id | string | Yes |  |
| type_sys_oterm_name | string | Yes | {"description": "Term name"} |

### Sample Data (5 rows)

| type_name | field_name | cdm_column_name | scalar_type | is_required | is_pk | is_upk | fk | constraint | comment | units_sys_oterm_id | units_sys_oterm_name | type_sys_oterm_id | type_sys_oterm_name |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Sample | depth | depth_meter | float | False | False | False | NULL | NULL | For below-ground samples, the average distance below ground level in meters where the sample was taken | UO:0000008 | meter | ME:0000219 | depth |
| Sample | elevation | elevation_meter | float | False | False | False | NULL | NULL | For above-ground samples, the average distance above ground level in meters where the sample was taken | UO:0000008 | meter | ME:0000220 | elevation |
| Sample | date | date | text | True | False | False | NULL | \d\d\d\d(-\d\d(-\d\d)?)? | YYYY[-MM[-DD]] | NULL | NULL | ME:0000009 | date |
| Sample | time | time | text | False | False | False | NULL | \d(\d)?(:\d\d(:\d\d)?)?\s*([apAP][mM])? | HH[:MM[:SS]] [AM\|PM] | NULL | NULL | ME:0000010 | time |
| Sample | timezone | timezone | text | False | False | False | NULL | NULL | ISO8601 compliant format, ie. UTC-7 | NULL | NULL | ME:0000201 | time zone |

---

## Table: ddt_brick0000510

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_strain_name | string | Yes | {"description": "strain ID", "type": "foreign_key", "references": "sdt_strain.sdt_strain_name"} |
| sdt_condition_name | string | Yes | {"description": "condition ID", "type": "foreign_key", "references": "sdt_condition.sdt_condition_name"} |
| description_comment_original_condition_description | string | Yes | {"description": "description, comment=Original Condition Description"} |
| sdt_sample_name | string | Yes | {"description": "environmental sample ID", "type": "foreign_key", "references": "sdt_sample.sdt_sample_name"} |
| date_comment_sampling_date | string | Yes | {"description": "date, comment=Sampling Date"} |
| sdt_location_name | string | Yes | {"description": "environmental sample location ID", "type": "foreign_key", "references": "sdt_location.sdt_location_name"} |
| enigma_campaign_sys_oterm_id | string | Yes | {"description": "ENIGMA Campaign, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| enigma_campaign_sys_oterm_name | string | Yes | {"description": "ENIGMA Campaign"} |
| enigma_labs_and_personnel_comment_contact_person_or_lab_sys_oterm_id | string | Yes | {"description": "ENIGMA Labs and Personnel, comment=Contact Person or Lab, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| enigma_labs_and_personnel_comment_contact_person_or_lab_sys_oterm_name | string | Yes | {"description": "ENIGMA Labs and Personnel, comment=Contact Person or Lab"} |

### Sample Data (5 rows)

| sdt_strain_name | sdt_condition_name | description_comment_original_condition_description | sdt_sample_name | date_comment_sampling_date | sdt_location_name | enigma_campaign_sys_oterm_id | enigma_campaign_sys_oterm_name | enigma_labs_and_personnel_comment_contact_person_or_lab_sys_oterm_id | enigma_labs_and_personnel_comment_contact_person_or_lab_sys_oterm_name |
|---|---|---|---|---|---|---|---|---|---|
| FW305-130 | anaerobic = 0; media name = LB, concentration = 25.0 (fold dilution); media name = Sediment Extract; temperature = 30.0 (degree Celsius) | Sediment extract to 1/25 LB, aerobic, 30°C | FW305-021115-2 | 2015-02-11 | FW-305 | ENIGMA:0000027 | Natural Organic Matter | ENIGMA:0000053 | Chakraborty Lab |
| FW305-BF6 | anaerobic = 0; aphotic = 1; media name = R2A, concentration = 25.0 (fold dilution); temperature = 25.0 (degree Celsius) | filter on  1/25 R2A, aerobic, aphotic, 25°C | FW305-021115-2 | 2015-02-11 | FW-305 | ENIGMA:0000027 | Natural Organic Matter | ENIGMA:0000053 | Chakraborty Lab |
| FW104-L1 | anaerobic = 0; media name = LB, growth stage = colony formation on solid media; media name = LB, growth stage = single colony grown in liquid media; temperature = 30.0 (degree Celsius), growth stage = colony formation on solid media; temperature = 30.0 (degree Celsius), growth stage = single colony grown in liquid media | LB | FW104-67-11-14-12 | 2012-11-14 | FW-104 | ENIGMA:0000003 | 100 Well Survey | ENIGMA:0000053 | Chakraborty Lab |
| FW507-19G05 | anaerobic = 0; media name = Eugon Broth, growth stage = colony formation on solid media; media name = Eugon Broth, growth stage = single colony grown in liquid media; temperature = 30.0 (degree Celsius), growth stage = colony formation on solid media; temperature = 30.0 (degree Celsius), growth stage = single colony grown in liquid media | Eugon | FW507-49-11-26-12 | 2012-11-26 | FW-507 | ENIGMA:0000003 | 100 Well Survey | ENIGMA:0000053 | Chakraborty Lab |
| FW507-4D12 | anaerobic = 0; media name = R2A, growth stage = colony formation on solid media; media name = R2A, growth stage = single colony grown in liquid media; temperature = 30.0 (degree Celsius), growth stage = colony formation on solid media; temperature = 30.0 (degree Celsius), growth stage = single colony grown in liquid media | R2A | FW507-49-11-26-12 | 2012-11-26 | FW-507 | ENIGMA:0000003 | 100 Well Survey | ENIGMA:0000053 | Chakraborty Lab |

---

## Table: ddt_brick0000517

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_sample_name | string | Yes | {"description": "environmental sample ID", "type": "foreign_key", "references": "sdt_sample.sdt_sample_name"} |
| sdt_strain_name | string | Yes | {"description": "strain ID", "type": "foreign_key", "references": "sdt_strain.sdt_strain_name"} |
| sdt_genome_name | string | Yes | {"description": "genome ID", "type": "foreign_key", "references": "sdt_genome.sdt_genome_name"} |
| read_coverage_statistic_average_comment_cov80_average_coverage_after_trimming_highest_and_lowest_10_percent_count_unit | double | Yes | {"description": "read coverage, statistic=average, comment=cov80 average coverage after trimming highest and lowest 10 percent", "unit": "count unit"} |
| sequence_identity_statistic_average_comment_average_percent_identity_of_aligned_reads_percent | double | Yes | {"description": "sequence identity, statistic=average, comment=average percent identity of aligned reads", "unit": "percent"} |
| read_coverage_comment_percent_of_1kb_chunks_of_genome_covered_by_at_least_one_read_percent | double | Yes | {"description": "read coverage, comment=percent of 1kb chunks of genome covered by at least one read", "unit": "percent"} |

### Sample Data (5 rows)

| sdt_sample_name | sdt_strain_name | sdt_genome_name | read_coverage_statistic_average_comment_cov80_average_coverage_after_trimming_highest_and_lowest_10_percent_count_unit | sequence_identity_statistic_average_comment_average_percent_identity_of_aligned_reads_percent | read_coverage_comment_percent_of_1kb_chunks_of_genome_covered_by_at_least_one_read_percent |
|---|---|---|---|---|---|
| 20240529-EFP01-F01 | CPT15-335-S11 | CPT15-335-S11.1 | 3.671087 | 99.3486 | 89.6596 |
| 20240529-EFP01-F01 | CPT15-335-S12 | CPT15-335-S12.1 | 3.689159 | 99.35079999999999 | 89.2848 |
| 20240529-EFP01-F01 | CPT15-335-S13 | CPT15-335-S13.1 | 3.674033 | 99.34920000000001 | 89.6854 |
| 20240529-EFP01-F01 | CPT15-335-S13 | CPT15-335-S13.3 | 3.730473 | 99.3451 | 89.5223 |
| 20240529-EFP01-F01 | DP16D-E2 | DP16D-E2.1 | 1.834835 | 96.9795 | 58.741699999999994 |

---

## Table: ddt_brick0000520

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_strain_name | string | Yes | {"description": "strain ID", "type": "foreign_key", "references": "sdt_strain.sdt_strain_name"} |
| sequence_type_sys_oterm_id | string | Yes | {"description": "sequence type, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| sequence_type_sys_oterm_name | string | Yes | {"description": "sequence type"} |
| strand_sys_oterm_id | string | Yes | {"description": "strand, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| strand_sys_oterm_name | string | Yes | {"description": "strand"} |
| sequence | string | Yes | {"description": "sequence"} |

### Sample Data (5 rows)

| sdt_strain_name | sequence_type_sys_oterm_id | sequence_type_sys_oterm_name | strand_sys_oterm_id | strand_sys_oterm_name | sequence |
|---|---|---|---|---|---|
| FW305-130 | ME:0000190 | 16S sequence | ME:0000187 | forward | GCAGTCGAGCGGTAAGGCCTTTCGGGGTACACGAGCGGCGAACGGGTGAGTAACACGTGGGTGATCTGCCCTGCACTTCGGGATAAGCCTGGGAAACTGGGTCTAATACCGGATATGACCTCAGGTTGCATGACTTGGGGTGGAAAGATTTATCGGTGCAGGATGGGCCCGCGGCCTATCAGCTTGTTGGTGGGGTAATGGCCTACCAAGGCGACGACGGGTAGCCGACCTGAGAGGGTGACCGGCCACACTGGGACTGAGACACGGCCCAGACTCCTACGGGAGGCAGCAGTGGGGAATATTGCACAATGGGCGAAAGCCTGATGCAGCGACGCCGCGTGAGGGATGACGGCCTTCGGGTTGTAAACCTCTTTCAGCAGGGACGAAGCGCAAGTGACGGTACCTGCAGAAGAAGCACCGGCTAACTACGTGCCAGCAGCCGCGGTAATACGTAGGGTGCAAGCGTTGTCCGGAATTACTGGGCGTAAAGAGTTCGTAGGCGGTTTGTCGCGTCGTTTGTGAAAACCAGCAGCTCAACTGCTGGCTTGCAGGCGATACGGGCAGACTTGAGTACTGCAGGGGAGACTGGAATTCCTGGTGTAGCGGTGAAATGCGCAGATATCAGGAGGAACACCGGTGGCGAAGGCGGGTCTCTGGGCAGTAACTGACGCTGAGGAACGAAAGCGTGGGTAGCGAACAGGATTAGATACCCTGGTAGTCCACGCCGTAAACGGTGGGCGCTAGGTGTGGGTTCCTTCCACGGAATCCGTGCCGTAGCTAACGCATTAAGCGCCCCGCCTGGGGAGTACGGCCGCAAGGCTAAAACTCAAAGGAATTGACGGGGGCCCGCACAAGCGGCGGAGCATGTGGATTAATTCGATGCAACGCGAAGAACCTTACCTGGGGTTTGACATATACCGGAAAGCTGCAGAGATGTGGCCCCCCTTGTGGTCGGTATACAGGTGGTGCATGGCTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCCTATCTTATGTTGCCAGCACGTTATGGTGGGGACTCGTAAGAGACTGCCGGGGTCAACTCGGAGGAAGGTGGGGACGACGTCAAGTCATCATGCCCCTTATGTCCAGGGCTTCACACATGCTACAATGGCCAGTACAGAGGGCTGCGAGACCGTGAGGTGGAGCGAATCCCTTAAAGCTGGTCTCAGTTCGGATCGGGGTCTGCAACTCGACCCCGTGAAGTNGGAGTCGCTAGTAATCGCAGATCAGCAACGCTGCGGTGAATACGTTCCCGGGCCTTGTACACACCGCCCGTCACGTCATGAAAGTCGGTAACACCCGAAGCCGGTGGCT |
| FW305-BF6 | ME:0000190 | 16S sequence | ME:0000187 | forward | TGCAGTCGAGCGGACTTGTAGGAGCTTGCTCCTGCAGGTTAGCGGCGGACGGGTGAGTAACACGTGGGCAACCTACCTGTAAGACTGGGATAACTTCGGGAAACCGGAGCTAATACCGGATGACATAAAGGAACTCCTGTTCCTTTATTGAAAGATGGCTTCGGCTATCACTTACAGATGGGCCCGCGGCGCAGTAGCTAGTTGGTGAGGTAACGGCTCACCAAGGCGACGATGCGTAGCCGACCTGAGAGGGTGATCGGCCACACTGGGACTGAGACACGGCCCAGACTCCTACGGGAGGCAGCAGTAGGGAATCTTCCGCAATGGACGAAAGTCTGACGGAGCAACGCCGCGTGAACGATGAAGGCCTTCGGGTCGTAAAGTTCTGTTGTTAGGGAAGAACAAGTGCTAGTTAAATAAGCTGGCACCTTGACGGTACCTAACCAGAAAGCCACGGCTAACTACGTGCCAGCAGCCGCGGTAATACGTAGGTGGCAAGCGTTGTCCGGAATTATTGGGCGTAAAGCGCGCGCAGGCGGTTTCTTAAGTCTGATGTGAAAGCCCCCGGCTCAACCGGGGAGGGTCATTGGAAACTGGGAAACTTGAGTGCAGAAGAGGAAAGTGGAATTCCAAGTGTAGCGGTGAAATGCGTAGAGATTTGGAGGAACACCAGTGGCGAAGGCGACTTTCTGGTCTGTAACTGACGCTGAGGCGCGAAAGCGTGGGGAGCAAACAGGATTAGATACCCTGGTAGTCCACGCTGTAAACGATGAGTGCTAAGTGTTAGAGGGTTTCCGCCCTTTAGTGCTGAAGTTAACGCATTAAGCACTCCGCCTGGGGAGTACGGTCGCAAGACTGAAACTCAAAGGAATTGACGGGGGCCCGCACAAGTGGTGGAGCATGTGGTTTAATTCGAAGCAACGCGAAGAACCTTACCAGGTCTTGACATCCTCTGACAACCCTAGAGATAGGGCTTTCCCTTCGGGGACAGAGTGACAGGTGGTGCATGGTTGTCGTCAGCTCGTGTCGTGAGATGTTNGGGTTAAGTCCCGCAACGAGCGCAACCCTTGATCTTAGTTGCCAGCATTTAGTTGGGCACTCTAAGGTGACTGCCGGTGACAAACCGGAGGAAGGTGGGGATGACGTCAAATCATCATGCCCCTTATGACCTGGGCTACACACGTGCTACAATGGATAGTACAAAGGGTTGCAAGACCGCGAGGTGGAGCTAATCCCATAAAACTATTCTCAGTTCGGATTGTAGGCTGCAACTCGCCTACATGAAGCCGGAATCACTAGTAATCGCGGATCAGCATGCCGCGGTGAATACGTTCCCGGGCCTTGTACACACCGCCCGTCACACCACGAGAGNTTGTAACACCCGAAGTCGGTNGGGTA |
| FW104-L1 | ME:0000190 | 16S sequence | ME:0000187 | forward | GTCGAGCGAATGGATTAAGAGCTTGCTCTTATGAAGTTAGCGGCGGACGGGTGAGTAACACGTGGGTAACCTGCCCATAAGACTGGGATAACTCCGGGAAACCGGGGCTAATACCGGATAACATTTTGAACCGCATGGTTCGAAATTGAAAGGCGGCTTCGGCTGTCACTTATGGATGGACCCGCGTCGCATTAGCTAGTTGGTGAGGTAACGGCTCACCAAGGCAACGATGCGTAGCCGACCTGAGAGGGTGATCGGCCACACTGGGACTGAGACACGGCCCAGACTCCTACGGGAGGCAGCAGTAGGGAATCTTCCGCAATGGACGAAAGTCTGACGGAGCAACGCCGCGTGAGTGATGAAGGCTTTCGGGTCGTAAAACTCTGTTGTTAGGGAAGAACAAGTGCTAGTTGAATAAGCTGGCACCTTGACGGTACCTAACCAGAAAGCCACGGCTAACTACGTGCCAGCAGCCGCGGTAATACGTAGGTGGCAAGCGTTATCCGGAATTATTGGGCGTAAAGCGCGCGCAGGTGGTTTCTTAAGTCTGATGTGAAAGCCCACGGCTCAACCGTGGAGGGTCATTGGAAACTGGGAGACTTGAGTGCAGAAGAGGAAAGTGGAATTCCATGTGTAGCGGTGAAATGCGTAGAGATATGGAGGAACACCAGTGGCGAAGGCGACTTTCTGGTCTGTAACTGACACTGAGGCGCGAAAGCGTGGGGAGCAAACAGGATTAGATACCCTGGTAGTCCACGCCGTAAACGATGAGTGCTAAGTGTTAGAGGGTTTCCGCCCTTTAGTGCTGAAGTTAACGCATTAAGCACTCCGCCTGGGGAGTACGGCCGCAAGGCTGAAACTCAAAGGAATTGACGGGGGCCCGCACAAGCGGTGGAGCATGTGGTTTAATTCGAAGCAACGCGAAGAACCTTACCAGGTCTTGACATCCTCTGACAACCCTAGAGATAGGGCTTCTCCTTCGGGAGCAGAGTGACAGGTGGTGCATGGTTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCTTGATCTTAGTTGCCATCATTAAGTTGGGCACTCTAAGTGACTGCCGGTGACAAACCGGAGGAAGGTGGGGATGACGTCAAATCATCATGCCCCTTATGACCTGG |
| FW507-19G05 | ME:0000190 | 16S sequence | ME:0000187 | forward | TGCAGTCGAGCGATGGATTAAGAGCTTGCTCTTATGAAGTTAGCGGGGGAAGGGAGAGAAACACGTGGGTAACCTGCCCATAAGACTGGGATAACTCCGGGAAACCGGGGCTAATACCGGATAACATTTTGAACTGCATGGTTCGAAATTGAAAGGCGGCTTCGGCTGTCACTTATGGATGGACCCGCGTCGCATTAGCTAGTTGGTGAGGTAACGGCTCACCAAGGCAACGATGCGTAGCCGACCTGAGAGGGTGATCGGCCACACTGGGACTGAGACACGGCCCAGACTCCTACGGGAGGCAGCAGTAGGGAATCTTCCGCAATGGACGAAAGTCTGACGGAGCAACGCCGCGTGAGTGATGAAGGCTTTCGGGTCGTAAAACTCTGTTGTTAGGGAAGAACAAGTGCTAGTTGAATAAGCTGGCACCTTGACGGTACCTAACCAGAAAGCCACGGCTAACTACGTGCCAGCAGCCGCGGTAATACGTAGGTGGCAAGCGTTATCCGGAATTATTGGGCGTAAAGCGCGCGCAGGTGGTTTCTTAAGTCTGATGTGAAAGCCCACGGCTCAACCGTGGAGGGTCATTGGAAACTGGGAGACTTGAGTGCAGAAGAGGAAAGTGGAATTCCATGTGTAGCGGTGAAATGCGTAGAGATATGGAGGAACACCAGTGGCGAAGGCGACTTTCTGGTCTGTAACTGACACTGAGGCGCGAAAGCGTGGGGAGCAAACAGGATTAGATACCCTGGTAGTCCACGCCGTAAACGATGAGTGCTAAGTGTTAGAGGGTTTCCGCCCTTTAGTGCTGAAGTTAACGCATTAAGCACTCCGCCTGGGGAGTACGGCCGCAAGGCTGAAACTCAAAGGAATTGACGGGGGCCCGCACAAGCGGTGGAGCATGTGGTTTAATTCGAAGCAACGCGAAGAACCTTACCAGGTCTTGACATCCTCTGAAAACCCTAGAGATAGGGCTTCTCCTTCGGGAGCAGAGTGACAGGTGGTGCATGGTTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCTTGATCTTAGTTGCCATCATTAAGTTGGGCACTCTAAGGTGACTGCCGGTGACAAACCGGAGGAAGGTGGGGATGACGTCAAATCATCATGCCCCTTATGACCTGGGCTACACACGTGCTACAATGGACGGTACAAAGAGCTGCAAGACCGCGAGGTGGAGCTAATCTCATAAAACCGTTCTCAGTTCGGATTGTAGGCTGCAACTCGCCTACATGAAGCTGGAATCGCTAGTAATCGCGGATCAGCATGCCGCGGTGAATACGTTCCCGGGCCTTGTACACACCGCCCGTCACACCACGAGAGTTTGTAACACCCGAAGTCGGTGGGG |
| FW507-4D12 | ME:0000190 | 16S sequence | ME:0000187 | forward | GAAGCATCGCAGCTATACATGCAGTCGAGCGNATGGATTAAGAGCTTGCTCTTATGAAGTTAGCGGCGGACGGGTGAGTAACACGTGGGTAACCTGCCCATAAGACTGGGATAACTCCGGGAAACCGGGGCTAATACCGGATAACATTTTGAACTGCATGGTTCGAAATTGAAAGGCGGCTTCGGCTGTCACTTATGGATGGACCCGCGTCGCATTAGCTAGTTGGTGAGGTAACGGCTCACCAAGGCAACGATGCGTAGCCGACCTGAGAGGGTGATCGGCCACACTGGGACTGAGACACGGCCCAGACTCCTACGGGAGGCAGCAGTAGGGAATCTTCCGCAATGGACGAAAGTCTGACGGAGCAACGCCGCGTGAGTGATGAAGGCTTTCGGGTCGTAAAACTCTGTTGTTAGGGAAGAACAAGTGCTAGTTGAATAAGCTGGCACCTTGACGGTACCTAACCAGAAAGCCACGGCTAACTACGTGCCAGCAGCCGCGGTAATACGTAGGTGGCAAGCGTTATCCGGAATTATTGGGCGTAAAGCGCGCGCAGGTGGTTTCTTAAGTCTGATGTGAAAGCCCACGGCTCAACCGTGGAGGGTCATTGGAAACTGGGAGACTTGAGTGCAGAAGAGGAAAGTGGAATTCCATGTGTAGCGGTGAAATGCGTAGAGATATGGAGGAACACCAGTGGCGAAGGCGACTTTCTGGTCTGTAACTGACACTGAGGCGCGAAAGCGTGGGGAGCAAACAGGATTAGATACCCTGGTAGTCCACGCCGTAAACGATGAGTGCTAAGTGTTAGAGGGTTTCCGCCCTTTAGTGCTGAAGTTAACGCATTAAGCACTCCGCCTGGGGAGTACGGCCGCAAGGCTGAAACTCAAAGGAATTGACGGGGGCCCGCACAAGCGGTGGAGCATGTGGTTTAATTCGAAGCAACGCGAAGAACCTTACCAGGTCTTGACATCCTCTGAAAACCCTAGAGATAGGGCTTCTCCTTCGGGAGCAGAGTGACAGGTGGTGCATGGTTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCTTGATCTTAGTTGCCATCATTAAGTTGGGCACTCTAAGGTGACTGCCGGTGACAAACCGGAGGAAGGTGGGGATGACGTCAAATCATCATGCCCCTTATGACCTGGGCTACACACGTGCTACAATGGACGGTACAAAGAGCTGCAAGACCGCGAGGTGGAGCTAATCTCATAAAACCGTTCTCAGTTCGGATTGTAGGCTGCAACTCGCCTACATGAAGCTGGAATCGCTAGTAATCGCGGATCAGCATGCCGCGGTGAATACGTTCCCGGGCCTTGTACACACCGCCCGTCACACCACGAGAGTTTGTAACACCCGAAGTCGGTGGGGTAACCTTTTTGGAGCCAGCCGCCTAAGTGACAGAGTT |

---

## Table: ddt_brick0000521

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_strain_name | string | Yes | {"description": "strain ID", "type": "foreign_key", "references": "sdt_strain.sdt_strain_name"} |
| link_context_read_set | string | Yes | {"description": "link, context=read set"} |
| link_context_genome | string | Yes | {"description": "link, context=genome"} |
| count_context_contig_count_unit | int | Yes | {"description": "count, context=contig", "unit": "count unit"} |
| count_context_gene_count_unit | int | Yes | {"description": "count, context=gene", "unit": "count unit"} |
| genome_completeness_method_checkm_percent | double | Yes | {"description": "genome completeness, method=CheckM", "unit": "percent"} |
| genome_contamination_method_checkm_percent | double | Yes | {"description": "genome contamination, method=CheckM", "unit": "percent"} |
| genome_n50_method_checkm_count_unit | int | Yes | {"description": "genome N50, method=CheckM", "unit": "count unit"} |
| read_coverage_statistic_average_count_unit | double | Yes | {"description": "read coverage, statistic=average", "unit": "count unit"} |
| jukes_cantor_distance_comment_between_sanger_16s_and_genomic_16s_substitutions_per_site | double | Yes | {"description": "Jukes-Cantor distance, comment=Between Sanger 16S and genomic 16S", "unit": "substitutions per site"} |

### Sample Data (5 rows)

| sdt_strain_name | link_context_read_set | link_context_genome | count_context_contig_count_unit | count_context_gene_count_unit | genome_completeness_method_checkm_percent | genome_contamination_method_checkm_percent | genome_n50_method_checkm_count_unit | read_coverage_statistic_average_count_unit | jukes_cantor_distance_comment_between_sanger_16s_and_genomic_16s_substitutions_per_site |
|---|---|---|---|---|---|---|---|---|---|
| DP16D-L5 | enigma-data-repository/genome_processing/DP16D-L5/reads/illumina/ | enigma-data-repository/genome_processing/DP16D-L5/assembliesAndAnnotations/DP16D-L5.1/ | 195 | 6173 | 100.0 | 0.13 | 82462 | 36.8525042466849 | 0.003856 |
| DP16D-R1 | enigma-data-repository/genome_processing/DP16D-R1/reads/illumina/ | enigma-data-repository/genome_processing/DP16D-R1/assembliesAndAnnotations/DP16D-R1.1/ | 125 | 6645 | 100.0 | 1.17 | 125507 | 27.971576692981095 | 0.001443 |
| DP16D-T1 | enigma-data-repository/genome_processing/DP16D-T1/reads/illumina/ | enigma-data-repository/genome_processing/DP16D-T1/assembliesAndAnnotations/DP16D-T1.1/ | 244 | 6184 | 100.0 | 0.58 | 55204 | 15.862196823815403 | 0.001434 |
| EB106-05-01-XG146 | enigma-data-repository/genome_processing/EB106-05-01-XG146/reads/illumina/ | enigma-data-repository/genome_processing/EB106-05-01-XG146/assembliesAndAnnotations/EB106-05-01-XG146.2/ | 3 | 7019 | 100.0 | 0.2 | 4112771 | NULL | 0.002177 |
| EB106-05-01-XG201 | enigma-data-repository/genome_processing/EB106-05-01-XG201/reads/illumina/ | enigma-data-repository/genome_processing/EB106-05-01-XG201/assembliesAndAnnotations/EB106-05-01-XG201.3/ | 3 | 4582 | 100.0 | 0.01 | 4825625 | NULL | 0.00247 |

---

## Table: ddt_brick0000522

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_strain_name | string | Yes | {"description": "strain ID", "type": "foreign_key", "references": "sdt_strain.sdt_strain_name"} |
| strain_relative_evolutionary_divergence_dimensionless_unit | double | Yes | {"description": "relative evolutionary divergence", "unit": "dimensionless unit"} |
| taxonomic_level_sys_oterm_id | string | Yes | {"description": "taxonomic level, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| taxonomic_level_sys_oterm_name | string | Yes | {"description": "taxonomic level"} |
| sdt_taxon_name | string | Yes | {"description": "taxon ID", "type": "foreign_key", "references": "sdt_taxon.sdt_taxon_name"} |

### Sample Data (5 rows)

| sdt_strain_name | strain_relative_evolutionary_divergence_dimensionless_unit | taxonomic_level_sys_oterm_id | taxonomic_level_sys_oterm_name | sdt_taxon_name |
|---|---|---|---|---|
| FW305-130 | NULL | ME:0000351 | taxonomic domain | Bacteria |
| FW305-130 | NULL | ME:0000252 | phylum | Actinomycetota |
| FW305-130 | NULL | ME:0000253 | class | Actinomycetes |
| FW305-130 | NULL | ME:0000254 | order | Mycobacteriales |
| FW305-130 | NULL | ME:0000255 | family | Mycobacteriaceae |

---

