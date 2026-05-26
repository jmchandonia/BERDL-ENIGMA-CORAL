---
name: cleanup-coral-process-data
description: Clean up CORAL Process.tsv exports by detecting duplicate or conflicting process provenance, preserving valid brick lifecycle provenance, and generating reviewed deletion candidates for older redundant processes. Use when exported CORAL process data has objects produced by multiple processes or when preparing process cleanup before CORAL-to-BERDL sync.
---

# Cleanup CORAL Process Data

Use this skill to review and clean CORAL process provenance exported from
CORAL, especially when an output object is produced by multiple processes.

## Guardrails

- Do not delete processes directly from CORAL during analysis.
- Generate reports and `processes_to_delete.txt` first.
- Do not embed database passwords or credentials in generated scripts.
- Treat brick lifecycle provenance specially: a brick may have both an
  experimental producing process and an `update data` or `withdraw data`
  lifecycle process without being a cleanup conflict.

## Workflow

1. **Load process export**
   - Read the exported `Process.tsv`.
   - Parse `input_objects` and `output_objects` as bracketed CORAL object lists.
   - Preserve the original process ID, process name/type, dates, inputs, and outputs.

2. **Find redundant identical processes**
   - Group processes by exact input-object signature and output-object signature.
   - When duplicates have identical inputs and outputs, keep the newest/highest
     process ID and mark older process IDs as deletion candidates.

3. **Find redundant subset processes**
   - For processes with identical input signatures, delete an older process only
     when a newer process has a strict superset of its outputs.
   - Record the kept process ID and the subset relationship in the report.

4. **Classify remaining multi-producer outputs**
   - For each output object produced by more than one remaining process, classify:
     - allowed brick lifecycle overlap
     - redundant duplicate already handled
     - conflicting process provenance requiring review
   - Allowed lifecycle overlap means a brick has both a primary experimental
     producing process and an `update data` or `withdraw data` lifecycle process.

5. **Write outputs**
   - `Process_consolidated.tsv`: process table after non-destructive consolidation.
   - `processes_to_delete.txt`: one redundant process ID per line.
   - `process_cleanup_report.tsv`: machine-readable deletion and review reasons.
   - `process_cleanup_summary.md`: counts, examples, and residual risks.

6. **Validate**
   - Re-run duplicate-output detection on `Process_consolidated.tsv`.
   - Every remaining duplicate output must be either an allowed brick lifecycle
     overlap or a review-needed conflict.

## References

- For the existing CORAL script behavior and cleanup rules, read `references/process_cleanup.md`.
