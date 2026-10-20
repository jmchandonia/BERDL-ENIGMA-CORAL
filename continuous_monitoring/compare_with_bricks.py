#!/usr/bin/env python3
"""Compare staged continuous-monitoring tables with the active API-derived CORAL bricks.

For every active (not withdrawn or superseded) brick in enigma.coral whose
provenance is hydrovu api, licor api or licor export, find the locally
generated brick TSV, map it to its location/zone table, and compare
timestamps and values with the staged TSV.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import cm_common as cm

REPO = Path(__file__).resolve().parents[1]
GENERATED = Path("/scratch/jmc/field_automated_measurements")
NAME = re.compile(r"^hazen_(aquatroll600|leveltroll500|hobo)_([A-Za-z0-9-]+?)(?:_(SZ1|SZ2|SZ3|VSZ|VZ))?_\d{8}_\d{8}(?:_v\d+)?$")
STREAM_SITES = {"SSO-L8", "SSO-L9", "SSO-M6", "SSO-U3"}
EASTERN = ZoneInfo("America/New_York")
FAMILY = {"aquatroll600": "aquatroll600", "leveltroll500": "leveltroll500", "hobo": "weather"}


def active_api_bricks() -> list[tuple[str, str, str]]:
    out = []
    for line in (REPO / "schema/ddt_ndarray_table.md").read_text().splitlines():
        if not line.startswith("| Brick"):
            continue
        f = [x.strip() for x in line.split("|")[1:-1]]
        brick, name, metadata, withdrawn, superseded = f[0], f[1], f[3], f[13], f[14]
        if withdrawn != "NULL" or superseded != "NULL" or not name.startswith("hazen_"):
            continue
        m = re.search(r"Provenance: ([a-z_ ]+)", metadata)
        if m and m.group(1).strip() in {"hydrovu api", "licor api", "licor_export"}:
            out.append((brick, name.removesuffix(".hndarray"), m.group(1).strip()))
    return out


def read_tsv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="") as handle:
        rows = list(csv.reader(handle, delimiter="\t"))
    return rows[0], rows[1:]


def close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-6)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--staging", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--shift-leveltroll-hours", type=float, default=4.0,
        help="add this to HydroVu SSO Level TROLL brick timestamps before matching (the bricks were not corrected)",
    )
    args = parser.parse_args()

    column_map = cm.load_column_map()["measurements"]
    tsv_by_name = {p.stem: p for p in sorted(GENERATED.glob("generated_continuous_monitoring*/tsv/*.tsv"))}
    staged_cache: dict[str, dict[str, dict[str, str]]] = {}
    results = []
    for brick, name, provenance in active_api_bricks():
        m = NAME.match(name)
        tsv = tsv_by_name.get(name)
        if not m or tsv is None:
            results.append({"brick": brick, "name": name, "status": "brick TSV not found locally"})
            continue
        table = cm.table_name(FAMILY[m.group(1)], m.group(2), m.group(3) or "")
        staged_path = args.staging / f"{table}.tsv"
        if not staged_path.exists():
            results.append({"brick": brick, "name": name, "table": table, "status": "table not staged"})
            continue
        if table not in staged_cache:
            header, rows = read_tsv(staged_path)
            staged_cache[table] = {row[0]: dict(zip(header, row)) for row in rows}
        staged = staged_cache[table]
        header, rows = read_tsv(tsv)
        shift = args.shift_leveltroll_hours if name.startswith("hazen_leveltroll500_SSO") and provenance == "hydrovu api" else 0
        if shift:
            rows = [[(datetime.fromisoformat(r[0]).astimezone(timezone.utc) + timedelta(hours=shift)).astimezone(EASTERN).isoformat(timespec="milliseconds"), *r[1:]] for r in rows]
        counts = defaultdict(int)
        mismatch_examples = []
        missing_columns = set()
        for row in rows:
            ts = row[0]
            counts["brick_rows"] += 1
            srow = staged.get(ts)
            if srow is None:
                counts["rows_missing_in_staged"] += 1
                if len(mismatch_examples) < 5:
                    mismatch_examples.append({"timestamp": ts, "issue": "row missing"})
                continue
            counts["rows_matched"] += 1
            for label, value in zip(header[1:], row[1:]):
                if value == "":
                    continue
                spec = column_map.get(label)
                if spec is None or spec["column"] not in srow:
                    missing_columns.add(label)
                    continue
                svalue = srow[spec["column"]]
                counts["values_compared"] += 1
                if svalue == "" or not close(float(value), float(svalue)):
                    counts["values_different"] += 1
                    if len(mismatch_examples) < 5:
                        mismatch_examples.append({"timestamp": ts, "column": spec["column"], "brick": value, "staged": svalue})
        status = "match" if counts["rows_missing_in_staged"] == 0 and counts["values_different"] == 0 and not missing_columns else "differs"
        results.append(
            {
                "brick": brick,
                "name": name,
                "provenance": provenance,
                "table": table,
                "status": status,
                "stream_site": m.group(2) in STREAM_SITES,
                "brick_shifted_hours": shift,
                **counts,
                "columns_missing_in_staged": sorted(missing_columns),
                "examples": mismatch_examples,
            }
        )
    args.out.write_text(json.dumps(results, indent=2) + "\n")
    summary = defaultdict(int)
    for r in results:
        summary[r["status"]] += 1
    print(dict(summary))
    for r in results:
        if r["status"] != "match":
            print(json.dumps({k: r.get(k) for k in ("brick", "name", "status", "brick_rows", "rows_missing_in_staged", "values_compared", "values_different", "columns_missing_in_staged")}))


if __name__ == "__main__":
    main()
