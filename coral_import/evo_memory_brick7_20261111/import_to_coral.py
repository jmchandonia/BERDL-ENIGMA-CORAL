# Run on the CORAL hub, in order, after (1) installing coral_import/ontology_update_20261111_sediment on stout and coral-enigma and
# reloading the ontologies, and (2) copying every file in files_to_import.txt to /home/coral/prod/data_import/data/ on coral-enigma.

# Step 1: move the GP01/GP03 samples to the upper ports (hub/apply_sample_moves.py; guarded, prints what it changed).

# Step 2: static objects, in dependency order.
toolx.update_core('Protocol_additions_20261111.tsv', 'Protocol')
toolx.update_core('Taxon_additions_20261111.tsv', 'Taxon')
toolx.update_core('OTU_additions_20261111.tsv', 'OTU')
toolx.update_core('Sample_additions_20261111.tsv', 'Sample')
toolx.update_core('Community_additions_20261111.tsv', 'Community')
toolx.update_core('Reads_additions_20261111.tsv', 'Reads')

# Step 3: sampling, filter and sequencing processes.
toolx.upload_process('Sampling', 'process_sampling_evo_20261111.tsv')
toolx.upload_process('Filter', 'process_filter_evo_20261111.tsv')
toolx.upload_process('16S Sequencing', 'process_16s_sequencing_evo_20261111.tsv')

# Step 4: the bricks.
toolx.upload_brick('hazen_field_post100ws_v2.json')
toolx.upload_brick('hazen_sediment_extractable_fwb306_2015.json')
toolx.upload_brick('hazen_sediment_soil_properties_fwb306_2015.json')
toolx.upload_brick('hazen_geochemistry_evo_injection_2017.json')
toolx.upload_brick('zhou_lab_evo_injection_2009_2017_zOTU_16S.json')
toolx.upload_brick('zhou_lab_evo_injection_2009_2017_zOTU_count.json')
toolx.upload_brick('zhou_lab_evo_injection_2009_2017_zOTU_taxonomy.json')

# Step 5: classification, assay and update processes.
toolx.upload_process('Classify OTUs', 'process_classify_otus_evo_20261111.tsv')
toolx.upload_process('Assay Geochemistry', 'process_assay_geochemistry_evo_2017_20261111.tsv')
toolx.upload_process('Assay Geochemistry', 'process_assay_geochemistry_fwb306_sediment_20261111.tsv')
toolx.upload_process('Update Data', 'process_update_data_hazen_field_post100ws_v2_20261111.tsv')
