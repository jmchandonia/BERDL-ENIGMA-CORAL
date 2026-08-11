# FEBa Genome, TnSeq Library, and Fitness Import Plan

## Goal

Model the reviewed ENIGMA-associated FEBa organisms in CORAL using the same
core relationships as the existing N2E2 data:

1. an exact FEBa assembly and annotation pair in the ENIGMA Data Repository;
2. corresponding `Genome` and `Gene` static records in CORAL;
3. corresponding `TnSeq_Library` static records linked to the FEBa genome;
4. one CORAL fitness brick per strain, linked by process provenance to the
   applicable TnSeq libraries.

The authoritative import source is the private ENIGMA Fitness Browser,
`enigma.fitprivate`. Public `kescience.fitnessbrowser` records are excluded
from this import, including for organisms present in both namespaces.

The private tables were generated from this immutable FEBa SQLite snapshot,
which remains the exact source artifact for private-data export and validation:

- file: `/scratch/jmc/fitprivate-rbtnseq/source/feba.db`
- size: 30,529,265,664 bytes
- SHA-256: `6b9e4edce230b2f82bff90242fe9ca46219598905d2eb775ab4f16ea446a1f11`
- prior reviewed private organism-to-strain mapping:
  `/scratch/jmc/fitprivate-rbtnseq/config/matched_organisms.tsv`.

The current strain authority and inclusion criterion is live
`enigma.coral.sdt_strain`. The 2026-08-10 live audit found:

- 48 public Fitness Browser organisms, of which 11 match current CORAL strains;
- 25 private fitprivate organisms, all of which match current CORAL strains;
- all 11 public matches are also present in fitprivate;
- 14 matching organisms occur only in fitprivate;
- no matching organism occurs only in the public source;
- 25 unique CORAL strains and 25 private source-organism datasets are therefore
  in scope.

The 11 dual-source organisms are `Btheta`, `Cup4G11`, `Keio`, `Pedo557`,
`Putida`, `acidovorax_3H11`, `pseudo13_GW456_L13`, `pseudo1_N1B4`,
`pseudo3_N2E3`, `pseudo5_N2C3_1`, and `pseudo6_N2E2`.

The 14 private-only organisms are `Brev2`, `Castellaniella_MT123`,
`Collimonas_GW821-FHT01A05`, `Enterobacter_XG201`, `Janthino_FHT05C05`,
`Janthinobacterium_agari`, `MT049`, `MT058`, `Phaga5`, `PseudoFW215-L2`,
`Rhodanobacter_MT42`, `rhodanobacter_10B01`, `rhodanobacter_R12`, and
`rhodanobacter_T8`.

Private scope contains 415 contigs, 139,581,003 bp, 126,072 source
gene/features, 46 distinct mutant libraries, 7,329 experiments, and 30,756,839
gene-fitness rows. The 11 matching public datasets are intentionally ignored.
The N2E2 audit established that its public measurements are an exact subset of
private, while public alone carries `pubId` annotations. Those publication
annotations will not be imported unless that metadata is added to the private
source or explicitly requested later.

## Phase 0: Freeze scope and build the work manifest

Create a dated, machine-readable work manifest with one row per private
`orgId` and a second strain-level rollup. Include columns for:

- source namespace, FEBa `orgId`, organism text, and source counts;
- authoritative CORAL strain ID and name;
- all distinct FEBa `mutantLibrary` values;
- EDR versions seen in active and withdrawn history;
- exact-match result and reused EDR version, if any;
- allocated new EDR version, if needed;
- target CORAL genome name;
- export, EDR publication, CORAL import, and validation status.

Fail before generating files if a selected source organism does not resolve to
exactly one live CORAL strain. Accepted matching forms are the exact current
strain name or the exact normalized full `genus species strain` display name;
record which form matched. Do not expand scope through unrestricted substring
or fuzzy matching.

## Phase 1: Inventory, deduplicate, and export EDR genomes

### 1.1 Inventory versions

Immediately before allocation, download the live `manifest.tsv` files from
both:

- `genome_processing/`
- `genome_processing_withdrawn/`

Parse every historical `<strain>.<N>` occurrence and inspect the actual active
and withdrawn object directories. Version numbers are reserved across both
trees, even when a manifest row only refers to a prior location as provenance.

