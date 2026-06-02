#!/usr/bin/env python3
"""Configure the BERDL MinIO client without printing credentials."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


def _valid(creds: dict[str, str | None]) -> bool:
    return bool(creds.get("MINIO_ACCESS_KEY") and creds.get("MINIO_SECRET_KEY"))


def _run_capture(cmd: list[str], *, env: dict[str, str] | None = None, timeout: int = 60) -> str:
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout


def _parse_last_json(stdout: str) -> dict[str, str | None]:
    for line in reversed(stdout.splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def _remote_berdl_settings() -> dict[str, str | None]:
    if shutil.which("berdl-remote") is None:
        return {}
    code = r"""
import json
settings = BERDLSettings()
print(json.dumps({
    "MINIO_ACCESS_KEY": getattr(settings, "MINIO_ACCESS_KEY", None),
    "MINIO_SECRET_KEY": getattr(settings, "MINIO_SECRET_KEY", None),
    "MINIO_ENDPOINT_URL": getattr(settings, "MINIO_ENDPOINT_URL", None) or "https://minio.berdl.kbase.us",
}))
""".strip()
    stdout = _run_capture(["berdl-remote", "python", code], timeout=90)
    payload = _parse_last_json(stdout)
    payload["source"] = "remote-BERDLSettings"
    return payload


def _local_env() -> dict[str, str | None]:
    return {
        "MINIO_ACCESS_KEY": os.environ.get("MINIO_ACCESS_KEY"),
        "MINIO_SECRET_KEY": os.environ.get("MINIO_SECRET_KEY"),
        "MINIO_ENDPOINT_URL": os.environ.get("MINIO_ENDPOINT_URL") or "https://minio.berdl.kbase.us",
        "source": "local-env",
    }


def _cshrc_env() -> dict[str, str | None]:
    csh = shutil.which("csh") or shutil.which("tcsh")
    if csh is None:
        return {}
    cshrc = Path.home() / ".cshrc"
    if not cshrc.exists():
        return {}
    code = (
        "import json, os; "
        "print(json.dumps({"
        "'MINIO_ACCESS_KEY': os.getenv('MINIO_ACCESS_KEY'), "
        "'MINIO_SECRET_KEY': os.getenv('MINIO_SECRET_KEY'), "
        "'MINIO_ENDPOINT_URL': os.getenv('MINIO_ENDPOINT_URL') or 'https://minio.berdl.kbase.us'}))"
    )
    command = f"source {shlex.quote(str(cshrc))}; python3 -c {shlex.quote(code)}"
    stdout = _run_capture([csh, "-fc", command], timeout=30)
    payload = _parse_last_json(stdout)
    payload["source"] = "cshrc"
    return payload


def _spark_env() -> dict[str, str | None]:
    token = os.environ.get("KBASE_AUTH_TOKEN") or os.environ.get("KB_AUTH_TOKEN")
    if not token:
        return {}
    sys.path.insert(0, "/h/jmc/src/BERIL-research-observatory/scripts")
    import ingest_lib  # noqa: F401
    from pyspark.sql.functions import lit, udf
    from pyspark.sql.types import StringType
    from spark_connect_remote import create_spark_session

    spark = create_spark_session(
        host_template="metrics.berdl.kbase.us",
        port=443,
        use_ssl=True,
        kbase_token=token,
        app_name="sync-coral-minio-env",
    )

    @udf(StringType())
    def getenv(name: str) -> str | None:
        return os.environ.get(name)

    keys = ["MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "MINIO_ENDPOINT_URL"]
    values = {}
    for key in keys:
        values[key] = spark.range(1).select(getenv(lit(key)).alias("value")).collect()[0]["value"]
    values["MINIO_ENDPOINT_URL"] = values.get("MINIO_ENDPOINT_URL") or "https://minio.berdl.kbase.us"
    values["source"] = "spark-env"
    return values


def _configure_mc(creds: dict[str, str | None]) -> None:
    env = os.environ.copy()
    env["MINIO_ACCESS_KEY"] = creds["MINIO_ACCESS_KEY"] or ""
    env["MINIO_SECRET_KEY"] = creds["MINIO_SECRET_KEY"] or ""
    env["MINIO_ENDPOINT_URL"] = creds.get("MINIO_ENDPOINT_URL") or "https://minio.berdl.kbase.us"
    env.setdefault("https_proxy", "http://127.0.0.1:8123")
    env.setdefault("no_proxy", "localhost,127.0.0.1")
    script = Path("/h/jmc/src/BERIL-research-observatory/scripts/configure_mc.sh")
    _run_capture(["bash", str(script), "--berdl-proxy"], env=env, timeout=30)


def main() -> int:
    _load_dotenv(Path(".env"))

    attempts = []
    for resolver in (_remote_berdl_settings, _spark_env, _cshrc_env, _local_env):
        try:
            creds = resolver()
            source = creds.get("source") or resolver.__name__
            if not _valid(creds):
                attempts.append(f"{source}: missing credentials")
                continue
            try:
                _configure_mc(creds)
            except Exception as exc:
                attempts.append(f"{source}: mc rejected credentials ({exc})")
                continue
            print(
                json.dumps(
                    {
                        "success": True,
                        "source": source,
                        "endpoint": creds.get("MINIO_ENDPOINT_URL") or "https://minio.berdl.kbase.us",
                    },
                    indent=2,
                )
            )
            return 0
        except Exception as exc:
            attempts.append(f"{resolver.__name__}: {exc}")

    print("Could not configure MinIO credentials:", file=sys.stderr)
    for attempt in attempts:
        print(f"- {attempt}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
