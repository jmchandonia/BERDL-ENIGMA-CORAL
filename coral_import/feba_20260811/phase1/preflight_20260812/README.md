# EDR publication preflight — 2026-08-12

This directory records the final read-only EDR gate for the 22 ENIGMA isolate
strain exports. No EDR or CORAL data was written.

- `genome_processing_manifest.tsv` and
  `genome_processing_withdrawn_manifest.tsv` are fresh MinIO downloads.
- `edr_candidate_prefix_listings.jsonl` contains bounded, nonrecursive listings
  for the 22 active and 22 withdrawn strain parents.
- `edr_version_inventory_report.json` reconciles the two manifests and the
  bounded object listings.
- `edr_publication_preflight_report.json` verifies the proposed next version,
  absence of both target paths, and local export size/SHA-256 for every strain.

Result: 22 of 22 passed, with status
`passed_awaiting_publication_approval`. The active and withdrawn manifest
SHA-256 values are, respectively:

```text
11d72d5aad7472dd60f43e5f7526f3a3c3d9ca43a8f64ebd33017c4606c67b9d
884e5f43ddb7a12cfa05dda29e6e8d820b15c3b4fef62eb2a48ac20776e7e988
```

Publication must use the source-controlled EDR workflow. The comparable
manifest convention is one `Genome` row pointing to each version's
`<strain>_Prodigal.gff`; its `Method` value must name the real publishing script
in that repository. Do not invent that path or upload directly to MinIO.
