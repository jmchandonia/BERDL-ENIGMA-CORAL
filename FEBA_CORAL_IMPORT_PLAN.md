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

The current strain authority is live `enigma.coral.sdt_strain`. The 2026-08-10
live audit found:

- 48 public Fitness Browser organisms, of which 11 match current CORAL strains;
- 25 private fitprivate organisms, all of which match current CORAL strains;
- all 11 public matches are also present in fitprivate;
- 14 matching organisms occur only in fitprivate;
- no matching organism occurs only in the public source;
- 25 unique CORAL strains and 25 private source-organism datasets passed the
  original strain-matching review.

The 2026-08-11 project decision adds a stricter inclusion rule: import only
ENIGMA isolate strains. Explicitly exclude the three reference or laboratory
strains `Btheta` (`Bacteroides thetaiotaomicron VPI-5482`), `Keio`
(`Escherichia coli BW25113`), and `Putida` (`Pseudomonas putida KT2440`). Keep
those rows in the reviewed scope-decision record, but never generate genomes,
static objects, conditions, libraries, bricks, or EDR paths for them.

The eight in-scope dual-source organisms are `Cup4G11`, `Pedo557`,
`acidovorax_3H11`, `pseudo13_GW456_L13`, `pseudo1_N1B4`, `pseudo3_N2E3`,
`pseudo5_N2C3_1`, and `pseudo6_N2E2`.

The 14 private-only organisms are `Brev2`, `Castellaniella_MT123`,
`Collimonas_GW821-FHT01A05`, `Enterobacter_XG201`, `Janthino_FHT05C05`,
`Janthinobacterium_agari`, `MT049`, `MT058`, `Phaga5`, `PseudoFW215-L2`,
`Rhodanobacter_MT42`, `rhodanobacter_10B01`, `rhodanobacter_R12`, and
`rhodanobacter_T8`.

Approved import scope contains 22 organisms/strains, 411 contigs, 122,466,056
bp, 110,899 source gene/features, 55,261 cross-reference rows, 34 distinct
mutant libraries, 3,846 experiments, and 16,292,891 gene-fitness rows. The
eight matching public datasets in this narrowed scope are intentionally ignored.
The N2E2 audit established that its public measurements are an exact subset of
private, while public alone carries `pubId` annotations. Those publication
annotations will not be imported unless that metadata is added to the private
source or explicitly requested later.

## Phase 0: Freeze scope and build the work manifest

Keep a dated 25-row scope-decision file covering the full reviewed crosswalk,
with an explicit include/exclude value and reason for every `orgId`. Build the
machine-readable work manifest with one row per included private `orgId` and a
second strain-level rollup. Include columns for:

- source namespace, FEBa `orgId`, organism text, and source counts;
- authoritative CORAL strain ID and name;
- all distinct FEBa `mutantLibrary` values;
- EDR versions seen in active and withdrawn history;
- exact-match result and reused EDR version, if any;
- allocated new EDR version, if needed;
- target CORAL genome name;
- export, EDR publication, CORAL import, and validation status.

Fail before generating files if the scope-decision file does not cover exactly
the reviewed 25-row crosswalk, or if a selected source organism does not resolve to
exactly one live CORAL strain. Accepted matching forms are the exact current
strain name or the exact normalized full `genus species strain` display name;
record which form matched. Do not expand scope through unrestricted substring
or fuzzy matching.

### 2026-08-11 implementation checkpoint

The durable scope file is
`coral_import/feba_20260811/config/feba_enigma_isolate_scope_20260811.tsv`.
Regenerated Phase 0 outputs contain exactly 22 organisms, 22 strains, and 34
libraries; Btheta, Keio, and Putida occur only in the exclusion metadata and
not in any generated work-manifest or library-crosswalk row. Live CORAL
revalidation returned and verified exactly those 22 strain name/ID pairs.

The live active and withdrawn EDR manifests were downloaded through MinIO. A
bounded inventory checked 44 strain/scope prefixes with no failures, found 53
historical version folders, and downloaded only the 53 contigs FASTA plus 53
Prodigal GFF files (661,266,263 bytes total). Canonical assembly comparison
found no FEBa assembly match for 21 isolates. The sole assembly match was
`rhodanobacter_T8` against active `FW510-T8.3`.

