# Database Schema: enigma_coral

Total Tables: 44

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
| FW127-D64 | CHEBI:33324 | strontium atom | 88.0 | True | 433.036384206056 | 3.90444907957109 | 0.0171 |
| FW127-D64 | CHEBI:33342 | zirconium atom | 90.0 | True | 0.164850102997522 | 0.056643754329317 | 0.0566 |
| FW127-D64 | CHEBI:33344 | niobium atom | 93.0 | True | 0.005850448472764 | 0.003772904991139 | 0.0091 |
| FW127-D64 | CHEBI:28685 | molybdenum atom | 95.0 | True | 0.008484774489076 | 0.023399294872951 | 0.0771 |
| FW127-D64 | CHEBI:22977 | cadmium atom | 114.0 | True | 140.533294897435 | 0.943642478870656 | 0.0182 |

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
| 36dace37b4f264444528e5c12c367af4 | TACGGGGGGGGCAAGCGTTGTTCGGAATTACTGGGCGTAAAGGGCTCGTAGGCGGCCGTTTTAGTCCGACGTGAAATCCCACGGCTCAACCGTGGAACTGCGTCGGATACTGAATGGCTTGAATCCAAGAGAGGGATGCGGAATTCCAGGTGTAGCGGTGAAATGCGTAGATATCTGGAGGAACACCGGTGGCGAAGGCGGCATCCTGGATTGGCATTGACGCTGAGGAGCGAAAGCCAGGGGAGCAAACGGG |
| 36daf00c1aec53fe5c3ccfedec020ebf | TACGGAGGATCCAAGCGTTATCCGGAATTACTGGGCGTAAAGAGTTGCGTAGGTGGCAGAGTAAGTAGACAGTGAAAGCGTGTGGCTCAACCATACACACATTGCCTAAACTGCTCAGCTAGAAGATGAGAGAGGTCACTGGAATTCCTAGTGTAGGAGTGAAATCCGTAGATATTAGGAGGAACACCGATGGCGTAGGCAGGTGACTGGCTCATTCTTGACACTAAGGCACGAAAGCGTGGGGAGCAAACGGG |
| 36db6446ae6c982e730ecc96246c0a64 | TACGAAGGTGGCAAGCGTTACTCGGAATTACTAGGCGTAAAGGGCAGGTAGGTGGTTTGATAAGTCTGTTGTGTAAGCTCCCGGCTTAACCGGGAGAGGTCAACGGATACTGTCAGACTTGAGTATAGGAGAGGATGCTGGAATTCCCGGTGTAGCGGTGAAATGCGCAGATATCGGGAGGAACACCAATGGCGAAAGCAGGCATCTGGACTATTACTGACGCTAAGCTGCGAAAGCTAGGGGAGCAAACAGG |
| 36db75e1c35c05403b8c5e77f0a5be9f | TACGAAGGGGGCTAGCGTTGTTCGGAATTACTGGGCGTAAAGCGTGCGCAGGCGGTTTTACAAGTCAGGGGTGAAAGCCCAGAGCTCAACTCTGGAAATGCCCTTGAAACTGTTAAGCTCGAGTGCGGGAGAGGTGAGTGGAATTCCCAGTGTAGAGGTGAAATTCGTAGATATTGGGAAGAACACCGGTGGCGAAGGCGGCTCACTGGCCCGTTTCTGACGCTCATGCACGATAGCGTGGGGATCAAACAGG |
| 36dba26a89cb0a9534fce3e83e369ef4 | TACGGGGGGGGCAAGCGTTGTTCGGAATTACTGGGCGTAAAGGGCTCGTAGGCGGCCAACTAAGTCAGACGTGAAATCCCTCGGCTTAACCGGGGAACTGCGTCTGATACTGGATGGCTTGAGTGTGGCAGAGGGGGGTGGAATTCCGCGTGTAGCAGTGAAATGCGTAGAGATGCGGAGGAACACCGATGGCGAAGGCAACCCCCTGGGCTGACACTGACGCTCAGGCACGAAAGCGTGGGGAGCAAACAGG |

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
| 0000672cf37091ed24be6595ac42659c | ME:0000351 | Taxonomic Domain | Bacteria |
| 0000672cf37091ed24be6595ac42659c | ME:0000252 | Phylum | Elusimicrobiota |
| 0000672cf37091ed24be6595ac42659c | ME:0000253 | Class | Elusimicrobia |
| 0000672cf37091ed24be6595ac42659c | ME:0000254 | Order | Lineage_IV |
| 0000672cf37091ed24be6595ac42659c | ME:0000255 | Family | Lineage_IV |

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
| 92762aeec32ee2df1dc7aa1cd079b8a2 | ME:0000254 | Order | Desulfobulbales |
| 92762aeec32ee2df1dc7aa1cd079b8a2 | ME:0000255 | Family | Desulfobulbaceae |
| 92762aeec32ee2df1dc7aa1cd079b8a2 | ME:0000256 | Genus | Desulfobulbus |
| 92774a391b34f2442444371af4bb1143 | ME:0000351 | Taxonomic Domain | Bacteria |
| 92774a391b34f2442444371af4bb1143 | ME:0000252 | Phylum | Proteobacteria |

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
| d25b9a35f0ffbb18c0a28a4c01488946 | SSO-L8-C10-00 | 0 |
| d25b9a35f0ffbb18c0a28a4c01488946 | SSO-L9B-C3-00 | 0 |
| d25b9a35f0ffbb18c0a28a4c01488946 | SSO-L9B-C5-00 | 0 |
| d25b9a35f0ffbb18c0a28a4c01488946 | SSO-L9B-C7-00 | 0 |
| d25b9a35f0ffbb18c0a28a4c01488946 | SSO-L9B-C10-00 | 0 |

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
| 1e663d96e33d1bc78ad5cc5879a85589 | U2-SZ1-20240313-F8 | 0 |
| 1e663d96e33d1bc78ad5cc5879a85589 | U2-SZ2-20240319-F01 | 0 |
| 1e663d96e33d1bc78ad5cc5879a85589 | U2-SZ2-20240319-F8 | 0 |
| e6bb966a6a98df0553ea4f5c449c98cb | L8-SZ1-20240314-F01 | 0 |
| e6bb966a6a98df0553ea4f5c449c98cb | L8-SZ1-20240314-F8 | 8 |

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
| 4d3f58e50214da6a52783e2bce1714d6 | L9-SZ2-20240909-F01 | 0 |
| 4d3f58e50214da6a52783e2bce1714d6 | U2-SZ1-20240918-F8 | 0 |
| 4d3f58e50214da6a52783e2bce1714d6 | U2-SZ1-20240918-F01 | 0 |
| 4d3f58e50214da6a52783e2bce1714d6 | U2-SZ2-20240918-F8 | 0 |
| 4d3f58e50214da6a52783e2bce1714d6 | U2-SZ2-20240918-F01 | 0 |

---

## Table: ddt_brick0000495

**Table Description:** DDT Brick table: Brick0000495

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
| FW305-130 | NULL | ME:0000351 | Taxonomic Domain | Bacteria |
| FW305-130 | NULL | ME:0000252 | Phylum | Actinomycetota |
| FW305-130 | NULL | ME:0000253 | Class | Actinomycetes |
| FW305-130 | NULL | ME:0000254 | Order | Mycobacteriales |
| FW305-130 | NULL | ME:0000255 | Family | Mycobacteriaceae |

---

## Table: ddt_brick0000501

