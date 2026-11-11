#!/bin/sh
# Combined daily lakehouse update for BOTH enigma.continuous_monitoring and
# enigma.sso_staging, run from cron on dipa.  One SSH tunnel + one JupyterHub
# spawn serve both loads, and ONE combined email is sent per day (see
# combined_report.py).  This replaces the per-namespace cron entry; each
# namespace's own run_daily.sh / loaders still work standalone for backfills.
#
# Flow: fetch + build each namespace (no proxy) -> open proxy chain + spawn once
#       -> load cm, load sso (through proxy) -> email the combined report.
#
# Fatal infra errors (tunnel/spawn) print to stdout so cron mails them.  A load
# that fails is captured in its load_result.json and surfaced in the combined
# report as an ALERT (still one email), not a second cron mail.
#
#   run_daily.sh                 normal daily run

set -u
EDR=${SSO_EDR_ROOT:-/data/edr/field_automated_measurements}
CM_BASE=${CM_WORK_ROOT:-$EDR/continuous_monitoring}
SSO_BASE=${SSO_WORK_ROOT:-$EDR/sso_staging}
# Export so the Python children resolve fetch/state/staging under the same roots
# (both default to <FAM_ROOT>/<ns> absolutely; this honors any override too).
export CM_WORK_ROOT="$CM_BASE" SSO_WORK_ROOT="$SSO_BASE" SSO_FAM_ROOT="$EDR"
CM_CODE=$CM_BASE/code
SSO_CODE=$SSO_BASE/code
CM_PY=${CM_PY:-$CM_BASE/.venv/bin/python}
SSO_PY=${SSO_PY:-$SSO_BASE/.venv/bin/python}
BASTION=${CM_BASTION:-ac.jmchandonia@login1.berkeley.kbase.us}
REPORT_TO=${SSO_REPORT_TO:-${CM_REPORT_TO:-jmc}}
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)

CM_STAGE=$CM_BASE/staging/$RUN_ID
SSO_STAGE=$SSO_BASE/staging/$RUN_ID
LOG=$SSO_BASE/logs/combined_$RUN_ID.log
SOCK=$SSO_BASE/state/tunnel.sock
PPROXY_PID=

mkdir -p "$SSO_BASE/logs" "$SSO_BASE/staging" "$SSO_BASE/state" "$CM_BASE/staging"
exec 9>"$SSO_BASE/state/daily.lock"
flock -n 9 || { echo "sso/cm combined daily: previous run still active; skipping $RUN_ID"; exit 0; }

# Credentials (KBASE_AUTH_TOKEN etc.) — prefer sso's, fall back to cm's.
for env in "$SSO_BASE/credentials.env" "$CM_BASE/credentials.env"; do
    [ -f "$env" ] && { set -a; . "$env"; set +a; break; }
done

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }
port_open() { ss -ltn 2>/dev/null | grep -q "127.0.0.1:$1 \|\*:$1 \|\[::1\]:$1 \|0.0.0.0:$1 "; }

cleanup() {
    [ -n "$PPROXY_PID" ] && kill "$PPROXY_PID" 2>/dev/null
    [ -S "$SOCK" ] && ssh -S "$SOCK" -O exit "$BASTION" >/dev/null 2>&1
    find "$SSO_BASE/staging" "$CM_BASE/staging" -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {} + 2>/dev/null
    find "$SSO_BASE/logs" -type f -mtime +90 -delete 2>/dev/null
}

fail() {  # fatal infra error: cron mails stdout
    echo "combined daily run $RUN_ID failed during: $1"
    echo "log: $LOG"
    echo "----"; tail -40 "$LOG"
    cleanup; exit 1
}

is_weekday() { d=$(date +%u); [ "$d" -ge 1 ] && [ "$d" -le 5 ]; }

