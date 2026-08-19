#!/usr/bin/env python3
"""Run the verified CORAL-to-BERDL publication path as one resumable command."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
FK_SCRIPT = (
    REPO_ROOT
    / "skills"
    / "check-berdl-foreign-keys"
    / "scripts"
    / "check_foreign_keys.py"
)
DEFAULT_REMOTE_ROOT = Path("/h/jmc/src/BERIL-research-observatory")
DEFAULT_INSTALLED_SKILLS = Path("/h/jmc/.codex/skills")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_dotenv(path: Path) -> list[str]:
    """Load simple KEY=VALUE entries without overriding the caller's env."""
    loaded: list[str] = []
    if not path.is_file():
        return loaded
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value[:1] == value[-1:] and value[:1] in {'"', "'"}:
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    if "KBASE_AUTH_TOKEN" not in os.environ and os.environ.get("KB_AUTH_TOKEN"):
        os.environ["KBASE_AUTH_TOKEN"] = os.environ["KB_AUTH_TOKEN"]
        loaded.append("KBASE_AUTH_TOKEN")
    return loaded


def _set_connection_defaults() -> None:
    os.environ.setdefault("grpc_proxy", "http://127.0.0.1:8123")
    os.environ.setdefault("https_proxy", "http://127.0.0.1:8123")
    os.environ.setdefault("no_proxy", "localhost,127.0.0.1")
    os.environ.setdefault("BERDL_NO_AUTO_SPAWN", "1")


def _port_open(port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def _wait_for_port(port: int, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _port_open(port):
            return
        time.sleep(1)
    raise RuntimeError(f"Timed out waiting for local port {port}")


def _nonempty_process_files(run_dir: Path, run_id: str) -> list[str]:
    """Return lifecycle process TSVs containing at least one payload row."""
    pending: list[str] = []
    metadata = run_dir / "metadata"
    for path in sorted(metadata.glob(f"process_*_{run_id}.tsv")):
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle, delimiter="\t")
            next(reader, None)
            if any(any(cell.strip() for cell in row) for row in reader):
                pending.append(str(path))
    return pending


def _read_names(path: Path | None) -> list[str]:
    if not path or not path.is_file():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _save_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2), encoding="utf-8")
    temporary.replace(path)


def _run(command: list[str], *, env: dict[str, str] | None = None) -> dict[str, Any]:
    started = time.monotonic()
    print("+ " + " ".join(command), flush=True)
    completed = subprocess.run(command, env=env)
    result = {
        "command": command,
        "returncode": completed.returncode,
        "seconds": round(time.monotonic() - started, 3),
    }
    if completed.returncode:
        raise subprocess.CalledProcessError(completed.returncode, command)
    return result


def _resolve_berdl_remote() -> str:
    discovered = shutil.which("berdl-remote")
    if discovered:
        return discovered
    candidate = DEFAULT_REMOTE_ROOT / ".venv-berdl" / "bin" / "berdl-remote"
    if candidate.is_file():
        return str(candidate)
    raise FileNotFoundError("berdl-remote is not installed or on PATH")


def _start_pproxy(run_dir: Path) -> None:
    if _port_open(8123):
        return
    if not _port_open(1338):
        raise RuntimeError(
            "The BERDL SOCKS tunnel on 127.0.0.1:1338 is not running; "
            "start the existing SSH tunnel and rerun this command"
        )
    candidates = [
        DEFAULT_INSTALLED_SKILLS / "berdl-minio" / "scripts" / "start_pproxy.sh",
        DEFAULT_REMOTE_ROOT / "scripts" / "start_pproxy.sh",
    ]
    script = next((path for path in candidates if path.is_file()), None)
    if script is None:
        raise FileNotFoundError("Could not locate the BERDL pproxy startup script")
    log_path = run_dir / "logs" / "pproxy.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        subprocess.Popen(
            ["bash", str(script)],
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=os.environ.copy(),
        )
    _wait_for_port(8123, 30)


def _bootstrap_remote(run_dir: Path) -> list[dict[str, Any]]:
    _start_pproxy(run_dir)
    executable = _resolve_berdl_remote()
    results = []
    for action in ("login", "spawn", "status"):
        results.append(_run([executable, action]))
    # Spawn is asynchronous. Wait for Spark Connect to become usable, while
    # keeping the local HTTP proxy check as the deterministic local preflight.
    time.sleep(10)
    return results


