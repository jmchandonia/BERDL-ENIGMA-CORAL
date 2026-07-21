---
name: check-berdl-foreign-keys
description: Validate declared foreign keys in BERDL tables against live Lakehouse data. Use after adding or reloading tables that contain JSON column comments with type foreign_key, when investigating orphaned links or unsafe joins, or when performing an explicit namespace-wide relationship audit.
---

# Check BERDL Foreign Keys

Use this skill after BERDL ingest has finished. The JSON column comments in the
ingest config are the relationship contract; Iceberg does not enforce them.

## Scoped Sync Check

1. Read `<run_dir>/ingest/changed_tables_with_foreign_keys.txt`.
2. If the file is empty, do not run the live check.
3. If it is non-empty, start the BERDL remote connection and local proxy as in
   the `berdl-query` or `sync-coral-to-berdl` skill.
4. Run:

```bash
python skills/check-berdl-foreign-keys/scripts/check_foreign_keys.py \
  --run-dir <run_dir> \
  --table-file <run_dir>/ingest/changed_tables_with_foreign_keys.txt
```

5. Require exit status zero before declaring the updated tables verified.
6. Inspect `reports/foreign_key_validation.json` and
   `reports/foreign_key_validation.tsv`. Report orphan samples and the exact
   declared relationship when a check fails.

The validator ignores null source values. It fails on orphaned non-null values,
missing live tables or columns, incompatible live source/target types, malformed
foreign-key declarations, and duplicate non-null values in a referenced target
column. Duplicate target values are failures because a join would multiply or
ambiguously match source rows.

Collection-valued relationships may be native Spark arrays or JSON arrays held
in string columns. The validator explodes one- and two-level collections to
their scalar keys and fails on non-null serialized collections that cannot be
parsed.

The sync selector also includes unchanged FK-bearing source tables when one of
their referenced target tables was reloaded. This catches key deletions in
mutable static/type tables without turning routine syncs into full audits.

## Other Modes

- Use `--plan-only` to inspect declarations without connecting to BERDL.
- Pass a custom `--config` instead of `--run-dir` for another BERDL package.
- Omit `--table-file` only for a deliberate audit of every enabled table in the
  config. Do not make full audits part of routine CORAL syncs.
- Use `--sample-limit` to control the bounded orphan examples stored in reports.

The validator checks the declared target exactly. Do not silently retarget a
failed relationship to another table even when values happen to match there;
fix the source schema or CORAL-to-BERDL mapping and reload the affected table.
