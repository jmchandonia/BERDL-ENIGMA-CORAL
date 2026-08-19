# FEBA TnSeq query examples

These examples describe the FEBA import completed on 2026-08-13. Confirm the
current brick IDs in `ddt_ndarray_table.md` before adapting them to a later
sync. Requests go to `POST /delta/tables/select` with database
`enigma_coral`; keep `limit <= 1000` and use uppercase order directions.

## Current N2E2 fitness brick

`Brick0000006` (`tnseq_n2e2.ndarray`) is superseded by `Brick0001693`
(`feba_tnseq_fitness_FW300-N2E2.3.ndarray`). The old row remains in
`ddt_ndarray` for lifecycle history, but its dynamic table is not current.

Query the current N2E2 condition-level fitness and FEBa t statistic with:

```json
{
  "database": "enigma_coral",
  "table": "ddt_brick0001693",
  "columns": [
    {"column": "sdt_condition_name"},
    {"column": "sdt_tnseq_library_name"},
    {"column": "fitness_score_log_ratio_unit_2", "alias": "fit"},
    {
      "column": "average_statistic_t_score_comment_source_column_t_feba_t_statistic_dimensionless_unit_2",
      "alias": "t"
    }
  ],
  "order_by": [{"column": "sdt_condition_name", "direction": "ASC"}],
  "limit": 1000,
  "offset": 0
}
```

The similarly named string columns without the `_2` suffix are nullable legacy
placeholders in this imported brick. Use the numeric `_2` columns for `fit`
and `t`.

## Experimental-condition metadata

`Brick0001674` holds metadata for all imported FEBA conditions. Fetch the
metadata for one N2E2 experiment as a separate bounded query:

```json
{
  "database": "enigma_coral",
  "table": "ddt_brick0001674",
  "columns": [
    {"column": "sdt_condition_name"},
    {"column": "sdt_tnseq_library_name"},
    {"column": "sdt_genome_name"},
    {
      "column": "description_comment_source_column_orgid_composite_source_key_part_1",
      "alias": "fitprivate_orgId"
    },
    {
      "column": "description_comment_source_column_expname_composite_source_key_part_2",
      "alias": "fitprivate_expName"
    },
    {"column": "media_name_comment_source_column_media", "alias": "media"},
    {
      "column": "temperature_comment_source_column_temperature_degree_celsius",
      "alias": "temperature_c"
    },
    {"column": "ph_comment_source_column_ph_ph", "alias": "pH"},
    {
      "column": "anaerobic_comment_source_column_aerobic_stored_as_the_logically_inverted_anaerobic_flag_whose_coral_term_is_validator_compatible",
      "alias": "anaerobic"
    }
  ],
  "filters": [
    {
      "column": "description_comment_source_column_orgid_composite_source_key_part_1",
      "operator": "=",
      "value": "pseudo6"
    }
  ],
  "order_by": [{"column": "sdt_condition_name", "direction": "ASC"}],
  "limit": 1000,
  "offset": 0
}
```

The array metadata documents the composite external relationship
`(fitprivate_orgId, fitprivate_expName) -> enigma.fitprivate.experiment(orgId,
expName)`. Because the structured select endpoint operates within one primary
database, resolve this cross-database link with two bounded API queries, or use
Spark SQL when an actual cross-database join is required.

## Library and genome objects

Resolve a named imported library to its genome without relying on CORAL's
generated IDs:

```json
{
  "database": "enigma_coral",
  "table": "sdt_tnseq_library",
  "joins": [
    {
      "join_type": "INNER",
      "database": "enigma_coral",
      "table": "sdt_genome",
      "on_left_column": "sdt_genome_name",
      "on_right_column": "sdt_genome_name"
    }
  ],
  "columns": [
    {"table_alias": "sdt_tnseq_library", "column": "sdt_tnseq_library_name"},
    {"table_alias": "sdt_tnseq_library", "column": "primers_model"},
    {"table_alias": "sdt_genome", "column": "sdt_genome_name"},
    {"table_alias": "sdt_genome", "column": "sdt_strain_name"},
    {"table_alias": "sdt_genome", "column": "link"}
  ],
  "order_by": [{"column": "sdt_tnseq_library_name", "direction": "ASC"}],
  "limit": 1000,
  "offset": 0
}
```

For an exact library, query `sdt_tnseq_library` first with a filter on its
unambiguous name column, then query `sdt_genome` by the returned
`sdt_genome_name`. This two-query form avoids ambiguous joined filters in the
structured endpoint.