def _stage_command(
    args: argparse.Namespace,
    stage: str,
    table_file: Path,
    fk_table_file: Path,
    drop_table_file: Path | None,
) -> list[str]:
    python = sys.executable
    if stage == "import":
        command = [
            python,
            str(SCRIPT_DIR / "run_full_import.py"),
            "--run-dir",
            str(args.run_dir),
            "--run-id",
            args.run_id,
            "--namespace",
            args.namespace,
            "--table-file",
            str(table_file),
            "--report",
            str(args.run_dir / "reports" / f"full_import_{args.run_id}.json"),
        ]
        if args.resume:
            command.append("--resume")
        if args.skip_upload:
            command.append("--skip-upload")
        if args.skip_import:
            command.append("--skip-import")
        if not _read_names(table_file):
            if "--skip-upload" not in command:
                command.append("--skip-upload")
            if "--skip-import" not in command:
                command.append("--skip-import")
        if args.apply_obsolete_drops:
            if not drop_table_file:
                raise FileNotFoundError("No reviewed obsolete-table list was found")
            command.extend(["--drop-table-file", str(drop_table_file)])
        else:
            command.append("--skip-drop-obsolete")
        return command
    if stage == "verify":
        return [
            python,
            str(SCRIPT_DIR / "verify_full_import.py"),
            "--run-dir",
            str(args.run_dir),
            "--namespace",
            args.namespace,
            "--table-file",
            str(table_file),
        ]
    if stage == "foreign_keys":
        return [
            python,
            str(FK_SCRIPT),
            "--run-dir",
            str(args.run_dir),
            "--namespace",
            args.namespace,
            "--table-file",
            str(fk_table_file),
            "--report-dir",
            str(args.run_dir / "reports"),
        ]
    if stage == "publish":
        command = [
            python,
            str(SCRIPT_DIR / "publish_schema_references.py"),
            "--run-dir",
            str(args.run_dir),
            "--repo-root",
            str(REPO_ROOT),
        ]
        if args.installed_skills_root:
            command.extend(
                ["--installed-skills-root", str(args.installed_skills_root)]
            )
        return command
    if stage == "install_sync_skill":
        source = REPO_ROOT / "skills" / "sync-coral-to-berdl"
        target = args.installed_skills_root / "sync-coral-to-berdl"
        return [
            "rsync",
            "-a",
            "--delete",
            "--exclude",
            "__pycache__",
            str(source) + "/",
            str(target) + "/",
        ]
    raise ValueError(f"Unknown stage: {stage}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run or resume the complete CORAL-to-BERDL sync publication path."
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--namespace", default="enigma_coral")
    parser.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    parser.add_argument("--table-file", type=Path)
    parser.add_argument("--fk-table-file", type=Path)
    parser.add_argument("--drop-table-file", type=Path)
    parser.add_argument("--apply-obsolete-drops", action="store_true")
    parser.add_argument("--skip-upload", action="store_true")
    parser.add_argument("--skip-import", action="store_true")
    parser.add_argument("--skip-verify", action="store_true")
    parser.add_argument("--skip-foreign-keys", action="store_true")
    parser.add_argument("--skip-publish", action="store_true")
    parser.add_argument("--skip-remote-bootstrap", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--installed-skills-root",
        type=Path,
        default=DEFAULT_INSTALLED_SKILLS if DEFAULT_INSTALLED_SKILLS.exists() else None,
    )
    parser.add_argument("--skip-installed-skill-sync", action="store_true")
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="validate local inputs and print commands without network or writes",
    )
    args = parser.parse_args()
    args.run_dir = args.run_dir.resolve()
    args.run_id = args.run_id or args.run_dir.name
    args.env_file = args.env_file.expanduser().resolve()
    if args.installed_skills_root:
        args.installed_skills_root = args.installed_skills_root.expanduser().resolve()
    return args