For a required new genome:

- use `.1` if the strain has no prior numbered genome;
- otherwise use `max(all active and withdrawn N) + 1`;
- if that result is `.2`, use `.3` because `.2` is reserved;
- never fill an older numbering gap;
- re-read both manifests immediately before publication to catch concurrent
  additions.

For example, the FEBa N2E2 export is `FW300-N2E2.3` because `.1` and `.2`
already exist.

### 1.2 Generate a source fingerprint

For each distinct private source genome, construct a
formatting-independent fingerprint from:

- every `(scaffoldId, normalized uppercase sequence)` pair;
- every source feature's `(locusId, scaffoldId, begin, end, strand, type)`;
- source gene symbol, description, and RefSeq/UniProt aliases as a secondary
  annotation comparison.

Download only the candidate EDR FASTA/GFF pairs for that strain and parse them
into the same representation. Do not infer identity from genome length,
contig count, feature count, filename, or strain name alone.

An accepted active exact match is reused and no new EDR version is created.
Record the evidence and selected existing version in the work manifest. A
withdrawn-only exact match is a decision gate; do not silently link new CORAL
records to `genome_processing_withdrawn`.

### 1.3 Export unmatched genomes

Write each pair under:

```text
genome_processing/<strain>/assembliesAndAnnotations/<strain>.<N>/
```

with the repository-required names:

```text
<strain>_contigs.fasta
<strain>_Prodigal.gff
```

The FASTA must preserve the exact FEBa `ScaffoldSeq.scaffoldId` values and
sequences. The GFF must preserve FEBa `Gene.locusId` values, one-based inclusive
coordinates, strand, source feature type, descriptions, gene symbols, GC
fractions, and available RefSeq/UniProt cross-references. It must be valid GFF3
even though the required filename ends in `.gff`. Use `FEBa` as the source
column and add header comments documenting that the file was exported from
FEBa rather than re-annotated by Prodigal.

Use the same deterministic scaffold ordering in FASTA, GFF, and the later
CORAL `contig_number` mapping. Write source checksum, per-file checksum,
sequence checksum, counts, and the exporter version into a local export
manifest.

### 1.4 Validate and publish

Before publication, require:

- FASTA sequences exactly equal the source `ScaffoldSeq` values;
- all GFF sequence IDs exist in FASTA;
- all coordinates and strands are valid;
- every source `Gene` row appears exactly once as a gene feature;
- all IDs and parent links are valid GFF3;
- re-parsed fingerprints equal the pre-export source fingerprints;
- target versions and paths remain unoccupied in both EDR trees.

Present an EDR preflight containing reuse/new decisions, target paths, sizes,
checksums, and proposed manifest rows. Publish only after approval through the
normal source-controlled EDR workflow, update its manifest according to EDR
convention, and verify the resulting MinIO objects and checksums.

## Phase 2: Prepare and load CORAL static records

This phase has a hard all-genomes-first barrier. Complete the fingerprint,
reuse/export, EDR publication, and verified CORAL `Genome` record for all 25
organisms before generating or loading any `Gene`, `Condition`,
`TnSeq_Library`, process, or fitness-brick artifact. Genome preparation is
expected to be the longest part of the project. Make it resume-safe through the
dated work manifest, but do not advance individual organisms past this barrier
while other genomes remain unfinished.

### 2.1 Genome records

Generate a dated `Genome` TSV without assigning CORAL IDs. For each reused or
new EDR genome provide:

- name: `<strain>.<N>`;
- strain foreign key: reviewed `sdt_strain_name`;
- contig count from `ScaffoldSeq`;
- feature count from FEBa `Gene`;
- relative repository directory link beginning with
  `enigma-data-repository/genome_processing/`.

If an exact EDR genome already has a matching CORAL `Genome` row, reuse it.
Otherwise add the CORAL row even though no new EDR files were needed.

### 2.2 Gene records

Generate a dated `Gene` TSV without assigning CORAL IDs. Map each source row to:

- the selected CORAL genome name;
- a globally unique CORAL `Gene.gene_id` formatted as
  `<genome-identifier>:<FEBa-locusId>`, where `genome-identifier` is the
  version-specific CORAL `Genome.name` unique key rather than the strain name
  or the auto-assigned internal `Genome000...` ID;
