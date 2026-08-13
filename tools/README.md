# Tools

Python CLI tools for querying BERDL/ENIGMA data and generating exports.

## What is here

- `get_schema.py`: Fetch schema metadata and render markdown.
- `get_table.py`: Export a table to markdown.
- `walk_provenance.py`: Trace object provenance and list related processes.
- `build_feba_phase0_manifest.py`: Build and resume the approved 22-isolate
  FEBa import inventory, source fingerprints, and TnSeq-library crosswalk.
- `build_feba_coral_import.py`: Build and CheckGeneric-validate the complete
  staged CORAL static-object, condition-metadata, fitness-brick, and process
  package using stable object names rather than CORAL-assigned IDs. Static TSV
  headers are checked against the literal CORAL typedef field names, and all
  required non-PK values are checked before package publication.
- `export_feba_genome.py`: Export a reviewed FEBa assembly and GFF3 annotation
  pair using EDR-required filenames after a genome version is allocated.
- `export_feba_genomes_batch.py`: Export every allocated in-scope genome and
  assemble the checksum/count preflight without publishing it.
- `verify_feba_edr_publication_preflight.py`: Fail-safe verification that all
  allocated versions remain next/free and all local export checksums still match.
- `stage_feba_edr_checkout.py`: Build the locally inspectable production-facing
  `genome_annotations` package, self-contained recorder inputs, manifest rows,
  checksums, and version-use audit.
- `record_feba_genomes_260812.py`: Validate a staged FEBa genome handoff from
  its default `genomes_to_record.tsv` and generate the EDR manifest rows.
- `inventory_feba_edr_versions.py`: Merge active/withdrawn EDR manifest
  occurrences and bounded object listings into the FEBa work manifest.
- `fetch_feba_edr_candidate_listings.py`: Run nonrecursive MinIO listings only
  for the selected active/withdrawn assembly prefixes.
- `fetch_feba_edr_candidate_files.py`: List files inside only the version
  folders returned by the bounded candidate-prefix inventory.
- `download_feba_edr_candidates.py`: Resume and verify downloads of only the
  contigs FASTA and Prodigal GFF in those candidate version folders.
- `compare_feba_edr_candidate_assemblies.py`: Compare candidate FASTA content
  with canonical FEBa assembly fingerprints and narrow annotation comparison.
- `compare_feba_edr_candidate_annotations.py`: Strictly compare source feature
  structure and metadata for the assembly-matching EDR candidates.
- `allocate_feba_edr_versions.py`: Allocate proposed non-gap-filling versions
  across active and withdrawn history after exact-match decisions are complete.
- `validate_feba_coral_strains.py`: Recheck only the selected strain
  name/ID pairs against live `enigma_coral.sdt_strain`.
- `generate_ncbi_submission.py`: Build NCBI submission spreadsheets and staging assets.
- `list_databases.py`: List BERDL MCP databases.

## Common usage

```bash
uv run python tools/list_databases.py
uv run python tools/get_schema.py
uv run python tools/get_table.py sdt_genome
```

## Options

- `--base-url` overrides the MCP server base URL (defaults to BERDL).
- `--schema-dir` overrides where schema markdown is read/written.

All tools require `KB_AUTH_TOKEN` in the environment if you use BERDL.
