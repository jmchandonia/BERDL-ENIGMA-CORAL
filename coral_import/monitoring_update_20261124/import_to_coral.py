# Run on the CORAL hub, in order, after copying every file in files_to_import.txt to /home/coral/prod/data_import/data/ on coral-enigma.
toolx.upload_brick('hazen_aquatroll600_EFPW03_20230401_20230509.json')
toolx.upload_brick('hazen_aquatroll600_EFPW06_20230118_20230509.json')
toolx.upload_process('Assay Environment', 'process_assay_environment_monitoring_update_20261124.tsv')
toolx.upload_brick('hazen_aquatroll600_EFPW03_20221221_20230401_v2.json')
toolx.upload_brick('hazen_hobo_WS3_20220509_20230725_v2.json')
toolx.upload_brick('hazen_hobo_WS3_20230725_20240522_v2.json')
toolx.upload_process('Update Data', 'process_update_data_monitoring_update_20261124.tsv')