send_report() {  # $1 = subject; body on stdin
    is_weekday || { cat >/dev/null; return 0; }
    [ -x /usr/sbin/sendmail ] || { cat >/dev/null; return 0; }
    { printf 'To: %s\n' "$REPORT_TO"
      printf 'Subject: %s\n' "$1"
      printf 'Auto-Submitted: auto-generated\n\n'
      cat
    } | /usr/sbin/sendmail -t 2>>"$LOG" || log "combined report send failed"
}

# ---- refresh the Google-Drive NFS mirror (before fetch; no proxy) ----
# Additive `rclone copy` of the ENIGMA team-drive data tree into the local
# mirror that sso_fetch rsyncs from, so data added to Drive since the last run
# is picked up.  (continuous_monitoring pulls straight from the HydroVu/LI-COR
# APIs and does not use this mirror.)  Non-fatal: on failure the existing mirror
# is used and the run continues.  rclone talks to Google directly, so this runs
# before the SOCKS proxy env is exported further below.
MIRROR_ROOT=${ENIGMA_MIRROR_ROOT:-/data/backup/google-drive}
MIRROR_SRC=${ENIGMA_MIRROR_SRC:-enigma_team_drive:/3. Data_ENIGMA/}
MIRROR_DEST=${ENIGMA_MIRROR_DEST:-enigma_team_drive_data_enigma_backup}
if command -v rclone >/dev/null 2>&1 && [ -d "$MIRROR_ROOT/$MIRROR_DEST" ]; then
    log "drive mirror refresh"
    ( cd "$MIRROR_ROOT" && rclone copy --max-depth 20 "$MIRROR_SRC" "$MIRROR_DEST/" -v ) \
        >> "$LOG" 2>&1 || log "drive mirror refresh failed (continuing with existing mirror)"
else
    log "drive mirror refresh skipped (rclone or mirror dir missing: $MIRROR_ROOT/$MIRROR_DEST)"
fi

# ---- fetch + build (no proxy; must not go through the SOCKS tunnel) ----

log "cm fetch"; "$CM_PY" "$CM_CODE/cm_fetch.py" >> "$LOG" 2>&1 || log "cm fetch failed (continuing)"
log "cm build"; "$CM_PY" "$CM_CODE/cm_build.py" --mode incremental --out "$CM_STAGE" >> "$LOG" 2>&1
cm_build_rc=$?
cm_tables=0
[ -f "$CM_STAGE/manifest.json" ] && cm_tables=$("$CM_PY" -c "import json,sys;print(len(json.load(open(sys.argv[1]))['tables']))" "$CM_STAGE/manifest.json" 2>/dev/null || echo 0)

log "sso fetch"; "$SSO_PY" "$SSO_CODE/sso_fetch.py" >> "$LOG" 2>&1 || log "sso fetch failed (continuing)"
log "sso build"; "$SSO_PY" "$SSO_CODE/sso_build.py" --mode incremental --out "$SSO_STAGE" --state "$SSO_BASE/state" >> "$LOG" 2>&1
sso_build_rc=$?
[ "$sso_build_rc" -eq 3 ] && log "sso build: new columns or held ids flagged (see manifest / report)"

# ---- proxy chain + JupyterHub spawn (once) ----

log "proxy chain"
export grpc_proxy=http://127.0.0.1:8123 https_proxy=http://127.0.0.1:8123 no_proxy=localhost,127.0.0.1 BERDL_NO_AUTO_SPAWN=1
if ! port_open 1338; then
    KEYCHAIN_FILE="$HOME/.keychain/$(hostname)-sh"
    [ -z "${SSH_AUTH_SOCK:-}" ] && [ -f "$KEYCHAIN_FILE" ] && . "$KEYCHAIN_FILE"
    rm -f "$SOCK"
    ssh -f -N -M -S "$SOCK" -o BatchMode=yes -o ExitOnForwardFailure=yes \
        -o ServerAliveInterval=60 -o ServerAliveCountMax=3 -o ConnectTimeout=30 \
        -D 127.0.0.1:1338 "$BASTION" >> "$LOG" 2>&1 || fail "ssh tunnel to $BASTION"
