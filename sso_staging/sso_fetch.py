#!/usr/bin/env python3
"""Refresh the local copy of the SSO campaign Drive subfolder.

Two modes (default = mirror):
  * mirror  rsync the '2026 SSO Time Series Field Data' subfolder out of the
            existing dipa Google-Drive NFS mirror into SSO_FETCH_DIR.  This is the
            default because the mirror is already maintained by its own rclone job
            and needs no Drive credentials here.
  * rclone  `rclone copy REMOTE SSO_FETCH_DIR` when SSO_RCLONE_REMOTE is set (the
            remote should already point at the campaign subfolder).

Env:
  SSO_FETCH_DIR     destination (default: <work_root>/fetch)
  SSO_MIRROR_DIR    NFS mirror root of the team drive (mirror mode)
  SSO_RCLONE_REMOTE rclone 'remote:path' (rclone mode)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import sso_common as sso

SUBFOLDER = "2026 SSO Time Series Field Data"
DEFAULT_MIRROR = ("/mnt/net/dipa.jmcnet/data/backup/google-drive/"
                  "enigma_team_drive_data_enigma_backup/Sampling Mission Control")


def log(msg: str) -> None:
    print(msg, flush=True)


def main() -> None:
    dest = sso.FETCH_DIR
    dest.mkdir(parents=True, exist_ok=True)
    remote = os.environ.get("SSO_RCLONE_REMOTE")
    if remote:
        log(f"rclone copy {remote} -> {dest}")
        cmd = ["rclone", "copy", remote, str(dest), "--transfers=4", "--checkers=8"]
    else:
        src = Path(os.environ.get("SSO_MIRROR_DIR", DEFAULT_MIRROR)) / SUBFOLDER
        if not src.is_dir():
            sys.exit(f"mirror subfolder not found: {src} (set SSO_MIRROR_DIR or SSO_RCLONE_REMOTE)")
        log(f"rsync {src}/ -> {dest}/")
        # --delete so files removed upstream disappear here too; keep it a faithful copy.
        cmd = ["rsync", "-a", "--delete", f"{src}/", f"{dest}/"]
    rc = subprocess.run(cmd).returncode
    if rc != 0:
        sys.exit(f"fetch failed (exit {rc})")
    log("fetch ok")


if __name__ == "__main__":
    main()