def main() -> int:
    args = _parse_args()
    if args.skip_verify and not args.skip_publish:
        raise RuntimeError("--skip-verify requires --skip-publish")
    config = args.run_dir / "ingest" / "config.dry_run.json"
    manifest = args.run_dir / "manifests" / "current.json"
    for required in (config, manifest):
        if not required.is_file():
            raise FileNotFoundError(f"Required sync artifact is absent: {required}")

    table_file = (args.table_file or args.run_dir / "ingest" / "changed_tables.txt").resolve()
    fk_table_file = (
        args.fk_table_file
        or args.run_dir / "ingest" / "changed_tables_with_foreign_keys.txt"
    ).resolve()
    if not table_file.is_file():
        raise FileNotFoundError(f"Changed-table list is absent: {table_file}")
    if args.drop_table_file:
        drop_table_file = args.drop_table_file.resolve()
    else:
        candidates = [
            args.run_dir / "ingest" / "live_obsolete_tables.txt",
            args.run_dir / "ingest" / "newly_obsolete_tables.txt",
        ]
        drop_table_file = next((path.resolve() for path in candidates if path.is_file()), None)

    pending = _nonempty_process_files(args.run_dir, args.run_id)
    if pending:
        raise RuntimeError(
            "Pending lifecycle process rows must be imported into CORAL and the "
            f"package regenerated before BERDL sync: {pending}"
        )
    if (
        args.skip_foreign_keys
        and _read_names(fk_table_file)
        and not args.skip_publish
    ):
        raise RuntimeError(
            "--skip-foreign-keys requires --skip-publish when the scoped "
            "foreign-key table list is non-empty"
        )

    stages = ["import"]
    if not args.skip_verify:
        stages.append("verify")
    if not args.skip_foreign_keys and _read_names(fk_table_file):
        stages.append("foreign_keys")
    if not args.skip_publish:
        stages.append("publish")
    if args.installed_skills_root and not args.skip_installed_skill_sync:
        stages.append("install_sync_skill")

    commands = {
        stage: _stage_command(
            args, stage, table_file, fk_table_file, drop_table_file
        )
        for stage in stages
    }
    if args.plan_only:
        print(json.dumps({
            "run_id": args.run_id,
            "namespace": args.namespace,
            "env_file": str(args.env_file),
            "changed_tables": _read_names(table_file),
            "foreign_key_tables": _read_names(fk_table_file),
            "obsolete_drops_enabled": args.apply_obsolete_drops,
            "drop_table_file": str(drop_table_file) if drop_table_file else None,
            "commands": commands,
        }, indent=2))
        return 0

    loaded = _load_dotenv(args.env_file)
    _set_connection_defaults()
    live_stages = {"import", "verify", "foreign_keys"} & set(stages)
    if live_stages and not os.environ.get("KBASE_AUTH_TOKEN"):
        raise RuntimeError(
            f"KBASE_AUTH_TOKEN or KB_AUTH_TOKEN is absent from the environment and {args.env_file}"
        )

    report_path = args.run_dir / "reports" / f"sync_pipeline_{args.run_id}.json"
    if args.resume and report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
    else:
        report = {
            "run_id": args.run_id,
            "namespace": args.namespace,
            "started_at": _utc_now(),
            "steps": {},
        }
    report["env_file"] = str(args.env_file)
    report["env_keys_loaded"] = loaded
    report["obsolete_drops_enabled"] = args.apply_obsolete_drops
    _save_report(report_path, report)

    pending_live = [
        stage for stage in stages
        if stage in live_stages
        and not (args.resume and report.get("steps", {}).get(stage, {}).get("status") == "passed")
    ]
    if pending_live and not args.skip_remote_bootstrap:
        report["remote_bootstrap"] = {
            "status": "running",
            "started_at": _utc_now(),
        }
        _save_report(report_path, report)
        try:
            details = _bootstrap_remote(args.run_dir)
        except Exception as exc:
            report["remote_bootstrap"].update(
                {"status": "failed", "finished_at": _utc_now(), "error": str(exc)}
            )
            _save_report(report_path, report)
            raise
        report["remote_bootstrap"].update(
            {"status": "passed", "finished_at": _utc_now(), "commands": details}
        )
        _save_report(report_path, report)

    for stage in stages:
        previous = report.get("steps", {}).get(stage, {})
        if args.resume and previous.get("status") == "passed":
            print(f"[resume] skipping completed stage: {stage}", flush=True)
            continue
        report.setdefault("steps", {})[stage] = {
            "status": "running",
            "started_at": _utc_now(),
            "command": commands[stage],
        }
        _save_report(report_path, report)
        try:
            details = _run(commands[stage])
            if stage == "install_sync_skill":
                source = REPO_ROOT / "skills" / "sync-coral-to-berdl"
                target = args.installed_skills_root / "sync-coral-to-berdl"
                _run([
                    "diff", "-qr", "--exclude=__pycache__", str(source), str(target)
                ])
        except Exception as exc:
            report["steps"][stage].update({
                "status": "failed",
                "finished_at": _utc_now(),
                "error": str(exc),
            })
            report["status"] = "failed"
            _save_report(report_path, report)
            raise
        report["steps"][stage].update({
            "status": "passed",
            "finished_at": _utc_now(),
            **details,
        })
        _save_report(report_path, report)

    report["status"] = "passed"
    report["finished_at"] = _utc_now()
    _save_report(report_path, report)
    print(f"Sync pipeline completed: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
