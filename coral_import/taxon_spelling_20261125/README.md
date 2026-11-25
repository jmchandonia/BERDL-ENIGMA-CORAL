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

Still to do (needs the user's OK): delete the 252 retired Taxon records and move the NCBI IDs of 6 of them to the kept
record. 23 superseded bricks still on the hub use retired names (19 old isolate_classification_gtdb_* with `B-17BO`, and
the first versions of four Zhou ASV taxonomy bricks, Brick0000454/458/461/478).
