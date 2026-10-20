#!/bin/sh
# Create or refresh the continuous-monitoring uv venv on dipa.
# vendor/ holds spark_connect_remote and berdl_remote copied from the stout
# BERIL .venv-berdl install; their GitHub repositories are no longer public.
set -e
BASE=${CM_WORK_ROOT:-/data/edr/field_automated_measurements/continuous_monitoring}
cd "$BASE"
[ -d .venv ] || uv venv --python 3.13 .venv
VIRTUAL_ENV="$BASE/.venv" uv pip install \
    ./vendor/spark_connect_remote ./vendor/berdl_remote \
    'pyspark[connect]==4.1.1' pproxy pandas pyarrow openpyxl requests pytz
.venv/bin/python -c 'import spark_connect_remote, berdl_remote, pyspark, openpyxl, pproxy; print("pyspark", pyspark.__version__)'