`FW510-T8.3` is not an exact annotation-pair match. It contains every one of
the 3,416 FEBa source features with the same ID, scaffold, coordinates, strand,
and feature type, but also contains 20 additional annotations: one region,
five ncRNAs, one tmRNA, eleven regulatory regions, one origin-of-replication
feature, and one CRISPR feature. Six product-description strings also differ
from the literal FEBa values (the EDR strings repair apparent inserted or
trailing whitespace). Because the exact-pair rule does not permit a superset or
metadata-normalized match, do not reuse `FW510-T8.3`. All 22 in-scope isolates
therefore require new EDR versions unless the rule is explicitly changed.

The initial post-inventory allocations below are proposed and not published.
Re-read both live manifests and confirm these paths remain unoccupied in the
final publication preflight.

| FEBa `orgId` | Proposed EDR/CORAL genome name |
| --- | --- |
| `Brev2` | `GW460-12-10-14-LB2.4` |
| `Castellaniella_MT123` | `MT123.5` |
| `Collimonas_GW821-FHT01A05` | `GW821-FHT01A05.4` |
| `Cup4G11` | `FW507-4G11.4` |
| `Enterobacter_XG201` | `EB106-05-01-XG201.4` |
| `Janthino_FHT05C05` | `GW822-FHT05C05.3` |
| `Janthinobacterium_agari` | `GW823-FHT01H08.4` |
| `MT049` | `MT49.4` |
| `MT058` | `MT58.3` |
| `Pedo557` | `GW460-11-11-14-LB5.3` |
| `Phaga5` | `GW460-11-11-14-LB1.3` |
| `PseudoFW215-L2` | `FW215-L2.3` |
| `Rhodanobacter_MT42` | `MT42.3` |
| `acidovorax_3H11` | `GW101-3H11.6` |
| `pseudo13_GW456_L13` | `GW456-L13.3` |
| `pseudo1_N1B4` | `FW300-N1B4.3` |
| `pseudo3_N2E3` | `FW300-N2E3.3` |
| `pseudo5_N2C3_1` | `FW300-N2C3.3` |
| `pseudo6_N2E2` | `FW300-N2E2.3` |
| `rhodanobacter_10B01` | `FW104-10B01.4` |
| `rhodanobacter_R12` | `FW510-R12.4` |
| `rhodanobacter_T8` | `FW510-T8.4` |

All 22 proposed local export directories have now been generated without
publishing them. Each export passed FASTA/GFF validation and has a per-file
SHA-256 checksum in
`coral_import/feba_20260811/phase1/feba_edr_export_preflight_20260811.json`.
The 44 files total 167,463,697 bytes. Their status is
`local_exports_complete_not_published`; EDR publication still requires the
final live-manifest/path recheck and explicit preflight approval.

### 2026-08-12 final publication preflight

Both EDR manifests were downloaded again through BERDL MinIO. Their content is
unchanged from the 2026-08-11 inventory:

- active manifest SHA-256:
  `11d72d5aad7472dd60f43e5f7526f3a3c3d9ca43a8f64ebd33017c4606c67b9d`;
- withdrawn manifest SHA-256:
  `884e5f43ddb7a12cfa05dda29e6e8d820b15c3b4fef62eb2a48ac20776e7e988`.

A fresh bounded MinIO listing checked all 44 active/withdrawn parent prefixes
with zero failures. The dated fail-safe preflight verified for all 22 strains
that the proposed version is still the correct next version across both
histories, neither proposed target directory exists, and both local export
files still match their recorded byte count and SHA-256 checksum. Its status is
`passed_awaiting_publication_approval`; evidence is under
`coral_import/feba_20260811/phase1/preflight_20260812/`.

The live manifest has 1,985 `Genome` rows: 1,880 point to `.gbff` files and 105
point to `_Prodigal.gff` files. The comparable Lauren-genome convention uses
one manifest row per genome version pointing to the `_Prodigal.gff`; the
contigs FASTA is present in the same version directory but does not receive a
second manifest row. The handoff now includes the method script named in its
manifest rows plus all of that script's default inputs. Publication must still
use the normal source-controlled EDR workflow; do not publish files directly
to MinIO.

### 2026-08-12 local production checkout

At the project owner's request, the complete inspectable package is staged at:

`coral_import/feba_20260811/production_checkout_20260812/`

It contains:

- `genome_annotations/`: 22 strain/version directories and 44 validated
  production files (one contigs FASTA and one Prodigal GFF per strain);