- aliases containing the raw FEBa `locusId`, `sysName`, RefSeq, and UniProt IDs
  where available;
- the 1-based contig number determined by the exported FASTA order;
- strand, one-based start/stop coordinates, and FEBa description/function.

There are 5,854 source locus IDs reused between selected organisms (primarily
generic `GFF*` identifiers), while `sdt_gene_name` is globally unique. Qualify
every gene consistently, including source locus IDs that happen to be unique.
For example, use `FW300-N2E2.3:Pf6N2E2_1`, not
`FW300-N2E2:Pf6N2E2_1`. The source locus ID must also remain recoverable as an
alias and in the GFF.

CORAL defines unique identifiers as unconstrained required `text`; no typedef
regex or length limit applies. For generated qualified identifiers in this
import, nevertheless enforce these operational rules:

- use exactly one colon as the component separator;
- require the complete identifier to be non-empty and globally unique;
- do not use pipes, tabs, carriage returns, newlines, NULs, or other control
  characters;
- do not permit leading or trailing whitespace;
- preserve component text exactly rather than replacing spaces or punctuation;
- stop if a source component already contains a colon, because the qualified
  identifier would become ambiguous.

The reviewed FEBa `locusId` and `expName` values contain no colons, pipes,
edge whitespace, tabs, or newlines.

### 2.3 Condition records required by the bricks

The current fitness brick uses `sdt_condition_name` as a foreign key. FEBa
experiment names are not globally unique: 1,132 `expName` values occur in more
than one selected organism, and those rows can describe different conditions.
Generate dated `Condition` additions using the deterministic format
`<strain-name>:<expName>` rather than merging equal `expName` strings across
organisms. For example, use `FW300-N2E2:set1IT012`. Do not use pipe characters
to join identifier components, and apply the generated-identifier rules above.

Retain a crosswalk containing `(orgId, expName, condition_name,
mutantLibrary)`. This crosswalk drives both brick dimensions and library links.

### 2.4 TnSeq library records

Create one dated `TnSeq_Library` row per distinct `(orgId, mutantLibrary)`;
current scope has 46. Case, suffix, display-name, and collaborating-site labels
often share a base-library name in `timeZeroSet`, but this does not establish
that they are the same physical pool. Preserve all 46 records and retain a
crosswalk from each raw label to its apparent base-library lineage.

Link every library to the selected FEBa genome. Do not aggregate per-experiment
`Experiment.nMapped` into a library-level metric. Leave optional library
metrics null unless a defensible library-level source is identified.

`primers_model` is required by CORAL but is absent from FEBa. The dated
`tnseq_library_model_evidence_20260810.tsv` crosswalk records the earlier
evidence and confidence. The local mastersheet and explicit project decisions
below now assign a model to all 46 selected raw labels; retain whether each
assignment was direct, a case alias, same-organism prior-row inheritance, or
approved base-lineage inheritance. The existing N2E2 CORAL value
`model_pKMW7` conflicts with the source publication: `pseudo6_N2E2_ML5` is a
mariner library made with `pKMW3`, while `pKMW7` is the Tn5 vector.

#### 2026-08-10 local mutant-library mastersheet lookup

The local
`tnseq_genome_sources/Mutant_library_mastersheet_v2 - RB-TnSeq.tsv` was
examined for only the 25 selected private organisms. No other mastersheet
organisms and no web sources were consulted for this lookup. Twenty-four
organisms matched the mastersheet `Nickname` exactly. The remaining organism,
`pseudo5_N2C3_1`, matched the mastersheet spelling `pseudo5_N2-C3_1` and the
same N2C3 organism text.

The table below reports the mastersheet `Plasmid or Tn5` cell for every one of
the 46 raw `Experiment.mutantLibrary` values in the selected FEBa scope.
`case variant` means the source label differs from the mastersheet library name
only in letter case. `no named row` means the organism is present but that
specific library label is not. `blank` and `?` reproduce the mastersheet cell
verbatim. A later project decision assigns values to selected blank and `?`
cells by same-organism prior-row inheritance, as recorded below. Values such as `AMD...`,
`AMD290 (mariner)`, `EZ random barcode TN5`, and `Conjugation` are also retained
verbatim and must not be silently translated into a plasmid name.

