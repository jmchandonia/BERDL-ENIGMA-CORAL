#!/usr/bin/env python3
"""Fetch recent HydroVu and LI-COR API data for enigma.continuous_monitoring.

Unlike field_automated_measurements/{hydrovu,licor}/get_new_data.py (which
stop at today-2 and never revisit a day), this fetcher:

* fetches through the current time, including today's partial day;
* re-fetches any day in the last --window-days (default 14) that is missing,
  failed, returned no data, or was fetched before the day was complete;
* writes into WORK_ROOT/fetch, never into the EDR hydrovu/ or licor/ trees,
  so partial days cannot leak into the monthly CORAL conversion.

Files are named by the day they actually contain (the EDR files are named one
day late):  fetch/hydrovu/YYYY/MM/YYMMDD_<location>_<page>.json and
fetch/licor/YYYY/MM/YYMMDD_weather_data.json.  HydroVu days are local
(America/New_York) days, as in the EDR fetcher; LI-COR days are UTC days,
because the LI-COR API interprets the naive window as UTC.

Credentials come from the environment or WORK_ROOT/credentials.env:
HYDROVU_CLIENT_ID, HYDROVU_CLIENT_SECRET, LICOR_API_TOKEN (and optionally
HYDROVU_SCOPE, LICOR_LOGGERS).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

import cm_common as cm

EASTERN = ZoneInfo("America/New_York")
HYDROVU_TOKEN_URL = "https://www.hydrovu.com/public-api/oauth/token"
HYDROVU_API = "https://www.hydrovu.com/public-api/v1/"
LICOR_URL = "https://api.licor.cloud/v1/data"
NO_RESULTS = "No results were found for these filters"
TIMEOUT = 120


def log(msg: str) -> None:
    print(msg, flush=True)


class FetchState:
    def __init__(self, path: Path):
        self.path = path
        try:
            data = json.loads(path.read_text())
        except FileNotFoundError:
            data = {}
        self.days: dict[str, dict] = data.get("days", {})
        self.files: dict[str, dict] = data.get("files", {})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"days": self.days, "files": self.files}, indent=1, sort_keys=True) + "\n")
        tmp.replace(self.path)

    def needs_fetch(self, key: str) -> bool:
        entry = self.days.get(key)
        return entry is None or entry.get("status") != "ok" or not entry.get("complete")


def write_json_atomic(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    tmp.replace(path)


def window_days(today: date, n: int) -> list[date]:
    return [today - timedelta(days=i) for i in range(n, -1, -1)]


# ---------------------------------------------------------------- HydroVu
def hydrovu_token() -> str:
    data = {"grant_type": "client_credentials", "scope": os.environ.get("HYDROVU_SCOPE", "public-api")}
    client = (os.environ["HYDROVU_CLIENT_ID"], os.environ["HYDROVU_CLIENT_SECRET"])
    response = requests.post(HYDROVU_TOKEN_URL, data={**data, "client_id": client[0], "client_secret": client[1]}, timeout=TIMEOUT)
    if response.status_code == 401:
        response = requests.post(HYDROVU_TOKEN_URL, data=data, auth=client, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()["access_token"]


def hydrovu_pages(url: str, token: str):
    headers = {"Authorization": f"Bearer {token}", "X-ISI-Start-Page": ""}
    while True:
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        yield response
        if response.status_code != 200:
            return
        next_page = response.headers.get("X-ISI-Next-Page")
        if not next_page:
            return
        headers["X-ISI-Start-Page"] = next_page


def safe_name(name: str) -> str:
    return re.sub(r"[ ()/]", "_", name)


def fetch_hydrovu(state: FetchState, now: datetime, n_days: int, settle: timedelta) -> dict[str, int]:
    counts = {"requests": 0, "ok": 0, "no_data": 0, "error": 0}
    token = hydrovu_token()
    locations = []
    for response in hydrovu_pages(HYDROVU_API + "locations/list", token):
        response.raise_for_status()
        locations.extend(response.json())
    today = now.astimezone(EASTERN).date()
    for loc in locations:
        name = safe_name(str(loc.get("name", "")))
        if not name or "DO_NOT_USE" in name.upper() or name.startswith("default-"):
            continue
        for day in window_days(today, n_days):
            key = f"hydrovu/{name}/{day.isoformat()}"
            if not state.needs_fetch(key):
                continue
            start = datetime(day.year, day.month, day.day, tzinfo=EASTERN)
            end = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=EASTERN)
            url = f"{HYDROVU_API}locations/{loc['id']}/data?startTime={int(start.timestamp())}&endTime={int(end.timestamp())}"
            fetched_at = datetime.now(timezone.utc)
            pages: list[dict] = []
            status = "ok"
            for response in hydrovu_pages(url, token):
                counts["requests"] += 1
                if response.status_code == 200:
                    pages.append(response.json())
                elif NO_RESULTS in response.text:
                    status = "no_data"
                else:
                    status = "error"
                    log(f"HydroVu {name} {day}: HTTP {response.status_code}")
            counts[status] += 1
            stem = f"hydrovu/{day:%Y}/{day:%m}/{day:%y%m%d}_{name}"
            old = [rel for rel in state.files if rel.startswith(stem + "_")]
            complete = fetched_at >= end.astimezone(timezone.utc) + settle
            if status == "ok":
                new = []
                for page_no, obj in enumerate(pages):
                    rel = f"{stem}_{page_no}.json"
                    write_json_atomic(cm.FETCH_DIR / rel, obj)
                    state.files[rel] = {"day": day.isoformat(), "complete": complete, "fetched_at": fetched_at.isoformat()}
                    new.append(rel)
                for rel in set(old) - set(new):
                    (cm.FETCH_DIR / rel).unlink(missing_ok=True)
                    state.files.pop(rel, None)
            state.days[key] = {"status": status, "complete": complete, "fetched_at": fetched_at.isoformat(), "pages": len(pages)}
        state.save()
    return counts


# ---------------------------------------------------------------- LI-COR
def fetch_licor(state: FetchState, now: datetime, n_days: int, settle: timedelta) -> dict[str, int]:
    counts = {"requests": 0, "ok": 0, "no_data": 0, "error": 0}
    headers = {"Authorization": f"Bearer {os.environ['LICOR_API_TOKEN']}", "Accept": "application/json"}
    loggers = os.environ.get("LICOR_LOGGERS", "21297014")
    today = now.astimezone(timezone.utc).date()
    for day in window_days(today, n_days):
        key = f"licor/{loggers}/{day.isoformat()}"
        if not state.needs_fetch(key):
            continue
        params = {
            "loggers": loggers,
            "start_date_time": f"{day.isoformat()} 00:00:00",
            "end_date_time": f"{day.isoformat()} 23:59:59",
        }
        fetched_at = datetime.now(timezone.utc)
        response = requests.get(LICOR_URL, headers=headers, params=params, timeout=TIMEOUT)
        counts["requests"] += 1
        status = "error"
        if response.status_code == 200:
            obj = response.json()
            status = "ok" if obj.get("data") else "no_data"
            if status == "ok":
                rel = f"licor/{day:%Y}/{day:%m}/{day:%y%m%d}_weather_data.json"
                complete = fetched_at >= datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=timezone.utc) + settle
                write_json_atomic(cm.FETCH_DIR / rel, obj)
                state.files[rel] = {"day": day.isoformat(), "complete": complete, "fetched_at": fetched_at.isoformat()}
        else:
            log(f"LI-COR {day}: HTTP {response.status_code}")
        counts[status] += 1
        end = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=timezone.utc)
        state.days[key] = {"status": status, "complete": fetched_at >= end + settle, "fetched_at": fetched_at.isoformat()}
        state.save()
        time.sleep(1)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--window-days", type=int, default=14)
    parser.add_argument("--settle-hours", type=float, default=6.0, help="a day counts as complete once fetched this long after it ended")
    parser.add_argument("--skip-hydrovu", action="store_true")
    parser.add_argument("--skip-licor", action="store_true")
    args = parser.parse_args()

    cm.load_env_file(cm.credentials_file())
    state = FetchState(cm.STATE_DIR / "fetch_state.json")
    now = datetime.now(timezone.utc)
    settle = timedelta(hours=args.settle_hours)
    failures = 0
    if not args.skip_hydrovu:
        counts = fetch_hydrovu(state, now, args.window_days, settle)
        log(f"HydroVu: {counts}")
        failures += counts["error"]
    if not args.skip_licor:
        counts = fetch_licor(state, now, args.window_days, settle)
        log(f"LI-COR: {counts}")
        failures += counts["error"]
    state.save()
    if failures:
        # Failed days stay marked for re-fetch on the next run.
        log(f"{failures} fetch requests failed; they will be retried for {args.window_days} days")


if __name__ == "__main__":
    main()