- `manifest_rows.tsv`: 22 `Genome` rows following the one-GFF-row-per-version
  convention, with method `genomes_from_feba/record_feba_genomes_260812.py`;
- `historical_version_audit.tsv`: separate version lists from the active
  manifest, active object tree, withdrawn manifest, and withdrawn object tree;
- `checksums.sha256` and `package_manifest.json`: package integrity and status;
- `genomes_from_feba/record_feba_genomes_260812.py`: the self-contained
  manifest-row recorder and fail-safe staged-file/version validator;
- `genomes_from_feba/genomes_to_record.tsv`: the recorder's default 22-genome
  input, including allocated versions, package-relative FASTA/GFF paths,
  sizes, checksums, manifest values, and prior-version history;
- `genomes_from_feba/evidence/`: frozen active and withdrawn manifest snapshots,
  the four-source version inventory, and the validated export preflight used
  to construct the default TSV;
- `genomes_from_feba/README.md`: no-argument validation and generation usage.

From the package root,
`python3 genomes_from_feba/record_feba_genomes_260812.py --check-only` uses
only staged defaults. Running without `--check-only` writes
`manifest_rows.generated.tsv`; it does not modify a production manifest. That
generated file must be byte-identical to `manifest_rows.tsv`.

The repository's BERDL MinIO mirror calls the corresponding production trees
`genome_processing` and `genome_processing_withdrawn`; the local handoff uses
the requested production-facing directory name `genome_annotations`. For all
22 strains, `proposed_previously_used=no`, the proposed number equals the next
allowed number after the union of both histories, and package checksum
verification passes. `GW101-3H11.6` demonstrates the important withdrawn-tree
case: versions 3, 4, and 5 occur in withdrawn history, so 6 is used rather than
reusing a lower active-tree gap. The package remains local and unpublished.

### 2026-08-12 exhaustive annotation comparison

The initial deduplication compared canonical assemblies for all 53 discovered
active/withdrawn EDR versions and performed detailed annotation comparison only
for the sole assembly match, `FW510-T8.3`. To answer the stricter question of
annotation identity independent of assembly identity, every one of the 53 EDR
GFF files was subsequently compared with its same-strain FEBa source
annotation.

The strict comparison covers source feature IDs, missing and additional
features, duplicate candidate IDs, scaffold, coordinates, strand, feature
type, locus tag/system name, gene symbol, product description, GC fraction,
and cross-references. Result: zero exact annotation matches among 53 versions,
zero versions without a recorded annotation difference, and zero exact
assembly-and-annotation pair matches. The machine-readable evidence is:

`coral_import/feba_20260811/phase1/live_edr_20260811/edr_all_candidate_annotation_comparison_report.json`

Therefore each of the 22 staged FEBa genome annotations differs from every
active or withdrawn EDR version discovered for the same strain.

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
reuse/export, EDR publication, and verified CORAL `Genome` record for all 22
organisms before generating or loading any `Gene`, `Condition`,
`TnSeq_Library`, process, or fitness-brick artifact. Genome preparation is
expected to be the longest part of the project. Make it resume-safe through the
dated work manifest, but do not advance individual organisms past this barrier
while other genomes remain unfinished.

Static import TSV headers must use the literal current CORAL typedef
`field_name` values, not BERDL/CDM export aliases. For additions, omit the
auto-assigned primary-key `id`; include every required non-PK property and use
the declared FK property name with the target object's unique name. In the
current typedef this means `Genome.strain`, `Gene.gene_id`, `Gene.genome`, and
`TnSeq_Library.genome`--not `strain_id`, Gene `name`, or `genome_id`. Before
delivery, compare every header exactly to the current typedef and reject null,
blank, or `nan` values in required properties.

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
experiment names are not globally unique: 587 `expName` values occur in more
than one selected organism, and those rows can describe different conditions.
Generate dated `Condition` additions using the deterministic format
`<strain-name>:<expName>` rather than merging equal `expName` strings across
organisms. For example, use `FW300-N2E2:set1IT012`. Do not use pipe characters
to join identifier components, and apply the generated-identifier rules above.

Retain a crosswalk containing `(orgId, expName, condition_name,
mutantLibrary)`. This crosswalk drives both brick dimensions and library links.

### 2.4 TnSeq library records

