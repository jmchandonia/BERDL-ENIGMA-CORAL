#!/usr/bin/env python3
"""Diagnose Spark Connect access to BERDL and optionally restart the user's Hub server.

Prints only non-secret details: tokens, cookies and passwords are never
printed (values of variables whose names suggest secrets are redacted, and
x-kbase-token parameters are stripped from URLs).  Run with the BERDL proxy
chain up (SOCKS 1338 + pproxy 8123).

    berdl_spark_diag.py              diagnose
    berdl_spark_diag.py --restart    diagnose, stop the Hub server, log in, spawn, diagnose again
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cm_common as cm  # noqa: E402

SECRET = re.compile(r"TOKEN|SECRET|PASSWORD|PASSWD|KEY|COOKIE|CREDENTIAL", re.IGNORECASE)
HOSTS = ("metrics.berdl.kbase.us", "spark.berdl.kbase.us")

POD_CODE = r'''
import os, re, socket
secret = re.compile(r"TOKEN|SECRET|PASSWORD|PASSWD|KEY|COOKIE|CREDENTIAL", re.I)
def clean(k, v):
    if secret.search(k):
        return "<redacted>"
    return re.sub(r"(x-kbase-token=)[^;&\s]+", r"\1<redacted>", v)
print("pod hostname:", socket.gethostname())
for k in sorted(os.environ):
    if re.search(r"SPARK|BERDL|JUPYTERHUB_USER|KBASE_USER|CDM", k):
        print(f"pod env {k}={clean(k, os.environ[k])}")
try:
    from berdl_notebook_utils.setup_spark_session import get_spark_session
    s = get_spark_session()
    print("pod spark current_user:", s.sql("SELECT current_user() AS u").collect()[0]["u"])
    print("pod spark version:", s.version)
except Exception as e:
    msg = str(e)
    m = re.search(r'details = "([^"]+)"', msg)
    print("pod spark FAILED:", type(e).__name__, (m.group(1) if m else msg[:300]))
'''


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def probe(host: str, token: str) -> None:
    from spark_connect_remote import create_spark_session

    started = time.monotonic()
    try:
        spark = create_spark_session(host_template=host, port=443, use_ssl=True, kbase_token=token, app_name="berdl_diag")
        user = spark.sql("SELECT current_user() AS u").collect()[0]["u"]
        print(f"[{now()}] {host}: OK current_user={user} ({time.monotonic() - started:.1f}s)")
        spark.stop()
    except Exception as e:  # report the gRPC failure verbatim, minus secrets
        text = re.sub(r"(x-kbase-token=)[^;&\s\"]+", r"\1<redacted>", str(e))
        status = re.search(r"status = (\S+)", text)
        details = re.search(r'details = "([^"]*)"', text)
        debug = re.search(r'debug_error_string = "([^\n]*)"', text)
        print(f"[{now()}] {host}: FAILED after {time.monotonic() - started:.1f}s")
        print(f"    exception: {type(e).__name__}")
        print(f"    grpc status: {status.group(1) if status else '?'}")
        print(f"    details: {details.group(1) if details else text[:300]}")
        if debug:
            print(f"    debug_error_string: {debug.group(1)[:600]}")


def hub_client():
    from berdl_remote.config import load_config
    from berdl_remote.hub import HubClient

    config = load_config()
    return config, HubClient(config)


def hub_report() -> None:
    config, hub = hub_client()
    resp = hub._session.get(f"{config.hub_url}/hub/api/users/{config.username}", timeout=30)
    print(f"[{now()}] hub user API: HTTP {resp.status_code} for user '{config.username}' at {config.hub_url}")
    if resp.ok:
        data = resp.json()
        for name, server in (data.get("servers") or {}).items():
            fields = {k: server.get(k) for k in ("ready", "pending", "started", "last_activity", "url", "stopped")}
            print(f"    server '{name or 'default'}': {fields}")
        if not data.get("servers"):
            print("    no running servers")


def pod_report() -> None:
    from berdl_remote.executor import BERDLRemoteExecutor

    config, _ = hub_client()
    executor = BERDLRemoteExecutor(config)
    out: list[str] = []
    try:
        executor._execute_on_kernel(POD_CODE, out.append)
    except Exception as e:
        out.append(f"pod check failed: {type(e).__name__}: {str(e)[:300]}")
    for line in "".join(out).splitlines():
        print(f"    {line}")


def stop_server() -> None:
    config, hub = hub_client()
    hub._fetch_xsrf(f"{config.hub_url}/hub/home")
    resp = hub._session.delete(f"{config.hub_url}/hub/api/users/{config.username}/server", timeout=60)
    print(f"[{now()}] stop server: HTTP {resp.status_code}")
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        if not hub.server_status().running:
            print(f"[{now()}] server stopped")
            return
        time.sleep(5)
    print(f"[{now()}] server still running after 300 s")


def run_cli(*args: str) -> None:
    cli = str(Path(sys.executable).with_name("berdl-remote"))
    result = subprocess.run([cli, *args], capture_output=True, text=True)
    lines = [l for l in (result.stdout + result.stderr).splitlines() if l.strip() and not SECRET.search(l)]
    print(f"[{now()}] berdl-remote {' '.join(args)}: rc={result.returncode}; " + " | ".join(lines[-3:]))


def diagnose(token: str) -> None:
    hub_report()
    for host in HOSTS:
        probe(host, token)
    print(f"[{now()}] inside the user's Jupyter pod:")
    pod_report()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--restart", action="store_true")
    args = parser.parse_args()

    cm.load_env_file(cm.credentials_file())
    token = os.environ["KBASE_AUTH_TOKEN"]
    os.environ.setdefault("grpc_proxy", "http://127.0.0.1:8123")
    os.environ.setdefault("https_proxy", "http://127.0.0.1:8123")
    os.environ.setdefault("no_proxy", "localhost,127.0.0.1")
    os.environ["BERDL_NO_AUTO_SPAWN"] = "1"

    print(f"[{now()}] client host {socket.gethostname()} ({platform.platform()}), python {platform.python_version()}")
    print(
        f"    pyspark {version('pyspark')}, spark_connect_remote {version('spark_connect_remote')}, "
        f"berdl_remote {version('berdl_remote')}, grpcio {version('grpcio')}"
    )
    print("    route: dipa -> SSH SOCKS tunnel via ac.jmchandonia@login1.berkeley.kbase.us -> pproxy http://127.0.0.1:8123")
    print("    URL: sc://<host>:443/;use_ssl=true;x-kbase-token=<redacted>")

    print("=== before restart")
    diagnose(token)
    if not args.restart:
        return
    print("=== restart: stop Hub server, log in again, spawn a new server")
    stop_server()
    run_cli("login", "--hub-url", "https://hub.berdl.kbase.us")
    run_cli("spawn", "--timeout", "300")
    print("    waiting 60 s for the new server's Spark Connect to come up")
    time.sleep(60)
    print("=== after restart")
    diagnose(token)


if __name__ == "__main__":
    main()
