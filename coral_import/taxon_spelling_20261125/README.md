# Taxon spelling cleanup, 2026-11-25 (in place)

The Taxon table held 252 taxa under two spellings (240 underscore against space, 12 capitalisation or more). The space
spelling is kept (user, 2026-11-24). At the user's direction the correction was made in place, because no data changed:

1. `01_rename_taxa.py`: guarded AQL rename of four Taxon records to NCBI's lower-case form (IDs unchanged):
   Taxon0005210, Taxon0000883, Taxon0001174, Taxon0002130 -> `Alphaproteobacteria|Deltaproteobacteria|Gammaproteobacteria|Rhizobiales incertae sedis`.
2. `02_apply_brick_edits.sh`: nineteen brick files in `coral-enigma:/home/coral/prod/data_store` overwritten with the same
   file in which only taxon names were replaced (`taxon_name_map.json`: `map` retired name -> kept name, `rename` old -> new;
   built by `plan_brick_edits.py`). Originals: `coral-enigma:/home/coral/prod/data_store_backup_taxon_spelling_20261125`.
   MD5 before and after: `brick_md5_old_new.txt`. No Update Data process; the bricks keep their IDs.
3. `03_verify_bricks.py`: every edited brick loads through CORAL with the same shape, no retired name, every name in Taxon.
4. Lakehouse: sync-20261125-104240 with a forced re-download and reload of the nineteen brick tables and `sdt_taxon`
   (the sync otherwise treats a brick ID as unchanging). 70/70 foreign keys.

## Part 2 (same day, `part2/`), all at once at the user's direction

Plan: `part2/taxon_plan.json` (`rename` 121 records, `retire` 252, `ncbi_copy` 6, `value_map` old brick value -> final name),
built by `build_map.py`; brick edits planned by `plan_bricks.py` over all 105 stored bricks that mention taxa.

1. `01_rename_and_ncbi.py`: preflight, save the 616 affected or related Taxon records (`taxon_records_before.json`), rename 121
   in place (93 incertae sedis, 18 Candidatus, 9 group/clade, `_Neoptera`), copy 6 NCBI ids to the kept twin. `B-17BO` kept.
2. `02_apply_brick_edits.sh`: 25 brick files overwritten (19 current, 6 withdrawn; 76,052 cells); originals in
   `coral-enigma:/home/coral/prod/data_store_backup_taxon_spelling_20261125_part2`; `brick_md5_old_new.txt`.
3. `03_verify_bricks.py`: bricks loaded through CORAL (taxa can also be a dimension variable: fama taxon-function profile).
4. `04_delete_retired.py`: 252 retired records removed after a preflight (16,453 -> 16,201 records, all names distinct).
5. `05_check_downloads.py`: the Taxon table and the 19 current bricks as downloaded by sync-20261125-121532 compared with the
   previous download plus the plan, cell by cell (`check_downloads_sync-20261125-121532.txt`): no difference from expectation.
   Lakehouse: 20 tables reloaded, 108/108 foreign keys.

Left alone: 619 names whose underscore is part of an identifier (GTDB `Genus_A`, accession and strain ids, SILVA and RDP labels,
culture-collection strains); and values in 17 withdrawn bricks that were never in Taxon (spreadsheet-mangled dates, missing species).