Create one dated `TnSeq_Library` row per distinct `(orgId, mutantLibrary)`;
current scope has 34. Case, suffix, display-name, and collaborating-site labels
often share a base-library name in `timeZeroSet`, but this does not establish
that they are the same physical pool. Preserve all 34 records and retain a
crosswalk from each raw label to its apparent base-library lineage.

Use the stable, version-specific library name
`<versioned-genome-name>.<source-mutantLibrary>.tnseq_library`; for example,
`FW300-N2E2.3.pseudo6_N2E2_ML5c.tnseq_library`. Bricks refer to this unique
name, the versioned genome name, and the qualified gene name. They must never
refer to CORAL-assigned primary keys such as `TnSeq_Library0000001`,
`Genome0000001`, or `Gene0000001`.

Link every library to the selected FEBa genome. Do not aggregate per-experiment
`Experiment.nMapped` into a library-level metric. Leave optional library
metrics null unless a defensible library-level source is identified.

`primers_model` is required by CORAL but is absent from FEBa. The dated
`tnseq_library_model_evidence_20260810.tsv` crosswalk records the earlier
evidence and confidence. The local mastersheet and explicit project decisions
below now assign a model to all 34 included raw labels; retain whether each
assignment was direct, a case alias, same-organism prior-row inheritance, or
approved base-lineage inheritance. The existing N2E2 CORAL value
`model_pKMW7` conflicts with the source publication: `pseudo6_N2E2_ML5` is a
mariner library made with `pKMW3`, while `pKMW7` is the Tn5 vector.

#### 2026-08-10 local mutant-library mastersheet lookup

The local
`tnseq_genome_sources/Mutant_library_mastersheet_v2 - RB-TnSeq.tsv` was
examined for only the 25 originally reviewed private organisms. No other
mastersheet organisms and no web sources were consulted for this lookup. Twenty-four
organisms matched the mastersheet `Nickname` exactly. The remaining organism,
`pseudo5_N2C3_1`, matched the mastersheet spelling `pseudo5_N2-C3_1` and the
same N2C3 organism text.

The table below preserves the mastersheet `Plasmid or Tn5` findings for all 46
raw `Experiment.mutantLibrary` values in the original review. Rows for Btheta,
Keio, and Putida are historical evidence only and are excluded from the import.
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
| `Btheta` (excluded) | `Btheta_ML6` = `pTGG45_NN1` in the mastersheet but project decision retained `pTGG46_NN1`; `Btheta_ML6a`, `Btheta_ML6b` = no named row but approved base-lineage inheritance assigned `pTGG46_NN1` |
| `Brev2` | `Brev2_ML6a` = blank in the mastersheet; assign `pTGG39_NN1` by inheritance from the immediately preceding same-organism row, `Brev2_ML6` |
| `Castellaniella_MT123` | `Castellaniella_MT123_ML3` = `AMD290` |
| `Collimonas_GW821-FHT01A05` | `Collimonas_GW821-FHT01A05_ML4` = `AMD289` |
| `Cup4G11` | `cupriavidus_4G11_ML11`, `cupriavidus_4G11_ML11a` = `pKMW3`; `cupriavidus_4G11_ML11_FieldsLab`, `cupriavidus_4G11_ML11_JBEI` = no named row but approved base-lineage inheritance assigns `pKMW3` |
| `Enterobacter_XG201` | `Enterobacter_XG201_ML2` = `?` in the mastersheet; assign `AMD289` by inheritance from the immediately preceding same-organism row, `Enterobacter_XG201_ML1` |
| `Keio` (excluded) | `Keio_ML9`, `Keio_ML9a` = `EZ random barcode TN5`; `KEIO_ML9a` = the same result by case-variant match; the review normalized these to `pKMW7`; `Keio_ML9a_ucsf` = no named row but approved base-lineage inheritance also assigned `pKMW7` |
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
| `Putida` (excluded) | `Putida_ML5` = `pKMW3`; `putida_ML5` = the same result by case-variant match; `Putida_ML5_JBEI`, `Putida_ML5_PNNL`, `Putida_ML5a` = blank in the mastersheet but were assigned `pKMW3` by same-organism prior-row inheritance |
| `PseudoFW215-L2` | `PseudoFW215-L2_ML1` = `AMD290` |
| `rhodanobacter_10B01` | `rhodanobacter_10B01_ML12` = `pTKO49_NN1`; source library label `Rhodanobacter sp. FW104-10B01` = no named library row but is an approved display-name alias of the same ML12 lineage and is assigned `pTKO49_NN1` |
| `Rhodanobacter_MT42` | `Rhodanobacter_MT42_ML2` = `AMD1385` |
| `rhodanobacter_T8` | `rhodanobacter_T8_ML1` = `AMD1385` |
| `rhodanobacter_R12` | `rhodanobacter_R12_ML3` = `AMD290 (mariner)` |
| `MT049` | `MT049_ML3` = `AMD290 (mariner)` |

