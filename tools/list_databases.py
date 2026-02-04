import argparse
import os
import sys
import requests

DEFAULT_BASE_URL = "https://hub.berdl.kbase.us/apis/mcp"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List BERDL MCP databases")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"MCP base URL (default: {DEFAULT_BASE_URL})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = os.environ.get("KB_AUTH_TOKEN")
    if not token:
        print("KB_AUTH_TOKEN is not set", file=sys.stderr)
        return 2

    headers = {"Authorization": f"Bearer {token}"}
    payload = {"use_hms": True, "filter_by_namespace": True}

    resp = requests.post(
        f"{args.base_url}/delta/databases/list",
        json=payload,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    print("\n".join(resp.json().get("databases", [])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