| FEBa `orgId` | Selected FEBa `mutantLibrary` values and mastersheet findings |
| --- | --- |
| `acidovorax_3H11` | `acidovorax_3H11_ML3a` = `pKMW3` |
| `Btheta` | `Btheta_ML6` = `pTGG45_NN1` in the mastersheet but project decision retains `pTGG46_NN1`; `Btheta_ML6a`, `Btheta_ML6b` = no named row but approved base-lineage inheritance assigns `pTGG46_NN1` |
| `Brev2` | `Brev2_ML6a` = blank in the mastersheet; assign `pTGG39_NN1` by inheritance from the immediately preceding same-organism row, `Brev2_ML6` |
| `Castellaniella_MT123` | `Castellaniella_MT123_ML3` = `AMD290` |
| `Collimonas_GW821-FHT01A05` | `Collimonas_GW821-FHT01A05_ML4` = `AMD289` |
| `Cup4G11` | `cupriavidus_4G11_ML11`, `cupriavidus_4G11_ML11a` = `pKMW3`; `cupriavidus_4G11_ML11_FieldsLab`, `cupriavidus_4G11_ML11_JBEI` = no named row but approved base-lineage inheritance assigns `pKMW3` |
| `Enterobacter_XG201` | `Enterobacter_XG201_ML2` = `?` in the mastersheet; assign `AMD289` by inheritance from the immediately preceding same-organism row, `Enterobacter_XG201_ML1` |
| `Keio` | `Keio_ML9`, `Keio_ML9a` = `EZ random barcode TN5`; `KEIO_ML9a` = the same result by case-variant match; normalize these to `pKMW7`; `Keio_ML9a_ucsf` = no named row but approved base-lineage inheritance also assigns `pKMW7` |
| `Phaga5` | `Phaga5_ML11` = `AMD290 (mariner)` |
| `Janthino_FHT05C05` | `Janthino_FHT05C05_ML1` = `AMD3737` |
| `Janthinobacterium_agari` | `Janthinobacterium_agari_ML9` = `AMD3737` |
| `MT058` | `MT058_ML2` = `AMD290 (mariner)` |
| `Pedo557` | `Pedo557_ML3` = `pTGG43_NN2` |
| `pseudo1_N1B4` | `pseudo1_N1B4_ML1` = `pKMW3`; `PsfN1B4_ML1` = no named row but approved base-lineage inheritance assigns `pKMW3` |
| `pseudo5_N2C3_1` | `pseudo5_N2-C3_1_ML2`, `pseudo5_N2-C3_1_ML2B` = `pKMW3`; `pseudo5_N2-C3_1_ML2a` = `pKMW3` by case-variant match to mastersheet `..._ML2A` |
| `pseudo6_N2E2` | `pseudo6_N2E2_ML5` = `pKMW3`; `pseudo6_N2E2_ML5a`, `pseudo6_N2E2_ML5b` = `pKMW3` by case-variant matches to mastersheet `..._ML5A` and `..._ML5B`; `pseudo6_N2E2_ML5c` = no named row but approved base-lineage inheritance assigns `pKMW3` |
| `pseudo3_N2E3` | `pseudo3_N2E3_ML2` = `pKMW3`; `pseudo3_N2E3_ML2a` = `pKMW3` by case-variant match to mastersheet `..._ML2A` |
| `pseudo13_GW456_L13` | `pseudo13_ML2` = `Conjugation` in the mastersheet but normalize it to `pKMW3`, matching the surrounding same-organism lineage; `pseudo13_ML2a` = `pKMW3` by case-variant match to mastersheet `pseudo13_ML2A` |
| `Putida` | `Putida_ML5` = `pKMW3`; `putida_ML5` = the same result by case-variant match; `Putida_ML5_JBEI`, `Putida_ML5_PNNL`, `Putida_ML5a` = blank in the mastersheet but assign `pKMW3` by same-organism prior-row inheritance; all selected `Putida_ML5` variants therefore use `pKMW3` |
| `PseudoFW215-L2` | `PseudoFW215-L2_ML1` = `AMD290` |
| `rhodanobacter_10B01` | `rhodanobacter_10B01_ML12` = `pTKO49_NN1`; source library label `Rhodanobacter sp. FW104-10B01` = no named library row but is an approved display-name alias of the same ML12 lineage and is assigned `pTKO49_NN1` |
| `Rhodanobacter_MT42` | `Rhodanobacter_MT42_ML2` = `AMD1385` |
| `rhodanobacter_T8` | `rhodanobacter_T8_ML1` = `AMD1385` |
| `rhodanobacter_R12` | `rhodanobacter_R12_ML3` = `AMD290 (mariner)` |
| `MT049` | `MT049_ML3` = `AMD290 (mariner)` |

