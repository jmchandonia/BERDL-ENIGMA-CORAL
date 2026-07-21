#!/usr/bin/env python3
"""Download all CORAL bricks concurrently with bounded, resumable requests."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import random
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests


UPSTREAM = Path("/h/jmc/src/CORAL/convert/spark-minio/download_brick_csvs.py")
BASE_URL = "https://coral-enigma.lbl.gov:443/coral"
PUBKEY = Path("/etc/ssl/certs/data_clearinghouse.pub")


def load_upstream():
    spec = importlib.util.spec_from_file_location("coral_brick_download", UPSTREAM)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {UPSTREAM}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def post_with_retries(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, object],
    retries: int,
    timeout: float,
) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                verify=False,
                timeout=(15, timeout),
            )
            response.raise_for_status()
            return response
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < retries:
                response = getattr(exc, "response", None)
                retry_after = 0
                if response is not None and response.status_code in {429, 503}:
                    try:
                        retry_after = int(response.headers.get("Retry-After", "0"))
                    except ValueError:
                        retry_after = 0
                delay = max(retry_after, min(5 * attempt, 30))
                time.sleep(delay + random.random() * 2)
    raise RuntimeError(f"POST failed after {retries} attempts: {url}: {last_error}")


def fetch_catalog(
    headers: dict[str, str], retries: int, timeout: float
) -> list[str]:
    response = post_with_retries(
        f"{BASE_URL}/search",
        headers=headers,
        payload={
            "format": "TSV",
            "raw": True,
            "queryMatch": {
                "category": "DDT_",
                "dataModel": "Brick",
                "dataType": "NDArray",
                "params": [],
            },
        },
        retries=retries,
        timeout=timeout,
    )
    lines = response.text.splitlines()
    if not lines or "brick_id" not in lines[0].split("\t"):
        raise ValueError("CORAL brick catalog response has no brick_id column")
    header = lines[0].split("\t")
    id_index = header.index("brick_id")
    ids = [line.split("\t")[id_index] for line in lines[1:] if line.strip()]
    if len(ids) != len(set(ids)):
        raise ValueError("CORAL brick catalog contains duplicate IDs")
    return ids


def download_one(
    brick_id: str,
    out_dir: Path,
    headers: dict[str, str],
    retries: int,
    timeout: float,
) -> tuple[str, int]:
    response = post_with_retries(
        f"{BASE_URL}/brick/{brick_id}",
        headers=headers,
        payload={"format": "CSV"},
        retries=retries,
        timeout=timeout,
    )
    payload = response.json()
    if payload.get("status") != "success" or not isinstance(payload.get("res"), str):
        raise ValueError(f"CORAL returned an invalid brick payload for {brick_id}")
    content = payload["res"]
    if not content:
        raise ValueError(f"CORAL returned an empty brick payload for {brick_id}")

    destination = out_dir / f"{brick_id}.csv"
    temporary = destination.with_suffix(".csv.downloading")
    temporary.write_text(content)
    temporary.replace(destination)
    return brick_id, destination.stat().st_size


def reuse_immutable_csv(source: Path, destination: Path) -> None:
    temporary = destination.with_suffix(".csv.copying")
    temporary.unlink(missing_ok=True)
    try:
        os.link(source, temporary)
    except OSError:
        subprocess.run(
            [
                "cp",
                "--reflink=auto",
                "--preserve=mode,timestamps",
                str(source),
                str(temporary),
            ],
            check=True,
        )
    temporary.replace(destination)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument(
        "--previous-run-dir",
        type=Path,
        help=(
            "Reuse immutable brick CSVs for catalog IDs present in the prior "
            "run and download only newly added IDs."
        ),
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    upstream = load_upstream()
    headers = upstream.build_authorized_headers(upstream.load_public_key(str(PUBKEY)))
    brick_ids = fetch_catalog(headers, args.retries, args.timeout)
    reused_prior: list[str] = []
    if args.previous_run_dir:
        previous_raw = args.previous_run_dir / "coral_export" / "brick_csv"
        for brick_id in brick_ids:
            destination = args.out_dir / f"{brick_id}.csv"
            if destination.is_file() and destination.stat().st_size > 0:
                continue
            source = previous_raw / destination.name
            if not source.is_file() or source.stat().st_size == 0:
                continue
            reuse_immutable_csv(source, destination)
            reused_prior.append(brick_id)

    pending = [
        brick_id
        for brick_id in brick_ids
        if not (args.out_dir / f"{brick_id}.csv").is_file()
        or (args.out_dir / f"{brick_id}.csv").stat().st_size == 0
    ]
    print(
        f"catalog={len(brick_ids)} existing={len(brick_ids) - len(pending)} "
        f"reused_prior={len(reused_prior)} new_pending={len(pending)}",
        flush=True,
    )

    failures: list[dict[str, str]] = []
    completed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                download_one,
                brick_id,
                args.out_dir,
                headers,
                args.retries,
                args.timeout,
            ): brick_id
            for brick_id in pending
        }
        for future in as_completed(futures):
            brick_id = futures[future]
            try:
                future.result()
                completed += 1
                if completed % 50 == 0 or completed == len(pending):
                    print(f"downloaded={completed}/{len(pending)}", flush=True)
            except Exception as exc:
                failures.append({"brick_id": brick_id, "error": repr(exc)})
                print(f"FAILED {brick_id}: {exc}", flush=True)

    missing = [
        brick_id
        for brick_id in brick_ids
        if not (args.out_dir / f"{brick_id}.csv").is_file()
        or (args.out_dir / f"{brick_id}.csv").stat().st_size == 0
    ]
    manifest = {
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE_URL,
        "catalog_count": len(brick_ids),
        "catalog_ids": brick_ids,
        "reused_prior_ids": reused_prior,
        "downloaded_new_ids": [
            brick_id for brick_id in pending if brick_id not in missing
        ],
        "completed_files": len(brick_ids) - len(missing),
        "missing_ids": missing,
        "failures": failures,
        "workers": args.workers,
        "retries": args.retries,
        "timeout_seconds": args.timeout,
    }
    manifest_path = args.out_dir.parent / "brick_download_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        f"complete={manifest['completed_files']} missing={len(missing)} "
        f"manifest={manifest_path}",
        flush=True,
    )
    return 1 if missing or failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