This local source resolves the previous `rhodanobacter_10B01_ML12` gap to
`pTKO49_NN1`. It also conflicts with the earlier external-evidence assignment
for `Btheta_ML6`: the mastersheet says `pTGG45_NN1`, not `pTGG46_NN1`.
The earlier 2026-08-11 project decision retained `pTGG46_NN1` for that library;
the literal mastersheet value remains recorded above as conflicting source
provenance. Btheta is now excluded from import, so neither value is emitted.
The mastersheet does not justify inheritance for absent suffix or
collaborating-site rows.

The 2026-08-11 blank-or-`?` rule is to inherit the `Plasmid or Tn5` value from
the immediately preceding mastersheet row only when that row belongs to the
same organism. Re-checking the relevant mastersheet rows applies the rule as
follows:

- `Brev2_ML6a` follows `Brev2_ML6 = pTGG39_NN1`, so assign `pTGG39_NN1`;
- excluded `Putida_ML5_JBEI`, `Putida_ML5_PNNL`, and `Putida_ML5a` followed
  the same-organism `Putida_ML5 = pKMW3` lineage in the historical review;
- `Enterobacter_XG201_ML2 = ?` immediately follows same-organism
  `Enterobacter_XG201_ML1 = AMD289`, so assign `AMD289`.

All in-scope mastersheet rows with a literal blank or `?` cell are resolved by
this rule. The rule does not create a match for a selected library label that
has no mastersheet row.

