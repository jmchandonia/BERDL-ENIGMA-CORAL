#!/bin/sh
# Daily enigma.continuous_monitoring update; run from cron on dipa.
#
# fetch (HydroVu + LI-COR, last 14 days) -> build staged TSVs -> open the
# BERDL proxy chain -> append to the lakehouse -> close the proxy chain.
# Prints nothing on success (so cron mails only failures and warnings).
#
#   run_daily.sh                      normal daily run
#   run_daily.sh --load-only DIR      skip fetch/build; load an existing staging
#                                     directory (e.g. a backfill) and commit its state

set -u
BASE=${CM_WORK_ROOT:-/data/edr/field_automated_measurements/continuous_monitoring}
CODE=$BASE/code
PY=$BASE/.venv/bin/python
BASTION=${CM_BASTION:-ac.jmchandonia@login1.berkeley.kbase.us}
# Weekday success report recipient; relays to the real inbox via lambic.
REPORT_TO=${CM_REPORT_TO:-jmc}
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
STAGE=$BASE/staging/$RUN_ID
LOAD_ONLY=
if [ "${1:-}" = "--load-only" ]; then
    LOAD_ONLY=1
    STAGE=$(cd "$2" && pwd) || exit 1
fi
LOG=$BASE/logs/daily_$RUN_ID.log
SOCK=$BASE/state/tunnel.sock
PPROXY_PID=

mkdir -p "$BASE/logs" "$BASE/staging" "$BASE/state"
exec 9>"$BASE/state/daily.lock"
flock -n 9 || { echo "continuous_monitoring: previous daily run still active; skipping $RUN_ID"; exit 0; }

if [ -f "$BASE/credentials.env" ]; then
    set -a; . "$BASE/credentials.env"; set +a
fi

port_open() { ss -ltn 2>/dev/null | grep -q "127.0.0.1:$1 \|\*:$1 \|\[::1\]:$1 \|0.0.0.0:$1 "; }

cleanup() {
    [ -n "$PPROXY_PID" ] && kill "$PPROXY_PID" 2>/dev/null
    [ -S "$SOCK" ] && ssh -S "$SOCK" -O exit "$BASTION" >/dev/null 2>&1
    find "$BASE/staging" -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {} + 2>/dev/null
    find "$BASE/logs" -type f -mtime +90 -delete 2>/dev/null
}

fail() {
    echo "continuous_monitoring daily run $RUN_ID failed during: $1"
    echo "log: $LOG"
    echo "----"
    tail -40 "$LOG"
    cleanup
    exit 1
}

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

# A positive confirmation on weekdays (Mon-Fri) lets the user tell "no mail
# because nothing failed" apart from "no mail because the whole run died".
# Failures still mail via cron (fail() prints to stdout); this is the success
# counterpart.  No-op on weekends and if sendmail is missing.
is_weekday() { d=$(date +%u); [ "$d" -ge 1 ] && [ "$d" -le 5 ]; }

send_report() {  # $1 = subject; body on stdin
    is_weekday || { cat >/dev/null; return 0; }
    [ -x /usr/sbin/sendmail ] || { cat >/dev/null; return 0; }
    { printf 'To: %s\n' "$REPORT_TO"
      printf 'Subject: %s\n' "$1"
      printf 'Auto-Submitted: auto-generated\n\n'
      cat
    } | /usr/sbin/sendmail -t 2>>"$LOG" || log "weekday report send failed"
}

report_load() {  # email the success report built from the staging load_result.json
    result="$STAGE/load_result.json"
    [ -f "$result" ] || { log "no load_result.json; skipping weekday report"; return 0; }
    subject=$("$PY" cm_report.py "$result" --subject 2>>"$LOG") || subject="[continuous_monitoring] OK $RUN_ID"
    "$PY" cm_report.py "$result" 2>>"$LOG" | send_report "$subject"
}

cd "$CODE" || fail "cd $CODE"

if [ -z "$LOAD_ONLY" ]; then
log "fetch"
"$PY" cm_fetch.py >> "$LOG" 2>&1 || fail "fetch"

log "build"
"$PY" cm_build.py --mode incremental --out "$STAGE" >> "$LOG" 2>&1
rc=$?
[ $rc -eq 0 ] || [ $rc -eq 3 ] || fail "build"
[ $rc -eq 3 ] && echo "continuous_monitoring $RUN_ID: some tables held back for unknown measurement labels; see $STAGE/manifest.json"