This local source resolves the previous `rhodanobacter_10B01_ML12` gap to
`pTKO49_NN1`. It also conflicts with the earlier external-evidence assignment
for `Btheta_ML6`: the mastersheet says `pTGG45_NN1`, not `pTGG46_NN1`.
The 2026-08-11 project decision is to retain `pTGG46_NN1` for `Btheta_ML6`;
the literal mastersheet value remains recorded above as conflicting source
provenance. The mastersheet does not justify inheritance for absent suffix or
collaborating-site rows.

The 2026-08-11 blank-or-`?` rule is to inherit the `Plasmid or Tn5` value from
the immediately preceding mastersheet row only when that row belongs to the
same organism. Re-checking the relevant mastersheet rows applies the rule as
follows:

- `Brev2_ML6a` follows `Brev2_ML6 = pTGG39_NN1`, so assign `pTGG39_NN1`;
- `Putida_ML5_JBEI`, `Putida_ML5_PNNL`, and `Putida_ML5a` follow the same-
  organism `Putida_ML5 = pKMW3` lineage, so assign `pKMW3` to all three;
- `Enterobacter_XG201_ML2 = ?` immediately follows same-organism
  `Enterobacter_XG201_ML1 = AMD289`, so assign `AMD289`.

Together with the direct and case-variant matches, every selected
`Putida_ML5` label therefore uses `pKMW3`. All selected mastersheet rows with a
literal blank or `?` cell are resolved by this rule. The rule does not create a
match for a selected library label that has no mastersheet row.

The 2026-08-11 project decision approves all six no-row base-lineage mappings:
`Btheta_ML6a` and `Btheta_ML6b` use `pTGG46_NN1`; the two
`cupriavidus_4G11_ML11` collaborating-site labels use `pKMW3`;
`Keio_ML9a_ucsf` uses `pKMW7`; `PsfN1B4_ML1` uses `pKMW3`;
`pseudo6_N2E2_ML5c` uses `pKMW3`; and the Rhodanobacter display-name label is
an alias of `rhodanobacter_10B01_ML12` and uses `pTKO49_NN1`. These are
supported by their FEBa `timeZeroSet` base-library names but remain recorded as
approved inheritance rather than direct mastersheet rows.

For CORAL, normalize a concrete mastersheet model token by prefixing `model_`:
for example, `pKMW3` becomes `model_pKMW3` and `AMD289` becomes
`model_AMD289`. Normalize `AMD290 (mariner)` to `model_AMD290` while preserving
`mariner` separately in the evidence/provenance crosswalk. Normalize
`EZ random barcode TN5` to `model_pKMW7`, and normalize the misplaced
`Conjugation` value for `pseudo13_ML2` to `model_pKMW3`. With the direct,
case-variant, prior-row, and approved base-lineage rules above, every one of the
46 selected libraries has an assigned CORAL `primers_model`.

### 2.5 Load and re-poll

Load in dependency order:

1. Genome additions;
2. Gene additions;
3. Condition additions;
4. TnSeq library additions.

Use dated files, let CORAL assign IDs, and stop on any rejected row. Re-poll
each updated static type and verify exact row counts, names, foreign keys,
coordinates, and EDR links before generating bricks.

## Phase 3: Generate fitness bricks and provenance

Create one new immutable brick per selected strain from private
`fitbyexp_<orgId>`/`genefitness` data. Do not alter an existing brick in place.
Record `enigma.fitprivate` and the immutable private `feba.db` snapshot in the
local import/audit manifest; do not include public Fitness Browser provenance.
In CORAL, retain only the condition-level external source link described in
Phase 3.1.