The original 2026-08-11 review approved all no-row base-lineage mappings:
excluded `Btheta_ML6a` and `Btheta_ML6b` used `pTGG46_NN1`; the two
`cupriavidus_4G11_ML11` collaborating-site labels use `pKMW3`;
excluded `Keio_ML9a_ucsf` used `pKMW7`; `PsfN1B4_ML1` uses `pKMW3`;
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
34 included libraries has an assigned CORAL `primers_model`. The evidence file
retains assignments for the 12 excluded libraries only as an audit trail; the
scope-gated builder omits them from generated artifacts.

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
brick.** Create one brick covering all 3,846 qualified TnSeq conditions. Its
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
selected scope contains 16,292,891 matrix cells and two numeric values (`fit`
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

### 2026-08-13 staged CORAL package

The complete local, not-yet-imported package is staged at
`coral_import/feba_20260811/coral_package_20260813/`. It contains four static
TSVs, 22 strain fitness bricks, one shared condition-metadata brick, 22 Assay
Fitness process rows, audit reports, separate static/brick import helpers, a
deferred N2E2 obsoletion process, and whole-package SHA-256 checksums.

Generation and independent read-back validation confirmed:

- 22 genomes, 110,899 genes, 3,846 qualified conditions, and 34 named TnSeq
  libraries;
- 22 rectangular fitness matrices containing 16,292,891 `fit` values and the
  same number of FEBa `t` values;
- 23 of 23 JSON bricks pass `gov.lbl.enigma.app.CheckGeneric`;
- every `object_ref` is mirrored in `string_values`, resolves to a unique name
  staged in the static TSVs, and contains no CORAL-assigned `Gene000...`,
  `Genome000...`, `Condition000...`, or `TnSeq_Library000...` ID;
- the N2E2 example cell for `FW300-N2E2.3:Pf6N2E2_1` and
  `FW300-N2E2:set1IT012` is exactly `fit=-0.101775502641824` and
  `t=-0.542151246146515`, matching the immutable SQLite source;
- every file passes `checksums.sha256` verification.

The current ontology defines the exact numeric term `T score <ME:0000157>`,
but the legacy Java checker incorrectly requires every data variable to also
carry the `is_valid_dimension_variable` flag; `T score` and several other valid
data-variable terms lack that flag. To preserve both import compatibility and
the exact meaning, the `t` array uses the validator-compatible numeric
`average` carrier with dimensionless units and a value-context ontology
property `statistic = T score <ME:0000157>`, plus `source column: t`. Similar
source-column context records the exact FEBa semantics for affected metadata
metrics. The complete mapping is in
`reports/experiment_column_mapping.tsv`.

Do not run the brick import helper immediately after static import. Re-poll
and verify all new unique names and foreign keys first. The package-level
`post_import/` N2E2 replacement process remains deferred until the new N2E2
objects and values have been loaded and validated in CORAL.

The first static-import attempt exposed three header errors: Genome used the
undeclared `strain_id`, Gene used `name` and `genome_id` instead of the
required `gene_id` and `genome`, and TnSeq Library used `genome_id` instead of
required `genome`. The generator and staged package were corrected on
2026-08-13 and now run an exact CORAL-typedef header/required-value preflight.

### 2026-08-13 CORAL import status

The project owner reports that all package static types, bricks, producing
processes, and the deferred N2E2 `Update Data` process have been imported into
CORAL. Treat this as import completion reported by the operator, not yet as an
independent post-import validation. Phase 4 begins with a fresh CORAL re-poll
to confirm exact counts, unique names, foreign keys, producing-process edges,
and that `tnseq_n2e2.ndarray` is obsolete in favor of
`feba_tnseq_fitness_FW300-N2E2.3.ndarray`.

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

### 2026-08-18/19 BERDL publication completion

The interrupted Lakehouse publication was audited and resumed from
`sync-coral-to-berdl/exports/sync-20260813-165014/`. Before resumption, the
live namespace still ended at `ddt_brick0001673`, contained the legacy
`ddt_brick0000006`, and contained none of the 23 new FEBA brick tables. The
resumed run uploaded all 45 staged objects (739,357,078 bytes), imported the
33 selected changed tables, and dropped `ddt_brick0000006`. The durable import
record is
`reports/full_import_sync-20260813-165014.json`: all 45 uploads are
`uploaded`, all 33 tables are `imported`, the obsolete table is `dropped`, and
the error list is empty.

Independent live verification then confirmed:

- all 733 expected active tables are present and all 755 configured obsolete
  tables are absent;
- all 33 imported tables have exact staged/live row-count parity (461,615
  rows in total, zero mismatches), including 3,846 condition-metadata rows,
  125,914 genes, 6,727 genomes, 35 TnSeq libraries, and all 23 brick tables;
- all 33 requested table comments and all 300 checked column comments are
  present and byte-for-byte equal to the generated configuration;
- all 3,846 distinct `(orgId, expName)` pairs in `ddt_brick0001674` resolve to
  exactly one row in `enigma.fitprivate.experiment` (zero missing and zero
  ambiguous target pairs);
- `Brick0000006` has `withdrawn_date=2026-08-13` and
  `superceded_by_ddt_ndarray_id=Brick0001693`; `Brick0001693` is current and
  has no successor;
- the complete live FK audit checked 102 relationships. All FEBA additions
  pass. Its only two failures are unchanged legacy defects already present in
  the 2026-07-24 baseline: 11,965 pre-existing gene rows refer to the absent
  aliases `FW300-N2A2.genome`/`FW300-N2E2.genome`, and one pre-existing genome
  row refers to absent strain `MT66-resequenced`. The 110,899 newly added gene
  rows and 22 newly added genome rows contribute zero orphans.

The CORAL converter-derived TnSeq reference defect was corrected during this
run: all affected brick schema and typedef references now target
`sdt_tnseq_library.sdt_tnseq_library_name`, not the nonexistent
`sdt_tnseq.sdt_tnseq_library_name`. A regression test protects this
normalization. The refreshed schema references were generated, copied to all
eight dependent locations, and synchronized to the installed local BERDL
skills.

The final repeat of the EDR MinIO prefix check is still pending because the
off-cluster route to `login1.berkeley.kbase.us:22` became unavailable after
the overnight proxy/tunnel loss. This does not affect the completed Lakehouse
load or its live Spark verification. The 22 exact EDR paths and checksums were
already validated during staging; repeat their live prefix listing when that
route returns.

## Remaining contingency

No exact active or withdrawn annotation-pair match was found in the current
22-strain scope, so withdrawn-only reuse does not block this import. If a future
pre-publication refresh discovers an exact match only under
`genome_processing_withdrawn`, stop for an explicit reuse-versus-new-version
decision rather than linking to it silently.