fi
if ! port_open 8123; then
    "$SSO_PY" -c "import sys, asyncio; sys.argv=['pproxy','-l','http://127.0.0.1:8123','-r','socks5://127.0.0.1:1338']; asyncio.set_event_loop(asyncio.new_event_loop()); from pproxy.server import main; main()" >> "$LOG" 2>&1 &
    PPROXY_PID=$!
    i=0; until port_open 8123; do i=$((i+1)); [ $i -gt 30 ] && fail "pproxy start"; sleep 1; done
fi

log "jupyterhub"
"$SSO_BASE/.venv/bin/berdl-remote" login --hub-url https://hub.berdl.kbase.us >> "$LOG" 2>&1 || fail "berdl-remote login"
"$SSO_BASE/.venv/bin/berdl-remote" spawn --timeout 180 >> "$LOG" 2>&1 || fail "berdl-remote spawn"

# ---- loads (through proxy; same Spark gateway) ----

if [ "$cm_tables" -gt 0 ]; then
    log "cm nitrate correction (recorded no-op)"
    "$CM_PY" "$CM_CODE/fix_nitrate_20261019.py" --if-needed >> "$LOG" 2>&1 || log "cm nitrate step failed (continuing)"
    log "cm L9-SZ2 depth offset correction (one-time; no-op once recorded)"
    "$CM_PY" "$CM_CODE/fix_offset_20261111.py" --id l9-sz2-depth-offset-20261111 --if-needed >> "$LOG" 2>&1 || log "cm offset step failed (continuing)"
    log "cm load"
    "$CM_PY" "$CM_CODE/cm_load.py" --staging "$CM_STAGE" --run-id "$RUN_ID" --wait-for-spark 300 --check-staleness >> "$LOG" 2>&1 || log "cm load failed (see report)"
    [ -f "$CM_STAGE/build_state_pending.json" ] && mv "$CM_STAGE/build_state_pending.json" "$CM_BASE/state/build_state.json"
    [ -f "$CM_STAGE/reading_schedule_pending.json" ] && mv "$CM_STAGE/reading_schedule_pending.json" "$CM_BASE/state/reading_schedule.json"
else
    log "cm: no new data to load"
    # Stub result so the combined report can still show cm ran cleanly.
    printf '{"ingest_run_id":"%s","mode":"incremental","rows_appended":0,"tables":{},"stale_tables":{},"finished_at":"%s"}\n' \
        "$RUN_ID" "$(date -u '+%F %T')Z" > "$CM_STAGE/load_result.json" 2>/dev/null || true
fi

log "sso load"
"$SSO_PY" "$SSO_CODE/sso_load.py" --staging "$SSO_STAGE" --run-id "$RUN_ID" --wait-for-spark 300 --check-staleness >> "$LOG" 2>&1 || log "sso load failed (see report)"
[ -f "$SSO_STAGE/gas_state_pending.json" ] && mv "$SSO_STAGE/gas_state_pending.json" "$SSO_BASE/state/gas_state.json"

# ---- one combined email ----

log "combined report"
export CM_CODE_DIR="$CM_CODE"
CM_ARGS=""
[ -f "$CM_STAGE/load_result.json" ] && CM_ARGS="--cm $CM_STAGE/load_result.json --cm-state $CM_BASE/state/stale_reported.json"
SSO_ARGS="--sso $SSO_STAGE/load_result.json --sso-state $SSO_BASE/state/report_state.json"
subject=$("$SSO_PY" "$SSO_CODE/combined_report.py" $SSO_ARGS $CM_ARGS --subject 2>>"$LOG") \
    || subject="[enigma lakehouse] $RUN_ID (report failed; see $LOG)"
"$SSO_PY" "$SSO_CODE/combined_report.py" $SSO_ARGS $CM_ARGS --commit 2>>"$LOG" | send_report "$subject"

grep -h "^WARNING" "$LOG"
log "done"
cleanup
exit 0