tables=$("$PY" -c "import json,sys; print(len(json.load(open(sys.argv[1]))['tables']))" "$STAGE/manifest.json")
if [ "$tables" -eq 0 ]; then
    log "nothing new to load"
    [ -f "$STAGE/build_state_pending.json" ] && mv "$STAGE/build_state_pending.json" "$BASE/state/build_state.json"
    [ -f "$STAGE/reading_schedule_pending.json" ] && mv "$STAGE/reading_schedule_pending.json" "$BASE/state/reading_schedule.json"
    grep -h "^WARNING" "$LOG"
    send_report "[continuous_monitoring] OK $RUN_ID: no new data" <<EOF
enigma.continuous_monitoring daily run $RUN_ID succeeded.

No new readings were available to append this run (fetch and build ran
cleanly; every staged row was already in the lakehouse).
EOF
    cleanup
    exit 0
fi
fi

log "proxy chain"
# Only the BERDL steps go through the proxy; the HydroVu/LI-COR fetch must not.
export grpc_proxy=http://127.0.0.1:8123 https_proxy=http://127.0.0.1:8123 no_proxy=localhost,127.0.0.1 BERDL_NO_AUTO_SPAWN=1
if ! port_open 1338; then
    # cron has no SSH agent; use the keychain agent that ~/.cshrc starts on
    # interactive logins (id_rsa has a passphrase).
    KEYCHAIN_FILE="$HOME/.keychain/$(hostname)-sh"
    [ -z "${SSH_AUTH_SOCK:-}" ] && [ -f "$KEYCHAIN_FILE" ] && . "$KEYCHAIN_FILE"
    rm -f "$SOCK"
    ssh -f -N -M -S "$SOCK" -o BatchMode=yes -o ExitOnForwardFailure=yes \
        -o ServerAliveInterval=60 -o ServerAliveCountMax=3 -o ConnectTimeout=30 \
        -D 127.0.0.1:1338 "$BASTION" >> "$LOG" 2>&1 || fail "ssh tunnel to $BASTION (if dipa rebooted, log into dipa once so keychain can load ~/.ssh/id_rsa)"
fi
if ! port_open 8123; then
    "$PY" -c "import sys, asyncio; sys.argv = ['pproxy', '-l', 'http://127.0.0.1:8123', '-r', 'socks5://127.0.0.1:1338']; asyncio.set_event_loop(asyncio.new_event_loop()); from pproxy.server import main; main()" >> "$LOG" 2>&1 &
    PPROXY_PID=$!
    i=0
    until port_open 8123; do
        i=$((i + 1)); [ $i -gt 30 ] && fail "pproxy start"; sleep 1
    done
fi

log "jupyterhub"
"$BASE/.venv/bin/berdl-remote" login --hub-url https://hub.berdl.kbase.us >> "$LOG" 2>&1 || fail "berdl-remote login"
"$BASE/.venv/bin/berdl-remote" spawn --timeout 180 >> "$LOG" 2>&1 || fail "berdl-remote spawn"

log "nitrate correction (one-time; no-op once recorded in ingest_runs)"
# Non-fatal: the correction is permanently recorded, so this is a no-op whose
# only work is opening a Spark session.  That session has no readiness wait, so
# it can lose the spawn race (pod up, port 15002 not yet listening).  Never let
# that block the load, which rides out the same race with --wait-for-spark.
"$PY" fix_nitrate_20261019.py --if-needed >> "$LOG" 2>&1 || log "nitrate correction step failed (continuing; it is a recorded no-op)"

log "load"
"$PY" cm_load.py --staging "$STAGE" --run-id "$RUN_ID" --wait-for-spark 300 >> "$LOG" 2>&1 || fail "load"
[ -f "$STAGE/build_state_pending.json" ] && mv "$STAGE/build_state_pending.json" "$BASE/state/build_state.json"
[ -f "$STAGE/reading_schedule_pending.json" ] && mv "$STAGE/reading_schedule_pending.json" "$BASE/state/reading_schedule.json"
grep -h "^WARNING" "$LOG"
report_load
log "done"
cleanup
exit 0
