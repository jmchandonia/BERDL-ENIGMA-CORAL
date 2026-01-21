import os
import sys
import requests

BASE_URL = "https://hub.berdl.kbase.us/apis/mcp"


def main() -> int:
    token = os.environ.get("KBASE_TOKEN")
    if not token:
        print("KBASE_TOKEN is not set", file=sys.stderr)
        return 2

    headers = {"Authorization": f"Bearer {token}"}
    payload = {"use_hms": True, "filter_by_namespace": True}

    resp = requests.post(f"{BASE_URL}/delta/databases/list", json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    print("\n".join(resp.json().get("databases", [])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
