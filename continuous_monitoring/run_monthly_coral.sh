#!/bin/sh
# Monthly CORAL conversion of the EDR HydroVu/LI-COR data (field_automated_measurements/update_monthly.sh).
# Moved from the stout crontab to dipa on 2026-10-16.  cron does not read
# ~/.cshrc (which also fails under cron's minimal environment), so CLASSPATH
# comes from classpath.txt, a snapshot of the login CLASSPATH on dipa
# (refresh with: printenv CLASSPATH > /data/edr/field_automated_measurements/continuous_monitoring/classpath.txt).
# The continuous-monitoring venv (which has requests and pytz) goes first on PATH.
set -eu
CLASSPATH=$(cat /data/edr/field_automated_measurements/continuous_monitoring/classpath.txt)
export CLASSPATH
export PATH=/data/edr/field_automated_measurements/continuous_monitoring/.venv/bin:/lab/bin:/usr/local/bin:/usr/bin:/bin
cd /data/edr/field_automated_measurements
exec ./update_monthly.sh
