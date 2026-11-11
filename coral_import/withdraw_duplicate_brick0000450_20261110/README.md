# Withdraw duplicate Brick0000450 (2026-11-10)

Brick0000450 `zhou_lab_27_well_survey_ASV_16S` (Zhou Lab 27 Well Survey ASV 16S Sequences, 14,917 sequences) is
row-for-row identical to Brick0000015 `zhou_27ws_ESV_16S`, the 27-well survey representative sequences produced by
the 425 Classify OTUs processes (Yupeng Fan) together with Brick0000014 (counts) and Brick0000012 (taxonomy).

Origin: in September 2024 the 27-well sequences were re-dumped with `DumpASV16SSeqs` from
`~/data/enigma/asv/27ws_asv_sequences.fasta` (the merged QIIME2 repseqs of MiSeq runs 190917, 190924, 191216 and
200908) as `generic_asv_16S_zhou_27ws.json`, to build the combined 100ws/spring19/corepilot/27ws OTU list. The
hub notebook `upload_new_data.ipynb` cell 23 uploaded it, although `~/data/enigma/asv/log` records that it
duplicates `generic_esv_rep_16S_zhou_27ws.json` (Brick0000015) "other than name" and should not be uploaded. No
process produces or uses it.

Action: one Withdraw Data process; the next CORAL-to-Lakehouse sync then classifies it obsolete and drops
`ddt_brick0000450` (standing rule). Brick0000015 is unaffected.