Proposed structure:

- type: `DA:0000010`, Gene Knockout Fitness;
- dimensions: gene and experiment/condition;
- gene dimension variable: CORAL gene foreign key;
- condition dimension variables:
  - CORAL condition foreign key;
  - CORAL TnSeq library foreign key, allowing one strain-level brick to contain
    experiments from multiple mutant libraries without creating a false third
    Cartesian dimension;
- data variable: fitness score in log-ratio units;
- second data variable: FEBa `t` statistic with `UO:0000186`, dimensionless
  unit.

### 3.1 Experiment metadata representation

Do not put the SQLite path or SQLite checksum into array-level metadata. Those
are local import/audit provenance and not CORAL array context. The one permitted
source reference is the documented condition-level foreign-key link to
`enigma.fitprivate` described below. Do not rely on a TSV sidecar for experiment
data: all imported experiment metadata must be stored in CORAL bricks.

The 2026-08-11 live BERDL audit of the legacy N2E2 fitness brick found:

- brick: `Brick0000006`, `tnseq_n2e2.ndarray`;
- status: active (`withdrawn_date` and `superceded_by_ddt_ndarray_id` are null);
- array metadata: empty (`[]`);
- shape: 4,994 genes by 184 conditions;
- gene dimension: only the `Gene` object reference;
- condition dimension: only the `Condition` object reference;
- data: only fitness score in `ME:0000379` log-ratio units.

The brick therefore does not store experiment descriptions, library identity,
time-zero set, personnel, date, media, temperature, pH, vessel, atmosphere,
treatments, growth-plate fields, read/QC metrics, or the FEBa `t` statistic.
The referenced static `Condition` object also contains only its generated ID
and unique condition name. The legacy condition names are unqualified values
such as `set12IT085`; they provide a join key, not rich condition metadata.

**Decision (approved 2026-08-11): use one separate TnSeq condition-metadata
brick.** Create one brick covering all 7,329 qualified TnSeq conditions. Its
single dimension is condition, keyed by the CORAL `Condition` object reference.
Store the FEBa experiment fields as typed variables in this brick, following
the existing CORAL pattern for condition-details metadata bricks. Each strain
fitness brick remains compact: gene and condition dimensions, the TnSeq-library
object reference aligned to the condition dimension, and the `fit` and `t` data
variables. The condition reference joins fitness values to the one-copy
metadata row. Do not duplicate the experiment metadata on each fitness brick's
experiment dimension; BERDL flattening would repeat it for every gene row.

Include `fitprivate_orgId` and `fitprivate_expName` as string variables aligned
to the condition dimension. Together they identify the source row and document
this composite external relationship:

`(fitprivate_orgId, fitprivate_expName) -> enigma.fitprivate.experiment(orgId, expName)`

Represent that target as the metadata brick's source link/relationship
description. It is not a CORAL `object_ref`, because the target is in another
BERDL namespace rather than a CORAL static-object table. The current BERDL
single-column foreign-key comment and validator cannot encode or enforce a
cross-namespace composite key, so preserve both source-key variables and run an
explicit anti-join against `enigma.fitprivate.experiment` after the CORAL-to-
BERDL sync. Require zero missing target pairs and zero ambiguous target pairs.

Example condition `FW300-N2E2:set1IT012` would occupy one row of
the shared TnSeq metadata brick with these values:

| Role | Example value |
| --- | --- |
| condition dimension object reference | `FW300-N2E2:set1IT012` |
| TnSeq library object reference | new ML5 library object linked to `FW300-N2E2.3`, with `model_pKMW3` |
| source identity/link | `fitprivate_orgId=FW300-N2E2`; `fitprivate_expName=set1IT012`; composite target `enigma.fitprivate.experiment(orgId, expName)` |
| source description | `expDesc=pyruvate (C)`; `expDescLong=Sodium pyruvate carbon source` |
| provenance fields | `timeZeroSet=3/9/2015 pseudo6_N2E2_ML5_set1`; `person=Mark`; `dateStarted=2015-03-09`; `expGroup=carbon source` |
| culture context | `media=RCH2_defined_noCarbon`; `mediaStrength=1.0` retained with its source semantics pending unit validation; temperature `30` degree Celsius; pH `7`; `24 deep-well microplate; Multitron`; aerobic; liquid; `750 rpm` |
| treatment | `condition_1=Sodium pyruvate`; `concentration_1=20`; `units_1=mM`; remaining treatment slots null |
| QC metadata | `nMapped=3384802`; `nUsed=1953597`; `cor12=0.177486159525045` with count/dimensionless units as applicable |

