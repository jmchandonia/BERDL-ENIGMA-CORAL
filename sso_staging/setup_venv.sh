#!/bin/sh
# Create or refresh the sso_staging uv venv on dipa.
# vendor/ holds spark_connect_remote and berdl_remote (copied from the stout
# BERIL .venv-berdl install, as in continuous_monitoring); their GitHub repos
# are no longer public.  If continuous_monitoring is already deployed beside
# this, you can symlink its vendor/ dir instead of copying.
set -e
BASE=${SSO_WORK_ROOT:-/data/edr/field_automated_measurements/sso_staging}
cd "$BASE"
[ -d .venv ] || uv venv --python 3.13 .venv
VIRTUAL_ENV="$BASE/.venv" uv pip install \
    ./vendor/spark_connect_remote ./vendor/berdl_remote \
    'pyspark[connect]==4.1.1' pproxy pandas pyarrow openpyxl requests pytz
.venv/bin/python -c 'import spark_connect_remote, berdl_remote, pyspark, openpyxl, pproxy; print("pyspark", pyspark.__version__)'
