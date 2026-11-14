# Run on the CORAL hub, in order, after copying every file in files_to_import.txt to /home/coral/prod/data_import/data/ on coral-enigma.
toolx.update_core('Sample_additions_20261113.tsv', 'Sample')
toolx.upload_process('Sampling', 'process_sampling_fw305_core_20261113.tsv')
toolx.upload_brick('elias_sediment_anions_iron_fw305_core_2013.json')
toolx.upload_brick('adams_metals_fw305_core_2013.json')
toolx.upload_brick('chakraborty_sediment_properties_fwb306_2015.json')
toolx.upload_process('Assay Geochemistry', 'process_assay_geochemistry_fw305_core_anions_20261113.tsv')
toolx.upload_process('Assay Geochemistry', 'process_assay_geochemistry_fw305_core_metals_20261113.tsv')
toolx.upload_process('Assay Geochemistry', 'process_assay_geochemistry_fwb306_chakraborty_20261113.tsv')
