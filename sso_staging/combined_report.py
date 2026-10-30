#!/usr/bin/env python3
"""Compose ONE daily email covering both the continuous_monitoring and the
sso_staging loads, so the operator gets a single message per day.

run_daily.sh runs both loads (each writes its own load_result.json), then calls
this with both results.  The continuous_monitoring section reuses cm_report's own
body + stateful silent-instrument diff; the sso_staging section comes from
sso_report.  Either side may be absent (e.g. cm had nothing to load).

    combined_report.py --sso SSO_RESULT [--cm CM_RESULT] [--cm-state FILE]
                       [--subject] [--commit]

--subject prints the one-line subject; otherwise the body.  --commit advances the
cm silent-instrument state (run once per message).  CM_CODE_DIR must point at the
continuous_monitoring code dir so cm_report can be imported (falls back to
sso-only if it cannot).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import sso_report

RUN_TAG = "[enigma daily]"


def _load(path):
    return json.loads(Path(path).read_text()) if path and Path(path).exists() else None


def _import_cm_report():
    cm_dir = os.environ.get("CM_CODE_DIR")
    if cm_dir and cm_dir not in sys.path:
        sys.path.insert(0, cm_dir)
    try:
        import cm_report
        return cm_report
    except Exception:
        return None


def build(cm_data, cm_diff, cm_mod, sso_data):
    alert = bool(sso_data and sso_report.has_alert(sso_data))
    cm_frag = "cm n/a"
    if cm_data is not None:
        appended = cm_data.get("rows_appended", 0)
        newly = len(cm_diff["newly"]) if cm_diff else 0
        cm_frag = f"cm +{appended:,}" + (f", {newly} newly silent" if newly else "")
        alert = alert or bool(newly)
    sso_frag = sso_report.subject_fragment(sso_data) if sso_data else "sso n/a"
    run = (sso_data or cm_data or {}).get("ingest_run_id", "?")
    subject = f"{RUN_TAG} {'ALERT' if alert else 'OK'} {run}: {cm_frag} | {sso_frag}"

    blocks = [f"{RUN_TAG} daily lakehouse load — {run}", ""]
    if cm_data is not None and cm_mod is not None:
        blocks.append(cm_mod.body(cm_data, cm_diff))
    elif cm_data is not None:
        blocks.append(f"continuous_monitoring: {cm_data.get('rows_appended', 0):,} rows appended "
                      f"(cm_report unavailable for detail).\n")
    else:
        blocks.append("continuous_monitoring: no result this run.\n")
    blocks.append("-" * 64)
    blocks.append(sso_report.body_section(sso_data) if sso_data else "sso_staging: no result this run.\n")
    return subject, "\n".join(blocks)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sso", required=True)
    ap.add_argument("--cm")
    ap.add_argument("--cm-state")
    ap.add_argument("--subject", action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    sso_data = _load(args.sso)
    cm_data = _load(args.cm)
    cm_mod = _import_cm_report() if cm_data is not None else None
    cm_diff = None
    if cm_data is not None and cm_mod is not None:
        cm_diff = cm_mod.stale_diff(cm_data, Path(args.cm_state) if args.cm_state else None)
        if args.commit and args.cm_state and cm_diff["new_state"] is not None:
            Path(args.cm_state).write_text(json.dumps(cm_diff["new_state"], indent=2) + "\n")

    subject, body = build(cm_data, cm_diff, cm_mod, sso_data)
    print(subject if args.subject else body, end="\n" if args.subject else "")


if __name__ == "__main__":
    main()
