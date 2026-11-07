#!/usr/bin/env python3
"""Build the CORAL import package for the 2024 SSO colloidal-borescope flow characterization (Hazen Lab).

Source: team Drive `2024_SSO_Borescope Characterization/Borescope Measurements/`: 36 borescope logs
(`YYYYMMDD_<well>-<zone>-<depth ft BTOC>[_Pref].log`, one line per tracked colloid: local time, azimuth, speed
in um/s, particles in frame), the 36 "Well Analysis Summary" PDFs written by the borescope software, and the
campaign metadata workbook (39 attempted measurements; three saw no colloids and have no log).

* `hazen_colloidal_borescope_flow_vectors_sso_2024`: one row per attempted measurement (39): the software's
  flow vector (azimuth, velocity) and its direction/speed statistics, data points, with depth, casing height,
  weather, preferential-flow call and samplers from the workbook. Statistics are taken from the PDFs for every
  measurement so that all share one definition: the workbook copied the *average* direction/speed instead of the
  flow vector for the nine 2024-02-26 measurements, and marks 20240205_M4-SZ2-24 "no colloids seen" although it
  has a 1,161-point log and summary.
* `hazen_colloidal_borescope_particle_tracks_sso_2024`: every log line (~47,000) with its measurement.

Run with the BERIL venv python (openpyxl); needs `pdftotext` on PATH:
    python tools/build_sso_borescope_coral_import.py
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_sso_batch_ab_coral_import as ab  # noqa: E402
from build_sso_batch_ab_coral_import import T, brick, comment, ctx, float_var, oterm_value, sval, typed, write_process  # noqa: E402

REPO = ab.REPO
TEAM = ab.DRIVE
RELEASE = "20261107"
TAG = f"sso_borescope_{RELEASE}"
OUT = REPO / f"coral_import/{TAG}"
EXPORT = REPO / "sync-coral-to-berdl/exports/sync-20261106-145216/coral_export/static_tsv"
STAGED = Path("/tmp/claude-1000/-scratch-jmc-BERDL-ENIGMA-CORAL/e08931f7-7c7d-4424-a1ff-a5f1bad88ee0/scratchpad/stagedval")
SRC = TEAM / "2024_SSO_Borescope Characterization/Borescope Measurements"
META = SRC / "2024_SSO_Borescope Characterization_Metadata.xlsx"
FTP = TEAM / "2024_SSO_Borescope Characterization/FTP_SSO_2024_Borescope and Monitoring Install.docx"
CAMPAIGN = "Subsurface Observatory <ENIGMA:0000166>"
PERSON = "Hazen Lab <ENIGMA:0000066>"
PROTO = "hazen-colloidal-borescope-sso-2024"
OFFSET = "-05:00"  # EST: all measurements are January-February 2024
SAMPLERS = {"KW": "Katie Fitzgerald Walker", "DJ": "Dominique Joyner", "SH": "Summer Hatmaker"}  # initials used in the workbook; names from the FTP
T.update({"physical measurement": "DA:0000002", "datetime": "ME:0000180", "foot": "ME:0000310", "top": "ME:0000311", "bottom": "ME:0000312",
          "elevation": "ME:0000220", "velocity": "ME:0000519", "azimuth": "ME:0000520", "micrometer per second": "ME:0000521",
          "degree": "UO:0000185", "median": "ME:0000153", "minimum": "ME:0000151", "maximum": "ME:0000152",
          "Subsurface Observatory": "ENIGMA:0000166"})


def rel(p: Path) -> str:
    return f"ENIGMA team Google Drive {p.relative_to(TEAM)}"


def stage_validator() -> None:
    ab.ONTOLOGIES = STAGED / "names"
    cp = (STAGED / "classpath.txt").read_text().strip()

    def run(json_path):
        proc = subprocess.run(["java", "-Xmx8g", "-cp", cp, "gov.lbl.enigma.app.CheckGenericStaged", str(json_path)], capture_output=True, text=True)
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0 and "Generic is OK!" in out, out
    ab.run_checkgeneric = run


def read_workbook() -> list[dict]:
    ws = openpyxl.load_workbook(META, read_only=True, data_only=True)["Sheet1"]
    rows = [tuple(r) + (None,) * 4 for r in ws.iter_rows(values_only=True)]
    hdr = rows[10]
    if [str(c).split("\n")[0].strip() for c in hdr[1:12]] != ["Sample ID_", "Sampler(s)", "Well-Zone", "Casing Height", "DTWBTOC", "DTWBGS",
                                                             "sampler observation of weather", "Preferential Flow?", "Vector", "Speed (um/sec)", "Data Points"]:
        raise ValueError(f"workbook header changed: {hdr[1:12]}")
    recs = []
    for r in rows[13:]:
        if not r[1] or not re.match(r"\d{8}_[A-Z]\d-SZ\d-\d+$", str(r[1]).strip()):
            continue
        sid = str(r[1]).strip()
        date, port, depth = sid[:8], sid[9:].rsplit("-", 1)[0], int(sid.rsplit("-", 1)[1])
        nodata = r[9] == "No data"
        recs.append({"id": sid, "date": f"{date[:4]}-{date[4:6]}-{date[6:]}", "port": port, "well": port.split("-")[0], "depth_btoc": float(r[5]),
                     "depth_bgs": float(r[6]), "casing": float(r[4]), "weather": str(r[7]).strip(), "samplers": str(r[2]).strip(),
                     "pref": None if r[8] in ("No data", None) else str(r[8]).strip().lower(), "wb_vector": None if nodata else float(r[9]),
                     "wb_speed": None if nodata else float(r[10]), "wb_points": None if nodata else int(float(r[11])), "wb_note": str(r[11]) if nodata else None,
                     "depth_check": depth})
        if abs(recs[-1]["depth_btoc"] - depth) > 0.01 or abs(recs[-1]["casing"] + recs[-1]["depth_bgs"] - recs[-1]["depth_btoc"]) > 0.01:
            raise ValueError(f"{sid}: depth/casing inconsistency {recs[-1]}")
    if len(recs) != 39:
        raise ValueError(f"expected 39 workbook rows, got {len(recs)}")
    return recs


def num(s):
    return float(s.replace(",", ""))


def read_summary(pdf: Path) -> dict:
    t = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    g = lambda pat, flags=0: re.search(pat, t, flags)
    out = {"points": int(g(r"Data Points:\s*(\d+)").group(1)), "time": g(r"Time:\s*([\d:]+) - ([\d:]+)").groups(),
           "well": g(r"Well Name:\s*(\S+)").group(1).replace("_", "-"), "depth": g(r"Depth:\s*(\d+)\s*ft\s*BTOC", re.I).group(1)}
    d = g(r"Avg Dir.*?\n\s*([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)", re.S)
    s = g(r"um/sec:\s*([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)")
    out["dir_stats"] = [num(x) for x in d.groups()]   # avg, median, min, max, std
    out["speed_stats"] = [num(x) for x in s.groups()]
    fv = g(r"Flow Direction:\s*\n\s*Direction:\s*([\d.,]+)")
    fs = g(r"Flow Speed\s*\n\s*um/sec:\s*([\d.,]+)")
    out["flow_dir"] = num(fv.group(1)) if fv else None
    out["flow_speed"] = num(fs.group(1)) if fs else None
    if (fv is None) != (fs is None):
        raise ValueError(f"{pdf.name}: half a flow vector")
    return out


def read_log(path: Path) -> list[tuple]:
    rows = []
    for line in path.read_text(errors="replace").splitlines():
        p = [x.strip().strip('"') for x in line.split(",")]
        if len(p) < 4 or not p[0]:
            continue
        t = dt.datetime.strptime(p[0], "%m-%d-%Y %H:%M:%S")
        rows.append((t, float(p[1]), float(p[2]), int(p[3])))
    return rows


def build(recs: list[dict], locations: set[str]):
    logs = {re.sub(r"_Pref$", "", p.stem): p for p in SRC.glob("*.log")}
    pdfs = {re.sub(r"_Pref$", "", p.stem): p for p in SRC.glob("*.pdf")}
    if len(logs) != 36 or set(logs) != set(pdfs):
        raise ValueError("expected 36 logs with matching PDFs")
    missing_logs = [r["id"] for r in recs if r["id"] not in logs]
    if len(missing_logs) != 3 or any(r["wb_note"] is None for r in recs if r["id"] in missing_logs):
        raise ValueError(f"logs missing for {missing_logs}")
    notes = []
    count_notes = []
    tracks = []
    for r in recs:
        r["location"] = f"SSO-{r['well']}"
        if r["location"] not in locations:
            raise ValueError(f"no Location {r['location']}")
        r["pref_file"] = logs[r["id"]].stem.endswith("_Pref") if r["id"] in logs else False
        if r["id"] in logs and r["pref_file"] != (r["pref"] == "yes"):
            raise ValueError(f"{r['id']}: _Pref file name vs workbook flag disagree")
        if r["id"] not in logs:
            r.update({"summary": None, "start": None, "end": None, "n_log": 0})
            continue
        s = read_summary(pdfs[r["id"]])
        # PDF "Well Name" is free text (M5_SZ1_19, 20240205_L9-SZ2-27, M5-SZ3 without depth): require well-zone and the Depth line
        if not s["well"].replace("_", "-").split("-", 1)[-1 if s["well"][0].isdigit() else 0].startswith(r["port"]) and r["port"] not in s["well"].replace("_", "-") or int(s["depth"]) != r["depth_check"]:
            raise ValueError(f"{r['id']}: PDF names {s['well']} {s['depth']}")
        rows = read_log(logs[r["id"]])
        if not rows or rows[0][0].strftime("%Y-%m-%d") != r["date"]:
            raise ValueError(f"{r['id']}: log date {rows[0][0]}")
        r.update({"summary": s, "start": rows[0][0], "end": rows[-1][0], "n_log": len(rows)})
        tracks.extend((r, t, a, v, n) for t, a, v, n in rows)
        if r["wb_vector"] is not None and (abs(r["wb_vector"] - (s["flow_dir"] or -1)) > 0.05 or abs(r["wb_speed"] - (s["flow_speed"] or -1)) > 0.05):
            which = "the summary's average direction/speed" if abs(r["wb_vector"] - s["dir_stats"][0]) < 0.05 else "values not in the summary"
            notes.append(f"{r['id']}: workbook vector/speed {r['wb_vector']}/{r['wb_speed']} = {which}; flow vector used here {s['flow_dir']}/{s['flow_speed']}")
        if r["wb_vector"] is None and s["flow_dir"] is not None:
            notes.append(f"{r['id']}: workbook says '{r['wb_note']}' but the log has {len(rows)} readings and the summary a flow vector {s['flow_dir']}/{s['flow_speed']}; the summary values are used")
        if len(rows) != s["points"]:
            count_notes.append(f"{r['id']} log {len(rows)} lines, summary {s['points']} data points")
        if r["wb_points"] is not None and r["wb_points"] != s["points"]:
            raise ValueError(f"{r['id']}: data points {r['wb_points']} vs PDF {s['points']}")
    # ---- brick A: flow vectors --------------------------------------------------------------------------
    n = len(recs)
    def dim_var(key, scalar, vals, unit=None, context=None):
        return typed(key, scalar, vals, unit, context if context is not None else [])
    dim = {"data_type": ab.term("environmental sample location"), "size": n, "typed_values": [
        {"value_type": ab.term("environmental sample location ID"), "values": {"scalar_type": "object_ref", "object_refs": [r["location"] for r in recs], "string_values": [r["location"] for r in recs]}},
        dim_var("location", "string", [r["port"] for r in recs]),
        float_var("depth", "foot", [ctx("top", sval("ground surface")), ctx("bottom", sval("borescope"))], [r["depth_bgs"] for r in recs]),
        dim_var("datetime", "string", [f"{r['start']:%Y-%m-%dT%H:%M:%S}{OFFSET}" if r["start"] else r["date"] for r in recs]),
        float_var("elevation", "foot", [ctx("instrument", sval("casing")), ctx("top", sval("casing top")), ctx("bottom", sval("ground surface"))], [r["casing"] for r in recs]),
        dim_var("comment", "string", [r["weather"] for r in recs], None, [ctx("category", sval("weather"))]),
        dim_var("category", "string", [r["pref"] for r in recs], None, [ctx("category", sval("preferential flow"))]),
        dim_var("comment", "string", [", ".join(SAMPLERS.get(x.strip(), x.strip()) for x in r["samplers"].split(",")) for r in recs], None, [ctx("category", sval("samplers"))]),
        dim_var("comment", "string", [logs[r["id"]].name if r["id"] in logs else None for r in recs], None, [ctx("category", sval("source file"))]),
    ]}
    S = lambda key, idx: [r["summary"][key][idx] if r["summary"] else None for r in recs]
    variables = [
        float_var("azimuth", "degree", [ctx("method", sval("borescope flow vector"))], [r["summary"]["flow_dir"] if r["summary"] else None for r in recs]),
        float_var("velocity", "micrometer per second", [ctx("method", sval("borescope flow vector"))], [r["summary"]["flow_speed"] if r["summary"] else None for r in recs]),
    ]
    for stat, i in (("average", 0), ("median", 1), ("minimum", 2), ("maximum", 3), ("standard deviation", 4)):
        variables.append(float_var(stat, "degree", [ctx("measurement", oterm_value("azimuth"))], S("dir_stats", i)))
    for stat, i in (("average", 0), ("median", 1), ("minimum", 2), ("maximum", 3), ("standard deviation", 4)):
        variables.append(float_var(stat, "micrometer per second", [ctx("measurement", oterm_value("velocity"))], S("speed_stats", i)))
    variables.append(typed("count", "int", [r["summary"]["points"] if r["summary"] else None for r in recs], "count unit", [ctx("category", sval("tracked particles"))]))
    array_context = [
        ctx("ENIGMA campaign", oterm_value("Subsurface Observatory")), ctx("personnel", oterm_value("Hazen Lab")),
        ctx("instrument", sval("Geotech colloidal borescope")),
        comment(f"Source: {rel(SRC)}: the borescope software's 'Well Analysis Summary' PDF of each measurement (flow vector, direction and speed statistics, data "
                "points, start/end time) and the campaign metadata workbook (ports, depths, casing heights, weather, preferential-flow call, samplers). "
                f"Field test plan: {rel(FTP)}"),
        comment("One row per attempted measurement, identified by well (location ID), port (location), borescope depth below ground surface (feet) and "
                "field date: the borescope was stepped 1 ft at a time below the top of casing, so depth BGS = that whole-foot depth minus the port's "
                "casing height above ground, which is recorded here. Start time is local EST (UTC-5). Flow vector azimuth (degrees clockwise from north, direction of travel) and "
                "velocity (um/s) are the software's estimate; they are null for the two measurements the software judged unreliable (M5-SZ1-21 on 02-08, "
                "M5-SZ3-30 on 02-09) and for the three attempts where no colloids were seen (L9-SZ1-18 01-31, L9-SZ2-24 and M4-SZ2-27 02-05), which have no "
                "log. The average, median, minimum, maximum and standard deviation of azimuth and velocity over all tracked particles are the software's "
                "arithmetic statistics; 'tracked particles' is its data-point count. 'preferential flow' is the samplers' call (the _Pref log files)"),
        comment("Workbook discrepancies resolved in favour of the software summaries: " + "; ".join(notes)),
        comment("'tracked particles' is the summary's data-point count; for " + str(len(count_notes)) + " measurements the log file (all of whose lines are in "
                "the particle-tracks brick) has more lines, by 1-4 lines except M5-SZ2-26 on 02-26 where the summary stops at 4096 points: " + "; ".join(count_notes)),
        comment("The individual particle tracks are in hazen_colloidal_borescope_particle_tracks_sso_2024, keyed by the same well, port, depth and date"),
    ]
    brick_a = brick("hazen_colloidal_borescope_flow_vectors_sso_2024",
                    "Hazen Lab colloidal-borescope groundwater flow vectors in SSO wells M4, M5 and L9 (screens SZ1-SZ3, 1-ft steps), 31 January to 26 "
                    "February 2024: flow azimuth and velocity with direction and speed statistics for 39 attempted measurements",
                    "physical measurement", array_context, [dim], variables)
    # ---- brick B: particle tracks ----------------------------------------------------------------------
    tracks.sort(key=lambda x: (x[0]["date"], x[0]["port"], x[0]["depth_bgs"], x[1]))
    dim_b = {"data_type": ab.term("time series"), "size": len(tracks), "typed_values": [
        {"value_type": ab.term("environmental sample location ID"), "values": {"scalar_type": "object_ref", "object_refs": [x[0]["location"] for x in tracks], "string_values": [x[0]["location"] for x in tracks]}},
        dim_var("location", "string", [x[0]["port"] for x in tracks]),
        float_var("depth", "foot", [ctx("top", sval("ground surface")), ctx("bottom", sval("borescope"))], [x[0]["depth_bgs"] for x in tracks]),
        dim_var("datetime", "string", [f"{x[1]:%Y-%m-%dT%H:%M:%S}{OFFSET}" for x in tracks]),
    ]}
    variables_b = [
        float_var("azimuth", "degree", [], [x[2] for x in tracks]),
        float_var("velocity", "micrometer per second", [], [x[3] for x in tracks]),
        typed("count", "int", [x[4] for x in tracks], "count unit", [ctx("category", sval("particles in frame"))]),
    ]
    array_context_b = [
        ctx("ENIGMA campaign", oterm_value("Subsurface Observatory")), ctx("personnel", oterm_value("Hazen Lab")),
        ctx("instrument", sval("Geotech colloidal borescope")),
        comment(f"Source: the 36 borescope log files in {rel(SRC)} (YYYYMMDD_<well>-<zone>-<depth ft BTOC>[_Pref].log): one line per tracked colloid "
                "with the camera clock (local EST, UTC-5), its azimuth (degrees clockwise from north), speed (um/s) and the number of particles in the "
                "frame. Well (location ID), port (location), depth below ground surface and the date of the timestamp identify the measurement; "
                "hazen_colloidal_borescope_flow_vectors_sso_2024 holds its casing height, start time, weather and the software's summary"),
    ]
    brick_b = brick("hazen_colloidal_borescope_particle_tracks_sso_2024",
                    "Hazen Lab colloidal-borescope particle tracks in SSO wells M4, M5 and L9, 31 January to 26 February 2024: azimuth, speed and particles "
                    f"in frame for every tracked colloid ({len(tracks)} readings in 36 measurements)",
                    "physical measurement", array_context_b, [dim_b], variables_b)
    return brick_a, brick_b, notes + count_notes, len(tracks)


def protocol_row(ftp_text: str) -> dict:
    return {"name": PROTO, "link": "", "description":
            "Colloidal-borescope measurement of groundwater flow in the ENIGMA Subsurface Observatory (Field Test Plan 'Identification of Flow Vectors Using "
            "Colloidal Borescope with Full Installation of Aqua TROLL and Level TROLL Telemetry Monitoring Systems at the SSO', Hazen Lab, 2024). A colloidal "
            "borescope (Geotech, Denver, CO) was lowered into the screened intervals of wells M4, M5 and L9 (saturated zones SZ1, SZ2 and, in M5, SZ3) at 1-ft "
            "steps below the top of casing and left for a few to ~40 minutes per depth while its camera tracked colloids; the instrument software logs each "
            "tracked particle's azimuth (degrees clockwise from north; magnetic declination set to 0), speed (um/s) and particle count, and reports per "
            "measurement the arithmetic average, median, minimum, maximum and standard deviation of direction and speed, the number of data points and its "
            "flow-vector estimate (direction and speed), which it withholds when the data are unreliable. Samplers called a depth 'preferential flow' when a "
            "consistent fast vector was seen (log files suffixed _Pref). Measurements: 2024-01-31 (M4-SZ1, L9-SZ1), 02-05 (L9-SZ2, M4-SZ2), 02-08 (M5-SZ1, "
            "M5-SZ2), 02-09 (M5-SZ3, heavy rainfall) and 02-26 (M5 repeats). The plan also cites 63 measurements of April-May 2023 (VSZ, SZ1, SZ2 of all SSO "
            "wells) that are not on the team Drive."}


def main() -> None:
    stage_validator()
    ab.load_ontology_names()
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    ab.OUT = OUT
    ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT = (OUT / d for d in ("json", "static", "process", "check", "reports"))
    for d in (ab.JSON_OUT, ab.STATIC_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT):
        d.mkdir(parents=True)
    with (EXPORT / "Location.tsv").open() as h:
        locations = {r["name"] for r in csv.DictReader(h, delimiter="\t")}
    with (EXPORT / "Protocol.tsv").open() as h:
        if PROTO in {r["name"] for r in csv.DictReader(h, delimiter="\t")}:
            raise ValueError("protocol exists")
    recs = read_workbook()
    brick_a, brick_b, notes, n_tracks = build(recs, locations)
    paths = [ab.write_brick(brick_a), ab.write_brick(brick_b)]
    with (ab.STATIC_OUT / f"Protocol_additions_{TAG}.tsv").open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=["name", "description", "link"], delimiter="\t", lineterminator="\n"); w.writeheader(); w.writerow(protocol_row(""))
    locs = sorted({r["location"] for r in recs})
    proc = ab.PROCESS_OUT / f"process_assay_environment_{TAG}.tsv"
    write_process(proc, [{"process": "Assay Environment <PROCESS:0000004>", "person": PERSON, "campaign": CAMPAIGN, "protocol": PROTO,
                          "date_start": min(r["date"] for r in recs), "date_end": max(r["date"] for r in recs),
                          "input_objects": ", ".join(f"Location: {l}" for l in locs), "output_objects": ", ".join(f"Generic: {b['name']}" for b in (brick_a, brick_b))}])
    files = [f"static/Protocol_additions_{TAG}.tsv"] + [f"json/{p.name}" for p in paths] + [f"process/{proc.name}"]
    (OUT / "files_to_import.txt").write_text("\n".join(files) + "\n")
    (OUT / "import_to_coral.py").write_text("\n".join([
        "# Run on the CORAL hub after staging files_to_import.txt in data_import/data and reloading COMO (coral_import/ontology_update_20261107_borescope)",
        f"toolx.update_core('Protocol_additions_{TAG}.tsv', 'Protocol')"] + [f"toolx.upload_brick('{p.name}')" for p in paths]
        + [f"toolx.upload_process('Assay Environment', '{proc.name}')", ""]))
    summary = {"release": RELEASE, "measurements": len(recs), "with_log": sum(1 for r in recs if r["summary"]), "flow_vectors": sum(1 for r in recs if r["summary"] and r["summary"]["flow_dir"] is not None),
               "tracks": n_tracks, "workbook_notes": notes, "hashes": {f: hashlib.sha256((OUT / f).read_bytes()).hexdigest() for f in files}}
    (ab.REPORT_OUT / "build_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    (OUT / "README.md").write_text(f"""# CORAL import package: SSO colloidal borescope 2024 ({RELEASE})

Built by `tools/build_sso_borescope_coral_import.py`; needs the COMO update `coral_import/ontology_update_20261107_borescope`
(velocity ME:0000519, azimuth ME:0000520, micrometer per second ME:0000521) installed and reloaded first.

| Brick | Shape | Variables |
| --- | --- | --- |
| hazen_colloidal_borescope_flow_vectors_sso_2024 | {len(recs)} measurements | flow azimuth/velocity, 5 statistics each, tracked particles |
| hazen_colloidal_borescope_particle_tracks_sso_2024 | {n_tracks} readings | azimuth, velocity, particles in frame |

Protocol `{PROTO}`; one Assay Environment process (Hazen Lab, Subsurface Observatory, 2024-01-31 to 2024-02-26).
Workbook discrepancies (resolved from the software summaries): {'; '.join(notes)}
""")
    print(json.dumps({k: v for k, v in summary.items() if k != "hashes"}, indent=1))


if __name__ == "__main__":
    main()