The N2E2 fitness brick would refer to that condition and its new library; for
gene `FW300-N2E2.3:Pf6N2E2_1`, the matrix cell would contain
`fit=-0.101775502641824` in log-ratio units and
`t=-0.542151246146515` in dimensionless units.

Object references must also be mirrored as strings in the generic ndarray.
Numeric variables must carry units: temperature uses degree
Celsius, pH uses the UO pH unit, count fields use `UO:0000189` (count unit),
ratios/statistics use `UO:0000186` (dimensionless unit), and fitness uses
`ME:0000379` (log ratio unit). Do not force a treatment concentration into a
numeric variable when its unit is missing or heterogeneous; preserve the raw
condition/concentration/unit values as brick variables and only add a
normalized numeric value when the source unit can be validated. Before brick
generation, review a column-by-column mapping of every source `Experiment`
column to its CORAL term, scalar type, unit, normalization, and missing-value
rule.

Use the exact FEBa gene and experiment ordering recorded in the generation
manifest. Validate that each source table is rectangular and contains no
orphan gene or experiment IDs. Current N2E2 is rectangular (5,133 genes x 388
experiments = 1,991,604 rows); validate all organisms independently rather
than assuming the same property.

Generate one file at a time with streaming/chunked source reads because the
selected scope contains 30,756,839 matrix cells and two numeric values (`fit`
and `t`) per cell. Validate each JSON fully before moving to the next strain.

Create process records that identify all applicable TnSeq libraries as inputs
and the strain fitness brick as output. First inspect the existing N2E2 process
term/protocol conventions and reuse them unless they cannot represent multiple
libraries. Never emit an empty or header-only `process_*.tsv`. If a non-empty
process file is generated, stop for CORAL loading and re-poll before proceeding.

After every brick load, verify:

- brick dimensions and row/value counts against FEBa;
- all gene, condition, and library foreign keys;
- sampled and aggregate fitness values against SQLite;
- producing-process and input-library provenance;
- no accidental replacement or withdrawal of older bricks.

## Phase 4: CORAL-to-BERDL sync and final audit

After all CORAL loads are complete:

1. re-poll CORAL static/system data and immutable bricks;
2. sync only changed static tables, process tables, ndarray metadata, and new
   brick tables into BERDL;
3. run foreign-key validation on every new/reloaded FK-bearing table and the
   explicit composite anti-join from the metadata brick to
   `enigma.fitprivate.experiment(orgId, expName)`;
4. verify all EDR genome links through MinIO;
5. verify genome, gene, library, condition, and brick row counts against the
   source/work manifests;
6. regenerate `schema/`, copy it to every dependent query/MCP skill, and push
   the skill changes through the established GitHub workflow.

After the new N2E2 genome, library, and FEBa brick have been loaded and fully
validated, obsolete the legacy ODPJKPKL-based N2E2 brick in favor of the new
brick. Do not modify the immutable legacy brick data. Use the established CORAL
replacement/obsoletion process convention so the old brick is an input and the
new brick is the output, in addition to the new brick's normal producing
process whose inputs are the applicable new TnSeq library objects.

Create a new N2E2 `TnSeq_Library` object with `model_pKMW3` linked to the newly
selected FEBa genome. Do not reuse the legacy library object linked to
`FW300-N2E2-reassembled.genome`, and do not rewrite that historical object's
genome link. Verify the new brick and all of its object references before
executing the obsoletion step.

## Decisions required before implementation

1. Decide how to handle an exact match found only under
   `genome_processing_withdrawn`.
2. Confirm EDR path-safe names for strains whose CORAL names contain spaces,
   and the expected manifest-row convention for each FASTA/GFF pair.