**Table Description:** DDT Brick table: Brick0000501

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_strain_name | string | Yes | {"description": "strain ID", "type": "foreign_key", "references": "sdt_strain.sdt_strain_name"} |
| sdt_condition_name | string | Yes | {"description": "condition ID", "type": "foreign_key", "references": "sdt_condition.sdt_condition_name"} |
| description_comment_original_condition_description | string | Yes | {"description": "description, Comment=Original Condition Description"} |
| sdt_sample_name | string | Yes | {"description": "environmental sample ID", "type": "foreign_key", "references": "sdt_sample.sdt_sample_name"} |
| date_comment_sampling_date | string | Yes | {"description": "date, Comment=Sampling Date"} |
| sdt_location_name | string | Yes | {"description": "environmental sample location ID", "type": "foreign_key", "references": "sdt_location.sdt_location_name"} |
| enigma_campaign_sys_oterm_id | string | Yes | {"description": "ENIGMA Campaign, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| enigma_campaign_sys_oterm_name | string | Yes | {"description": "ENIGMA Campaign"} |
| enigma_labs_and_personnel_comment_contact_person_or_lab_sys_oterm_id | string | Yes | {"description": "ENIGMA Labs and Personnel, Comment=Contact Person or Lab, ontology term CURIE", "type": "foreign_key", "references": "sys_oterm.sys_oterm_id"} |
| enigma_labs_and_personnel_comment_contact_person_or_lab_sys_oterm_name | string | Yes | {"description": "ENIGMA Labs and Personnel, Comment=Contact Person or Lab"} |

### Sample Data (5 rows)

| sdt_strain_name | sdt_condition_name | description_comment_original_condition_description | sdt_sample_name | date_comment_sampling_date | sdt_location_name | enigma_campaign_sys_oterm_id | enigma_campaign_sys_oterm_name | enigma_labs_and_personnel_comment_contact_person_or_lab_sys_oterm_id | enigma_labs_and_personnel_comment_contact_person_or_lab_sys_oterm_name |
|---|---|---|---|---|---|---|---|---|---|
| FW305-130 | Anaerobic = 0; media name = LB, concentration = 25.0 (fold dilution); media name = Sediment Extract; temperature = 30.0 (degree Celsius) | Anaerobic = 0; media name = LB, concentration = 25.0 (fold dilution); media name = Sediment Extract; temperature = 30.0 (degree Celsius) | FW305-021115-2 | 2015-02-11 | FW-305 | ENIGMA:0000027 | Natural Organic Matter | ENIGMA:0000053 | Chakraborty Lab |
| FW305-BF6 | Anaerobic = 0; Aphotic = 1; media name = R2A, concentration = 25.0 (fold dilution); temperature = 25.0 (degree Celsius) | Anaerobic = 0; Aphotic = 1; media name = R2A, concentration = 25.0 (fold dilution); temperature = 25.0 (degree Celsius) | FW305-021115-2 | 2015-02-11 | FW-305 | ENIGMA:0000027 | Natural Organic Matter | ENIGMA:0000053 | Chakraborty Lab |
| FW104-L1 | Anaerobic = 0; media name = LB; temperature = 30.0 (degree Celsius) | Anaerobic = 0; media name = LB; temperature = 30.0 (degree Celsius) | FW104-67-11-14-12 | 2012-11-14 | FW-104 | ENIGMA:0000003 | 100 Well Survey | ENIGMA:0000053 | Chakraborty Lab |
| FW507-19G05 | Anaerobic = 0; media name = Eugon Broth; temperature = 30.0 (degree Celsius) | Anaerobic = 0; media name = Eugon Broth; temperature = 30.0 (degree Celsius) | FW507-49-11-26-12 | 2012-11-26 | FW-507 | ENIGMA:0000003 | 100 Well Survey | ENIGMA:0000053 | Chakraborty Lab |
| FW507-4D12 | Anaerobic = 0; media name = R2A; temperature = 30.0 (degree Celsius) | Anaerobic = 0; media name = R2A; temperature = 30.0 (degree Celsius) | FW507-49-11-26-12 | 2012-11-26 | FW-507 | ENIGMA:0000003 | 100 Well Survey | ENIGMA:0000053 | Chakraborty Lab |

---

## Table: ddt_brick0000507

**Table Description:** DDT Brick table: Brick0000507

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
| FW305-130 | ME:0000190 | 16S Sequence | ME:0000187 | Forward | GCAGTCGAGCGGTAAGGCCTTTCGGGGTACACGAGCGGCGAACGGGTGAGTAACACGTGGGTGATCTGCCCTGCACTTCGGGATAAGCCTGGGAAACTGGGTCTAATACCGGATATGACCTCAGGTTGCATGACTTGGGGTGGAAAGATTTATCGGTGCAGGATGGGCCCGCGGCCTATCAGCTTGTTGGTGGGGTAATGGCCTACCAAGGCGACGACGGGTAGCCGACCTGAGAGGGTGACCGGCCACACTGGGACTGAGACACGGCCCAGACTCCTACGGGAGGCAGCAGTGGGGAATATTGCACAATGGGCGAAAGCCTGATGCAGCGACGCCGCGTGAGGGATGACGGCCTTCGGGTTGTAAACCTCTTTCAGCAGGGACGAAGCGCAAGTGACGGTACCTGCAGAAGAAGCACCGGCTAACTACGTGCCAGCAGCCGCGGTAATACGTAGGGTGCAAGCGTTGTCCGGAATTACTGGGCGTAAAGAGTTCGTAGGCGGTTTGTCGCGTCGTTTGTGAAAACCAGCAGCTCAACTGCTGGCTTGCAGGCGATACGGGCAGACTTGAGTACTGCAGGGGAGACTGGAATTCCTGGTGTAGCGGTGAAATGCGCAGATATCAGGAGGAACACCGGTGGCGAAGGCGGGTCTCTGGGCAGTAACTGACGCTGAGGAACGAAAGCGTGGGTAGCGAACAGGATTAGATACCCTGGTAGTCCACGCCGTAAACGGTGGGCGCTAGGTGTGGGTTCCTTCCACGGAATCCGTGCCGTAGCTAACGCATTAAGCGCCCCGCCTGGGGAGTACGGCCGCAAGGCTAAAACTCAAAGGAATTGACGGGGGCCCGCACAAGCGGCGGAGCATGTGGATTAATTCGATGCAACGCGAAGAACCTTACCTGGGGTTTGACATATACCGGAAAGCTGCAGAGATGTGGCCCCCCTTGTGGTCGGTATACAGGTGGTGCATGGCTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCCTATCTTATGTTGCCAGCACGTTATGGTGGGGACTCGTAAGAGACTGCCGGGGTCAACTCGGAGGAAGGTGGGGACGACGTCAAGTCATCATGCCCCTTATGTCCAGGGCTTCACACATGCTACAATGGCCAGTACAGAGGGCTGCGAGACCGTGAGGTGGAGCGAATCCCTTAAAGCTGGTCTCAGTTCGGATCGGGGTCTGCAACTCGACCCCGTGAAGTNGGAGTCGCTAGTAATCGCAGATCAGCAACGCTGCGGTGAATACGTTCCCGGGCCTTGTACACACCGCCCGTCACGTCATGAAAGTCGGTAACACCCGAAGCCGGTGGCT |
| FW305-BF6 | ME:0000190 | 16S Sequence | ME:0000187 | Forward | TGCAGTCGAGCGGACTTGTAGGAGCTTGCTCCTGCAGGTTAGCGGCGGACGGGTGAGTAACACGTGGGCAACCTACCTGTAAGACTGGGATAACTTCGGGAAACCGGAGCTAATACCGGATGACATAAAGGAACTCCTGTTCCTTTATTGAAAGATGGCTTCGGCTATCACTTACAGATGGGCCCGCGGCGCAGTAGCTAGTTGGTGAGGTAACGGCTCACCAAGGCGACGATGCGTAGCCGACCTGAGAGGGTGATCGGCCACACTGGGACTGAGACACGGCCCAGACTCCTACGGGAGGCAGCAGTAGGGAATCTTCCGCAATGGACGAAAGTCTGACGGAGCAACGCCGCGTGAACGATGAAGGCCTTCGGGTCGTAAAGTTCTGTTGTTAGGGAAGAACAAGTGCTAGTTAAATAAGCTGGCACCTTGACGGTACCTAACCAGAAAGCCACGGCTAACTACGTGCCAGCAGCCGCGGTAATACGTAGGTGGCAAGCGTTGTCCGGAATTATTGGGCGTAAAGCGCGCGCAGGCGGTTTCTTAAGTCTGATGTGAAAGCCCCCGGCTCAACCGGGGAGGGTCATTGGAAACTGGGAAACTTGAGTGCAGAAGAGGAAAGTGGAATTCCAAGTGTAGCGGTGAAATGCGTAGAGATTTGGAGGAACACCAGTGGCGAAGGCGACTTTCTGGTCTGTAACTGACGCTGAGGCGCGAAAGCGTGGGGAGCAAACAGGATTAGATACCCTGGTAGTCCACGCTGTAAACGATGAGTGCTAAGTGTTAGAGGGTTTCCGCCCTTTAGTGCTGAAGTTAACGCATTAAGCACTCCGCCTGGGGAGTACGGTCGCAAGACTGAAACTCAAAGGAATTGACGGGGGCCCGCACAAGTGGTGGAGCATGTGGTTTAATTCGAAGCAACGCGAAGAACCTTACCAGGTCTTGACATCCTCTGACAACCCTAGAGATAGGGCTTTCCCTTCGGGGACAGAGTGACAGGTGGTGCATGGTTGTCGTCAGCTCGTGTCGTGAGATGTTNGGGTTAAGTCCCGCAACGAGCGCAACCCTTGATCTTAGTTGCCAGCATTTAGTTGGGCACTCTAAGGTGACTGCCGGTGACAAACCGGAGGAAGGTGGGGATGACGTCAAATCATCATGCCCCTTATGACCTGGGCTACACACGTGCTACAATGGATAGTACAAAGGGTTGCAAGACCGCGAGGTGGAGCTAATCCCATAAAACTATTCTCAGTTCGGATTGTAGGCTGCAACTCGCCTACATGAAGCCGGAATCACTAGTAATCGCGGATCAGCATGCCGCGGTGAATACGTTCCCGGGCCTTGTACACACCGCCCGTCACACCACGAGAGNTTGTAACACCCGAAGTCGGTNGGGTA |
| FW104-L1 | ME:0000190 | 16S Sequence | ME:0000187 | Forward | GTCGAGCGAATGGATTAAGAGCTTGCTCTTATGAAGTTAGCGGCGGACGGGTGAGTAACACGTGGGTAACCTGCCCATAAGACTGGGATAACTCCGGGAAACCGGGGCTAATACCGGATAACATTTTGAACCGCATGGTTCGAAATTGAAAGGCGGCTTCGGCTGTCACTTATGGATGGACCCGCGTCGCATTAGCTAGTTGGTGAGGTAACGGCTCACCAAGGCAACGATGCGTAGCCGACCTGAGAGGGTGATCGGCCACACTGGGACTGAGACACGGCCCAGACTCCTACGGGAGGCAGCAGTAGGGAATCTTCCGCAATGGACGAAAGTCTGACGGAGCAACGCCGCGTGAGTGATGAAGGCTTTCGGGTCGTAAAACTCTGTTGTTAGGGAAGAACAAGTGCTAGTTGAATAAGCTGGCACCTTGACGGTACCTAACCAGAAAGCCACGGCTAACTACGTGCCAGCAGCCGCGGTAATACGTAGGTGGCAAGCGTTATCCGGAATTATTGGGCGTAAAGCGCGCGCAGGTGGTTTCTTAAGTCTGATGTGAAAGCCCACGGCTCAACCGTGGAGGGTCATTGGAAACTGGGAGACTTGAGTGCAGAAGAGGAAAGTGGAATTCCATGTGTAGCGGTGAAATGCGTAGAGATATGGAGGAACACCAGTGGCGAAGGCGACTTTCTGGTCTGTAACTGACACTGAGGCGCGAAAGCGTGGGGAGCAAACAGGATTAGATACCCTGGTAGTCCACGCCGTAAACGATGAGTGCTAAGTGTTAGAGGGTTTCCGCCCTTTAGTGCTGAAGTTAACGCATTAAGCACTCCGCCTGGGGAGTACGGCCGCAAGGCTGAAACTCAAAGGAATTGACGGGGGCCCGCACAAGCGGTGGAGCATGTGGTTTAATTCGAAGCAACGCGAAGAACCTTACCAGGTCTTGACATCCTCTGACAACCCTAGAGATAGGGCTTCTCCTTCGGGAGCAGAGTGACAGGTGGTGCATGGTTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCTTGATCTTAGTTGCCATCATTAAGTTGGGCACTCTAAGTGACTGCCGGTGACAAACCGGAGGAAGGTGGGGATGACGTCAAATCATCATGCCCCTTATGACCTGG |
| FW507-19G05 | ME:0000190 | 16S Sequence | ME:0000187 | Forward | TGCAGTCGAGCGATGGATTAAGAGCTTGCTCTTATGAAGTTAGCGGGGGAAGGGAGAGAAACACGTGGGTAACCTGCCCATAAGACTGGGATAACTCCGGGAAACCGGGGCTAATACCGGATAACATTTTGAACTGCATGGTTCGAAATTGAAAGGCGGCTTCGGCTGTCACTTATGGATGGACCCGCGTCGCATTAGCTAGTTGGTGAGGTAACGGCTCACCAAGGCAACGATGCGTAGCCGACCTGAGAGGGTGATCGGCCACACTGGGACTGAGACACGGCCCAGACTCCTACGGGAGGCAGCAGTAGGGAATCTTCCGCAATGGACGAAAGTCTGACGGAGCAACGCCGCGTGAGTGATGAAGGCTTTCGGGTCGTAAAACTCTGTTGTTAGGGAAGAACAAGTGCTAGTTGAATAAGCTGGCACCTTGACGGTACCTAACCAGAAAGCCACGGCTAACTACGTGCCAGCAGCCGCGGTAATACGTAGGTGGCAAGCGTTATCCGGAATTATTGGGCGTAAAGCGCGCGCAGGTGGTTTCTTAAGTCTGATGTGAAAGCCCACGGCTCAACCGTGGAGGGTCATTGGAAACTGGGAGACTTGAGTGCAGAAGAGGAAAGTGGAATTCCATGTGTAGCGGTGAAATGCGTAGAGATATGGAGGAACACCAGTGGCGAAGGCGACTTTCTGGTCTGTAACTGACACTGAGGCGCGAAAGCGTGGGGAGCAAACAGGATTAGATACCCTGGTAGTCCACGCCGTAAACGATGAGTGCTAAGTGTTAGAGGGTTTCCGCCCTTTAGTGCTGAAGTTAACGCATTAAGCACTCCGCCTGGGGAGTACGGCCGCAAGGCTGAAACTCAAAGGAATTGACGGGGGCCCGCACAAGCGGTGGAGCATGTGGTTTAATTCGAAGCAACGCGAAGAACCTTACCAGGTCTTGACATCCTCTGAAAACCCTAGAGATAGGGCTTCTCCTTCGGGAGCAGAGTGACAGGTGGTGCATGGTTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCTTGATCTTAGTTGCCATCATTAAGTTGGGCACTCTAAGGTGACTGCCGGTGACAAACCGGAGGAAGGTGGGGATGACGTCAAATCATCATGCCCCTTATGACCTGGGCTACACACGTGCTACAATGGACGGTACAAAGAGCTGCAAGACCGCGAGGTGGAGCTAATCTCATAAAACCGTTCTCAGTTCGGATTGTAGGCTGCAACTCGCCTACATGAAGCTGGAATCGCTAGTAATCGCGGATCAGCATGCCGCGGTGAATACGTTCCCGGGCCTTGTACACACCGCCCGTCACACCACGAGAGTTTGTAACACCCGAAGTCGGTGGGG |
| FW507-4D12 | ME:0000190 | 16S Sequence | ME:0000187 | Forward | GAAGCATCGCAGCTATACATGCAGTCGAGCGNATGGATTAAGAGCTTGCTCTTATGAAGTTAGCGGCGGACGGGTGAGTAACACGTGGGTAACCTGCCCATAAGACTGGGATAACTCCGGGAAACCGGGGCTAATACCGGATAACATTTTGAACTGCATGGTTCGAAATTGAAAGGCGGCTTCGGCTGTCACTTATGGATGGACCCGCGTCGCATTAGCTAGTTGGTGAGGTAACGGCTCACCAAGGCAACGATGCGTAGCCGACCTGAGAGGGTGATCGGCCACACTGGGACTGAGACACGGCCCAGACTCCTACGGGAGGCAGCAGTAGGGAATCTTCCGCAATGGACGAAAGTCTGACGGAGCAACGCCGCGTGAGTGATGAAGGCTTTCGGGTCGTAAAACTCTGTTGTTAGGGAAGAACAAGTGCTAGTTGAATAAGCTGGCACCTTGACGGTACCTAACCAGAAAGCCACGGCTAACTACGTGCCAGCAGCCGCGGTAATACGTAGGTGGCAAGCGTTATCCGGAATTATTGGGCGTAAAGCGCGCGCAGGTGGTTTCTTAAGTCTGATGTGAAAGCCCACGGCTCAACCGTGGAGGGTCATTGGAAACTGGGAGACTTGAGTGCAGAAGAGGAAAGTGGAATTCCATGTGTAGCGGTGAAATGCGTAGAGATATGGAGGAACACCAGTGGCGAAGGCGACTTTCTGGTCTGTAACTGACACTGAGGCGCGAAAGCGTGGGGAGCAAACAGGATTAGATACCCTGGTAGTCCACGCCGTAAACGATGAGTGCTAAGTGTTAGAGGGTTTCCGCCCTTTAGTGCTGAAGTTAACGCATTAAGCACTCCGCCTGGGGAGTACGGCCGCAAGGCTGAAACTCAAAGGAATTGACGGGGGCCCGCACAAGCGGTGGAGCATGTGGTTTAATTCGAAGCAACGCGAAGAACCTTACCAGGTCTTGACATCCTCTGAAAACCCTAGAGATAGGGCTTCTCCTTCGGGAGCAGAGTGACAGGTGGTGCATGGTTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCTTGATCTTAGTTGCCATCATTAAGTTGGGCACTCTAAGGTGACTGCCGGTGACAAACCGGAGGAAGGTGGGGATGACGTCAAATCATCATGCCCCTTATGACCTGGGCTACACACGTGCTACAATGGACGGTACAAAGAGCTGCAAGACCGCGAGGTGGAGCTAATCTCATAAAACCGTTCTCAGTTCGGATTGTAGGCTGCAACTCGCCTACATGAAGCTGGAATCGCTAGTAATCGCGGATCAGCATGCCGCGGTGAATACGTTCCCGGGCCTTGTACACACCGCCCGTCACACCACGAGAGTTTGTAACACCCGAAGTCGGTGGGGTAACCTTTTTGGAGCCAGCCGCCTAAGTGACAGAGTT |

---

## Table: ddt_brick0000508

**Table Description:** DDT Brick table: Brick0000508

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_sample_name | string | Yes | {"description": "environmental sample ID", "type": "foreign_key", "references": "sdt_sample.sdt_sample_name"} |
| sdt_strain_name | string | Yes | {"description": "strain ID", "type": "foreign_key", "references": "sdt_strain.sdt_strain_name"} |
| sdt_genome_name | string | Yes | {"description": "genome ID", "type": "foreign_key", "references": "sdt_genome.sdt_genome_name"} |
| read_coverage_statistic_average_comment_cov80_average_coverage_after_trimming_highest_and_lowest_10_percent_count_unit | double | Yes | {"description": "read coverage, Statistic=Average, Comment=cov80 average coverage after trimming highest and lowest 10 percent", "unit": "count unit"} |
| sequence_identity_statistic_average_comment_average_percent_identity_of_aligned_reads_percent | double | Yes | {"description": "sequence identity, Statistic=Average, Comment=average percent identity of aligned reads", "unit": "percent"} |
| read_coverage_comment_percent_of_1kb_chunks_of_genome_covered_by_at_least_one_read_percent | double | Yes | {"description": "read coverage, Comment=percent of 1kb chunks of genome covered by at least one read", "unit": "percent"} |

### Sample Data (5 rows)

| sdt_sample_name | sdt_strain_name | sdt_genome_name | read_coverage_statistic_average_comment_cov80_average_coverage_after_trimming_highest_and_lowest_10_percent_count_unit | sequence_identity_statistic_average_comment_average_percent_identity_of_aligned_reads_percent | read_coverage_comment_percent_of_1kb_chunks_of_genome_covered_by_at_least_one_read_percent |
|---|---|---|---|---|---|
| 20240529-EFP01-F01 | CPT15-335-S11 | CPT15-335-S11.1 | 3.671087 | 99.3486 | 89.6596 |
| 20240529-EFP01-F01 | CPT15-335-S12 | CPT15-335-S12.1 | 3.689159 | 99.35079999999999 | 89.2848 |
| 20240529-EFP01-F01 | CPT15-335-S13 | CPT15-335-S13.1 | 3.674033 | 99.34920000000001 | 89.6854 |
| 20240529-EFP01-F01 | CPT15-335-S13 | CPT15-335-S13.3 | 3.730473 | 99.3451 | 89.5223 |
| 20240529-EFP01-F01 | DP16D-E2 | DP16D-E2.1 | 1.834835 | 96.9795 | 58.741699999999994 |

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
| ME:0000001 | ME:0000000 | context_measurement_ontology | context | [] | Root of all Context and Measurement Terms. | ['ORef:ME:0000001'] | {'data_type': 'oterm_ref', 'is_hidden': 'true', 'is_microtype': 'true', 'is_valid_data_variable': 'true', 'is_valid_property': 'true'} |
| ME:0000002 | ME:0000001 | context_measurement_ontology | experimental context | [] | Context describing experimental design. | ['ORef:ME:0000002'] | {'data_type': 'oterm_ref', 'is_microtype': 'true', 'is_valid_data_variable': 'true', 'is_valid_property': 'true'} |
| ME:0000003 | ME:0000002 | context_measurement_ontology | series type | [] | Context describing the purpose of a series. | ['ORef:ME:0000003'] | {'data_type': 'oterm_ref', 'is_microtype': 'true', 'is_valid_data_variable': 'true', 'is_valid_property': 'true'} |
| ME:0000004 | ME:0000003 | context_measurement_ontology | time series | [] | A time series, in which a series of measurements was taken at different timepoints. | NULL | {'data_type': 'float', 'is_microtype': 'true', 'is_valid_data_variable': 'true', 'is_valid_dimension': 'true', 'is_valid_dimension_variable': 'true', 'is_valid_property': 'true', 'valid_units_parent': 'UO:0000003'} |

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
| Process0044816 | PROCESS:0000020 | 16S Sequencing | ENIGMA:0000053 | Chakraborty Lab | ENIGMA:0000004 | ENIGMA Microbial Isolation Characterization | NULL | NULL | NULL | ['Strain:Strain0000455'] | ['Brick-0000064:Brick0000383'] |
| Process0044817 | PROCESS:0000020 | 16S Sequencing | ENIGMA:0000053 | Chakraborty Lab | ENIGMA:0000004 | ENIGMA Microbial Isolation Characterization | NULL | NULL | NULL | ['Strain:Strain0000456'] | ['Brick-0000064:Brick0000383'] |
| Process0044818 | PROCESS:0000020 | 16S Sequencing | ENIGMA:0000053 | Chakraborty Lab | ENIGMA:0000004 | ENIGMA Microbial Isolation Characterization | NULL | NULL | NULL | ['Strain:Strain0000457'] | ['Brick-0000064:Brick0000383'] |
| Process0044819 | PROCESS:0000020 | 16S Sequencing | ENIGMA:0000053 | Chakraborty Lab | ENIGMA:0000004 | ENIGMA Microbial Isolation Characterization | NULL | NULL | NULL | ['Strain:Strain0000458'] | ['Brick-0000064:Brick0000383'] |
| Process0044820 | PROCESS:0000020 | 16S Sequencing | ENIGMA:0000053 | Chakraborty Lab | ENIGMA:0000004 | ENIGMA Microbial Isolation Characterization | NULL | NULL | NULL | ['Strain:Strain0000459'] | ['Brick-0000064:Brick0000383'] |

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
| Location0000450 | MLSB5-14.8 | 35.97567215 | -84.27469319 | CONTINENT:0000007 | North America | COUNTRY:0000263 | USA | Tennessee (TN), Oak Ridge Reservation (ORR) | ENVO:01000221 | temperate woodland biome | ENVO:01000002 | water well |
| Location0000451 | MLSB6-16.8 | 35.97567215 | -84.27469319 | CONTINENT:0000007 | North America | COUNTRY:0000263 | USA | Tennessee (TN), Oak Ridge Reservation (ORR) | ENVO:01000221 | temperate woodland biome | ENVO:01000002 | water well |
| Location0000452 | MLSB7-19.2 | 35.97567215 | -84.27469319 | CONTINENT:0000007 | North America | COUNTRY:0000263 | USA | Tennessee (TN), Oak Ridge Reservation (ORR) | ENVO:01000221 | temperate woodland biome | ENVO:01000002 | water well |
| Location0000453 | MLSC1-19.2 | 35.97564541 | -84.27472289 | CONTINENT:0000007 | North America | COUNTRY:0000263 | USA | Tennessee (TN), Oak Ridge Reservation (ORR) | ENVO:01000221 | temperate woodland biome | ENVO:01000002 | water well |
| Location0000454 | MLSC2-18.0 | 35.97564541 | -84.27472289 | CONTINENT:0000007 | North America | COUNTRY:0000263 | USA | Tennessee (TN), Oak Ridge Reservation (ORR) | ENVO:01000221 | temperate woodland biome | ENVO:01000002 | water well |

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
| Strain0001578 | FW305-C-30-11 | NULL | NULL | NULL | [] |
| Strain0001579 | FW305-C-30-12 | NULL | NULL | NULL | [] |
| Strain0001580 | FW305-C-30-13 | NULL | NULL | NULL | [] |
| Strain0001581 | FW305-C-30-14 | NULL | NULL | NULL | [] |
| Strain0001582 | FW305-C-30-16 | NULL | NULL | NULL | [] |

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
| Community0001105 | Isolate MT109 | ME:0000235 | Isolate Community | NULL | NULL | Cd (0.5 uM) + Co (3 uM) + Cu (1 uM) + Fe (1 uM) + Mn (10 uM) + Ni (15 uM) + U (10 uM) + fumarate + lactate + nitrate (20 mM) + pH5.5 + aerobic | ['MT109'] | NULL |
| Community0001106 | Isolate FW106-XG1 | ME:0000235 | Isolate Community | NULL | NULL | 25 °C + anaerobic + Basal + fumarate | ['FW106-XG1'] | NULL |
| Community0001107 | Isolate FW115-XG2 | ME:0000235 | Isolate Community | NULL | NULL | 25 °C + anaerobic + Basal + carbon mix | ['FW115-XG2'] | NULL |
| Community0001108 | Isolate GW271-XG3 | ME:0000235 | Isolate Community | NULL | NULL | 25 °C + anaerobic + Basal + carbon mix | ['GW271-XG3'] | NULL |
| Community0001109 | Isolate GW271-XG4 | ME:0000235 | Isolate Community | NULL | NULL | 25 °C + anaerobic + LB | ['GW271-XG4'] | NULL |

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
| Reads0012933 | 148125/GW821-FHT10F05-cutadapt-trim.reads_unpaired_fwd | 36970 | ME:0000114 | Single End Read | ME:0000117 | Illumina | https://narrative.kbase.us/#dataview/148125/GW821-FHT10F05-cutadapt-trim.reads_unpaired_fwd |
| Reads0012934 | 148125/GW821-FHT10F05-cutadapt-trim.reads_unpaired_rev | 18459 | ME:0000114 | Single End Read | ME:0000117 | Illumina | https://narrative.kbase.us/#dataview/148125/GW821-FHT10F05-cutadapt-trim.reads_unpaired_rev |
| Reads0012935 | 148125/GW821-FHT10A06-cutadapt-trim.reads_unpaired_fwd | 32818 | ME:0000114 | Single End Read | ME:0000117 | Illumina | https://narrative.kbase.us/#dataview/148125/GW821-FHT10A06-cutadapt-trim.reads_unpaired_fwd |
| Reads0012936 | 148125/GW821-FHT10A06-cutadapt-trim.reads_unpaired_rev | 17525 | ME:0000114 | Single End Read | ME:0000117 | Illumina | https://narrative.kbase.us/#dataview/148125/GW821-FHT10A06-cutadapt-trim.reads_unpaired_rev |
| Reads0012937 | 148125/GW821-FHT10C06-cutadapt-trim.reads_unpaired_fwd | 35494 | ME:0000114 | Single End Read | ME:0000117 | Illumina | https://narrative.kbase.us/#dataview/148125/GW821-FHT10C06-cutadapt-trim.reads_unpaired_fwd |

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
| Assembly0000857 | 154265/GW821-FHT12H02.contigs/1 | GW821-FHT12H02 | 20 | https://narrative.kbase.us/#dataview/154265/GW821-FHT12H02.contigs/1 |
| Assembly0000858 | 154265/GW821-FHT12C03.contigs/1 | GW821-FHT12C03 | 83 | https://narrative.kbase.us/#dataview/154265/GW821-FHT12C03.contigs/1 |
| Assembly0000859 | 154265/GW101-3H11.contigs/2 | GW101-3H11 | 19 | https://narrative.kbase.us/#dataview/154265/GW101-3H11.contigs/2 |
| Assembly0000860 | 154265/GW821-FHT10B04.contigs/2 | GW821-FHT10B04 | 166 | https://narrative.kbase.us/#dataview/154265/GW821-FHT10B04.contigs/2 |
| Assembly0000861 | 154265/GW821-FHT12D04.contigs/1 | GW821-FHT12D04 | 2784 | https://narrative.kbase.us/#dataview/154265/GW821-FHT12D04.contigs/1 |

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
| Genome0003353 | 54002/GW821-FHT07D05.genome | GW821-FHT07D05 | 2805 | 12591 | https://narrative.kbase.us/#dataview/54002/GW821-FHT07D05.genome |
| Genome0003354 | 54002/FW305-97A.genome | FW305-97A | 223 | 8263 | https://narrative.kbase.us/#dataview/54002/FW305-97A.genome |
| Genome0003355 | 54002/GW823-FHT01A01.genome | GW823-FHT01A01 | 1698 | 5179 | https://narrative.kbase.us/#dataview/54002/GW823-FHT01A01.genome |
| Genome0003356 | 54002/GW821-FHT07B01.genome | GW821-FHT07B01 | 1428 | 5569 | https://narrative.kbase.us/#dataview/54002/GW821-FHT07B01.genome |
| Genome0003357 | 54002/GW822-FHT01C09.genome | GW822-FHT01C09 | 52 | 33 | https://narrative.kbase.us/#dataview/54002/GW822-FHT01C09.genome |

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
| Gene0007508 | ODPJKPKL_03780 | FW300-N2E2.genome | [] | 1 | + | 4340935 | 4341402 | hypothetical protein |
| Gene0007509 | ODPJKPKL_03781 | FW300-N2E2.genome | [] | 1 | + | 4341399 | 4342127 | 3-oxoacyl-[acyl-carrier-protein] reductase FabG |
| Gene0007510 | ODPJKPKL_03782 | FW300-N2E2.genome | [] | 1 | + | 4342127 | 4343353 | 3-oxoacyl-[acyl-carrier-protein] synthase 2 |
| Gene0007511 | ODPJKPKL_03783 | FW300-N2E2.genome | [] | 1 | + | 4343396 | 4343842 | hypothetical protein |
| Gene0007512 | ODPJKPKL_03785 | FW300-N2E2.genome | [] | 1 | + | 4344885 | 4345844 | Soluble epoxide hydrolase |

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
| Bin0000156 | FW300_bin_30 | FW300.contigs | ['FW300_contig_918', 'FW300_contig_1050', 'FW300_contig_1169', 'FW300_contig_1242', 'FW300_contig_1258', 'FW300_contig_1356', 'FW300_contig_1409', 'FW300_contig_1505', 'FW300_contig_1683', 'FW300_contig_1943', 'FW300_contig_1968', 'FW300_contig_2017', 'FW300_contig_2020', 'FW300_contig_2030', 'FW300_contig_2067', 'FW300_contig_2355', 'FW300_contig_2569', 'FW300_contig_2714', 'FW300_contig_2784', 'FW300_contig_2840', 'FW300_contig_2993', 'FW300_contig_3188', 'FW300_contig_3364', 'FW300_contig_3416', 'FW300_contig_3771', 'FW300_contig_3806', 'FW300_contig_3839', 'FW300_contig_3864', 'FW300_contig_4064', 'FW300_contig_4079', 'FW300_contig_4096', 'FW300_contig_4199', 'FW300_contig_4213', 'FW300_contig_4235', 'FW300_contig_4374', 'FW300_contig_4728', 'FW300_contig_5039', 'FW300_contig_5183', 'FW300_contig_5348', 'FW300_contig_5389', 'FW300_contig_5809', 'FW300_contig_5911', 'FW300_contig_6132', 'FW300_contig_6247', 'FW300_contig_6250', 'FW300_contig_6462', 'FW300_contig_6464', 'FW300_contig_6498', 'FW300_contig_6607', 'FW300_contig_6895', 'FW300_contig_7003', 'FW300_contig_7271', 'FW300_contig_7625', 'FW300_contig_8078', 'FW300_contig_8418', 'FW300_contig_8856', 'FW300_contig_9074', 'FW300_contig_9534', 'FW300_contig_9568', 'FW300_contig_9612', 'FW300_contig_9738', 'FW300_contig_9897', 'FW300_contig_9901', 'FW300_contig_10005', 'FW300_contig_10033', 'FW300_contig_10036', 'FW300_contig_10127', 'FW300_contig_10425', 'FW300_contig_10610', 'FW300_contig_11136', 'FW300_contig_11563', 'FW300_contig_11578', 'FW300_contig_11837', 'FW300_contig_11869', 'FW300_contig_11905', 'FW300_contig_12004', 'FW300_contig_12069', 'FW300_contig_12363', 'FW300_contig_12694', 'FW300_contig_13254', 'FW300_contig_13346', 'FW300_contig_13474', 'FW300_contig_13946', 'FW300_contig_13982', 'FW300_contig_13998', 'FW300_contig_14127', 'FW300_contig_14128', 'FW300_contig_14236', 'FW300_contig_14851', 'FW300_contig_15049', 'FW300_contig_15454', 'FW300_contig_15733', 'FW300_contig_15858', 'FW300_contig_15901', 'FW300_contig_16444', 'FW300_contig_16604', 'FW300_contig_18041', 'FW300_contig_18664', 'FW300_contig_18818', 'FW300_contig_19054', 'FW300_contig_19119', 'FW300_contig_20373', 'FW300_contig_21713', 'FW300_contig_22391', 'FW300_contig_22459', 'FW300_contig_22754', 'FW300_contig_23837', 'FW300_contig_24177', 'FW300_contig_24203'] |
| Bin0000157 | FW300_bin_31 | FW300.contigs | ['FW300_contig_4', 'FW300_contig_6', 'FW300_contig_7', 'FW300_contig_10', 'FW300_contig_11', 'FW300_contig_16', 'FW300_contig_19', 'FW300_contig_22', 'FW300_contig_28', 'FW300_contig_30', 'FW300_contig_36', 'FW300_contig_42', 'FW300_contig_46', 'FW300_contig_48', 'FW300_contig_49', 'FW300_contig_61', 'FW300_contig_67', 'FW300_contig_75', 'FW300_contig_99', 'FW300_contig_102', 'FW300_contig_123', 'FW300_contig_135', 'FW300_contig_179', 'FW300_contig_181', 'FW300_contig_187', 'FW300_contig_202', 'FW300_contig_215', 'FW300_contig_265', 'FW300_contig_308', 'FW300_contig_450', 'FW300_contig_486', 'FW300_contig_496', 'FW300_contig_694', 'FW300_contig_723', 'FW300_contig_1052', 'FW300_contig_1144', 'FW300_contig_1266', 'FW300_contig_6642', 'FW300_contig_10334', 'FW300_contig_12755', 'FW300_contig_16386', 'FW300_contig_18883'] |
| Bin0000158 | FW300_bin_32 | FW300.contigs | ['FW300_contig_92', 'FW300_contig_98', 'FW300_contig_112', 'FW300_contig_113', 'FW300_contig_119', 'FW300_contig_164', 'FW300_contig_177', 'FW300_contig_180', 'FW300_contig_183', 'FW300_contig_196', 'FW300_contig_200', 'FW300_contig_203', 'FW300_contig_213', 'FW300_contig_246', 'FW300_contig_252', 'FW300_contig_253', 'FW300_contig_262', 'FW300_contig_270', 'FW300_contig_287', 'FW300_contig_327', 'FW300_contig_352', 'FW300_contig_360', 'FW300_contig_361', 'FW300_contig_373', 'FW300_contig_375', 'FW300_contig_392', 'FW300_contig_411', 'FW300_contig_413', 'FW300_contig_417', 'FW300_contig_435', 'FW300_contig_453', 'FW300_contig_520', 'FW300_contig_553', 'FW300_contig_556', 'FW300_contig_578', 'FW300_contig_579', 'FW300_contig_596', 'FW300_contig_613', 'FW300_contig_629', 'FW300_contig_647', 'FW300_contig_683', 'FW300_contig_698', 'FW300_contig_717', 'FW300_contig_751', 'FW300_contig_771', 'FW300_contig_774', 'FW300_contig_784', 'FW300_contig_792', 'FW300_contig_797', 'FW300_contig_847', 'FW300_contig_863', 'FW300_contig_896', 'FW300_contig_898', 'FW300_contig_905', 'FW300_contig_931', 'FW300_contig_956', 'FW300_contig_958', 'FW300_contig_985', 'FW300_contig_995', 'FW300_contig_1164', 'FW300_contig_1207', 'FW300_contig_1339', 'FW300_contig_1373', 'FW300_contig_1380', 'FW300_contig_1395', 'FW300_contig_1403', 'FW300_contig_1411', 'FW300_contig_1469', 'FW300_contig_1585', 'FW300_contig_1639', 'FW300_contig_1644', 'FW300_contig_1679', 'FW300_contig_1680', 'FW300_contig_1709', 'FW300_contig_1759', 'FW300_contig_1787', 'FW300_contig_1845', 'FW300_contig_1877', 'FW300_contig_1907', 'FW300_contig_1965', 'FW300_contig_2180', 'FW300_contig_2237', 'FW300_contig_2284', 'FW300_contig_2300', 'FW300_contig_2432', 'FW300_contig_2756', 'FW300_contig_2894', 'FW300_contig_3080', 'FW300_contig_3146', 'FW300_contig_3282', 'FW300_contig_3630', 'FW300_contig_3632', 'FW300_contig_3876', 'FW300_contig_3933', 'FW300_contig_4158', 'FW300_contig_4258', 'FW300_contig_4280', 'FW300_contig_4655', 'FW300_contig_4949', 'FW300_contig_5345', 'FW300_contig_5666', 'FW300_contig_5730', 'FW300_contig_5756', 'FW300_contig_5797', 'FW300_contig_6166', 'FW300_contig_6586', 'FW300_contig_6623', 'FW300_contig_6753', 'FW300_contig_7255', 'FW300_contig_7703', 'FW300_contig_7923', 'FW300_contig_8156', 'FW300_contig_9004', 'FW300_contig_11770', 'FW300_contig_12092', 'FW300_contig_12801', 'FW300_contig_12818', 'FW300_contig_13491', 'FW300_contig_13879', 'FW300_contig_14295', 'FW300_contig_14652', 'FW300_contig_15895', 'FW300_contig_19080', 'FW300_contig_21873'] |
| Bin0000159 | FW300_bin_33 | FW300.contigs | ['FW300_contig_63', 'FW300_contig_70', 'FW300_contig_89', 'FW300_contig_105', 'FW300_contig_107', 'FW300_contig_144', 'FW300_contig_206', 'FW300_contig_207', 'FW300_contig_222', 'FW300_contig_237', 'FW300_contig_254', 'FW300_contig_272', 'FW300_contig_292', 'FW300_contig_319', 'FW300_contig_328', 'FW300_contig_362', 'FW300_contig_394', 'FW300_contig_416', 'FW300_contig_445', 'FW300_contig_464', 'FW300_contig_483', 'FW300_contig_532', 'FW300_contig_537', 'FW300_contig_540', 'FW300_contig_551', 'FW300_contig_552', 'FW300_contig_564', 'FW300_contig_568', 'FW300_contig_580', 'FW300_contig_585', 'FW300_contig_601', 'FW300_contig_633', 'FW300_contig_665', 'FW300_contig_704', 'FW300_contig_726', 'FW300_contig_728', 'FW300_contig_733', 'FW300_contig_734', 'FW300_contig_795', 'FW300_contig_812', 'FW300_contig_832', 'FW300_contig_836', 'FW300_contig_838', 'FW300_contig_845', 'FW300_contig_848', 'FW300_contig_913', 'FW300_contig_923', 'FW300_contig_939', 'FW300_contig_945', 'FW300_contig_946', 'FW300_contig_949', 'FW300_contig_997', 'FW300_contig_1057', 'FW300_contig_1062', 'FW300_contig_1105', 'FW300_contig_1115', 'FW300_contig_1130', 'FW300_contig_1163', 'FW300_contig_1279', 'FW300_contig_1289', 'FW300_contig_1314', 'FW300_contig_1383', 'FW300_contig_1429', 'FW300_contig_1439', 'FW300_contig_1517', 'FW300_contig_1549', 'FW300_contig_1596', 'FW300_contig_1602', 'FW300_contig_1614', 'FW300_contig_1663', 'FW300_contig_1755', 'FW300_contig_1957', 'FW300_contig_1975', 'FW300_contig_1993', 'FW300_contig_2008', 'FW300_contig_2118', 'FW300_contig_2124', 'FW300_contig_2478', 'FW300_contig_2529', 'FW300_contig_2579', 'FW300_contig_2665', 'FW300_contig_2745', 'FW300_contig_3000', 'FW300_contig_3019', 'FW300_contig_3150', 'FW300_contig_3155', 'FW300_contig_3338', 'FW300_contig_3376', 'FW300_contig_3413', 'FW300_contig_3845', 'FW300_contig_4027', 'FW300_contig_4653', 'FW300_contig_5210', 'FW300_contig_5229', 'FW300_contig_5379', 'FW300_contig_5536', 'FW300_contig_6043', 'FW300_contig_6080', 'FW300_contig_6121', 'FW300_contig_6364', 'FW300_contig_6415', 'FW300_contig_6930', 'FW300_contig_7019', 'FW300_contig_7184', 'FW300_contig_8488', 'FW300_contig_8583', 'FW300_contig_8706', 'FW300_contig_8709', 'FW300_contig_9095', 'FW300_contig_9390', 'FW300_contig_9530', 'FW300_contig_9533', 'FW300_contig_9885', 'FW300_contig_10454', 'FW300_contig_10699', 'FW300_contig_11001', 'FW300_contig_11195', 'FW300_contig_12597', 'FW300_contig_13415', 'FW300_contig_13480', 'FW300_contig_13846', 'FW300_contig_14006', 'FW300_contig_14711', 'FW300_contig_15202', 'FW300_contig_15484', 'FW300_contig_16176', 'FW300_contig_16317', 'FW300_contig_17497', 'FW300_contig_17616', 'FW300_contig_17773', 'FW300_contig_17829', 'FW300_contig_17981', 'FW300_contig_19479', 'FW300_contig_23855'] |
| Bin0000160 | FW300_bin_34 | FW300.contigs | ['FW300_contig_703', 'FW300_contig_3230', 'FW300_contig_3414', 'FW300_contig_3739', 'FW300_contig_3878', 'FW300_contig_4346', 'FW300_contig_4670', 'FW300_contig_4953', 'FW300_contig_5288', 'FW300_contig_5332', 'FW300_contig_5518', 'FW300_contig_6206', 'FW300_contig_6420', 'FW300_contig_7176', 'FW300_contig_7332', 'FW300_contig_7475', 'FW300_contig_7773', 'FW300_contig_7803', 'FW300_contig_7928', 'FW300_contig_8314', 'FW300_contig_8580', 'FW300_contig_8604', 'FW300_contig_8647', 'FW300_contig_8654', 'FW300_contig_8757', 'FW300_contig_8772', 'FW300_contig_8829', 'FW300_contig_9404', 'FW300_contig_9469', 'FW300_contig_9798', 'FW300_contig_9912', 'FW300_contig_10062', 'FW300_contig_10108', 'FW300_contig_10210', 'FW300_contig_10336', 'FW300_contig_10358', 'FW300_contig_10502', 'FW300_contig_10563', 'FW300_contig_10629', 'FW300_contig_10660', 'FW300_contig_10686', 'FW300_contig_10849', 'FW300_contig_10963', 'FW300_contig_10980', 'FW300_contig_10993', 'FW300_contig_11114', 'FW300_contig_11247', 'FW300_contig_11272', 'FW300_contig_11300', 'FW300_contig_11436', 'FW300_contig_11462', 'FW300_contig_11623', 'FW300_contig_11797', 'FW300_contig_11886', 'FW300_contig_12019', 'FW300_contig_12081', 'FW300_contig_12130', 'FW300_contig_12141', 'FW300_contig_12260', 'FW300_contig_12356', 'FW300_contig_12392', 'FW300_contig_12431', 'FW300_contig_12439', 'FW300_contig_12447', 'FW300_contig_12603', 'FW300_contig_12605', 'FW300_contig_12644', 'FW300_contig_12754', 'FW300_contig_12832', 'FW300_contig_12867', 'FW300_contig_12869', 'FW300_contig_13006', 'FW300_contig_13018', 'FW300_contig_13076', 'FW300_contig_13275', 'FW300_contig_13279', 'FW300_contig_13307', 'FW300_contig_13311', 'FW300_contig_13349', 'FW300_contig_13363', 'FW300_contig_13371', 'FW300_contig_13374', 'FW300_contig_13384', 'FW300_contig_13433', 'FW300_contig_13449', 'FW300_contig_13504', 'FW300_contig_13521', 'FW300_contig_13586', 'FW300_contig_13600', 'FW300_contig_13628', 'FW300_contig_13726', 'FW300_contig_13775', 'FW300_contig_13787', 'FW300_contig_13798', 'FW300_contig_13865', 'FW300_contig_13883', 'FW300_contig_13920', 'FW300_contig_13931', 'FW300_contig_13943', 'FW300_contig_13950', 'FW300_contig_13957', 'FW300_contig_13990', 'FW300_contig_14011', 'FW300_contig_14031', 'FW300_contig_14104', 'FW300_contig_14117', 'FW300_contig_14199', 'FW300_contig_14202', 'FW300_contig_14228', 'FW300_contig_14239', 'FW300_contig_14562', 'FW300_contig_14770', 'FW300_contig_14790', 'FW300_contig_14795', 'FW300_contig_14817', 'FW300_contig_14818', 'FW300_contig_14863', 'FW300_contig_15053', 'FW300_contig_15133', 'FW300_contig_15146', 'FW300_contig_15147', 'FW300_contig_15208', 'FW300_contig_15299', 'FW300_contig_15310', 'FW300_contig_15339', 'FW300_contig_15496', 'FW300_contig_15543', 'FW300_contig_15554', 'FW300_contig_15571', 'FW300_contig_15573', 'FW300_contig_15675', 'FW300_contig_15779', 'FW300_contig_15789', 'FW300_contig_15823', 'FW300_contig_15861', 'FW300_contig_15973', 'FW300_contig_15995', 'FW300_contig_16160', 'FW300_contig_16161', 'FW300_contig_16221', 'FW300_contig_16252', 'FW300_contig_16331', 'FW300_contig_16345', 'FW300_contig_16346', 'FW300_contig_16433', 'FW300_contig_16451', 'FW300_contig_16479', 'FW300_contig_16481', 'FW300_contig_16498', 'FW300_contig_16502', 'FW300_contig_16586', 'FW300_contig_16701', 'FW300_contig_16719', 'FW300_contig_16738', 'FW300_contig_16755', 'FW300_contig_16783', 'FW300_contig_16815', 'FW300_contig_16824', 'FW300_contig_16859', 'FW300_contig_16872', 'FW300_contig_16887', 'FW300_contig_16940', 'FW300_contig_16981', 'FW300_contig_17002', 'FW300_contig_17010', 'FW300_contig_17015', 'FW300_contig_17051', 'FW300_contig_17079', 'FW300_contig_17098', 'FW300_contig_17138', 'FW300_contig_17170', 'FW300_contig_17284', 'FW300_contig_17342', 'FW300_contig_17431', 'FW300_contig_17448', 'FW300_contig_17565', 'FW300_contig_17582', 'FW300_contig_17611', 'FW300_contig_17641', 'FW300_contig_17647', 'FW300_contig_17648', 'FW300_contig_17705', 'FW300_contig_17733', 'FW300_contig_17802', 'FW300_contig_17872', 'FW300_contig_17930', 'FW300_contig_17936', 'FW300_contig_18002', 'FW300_contig_18045', 'FW300_contig_18054', 'FW300_contig_18089', 'FW300_contig_18147', 'FW300_contig_18177', 'FW300_contig_18228', 'FW300_contig_18230', 'FW300_contig_18242', 'FW300_contig_18285', 'FW300_contig_18304', 'FW300_contig_18331', 'FW300_contig_18383', 'FW300_contig_18470', 'FW300_contig_18484', 'FW300_contig_18492', 'FW300_contig_18530', 'FW300_contig_18536', 'FW300_contig_18560', 'FW300_contig_18600', 'FW300_contig_18611', 'FW300_contig_18656', 'FW300_contig_18697', 'FW300_contig_18756', 'FW300_contig_18782', 'FW300_contig_18784', 'FW300_contig_18785', 'FW300_contig_18819', 'FW300_contig_18836', 'FW300_contig_18926', 'FW300_contig_18937', 'FW300_contig_18940', 'FW300_contig_18956', 'FW300_contig_18964', 'FW300_contig_18986', 'FW300_contig_18999', 'FW300_contig_19092', 'FW300_contig_19123', 'FW300_contig_19157', 'FW300_contig_19196', 'FW300_contig_19216', 'FW300_contig_19244', 'FW300_contig_19273', 'FW300_contig_19276', 'FW300_contig_19317', 'FW300_contig_19335', 'FW300_contig_19336', 'FW300_contig_19371', 'FW300_contig_19375', 'FW300_contig_19408', 'FW300_contig_19430', 'FW300_contig_19433', 'FW300_contig_19488', 'FW300_contig_19574', 'FW300_contig_19590', 'FW300_contig_19633', 'FW300_contig_19679', 'FW300_contig_19681', 'FW300_contig_19700', 'FW300_contig_19721', 'FW300_contig_19735', 'FW300_contig_19776', 'FW300_contig_19882', 'FW300_contig_20023', 'FW300_contig_20037', 'FW300_contig_20061', 'FW300_contig_20206', 'FW300_contig_20265', 'FW300_contig_20376', 'FW300_contig_20493', 'FW300_contig_20657', 'FW300_contig_20680', 'FW300_contig_20711', 'FW300_contig_20780', 'FW300_contig_20785', 'FW300_contig_20794', 'FW300_contig_20800', 'FW300_contig_20849', 'FW300_contig_20882', 'FW300_contig_20914', 'FW300_contig_20926', 'FW300_contig_20994', 'FW300_contig_21008', 'FW300_contig_21235', 'FW300_contig_21251', 'FW300_contig_21275', 'FW300_contig_21290', 'FW300_contig_21336', 'FW300_contig_21361', 'FW300_contig_21428', 'FW300_contig_21434', 'FW300_contig_21446', 'FW300_contig_21469', 'FW300_contig_21504', 'FW300_contig_21506', 'FW300_contig_21600', 'FW300_contig_21601', 'FW300_contig_21628', 'FW300_contig_21722', 'FW300_contig_21784', 'FW300_contig_21814', 'FW300_contig_21824', 'FW300_contig_21830', 'FW300_contig_21851', 'FW300_contig_21861', 'FW300_contig_21961', 'FW300_contig_21985', 'FW300_contig_22028', 'FW300_contig_22043', 'FW300_contig_22067', 'FW300_contig_22069', 'FW300_contig_22095', 'FW300_contig_22120', 'FW300_contig_22127', 'FW300_contig_22159', 'FW300_contig_22160', 'FW300_contig_22166', 'FW300_contig_22260', 'FW300_contig_22366', 'FW300_contig_22472', 'FW300_contig_22478', 'FW300_contig_22494', 'FW300_contig_22510', 'FW300_contig_22542', 'FW300_contig_22551', 'FW300_contig_22584', 'FW300_contig_22602', 'FW300_contig_22626', 'FW300_contig_22729', 'FW300_contig_22811', 'FW300_contig_22815', 'FW300_contig_22837', 'FW300_contig_22844', 'FW300_contig_22887', 'FW300_contig_22971', 'FW300_contig_23018', 'FW300_contig_23039', 'FW300_contig_23053', 'FW300_contig_23128', 'FW300_contig_23141', 'FW300_contig_23187', 'FW300_contig_23194', 'FW300_contig_23196', 'FW300_contig_23246', 'FW300_contig_23289', 'FW300_contig_23319', 'FW300_contig_23346', 'FW300_contig_23359', 'FW300_contig_23372', 'FW300_contig_23407', 'FW300_contig_23429', 'FW300_contig_23464', 'FW300_contig_23505', 'FW300_contig_23547', 'FW300_contig_23568', 'FW300_contig_23576', 'FW300_contig_23691', 'FW300_contig_23712', 'FW300_contig_23723', 'FW300_contig_23753', 'FW300_contig_23769', 'FW300_contig_23783', 'FW300_contig_23794', 'FW300_contig_23827', 'FW300_contig_23841', 'FW300_contig_23854', 'FW300_contig_23910', 'FW300_contig_23911', 'FW300_contig_23999', 'FW300_contig_24002', 'FW300_contig_24024', 'FW300_contig_24053', 'FW300_contig_24070', 'FW300_contig_24080', 'FW300_contig_24095', 'FW300_contig_24110', 'FW300_contig_24129', 'FW300_contig_24143', 'FW300_contig_24148', 'FW300_contig_24161', 'FW300_contig_24163', 'FW300_contig_24197', 'FW300_contig_24205', 'FW300_contig_24207', 'FW300_contig_24212', 'FW300_contig_24216', 'FW300_contig_24228', 'FW300_contig_24237', 'FW300_contig_24244', 'FW300_contig_24325', 'FW300_contig_24363', 'FW300_contig_24382', 'FW300_contig_24384', 'FW300_contig_24408', 'FW300_contig_24526', 'FW300_contig_24528', 'FW300_contig_24531', 'FW300_contig_24540', 'FW300_contig_24605', 'FW300_contig_24652', 'FW300_contig_24654'] |

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
| Protocol0000001 | spencer-2017-cutadapt | The program Cutadapt v1.12 was used to remove adapter sequences with parameters -a CTGTCTCTTAT -A CTGTCTCTTAT (Martin, 2011).  | NULL |
| Protocol0000002 | spencer-2017-trimmomatic | We performed sliding window quality filtering with Trimmomatic v0.36 using parameters (-phred33 LEADING:3 TRAILING:3 SLIDINGWINDOW:5:20 MINLEN:50) (Bolger et al., 2014) | NULL |
| Protocol0000003 | spencer-2017-spades | All genomes were assembled de novo using SPAdes v3.9.0 with the following options (-k 21,33,55,77 --careful) (Bankevich et al., 2012) | NULL |
| Protocol0000004 | chandonia-2019-cutadapt | kb_cutadapt 1.0.7 (cutadapt 1.18) with options: {
                    "input_reads": name,
                    "output_object_name": cut_name,
                    "5P": None,
                    "3P": {
                        "adapter_sequence_3P": "CTGTCTCTTAT",
                        "anchored_3P": 0
                    },
                    "error_tolerance": 0.1,
                    "min_overlap_length": 3,
                    "min_read_length": 50,
                    "discard_untrimmed": "0"
                }, | https://narrative.kbase.us/narrative/ws.38718.obj.1 |
| Protocol0000005 | chandonia-2019-trimmomatic | kb_trimmomatic 1.2.13 (trimmomatic 0.36) with options: {
                    "input_reads_ref": name,
                    "output_reads_name": trim_name,
                    "translate_to_phred33": "1",
                    "adapter_clip": None,
                    "sliding_window": {
                        "sliding_window_size": 5,
                        "sliding_window_min_quality": 20
                    },
                    "crop_length": 0,
                    "head_crop_length": 0,
                    "leading_min_quality": 3,
                    "trailing_min_quality": 3,
                    "min_length": 50
                }, | https://narrative.kbase.us/narrative/ws.38718.obj.1 |

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
| Image0000055 | EB271-05-03-aodc.jpg | EB271-05-03 AODC image | image/jpeg | 673845 | 2560,1920 | /images/EB271-05-03-aodc.jpg |
| Image0000056 | EB271-05-04-aodc.jpg | EB271-05-04 AODC image | image/jpeg | 656716 | 2560,1920 | /images/EB271-05-04-aodc.jpg |
| Image0000057 | FW106-2016-11-16-10ml-aodc.jpg | FW106-2016-11-16-10ml AODC image | image/jpeg | 714792 | 2560,1920 | /images/FW106-2016-11-16-10ml-aodc.jpg |
| Image0000058 | FW106-2016-11-16-1ml-aodc.jpg | FW106-2016-11-16-1ml AODC image | image/jpeg | 605010 | 2560,1920 | /images/FW106-2016-11-16-1ml-aodc.jpg |
| Image0000059 | FW106-2017-04-05-1ml-aodc.jpg | FW106-2017-04-05-1ml AODC image | image/jpeg | 606245 | 2560,1920 | /images/FW106-2017-04-05-1ml-aodc.jpg |

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
| DubSeq_Library0000001 | Escherichia-coli-BW25113.dubseq_library | Escherichia-coli-BW25113.genome | NULL |
| DubSeq_Library0000002 | Pseudomonas-putida-KT2440.dubseq_library | Pseudomonas-putida-KT2440.genome | NULL |
| DubSeq_Library0000003 | Bacteroides-thetaiotaomicron-VPI-5482.dubseq_library | Bacteroides-thetaiotaomicron-VPI-5482.genome | NULL |

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
| Community | defined_strains | defined_sdt_strain_names | [text] | False | False | False | [Strain.name] | NULL | List of strains that comprise the community, if the community is defined | NULL | NULL | ME:0000044 | strain ID |
| Community | description | sdt_community_description | text | False | False | False | NULL | NULL | Free-text field providing additional details or notes about the community | NULL | NULL | ME:0000202 | description |
| Reads | id | sdt_reads_id | text | True | True | False | NULL | NULL | Unique identifier for each reads dataset (Primary key) | NULL | NULL | ME:0000273 | internal Reads ID |
| Reads | name | sdt_reads_name | text | True | False | True | NULL | NULL | Unique name for the reads | NULL | NULL | ME:0000248 | reads ID |
| Reads | read_count | read_count_count_unit | int | True | False | False | NULL | NULL | Number of reads | UO:0000189 | count unit | ME:0000126 | count |

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
| 9d30df1c09b60bb791f16b9f769c6335 | GW800-12-12-12 0.2 micron filter | 1 | 0 |
| 9d30df1c09b60bb791f16b9f769c6335 | GW800-12-12-12 10 micron filter | 1 | 0 |
| 9d30df1c09b60bb791f16b9f769c6335 | GW921-86-1-28-13 0.2 micron filter | 1 | 0 |
| 9d30df1c09b60bb791f16b9f769c6335 | GW921-86-1-28-13 10 micron filter | 1 | 0 |
| 9d30df1c09b60bb791f16b9f769c6335 | GW925-68-1-28-13 0.2 micron filter | 1 | 0 |

---

