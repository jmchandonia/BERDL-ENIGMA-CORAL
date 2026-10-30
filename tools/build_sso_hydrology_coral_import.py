#!/usr/bin/env python3
"""Build the CORAL import package for SSO hydrology: manual depth to water (2024) and the 2026 bromide tracer tests.

* `hazen_manual_dtw_sso_2024`: DTW_ManualMeasurements_SSO.xlsx, 37 ports x 6 survey dates
  (2024-01-31 to 2024-02-28), depth to water below ground surface in feet.
* `hazen_manual_dtw_sso_pump_test_2024`: Manual DTW BGS.xlsx, 790 timed readings during the
  March 2024 pump tests.
* `hazen_temphion_SSO-<well>_<zone>_<start>_<end>`: one brick per Seametrics TempHion probe log
  (temperature, bromide ion-selective electrode, and redox on the probes that carry one) for the
  three 2026 KBr tracer tests (U2-SZ1 2026-02-18, M4-SZ1 2026-03-10, M5-VSZ 2026-04-10).

The raw April 2024 pump-test TROLL logs are NOT loaded: their readme says not to use them raw
(pressure corrections pending) and the probes were out of the water while wells were pumped.

Run with the BERIL venv python (openpyxl):
    python tools/build_sso_hydrology_coral_import.py
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_sso_batch_ab_coral_import as ab  # noqa: E402
from build_sso_batch_ab_coral_import import T, NAMES, brick, comment, ctx, float_var, oterm_value, sval, typed, write_process  # noqa: E402

REPO = ab.REPO
TEAM = ab.DRIVE
MYDRIVE = Path("/mnt/net/dipa.jmcnet/data/backup/google-drive/my_drive/DataManagement_ENIGMA/ENIGMA Data")
RELEASE = "20261020"
OUT = REPO / f"coral_import/sso_hydrology_{RELEASE}"
EXPORT = REPO / "sync-coral-to-berdl/exports/sync-20261020-124617/coral_export/static_tsv"
STAGED = Path("/tmp/claude-1000/-scratch-jmc-BERDL-ENIGMA-CORAL/e08931f7-7c7d-4424-a1ff-a5f1bad88ee0/scratchpad/stagedval")
DTW_2024 = TEAM / "2024_SSO/DTW_ManualMeasurements_SSO.xlsx"
DTW_PUMP = TEAM / "2024_SSO_Pump Test/Hazen_Field Data/Manual DTW BGS.xlsx"
TRACER_DIRS = [  # (test number, injection port, injection date, source directory)
    (1, "U2-SZ1", "2026-02-18", TEAM / "2026_SSO_Tracer Tests/U2-SZ1 Injection 20260218"),
    (2, "M4-SZ1", "2026-03-10", TEAM / "2026_SSO_Tracer Tests/M4-SZ1 Injection 20260310"),
    (3, "M5-VSZ", "2026-04-10", MYDRIVE / "2026_SSO_Tracer Tests/M5-VSZ Injection 20260410"),
]
CAMPAIGN = "Subsurface Observatory <ENIGMA:0000166>"
DST_2026 = dt.datetime(2026, 3, 8, 2, 0)

T.update({
    "physical measurement": "DA:0000002", "datetime": "ME:0000180", "redox potential": "ME:0000125",
    "bromide": "CHEBI:15858", "ppm": "UO:0000169", "millivolt": "UO:0000247", "foot": "ME:0000310",
    "top": "ME:0000311", "bottom": "ME:0000312", "Katie Fitzgerald Walker": "ENIGMA:0000135",
})
WELLS = ["U1", "U2", "U3", "M4", "M5", "M6", "L7", "L8", "L9"]
ZONES = ["VZ", "VSZ", "SZ1", "SZ2", "SZ3"]
SCREEN_MID_FT = {"VZ": 7.5, "VSZ": 11.5, "SZ1": 17.0, "SZ2": 23.0, "SZ3": 31.0}  # SSO Cheat Sheet, screen depth BGS
PORT_RE = re.compile(r"^(U[123]|M[456]|L[789])-(VZ|VSZ|SZ[123])$")


def rel(p: Path) -> str:
    if str(p).startswith(str(MYDRIVE)):
        return f"ENIGMA team Google Drive {p.relative_to(MYDRIVE)} (copied to the team drive 2026-10-09)"
    return f"ENIGMA team Google Drive {p.relative_to(TEAM)}"


def stage_validator() -> None:
    ab.ONTOLOGIES = STAGED / "names"
    for d in ("names", "ont"):  # the live ontology now includes ME:0000513-0000515
        (STAGED / d / "context_measurement_ontology.obo").write_bytes(Path("/home/coral/prod/data_import/ontologies/context_measurement_ontology.obo").read_bytes())
    cp = (STAGED / "classpath.txt").read_text().strip()

    def run(json_path):
        proc = subprocess.run(["java", "-Xmx8g", "-cp", cp, "gov.lbl.enigma.app.CheckGenericStaged", str(json_path)], capture_output=True, text=True)
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0 and "Generic is OK!" in out, out
    ab.run_checkgeneric = run


def port_key(port: str):
    w, z = port.split("-")
    return (WELLS.index(w), ZONES.index(z))


def depth_bgs_ctx():
    return [ctx("top", sval("ground surface")), ctx("bottom", sval("water surface"))]


def port_dim(ports: list[str], extra=None) -> dict:
    locs = [f"SSO-{p.split('-')[0]}" for p in ports]
    return {"data_type": ab.term("environmental sample location"), "size": len(ports), "typed_values": [
        {"value_type": ab.term("environmental sample location ID"), "values": {"scalar_type": "object_ref", "object_refs": locs, "string_values": locs}},
        typed("location", "string", ports, None, []),
        typed("depth", "float", [SCREEN_MID_FT[p.split("-")[1]] for p in ports], "foot", [ctx("top", sval("ground surface")), ctx("bottom", sval("screen midpoint"))]),
    ] + (extra or [])}


# ----------------------------------------------------------------------------
# Manual depth to water
# ----------------------------------------------------------------------------

def build_dtw_2024():
    wb = openpyxl.load_workbook(DTW_2024, data_only=True)
    bgs = list(wb["DTW ft BGS"].iter_rows(values_only=True))
    btoc = list(wb["DTW ft BTOC"].iter_rows(values_only=True))
    dates = [d for d in bgs[0][1:] if d]
    if [int(d) for d in btoc[0][2:2 + len(dates)]] != dates:
        raise ValueError("BGS and BTOC sheets list different dates")
    rows = {r[0]: r[1:1 + len(dates)] for r in bgs[1:] if r[0] and PORT_RE.match(str(r[0]))}
    stick = {r[0]: r for r in btoc[1:] if r[0] and PORT_RE.match(str(r[0]))}
    ports = sorted(rows, key=port_key)
    if len(ports) != 37 or set(stick) != set(ports):
        raise ValueError(f"unexpected ports {len(ports)}")
    values, nd = [], []
    checked = 0
    for p in ports:
        for j, d in enumerate(dates):
            v = rows[p][j]
            t = stick[p][2 + j]
            if v == "ND" or t == "ND":
                if not (v in ("ND", None) and t in ("ND", None)):
                    raise ValueError(f"{p} {d}: ND in one sheet only")
                values.append(None); nd.append(f"{p} {d}")
            elif v is None:
                values.append(None)
            else:
                if abs(float(t) - float(stick[p][1]) - float(v)) > 0.005:
                    raise ValueError(f"{p} {d}: BGS {v} != BTOC {t} - stick-up {stick[p][1]}")
                checked += 1
                values.append(round(float(v), 3))
    date_dim = {"data_type": ab.term("time series"), "size": len(dates), "typed_values": [
        typed("date", "string", [f"{str(d)[:4]}-{str(d)[4:6]}-{str(d)[6:]}" for d in dates], None, [])]}
    variables = [float_var("depth", "foot", depth_bgs_ctx(), values)]
    array_context = [
        ctx("personnel", oterm_value("Hazen Lab")),
        ctx("ENIGMA campaign", oterm_value("Subsurface Observatory")),
        ctx("method", sval("Manual depth to water measured with a water-level tape from the top of casing of each port and converted to below ground surface by subtracting the port's casing stick-up")),
        comment(f"Variable: depth to water below ground surface (feet), from sheet 'DTW ft BGS'; the sheet 'DTW ft BTOC' holds the measured depth below top of casing and the stick-ups, and BTOC minus stick-up equals the BGS value in all {checked} cells. "
                "The port dimension also gives each port's screen midpoint below ground surface (VZ 6-9 ft, VSZ 10-13 ft, SZ1 15-19 ft, SZ2 21-25 ft, SZ3 27-35 ft; SSO Cheat Sheet)"),
        comment(f"Null where the port was not measured, and for 'ND' (no water detected): {', '.join(nd)}"),
        comment(f"Source: {rel(DTW_2024)}"),
    ]
    obj = brick("hazen_manual_dtw_sso_2024", "Hazen Lab manual depth to water at the 37 SSO ports, six surveys from 2024-01-31 to 2024-02-28",
                "physical measurement", array_context, [port_dim(ports), date_dim], variables)
    obj["array_context"][0]["value"] = oterm_value("environmental measurement")
    return obj, sorted({f"SSO-{p.split('-')[0]}" for p in ports}, key=lambda l: WELLS.index(l[4:]))


def build_dtw_pump():
    ws = openpyxl.load_workbook(DTW_PUMP, data_only=True)["Manual DTW BGS"]
    rows = list(ws.iter_rows(values_only=True))
    if [str(x) for x in rows[0][:3]] != ["DATE TIME", "[1]Manual DTW BTOC'!A1", "DTW BGS"]:
        raise ValueError(f"pump DTW header changed {rows[0][:3]}")
    recs = []
    for r in rows[1:]:
        if r[0] is None and r[1] is None and r[2] is None:
            continue
        if not isinstance(r[0], dt.datetime) or not PORT_RE.match(str(r[1]).strip()) or not isinstance(r[2], (int, float)):
            raise ValueError(f"unexpected pump DTW row {r[:3]}")
        recs.append((str(r[1]).strip(), r[0], round(float(r[2]), 3)))
    schedule = []
    for r in rows[1:10]:
        if r[4]:
            schedule.append(f"{r[4]} {r[5]:%Y-%m-%d %H:%M}-{r[6]:%H:%M}" + (f" ({r[8]})" if r[8] else ""))
    keys = Counter((p, t) for p, t, _ in recs)
    dups = [k for k, n in keys.items() if n > 1]
    if len(dups) != 3:
        raise ValueError(f"unexpected repeated pump DTW readings {dups}")
    recs.sort(key=lambda x: (port_key(x[0]), x[1]))
    ports = [p for p, _, _ in recs]
    dim = port_dim(ports, [typed("datetime", "string", [f"{t:%Y-%m-%dT%H:%M:%S}-04:00" for _, t, _ in recs], None, [])])
    variables = [float_var("depth", "foot", depth_bgs_ctx(), [v for _, _, v in recs])]
    array_context = [
        ctx("personnel", oterm_value("Hazen Lab")),
        ctx("ENIGMA campaign", oterm_value("Subsurface Observatory")),
        ctx("method", sval("Manual depth to water during the March 2024 SSO pump tests, measured with a water-level tape from the top of casing and given below ground surface in the source sheet"),),
        comment("Variable: depth to water below ground surface (feet). One row per reading: the well Location, the port, the port's screen midpoint below ground surface (SSO Cheat Sheet) and the local date and time (EDT, UTC-4)"),
        comment("Pumped port and pumping period (local time) from the source sheet: " + "; ".join(schedule)),
        comment("Repeated readings in the same minute are kept as separate rows: " + "; ".join(f"{p} {t:%Y-%m-%d %H:%M} ({', '.join(f'{v:g}' for q, u, v in recs if q == p and u == t)} ft)" for p, t in sorted(dups, key=lambda k: (k[1], k[0])))),
        comment(f"Source: {rel(DTW_PUMP)}, sheet Manual DTW BGS (columns DATE TIME, well-zone, DTW BGS); the measured depths below top of casing are in a linked workbook that is not on the Drive"),
    ]
    obj = brick("hazen_manual_dtw_sso_pump_test_2024", f"Hazen Lab manual depth to water during the March 2024 SSO pump tests ({len(recs)} readings)",
                "physical measurement", array_context, [dim], variables)
    obj["array_context"][0]["value"] = oterm_value("environmental measurement")
    return obj, sorted({f"SSO-{p.split('-')[0]}" for p in ports}, key=lambda l: WELLS.index(l[4:])), recs


# ----------------------------------------------------------------------------
# Tracer probe logs
# ----------------------------------------------------------------------------

def read_probe(path: Path):
    meta, hdr, rows, cal = {}, None, [], {}
    section = None
    with path.open(encoding="utf-8-sig", errors="strict") as h:
        for rec in csv.reader(h):
            rec = [x.strip() for x in rec]
            while rec and rec[-1] == "":
                rec.pop()
            if not rec:
                continue
            if rec[0] in ("Advanced Calibration Data", "Field Calibration Data"):
                section = rec[0]
            if section == "Field Calibration Data" and len(rec) > 3 and rec[0] == "" and rec[1] == "" and rec[2]:
                cal.setdefault("field", []).append(rec[2])
            if rec[0] in ("Sensor SN", "Sensor Type", "Sensor Name", "File Name", "# Records"):
                meta[rec[0]] = rec[1]
            if rec[0] == "Statistical Data":
                hdr = rec[2:]
                section = "data"
            if section == "data" and rec[0].isdigit() and len(rec) >= 2 + len(hdr or []):
                rows.append(rec)
    if hdr is None or hdr[:2] != ["Temperature-1 (°C)", "ISE-Bromide-3 (ppm)"] or hdr[2:] not in ([], ["Redox-4 (mV)"]):
        raise ValueError(f"{path.name}: unexpected columns {hdr}")
    return meta, hdr, rows, cal


def probe_times(test: int, path: Path, rows) -> tuple[list[str], str]:
    """Local timestamps with offset; returns the strings and a note on any repair."""
    note = ""
    if "/" in rows[0][1]:  # resaved through Excel: minute resolution; rebuild from the 10 s record cadence
        recs = [int(r[0]) for r in rows]
        mins = [dt.datetime.strptime(r[1], "%m/%d/%y %H:%M") for r in rows]
        good = []
        for s in range(60):
            t0 = mins[0] + dt.timedelta(seconds=s)
            if all((t0 + dt.timedelta(seconds=10 * (n - recs[0]))).replace(second=0) == m for n, m in zip(recs, mins)):
                good.append(s)
        if not good or good != list(range(good[0], good[0] + len(good))):
            raise ValueError(f"{path.name}: cannot rebuild seconds {good}")
        s = (good[0] + good[-1]) // 2
        t0 = mins[0] + dt.timedelta(seconds=s)
        times = [t0 + dt.timedelta(seconds=10 * (n - recs[0])) for n in recs]
        missing = recs[-1] - recs[0] + 1 - len(recs)
        note = (f"The source file was resaved through a spreadsheet program, which cut its timestamps to the minute; the seconds were rebuilt from the record numbers and the probe's fixed 10 s interval "
                f"(every one of the {len(rows)} rows agrees with first-record seconds {good[0]} to {good[-1]}; {s} used, so times are within 5 s). {missing} record numbers are missing from the file, all during the injection on 2026-04-10")
    else:
        times = [dt.datetime.strptime(r[1], "%d-%b-%Y %H:%M:%S") for r in rows]
    if test == 1:
        # The export prints the hour after 2026-03-08 02:00 one hour late and then returns to the
        # probe clock, so 03:00-03:59 appears twice. The probe clock itself never changed.
        jumps = [i for i in range(1, len(times)) if (times[i] - times[i - 1]).total_seconds() in (3610, -3590)]
        if len(jumps) != 2 or times[jumps[0] - 1] >= DST_2026 or times[jumps[0]] < DST_2026 + dt.timedelta(hours=1):
            raise ValueError(f"{path.name}: unexpected clock jumps {jumps}")
        a, b = jumps
        times = times[:a] + [t - dt.timedelta(hours=1) for t in times[a:b]] + times[b:]
        note = (f"The export prints the {b - a} records after 2026-03-08 02:00 one hour late (the daylight-saving change) and then resumes the probe clock, so 03:00 to 03:59 appeared twice; "
                "those records are moved back one hour, restoring the probe's continuous 10 s series in standard time")
        offset = "-05:00"
    else:
        offset = "-04:00"
    steps = Counter(int((b - a).total_seconds()) for a, b in zip(times, times[1:]))
    if any(s <= 0 for s in steps):
        raise ValueError(f"{path.name}: non-increasing times after repair {steps}")
    return [f"{t:%Y-%m-%dT%H:%M:%S}{offset}" for t in times], note


def build_probe(test: int, inj_port: str, inj_date: str, path: Path):
    meta, hdr, rows, cal = read_probe(path)
    file_port = path.name.split("_")[0]
    port = meta["Sensor Name"]
    if not PORT_RE.match(port):
        raise ValueError(f"{path.name}: sensor name {port}")
    if port != file_port:
        return None, f"{path.name}: the file holds the {port} probe log (sensor {meta['Sensor SN']}), not {file_port}; skipped"
    if int(meta["# Records"]) < len(rows) or len(rows) < 1000:
        raise ValueError(f"{path.name}: {len(rows)} rows for {meta['# Records']} records")
    times, note = probe_times(test, path, rows)
    well, zone = port.split("-")
    col = lambda k: [float(r[k]) if r[k] != "" else None for r in rows]
    variables = [
        float_var("temperature", "degree Celsius", [], col(2)),
        float_var("concentration", "ppm", [ctx("molecule from list", oterm_value("bromide"))], col(3)),
    ]
    if len(hdr) == 3:
        variables.append(float_var("redox potential", "millivolt", [], col(4)))
    start, end = times[0][:10].replace("-", ""), times[-1][:10].replace("-", "")
    field_cal = cal.get("field", [])
    array_context = [
        ctx("instrument", sval(f"Seametrics TempHion probe, serial {meta['Sensor SN'].lstrip('0')}")),
        ctx("environmental sample location ID", {"scalar_type": "object_ref", "object_ref": f"SSO-{well}", "string_value": f"SSO-{well}"}),
        ctx("data variables type", oterm_value("environmental measurement")),
        ctx("location", sval(port)),
        ctx("personnel", oterm_value("Katie Fitzgerald Walker")),
        ctx("ENIGMA campaign", oterm_value("Subsurface Observatory")),
        ctx("method", sval(f"Bromide tracer test {test}: 10 L of 9,000 ppm potassium bromide injected into {inj_port} on {inj_date}; probes in the monitored ports logged every 10 s. "
                           "Bromide by ion-selective electrode (ppm, two-point field calibration at 500 and 5,000 ppm" + (f" on {field_cal[0].split()[0]}" if field_cal else "") + ")"
                           + ("; redox by the probe's ORP electrode (mV)" if len(hdr) == 3 else ""))),
        comment(f"Times are the probe clock in local {'standard (EST, UTC-5)' if test == 1 else 'daylight (EDT, UTC-4)'} time: the probes were started in the field with the field computer's clock"
                + (" before the 2026-03-08 daylight-saving change" if test == 1 else " after the 2026-03-08 daylight-saving change") + "; the in-well bromide rise during test 3 matches the field log's 09:40 EDT injection to within about 20 minutes"),
    ]
    if note:
        array_context.append(comment(note))
    array_context.append(comment(f"Source: {rel(path)} (sensor name {port}, test file name '{meta['File Name']}')"))
    obj = {"name": f"hazen_temphion_SSO-{well}_{zone}_{start}_{end}.hndarray",
           "description": f"Hazen Lab Seametrics TempHion bromide probe data for SSO-{well} {zone}, tracer test {test}, from {times[0][:10]} to {times[-1][:10]}",
           "data_type": ab.term("physical measurement"), "array_context": array_context, "n_dimensions": 1,
           "dim_context": [{"data_type": ab.term("time series"), "size": len(times), "typed_values": [typed("datetime", "string", times, None, [])]}],
           "typed_values": variables}
    return obj, None


# ----------------------------------------------------------------------------

def main() -> None:
    stage_validator()
    ab.load_ontology_names()
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    ab.OUT = OUT
    ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT = (OUT / d for d in ("json", "static", "process", "check", "reports"))
    for d in (ab.JSON_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT):
        d.mkdir(parents=True)
    with (EXPORT / "Location.tsv").open() as h:
        locations = {r["name"] for r in csv.DictReader(h, delimiter="\t")}
    summary = {"release": RELEASE, "bricks": [], "skipped": []}
    rows = []

    def record(obj, locs, person, d0, d1):
        missing = [l for l in locs if l not in locations]
        if missing:
            raise ValueError(f"{obj['name']}: Locations not in CORAL {missing}")
        path = ab.write_brick(obj)
        summary["bricks"].append({"name": obj["name"], "json": path.name, "shape": [d["size"] for d in obj["dim_context"]], "variables": len(obj["typed_values"])})
        rows.append({"process": "Assay Environment <PROCESS:0000004>", "person": person, "campaign": CAMPAIGN, "protocol": "null",
                     "date_start": d0, "date_end": d1, "input_objects": ", ".join(f"Location: {l}" for l in locs), "output_objects": f"Generic: {obj['name']}"})

    obj, locs = build_dtw_2024()
    record(obj, locs, "Hazen Lab <ENIGMA:0000066>", "2024-01-31", "2024-02-28")
    obj, locs, recs = build_dtw_pump()
    record(obj, locs, "Hazen Lab <ENIGMA:0000066>", f"{min(t for _, t, _ in recs):%Y-%m-%d}", f"{max(t for _, t, _ in recs):%Y-%m-%d}")
    for test, inj_port, inj_date, d in TRACER_DIRS:
        for path in sorted(d.glob("*.csv")):
            if "PSI" in path.name:
                summary["skipped"].append(f"{path.name}: pressure log with time of day only (no dates); not loaded")
                continue
            obj, why = build_probe(test, inj_port, inj_date, path)
            if obj is None:
                summary["skipped"].append(why)
                continue
            times = obj["dim_context"][0]["typed_values"][0]["values"]["string_values"]
            record(obj, [obj["array_context"][1]["value"]["object_ref"]], f"Katie Fitzgerald Walker <{T['Katie Fitzgerald Walker']}>", times[0][:10], times[-1][:10])
    process_path = ab.PROCESS_OUT / f"process_assay_environment_sso_hydrology_{RELEASE}.tsv"
    write_process(process_path, rows)
    files = [f"json/{b['json']}" for b in summary["bricks"]] + [f"process/{process_path.name}"]
    (OUT / "files_to_import.txt").write_text("\n".join(files) + "\n")
    (OUT / "import_to_coral.py").write_text("\n".join(
        ["# Paste into the CORAL import notebook after uploading every file in files_to_import.txt", "", "# Cell 1: the bricks."]
        + [f"toolx.upload_brick('{b['json']}')" for b in summary["bricks"]]
        + ["", "# Cell 2: the assay processes.", f"toolx.upload_process('Assay Environment', '{process_path.name}')", ""]))
    (ab.REPORT_OUT / "build_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
