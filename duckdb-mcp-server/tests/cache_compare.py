#!/usr/bin/env python3
"""
Compare cached BERDL MCP responses against a target MCP base URL.

Usage:
  uv run python duckdb-mcp-server/tests/cache_compare.py --cache-dir /path/to/.berdl_cache --base-url http://10.2.2.14/apis/mcp
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

import requests


@dataclass
class CacheEntry:
    path: Path
    url: str
    payload: Dict[str, Any]
    response: Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare cached MCP responses against a target base URL."
    )
    parser.add_argument(
        "--cache-dir",
        required=True,
        help="Path to BERDL cache directory (e.g., .berdl_cache).",
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="Target MCP base URL to compare against.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Request timeout in seconds (default: 120).",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Optional limit on number of cache files to compare.",
    )
    parser.add_argument(
        "--auth-token",
        default=os.environ.get("KB_AUTH_TOKEN"),
        help="Optional auth token; defaults to KB_AUTH_TOKEN env var.",
    )
    return parser.parse_args()


def iter_cache_files(cache_dir: Path) -> Iterable[Path]:
    for path in sorted(cache_dir.glob("*.json")):
        yield path


def load_cache_entry(path: Path) -> Optional[CacheEntry]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None

    if isinstance(data, dict) and "query" in data and "response" in data:
        query = data.get("query") or {}
        url = query.get("url")
        payload = query.get("payload")
        if isinstance(url, str) and isinstance(payload, dict):
            return CacheEntry(path=path, url=url, payload=payload, response=data.get("response"))
        return None

    return None


def rebuild_url(base_url: str, cached_url: str) -> str:
    cached_path = urlparse(cached_url).path
    base_path = urlparse(base_url).path.rstrip("/")
    if base_path and cached_path.startswith(base_path):
        cached_path = cached_path[len(base_path) :]
    return base_url.rstrip("/") + cached_path


def normalize_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2)


def summarize_json(data: Any, max_len: int = 600) -> str:
    dump = normalize_json(data)
    if len(dump) <= max_len:
        return dump
    return dump[:max_len] + "\n... (truncated)"


def normalize_string(value: str) -> str:
    if "https://genomics.lbl.gov/enigma-data" in value:
        value = value.replace("https://genomics.lbl.gov/enigma-data/", "enigma-data-repository/")
        value = value.replace("https://genomics.lbl.gov/enigma-data", "enigma-data-repository")
    return value


def _decimal_places(value: Decimal) -> int:
    exp = value.as_tuple().exponent
    return max(-exp, 0)


def _to_decimal(value: Any) -> Optional[Decimal]:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def numbers_match(a: Any, b: Any) -> bool:
    da = _to_decimal(a)
    db = _to_decimal(b)
    if da is None or db is None:
        return False
    if da == db:
        return True
    places_a = _decimal_places(da)
    places_b = _decimal_places(db)
    if places_a == places_b:
        return False
    if places_a < places_b:
        less_precise = da
        more_precise = db
        places = places_a
    else:
        less_precise = db
        more_precise = da
        places = places_b
    quant = Decimal(1).scaleb(-places)
    try:
        return more_precise.quantize(quant) == less_precise
    except (InvalidOperation, ValueError):
        return False


def compare_values(expected: Any, actual: Any) -> bool:
    if expected is actual:
        return True
    if isinstance(expected, str) and isinstance(actual, str):
        return normalize_string(expected) == normalize_string(actual)
    if isinstance(expected, (int, float, Decimal)) and isinstance(actual, (int, float, Decimal)):
        return numbers_match(expected, actual)
    if isinstance(expected, dict) and isinstance(actual, dict):
        if expected.keys() != actual.keys():
            return False
        return all(compare_values(expected[k], actual[k]) for k in expected)
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return False
        return all(compare_values(e, a) for e, a in zip(expected, actual))
    return expected == actual


def find_first_diff(expected: Any, actual: Any, path: str = "$") -> Optional[str]:
    if compare_values(expected, actual):
        return None
    if isinstance(expected, dict) and isinstance(actual, dict):
        expected_keys = set(expected.keys())
        actual_keys = set(actual.keys())
        if expected_keys != actual_keys:
            missing = sorted(expected_keys - actual_keys)
            extra = sorted(actual_keys - expected_keys)
            return f"{path}: key mismatch missing={missing} extra={extra}"
        for key in sorted(expected_keys):
            sub = find_first_diff(expected[key], actual[key], f"{path}.{key}")
            if sub:
                return sub
        return f"{path}: dict mismatch"
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return f"{path}: list length {len(expected)} != {len(actual)}"
        for idx, (e, a) in enumerate(zip(expected, actual)):
            sub = find_first_diff(e, a, f"{path}[{idx}]")
            if sub:
                return sub
        return f"{path}: list mismatch"
    if isinstance(expected, str) and isinstance(actual, str):
        return (
            f"{path}: string mismatch\n"
            f"  expected={summarize_json(normalize_string(expected))}\n"
            f"  actual={summarize_json(normalize_string(actual))}"
        )
    if isinstance(expected, (int, float, Decimal)) or isinstance(actual, (int, float, Decimal)):
        return f"{path}: number mismatch expected={expected} actual={actual}"
    return f"{path}: value mismatch expected={expected} actual={actual}"


def compare_responses(expected: Any, actual: Any) -> Tuple[bool, str]:
    if compare_values(expected, actual):
        return True, ""
    detail = find_first_diff(expected, actual)
    return False, detail or "mismatch"


def main() -> int:
    args = parse_args()
    cache_dir = Path(args.cache_dir)
    if not cache_dir.exists() or not cache_dir.is_dir():
        print(f"Cache directory not found: {cache_dir}", file=sys.stderr)
        return 2

    headers: Dict[str, str] = {}
    if args.auth_token:
        headers["Authorization"] = f"Bearer {args.auth_token}"

    mismatches: List[str] = []
    errors: List[str] = []
    total = 0
    matched = 0

    for idx, path in enumerate(iter_cache_files(cache_dir)):
        if args.max_files is not None and idx >= args.max_files:
            break
        entry = load_cache_entry(path)
        if entry is None:
            continue
        total += 1
        url = rebuild_url(args.base_url, entry.url)
        try:
            resp = requests.post(url, json=entry.payload, headers=headers, timeout=args.timeout)
        except Exception as exc:
            errors.append(f"{path.name}: request error: {exc}")
            continue

        if resp.status_code == 404:
            errors.append(f"{path.name}: 404 Not Found url={url} payload={entry.payload}")
            continue

        if resp.status_code >= 400:
            body = resp.text[:500] if resp.text else ""
            errors.append(
                f"{path.name}: HTTP {resp.status_code} url={url} payload={entry.payload} body={body}"
            )
            continue

        try:
            actual = resp.json()
        except Exception as exc:
            errors.append(f"{path.name}: JSON decode error: {exc}")
            continue

        same, reason = compare_responses(entry.response, actual)
        if same:
            matched += 1
            continue

        mismatch_detail = (
            f"{path.name}: url={url}\n"
            f"payload={normalize_json(entry.payload)}\n"
            f"diff={reason}\n"
            f"expected={summarize_json(entry.response)}\n"
            f"actual={summarize_json(actual)}"
        )
        mismatches.append(mismatch_detail)

    print(f"Compared: {total}")
    print(f"Matched: {matched}")
    print(f"Mismatched: {len(mismatches)}")
    print(f"Errors: {len(errors)}")

    if mismatches:
        print("Mismatched cache entries:")
        for detail in mismatches[:20]:
            print("-" * 80)
            print(detail)
        if len(mismatches) > 20:
            print(f"  ... and {len(mismatches) - 20} more")

    if errors:
        print("Errors:")
        for err in errors[:50]:
            print(f"  - {err}")
        if len(errors) > 50:
            print(f"  ... and {len(errors) - 50} more")

    return 0 if not mismatches and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
