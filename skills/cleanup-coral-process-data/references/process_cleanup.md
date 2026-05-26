# Process Cleanup

This skill is based on the cleanup logic in:

```text
/h/jmc/src/CORAL/convert/spark-minio/exported_tsvs/
```

Relevant legacy scripts:

- `combine_processes.py`: consolidates identical-output and subset-output processes.
- `combine_processes_v3.py`: groups by identical input/output signatures, keeps the highest process ID, then removes older subset-output processes when inputs match.
- `check_dupes.py`: reports outputs that still appear in multiple processes.
- `parse_process.py`: classifies duplicate outputs and prints examples.
- `generate_delete_script.sh`: legacy deletion script generator. Treat it as a pattern for the deletion list only; do not copy embedded credentials.

## Object Parsing

Process object lists use bracketed CORAL references such as:

```text
[Brick-0000019:Brick0000003]
```

Parse the object ID before the first colon and ignore empty tokens. Sort object
IDs when building signatures.

## Safe Deletion Candidates

Identical process candidates:

- same sorted input object IDs
- same sorted output object IDs
- keep the highest/newest process ID
- mark older process IDs for deletion

Subset process candidates:

- same sorted input object IDs
- newer process has a strict superset of older process outputs
- mark the older subset process for deletion

Do not remove processes merely because outputs overlap. Different inputs for
the same output require review unless the overlap is an allowed brick lifecycle
case.

## Brick Lifecycle Exception

Brick outputs can legitimately be associated with both:

- a primary experimental or analysis process that produced the brick data
- an `update data` or `withdraw data` process that records lifecycle provenance

This is not a conflict by itself. Keep both process records unless they also
match the identical-process or subset-process deletion rules.

## Review Needed

Flag, do not delete automatically, when:

- one output object has multiple producers with different input signatures
- process names/classes imply different scientific operations
- multiple lifecycle processes disagree about successor or withdrawn state
- a process ID order conflicts with process dates
- brick lifecycle overlap cannot be classified as allowed

## Deletion Execution

The cleanup workflow should stop after generating reports unless the user
explicitly asks to delete processes from CORAL.

If deletion is requested later:

- use `processes_to_delete.txt` as the reviewed input
- require secure credentials from environment or an approved configuration
- do not generate scripts with hardcoded passwords
- re-run duplicate detection after deletion/export
