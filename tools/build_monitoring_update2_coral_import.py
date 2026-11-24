#!/usr/bin/env python3
"""Monitoring update of 2026-11-24: EFPW03 and EFPW06 direct downloads, and the WS3 export bricks with their clock corrected.

  hazen_aquatroll600_EFPW03_<dates>            direct download, 2023-04-01 to 05-09 (clock Central, as labelled; checked against the HydroVu brick)
  hazen_aquatroll600_EFPW03_20221221_<date>_v2 Brick0001232 (HydroVu) ending where the download begins
  hazen_aquatroll600_EFPW06_<dates>            direct download, 2023-01-18 to 05-09 (clock Eastern, as labelled; not checkable)
  hazen_hobo_WS3_*_v2 (two)                    Brick0002351/0002352: the Area 3 LI-COR export is on Eastern Standard Time all year (no offset in its
                                               time column); it was read as local time, so daylight-saving readings were one hour early

Reuses the helpers and scratch inputs of tools/build_monitoring_update_coral_import.py. Nothing here touches the CORAL hub.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_monitoring_update_coral_import as mu  # noqa: E402
from build_monitoring_update_coral_import import ab, hy, iso, write_process  # noqa: E402

REPO = ab.REPO
STAMP = "20261124"
OUT = REPO / f"coral_import/monitoring_update_{STAMP}"
LIVE = REPO / "sync-coral-to-berdl/exports/sync-20261119-211840/coral_export/static_tsv"
mu.EXPORT_DATA = REPO / "sync-coral-to-berdl/exports/sync-20261119-211840/berdl_upload/data"
EASTERN = ZoneInfo("America/New_York")
CENTRAL = ZoneInfo("America/Chicago")
EST = dt.timezone(dt.timedelta(hours=-5))
DOWNLOADS = ab.DRIVE / "Hazen SSO Continuous Monitoring/AQUATROLL DATA/Download Zips/AT600 download_05092023"
EFPW03 = DOWNLOADS / "EFPW03_09292022_2023-05-09_10-05-49-750.xlsx"
EFPW06 = DOWNLOADS / "EFPW06_011823_2023-05-09_10-57-18-940.csv"
B = "Brick0001231"  # template for the EFPW column definitions (the EFPW02 HydroVu brick)
# export header (start of) -> (definition column, template brick, factor)
COLS = {
    "pH (pH)": ("ph_ph", B, 1), "pH(mV) (mV)": ("ph_millivolt", B, 1), "Oxidation Reduction Potential (ORP) (mV)": ("redox_potential_millivolt", B, 1),
    "Actual Conductivity": ("conductivity_microsiemen_per_centimeter", B, 1), "Specific Conductivity": ("specific_conductivity_microsiemen_per_centimeter", B, 1),
    "Salinity (PSU)": ("salinity_practical_salinity_unit", B, 1), "Resistivity (ohm-cm)": ("resistivity_ohm_cm", B, 1),
    "Water Density (g/cm3)": ("density_molecule_from_list_water_gram_per_cubic_centimeter", B, 1),
    "Total Dissolved Solids (ppt)": ("concentration_phase_solid_physiochemical_state_dissolved_milligram_per_liter", B, 1000.0),  # parts per thousand -> mg/L
    "Battery Percentage (%)": ("charge_instrument_battery_percent", B, 1),
    "Nitrate (NO3 - N) (mg/L)": (mu.NITRATE, "Brick0002052", 1),
    "Pressure (PSI)": ("water_pressure_pound_per_square_inch", B, 1), "Depth (ft)": ("depth_top_water_surface_bottom_instrument_meter", B, 0.3048),
    "Barometric Pressure (mmHg)": ("air_pressure_millimetres_of_mercury", "Brick0002052", 1),
    "Rhodamine Concentration": ("concentration_molecule_from_list_rhodamine_b_milligram_per_liter", "Brick0001362", 0.001),  # ug/L -> mg/L
}
SKIPPED = ("Nitrate mV (mV)", "Rhodamine Fluorescence (RFU)")  # plus the second Temperature (C), the rhodamine sensor's
UNITS_NOTE = ("Converted from the export's units: total dissolved solids from parts per thousand to mg/L, depth of water above the instrument from feet to meters, "
              "rhodamine from micrograms to milligrams per liter (no tracer was present). Nitrate is the instrument's nitrate reading in mg/L (the export header "
              "'NO3 - N' is the instrument's label; the values are nitrate). Not stored: the nitrate electrode millivolts, rhodamine fluorescence and the rhodamine "
              "sensor's temperature")
RAW_NOTE = "The download is as it came from the instrument; the folder's readme says these files have not been cleaned for discrepancies"


def columns_from(head, data):
    """Map the export's columns to variable definitions; the first 'Temperature (C)' is the conductivity sensor's."""
    cols, vals, used = {}, {}, set()
    for key, (col, bid, f) in COLS.items():
        j = next((i for i, h in enumerate(head) if h.startswith(key)), None)
        if j is None:
            continue
        used.add(j)
        cols[col] = mu.template_def(col, bid)
        v = [None if r[j] in (None, "") else float(r[j]) * f for r in data]
        if col == mu.NITRATE:  # the builder's rule: below 0, or at or above 49,000 mg/L, is a sentinel
            v = [None if x is not None and (x < 0 or x >= 49000) else x for x in v]
        vals[col] = v
    tj = [i for i, h in enumerate(head) if h == "Temperature (C)"]
    if len(tj) != 2:
        raise ValueError(f"temperature columns {tj}")
    used.add(tj[0])
    cols["temperature_degree_celsius"] = mu.template_def("temperature_degree_celsius", B)
    vals["temperature_degree_celsius"] = [float(r[tj[0]]) for r in data]
    left = [h for i, h in enumerate(head) if i >= 2 and i not in used and h and i != tj[1] and not h.startswith(SKIPPED)]
    if left:
        raise ValueError(f"unmapped columns {left}")
    return cols, vals


def weekly(times, vals, col):
    out = {}
    for t, v in zip(times, vals[col]):
        if v is not None:
            out.setdefault(t.astimezone(EASTERN).strftime("%Y-%m"), []).append(v)
    return ", ".join(f"{k} {sorted(v)[len(v) // 2]:.3g}" for k, v in sorted(out.items()))


def build_efpw03(report, updates):
    ws = openpyxl.load_workbook(EFPW03, data_only=True, read_only=True).worksheets[0]
    rows = [r for r in ws.iter_rows(values_only=True)]
    cells = [str(c) for r in rows[:140] for c in r if c is not None]
    if "Aqua TROLL 600 Non-Vented" not in cells or "EFPW03_09292022" not in cells or "Time Zone: Central Daylight Time" not in cells:
        raise ValueError("EFPW03 log properties")
    i = next(k for k, r in enumerate(rows) if r and r[0] == "Date and Time" and r[1] != "Note")
    head = [str(c).strip() if c is not None else "" for c in rows[i]]
    data = [r for r in rows[i + 1:] if isinstance(r[0], dt.datetime) and isinstance(r[2], (int, float))]
    if len(data) != 5434:
        raise ValueError(f"EFPW03 rows {len(data)}")
    start = data[0][0].replace(tzinfo=CENTRAL).astimezone(dt.timezone.utc)
    times = [start + dt.timedelta(seconds=round(float(r[1]) - float(data[0][1]))) for r in data]
    for r, t in zip(data, times):
        if abs((t.astimezone(CENTRAL).replace(tzinfo=None) - r[0]).total_seconds()) > 60:
            raise ValueError(f"EFPW03 clock and elapsed time disagree at {r[0]}")
    cols, vals = columns_from(head, data)
    obj, name, keep = mu.efpw_brick(
        "EFPW03", "Aqua TROLL 600 Non-Vented", f"manual download, {EFPW03.name}",
        ["Direct download (Win-Situ) of the EFPW03 Aqua TROLL 600 log, read every 10 minutes. The export's times are Central, as it says: over the four days it shares "
         "with the HydroVu data of this instrument the two agree at the same instant (water pressure within 0.002 psi, temperature within 0.001 C). Times are stored "
         "as Eastern with the offset. " + RAW_NOTE, UNITS_NOTE, f"Source: {hy.rel(EFPW03)}"],
        times, cols, vals)
    report += ["## EFPW03 direct download", "", f"- {name}: {len(times)} readings, {iso(times[0])[:16]} to {iso(times[-1])[:16]}; {len(keep)} variables",
               f"- nitrate median by month (mg/L): {weekly(times, vals, mu.NITRATE)}; specific conductivity: {weekly(times, vals, 'specific_conductivity_microsiemen_per_centimeter')}", ""]
    # the HydroVu brick it overlaps, ending where the download begins
    st, scols, stimes, svals = mu.load_stored("Brick0001232")
    keep_idx = [k for k, t in enumerate(stimes) if t < times[0]]
    dropped = len(stimes) - len(keep_idx)
    if not 150 <= dropped <= 230:
        raise ValueError(f"EFPW03 HydroVu overlap rows {dropped}")
    new_times = [stimes[k] for k in keep_idx]
    defs = {c: mu.var_def(t) for c, t in zip(scols, st["typed_values"])}
    new = mu.assemble(st, mu.next_name(st["name"], new_times), st["description"],
                      [f"Replaces {st['name']} (Brick0001232): ends at {iso(new_times[-1])[:16]}; the {dropped} half-hourly HydroVu readings after that are covered, "
                       f"every 10 minutes, by the instrument's direct download ({name}); no other value changed"],
                      (new_times, [{c: svals[c][k] for c in scols} for k in keep_idx]), scols, defs)
    ab.write_brick(new)
    updates.append((st["name"], new["name"]))
    report += [f"- replaces Brick0001232 {st['name']} with {new['name']}: {len(stimes)} -> {len(new_times)} readings (the last {dropped} are covered by the download)", ""]
    return [(obj, ["EFPW03"], "Hazen Lab <ENIGMA:0000066>", "Field Sampling <ENIGMA:0000095>", f"{times[0].astimezone(EASTERN):%Y-%m-%d}", f"{times[-1].astimezone(EASTERN):%Y-%m-%d}")]


def build_efpw06(report, updates):
    lines = EFPW06.read_text(errors="ignore").replace("\r", "").split("\n")
    text = "\n".join(lines[:120])
    if "Aqua TROLL 600 Non-Vented" not in text or "EFPW06_011823" not in text or "Time Zone: Eastern Standard Time/Eastern Daylight Time" not in text:
        raise ValueError("EFPW06 log properties")
    k = next(i for i, l in enumerate(lines) if l.startswith("Date and Time,") and "Note" not in l)
    head = [c.strip() for c in next(csv.reader([lines[k]]))]
    data = [[c.strip() for c in next(csv.reader([l]))] for l in lines[k + 1:] if l[:1].isdigit()]
    if len(data) != 15970:
        raise ValueError(f"EFPW06 rows {len(data)}")
    first = dt.datetime.strptime(data[0][0], "%m/%d/%Y %I:%M:%S %p")
    start = first.replace(tzinfo=EASTERN).astimezone(dt.timezone.utc)
    times = [start + dt.timedelta(seconds=round(float(r[1]) - float(data[0][1]))) for r in data]
    for r, t in zip(data, times):
        if abs((t.astimezone(EASTERN).replace(tzinfo=None) - dt.datetime.strptime(r[0], "%m/%d/%Y %I:%M:%S %p")).total_seconds()) > 60:
            raise ValueError(f"EFPW06 clock and elapsed time disagree at {r[0]}")
    cols, vals = columns_from(head, data)
    obj, name, keep = mu.efpw_brick(
        "EFPW06", "Aqua TROLL 600 Non-Vented", f"manual download, {EFPW06.name}",
        ["Direct download (Win-Situ) of the EFPW06 Aqua TROLL 600 log, read every 10 minutes, starting two hours after the HydroVu record of the earlier EFPW06 "
         "instrument ends (hazen_leveltroll500_EFPW06_20221221_20230118). The export's times are Eastern, as it says; this log has no barometer and shares no period "
         "with other data of the instrument, so the clock could not be checked independently. " + RAW_NOTE, UNITS_NOTE, f"Source: {hy.rel(EFPW06)}"],
        times, cols, vals)
    gaps = Counter(round((y - x).total_seconds() / 60) for x, y in zip(times, times[1:]))
    report += ["## EFPW06 direct download", "", f"- {name}: {len(times)} readings, {iso(times[0])[:16]} to {iso(times[-1])[:16]}; intervals (min) {dict(gaps.most_common(2))}; {len(keep)} variables",
               f"- nitrate median by month (mg/L): {weekly(times, vals, mu.NITRATE)}; specific conductivity: {weekly(times, vals, 'specific_conductivity_microsiemen_per_centimeter')}", ""]
    return [(obj, ["EFPW06"], "Hazen Lab <ENIGMA:0000066>", "Field Sampling <ENIGMA:0000095>", f"{times[0].astimezone(EASTERN):%Y-%m-%d}", f"{times[-1].astimezone(EASTERN):%Y-%m-%d}")]


def build_ws3(report, updates):
    """Brick0002351 and Brick0002352 again, with the export's times read as Eastern Standard Time (UTC-5) all year."""
    ccols, crows = mu.cm_table("hazen_hobo_ws3")
    api_start = mu.load_stored("Brick0001359")[2][0]
    rows = []
    for t, v, prov, src in crows:
        if prov != "licor export":
            continue
        true = t.replace(tzinfo=None).replace(tzinfo=EST)  # the wall-clock time as the export gives it, at UTC-5
        if true < api_start:
            rows.append((true, v, src))
    rows.sort(key=lambda x: x[0])
    if len({r[0] for r in rows}) != len(rows):
        raise ValueError("WS3: duplicate times after the correction")
    first_full = next(i for i, (_, v, _) in enumerate(rows) if any(v.get(c) is not None for c in ccols if c not in mu.RAIN))
    tst, tcols, _, _ = mu.load_stored("Brick0001359")
    defs = {c: mu.var_def(t) for c, t in zip(tcols, tst["typed_values"])}
    report += ["## WS3 export bricks, clock corrected", "", "| replaces | new brick | rows | first reading | last reading | readings moved one hour later |", "|---|---|---|---|---|---|"]
    for bid, part in (("Brick0002351", rows[:first_full]), ("Brick0002352", rows[first_full:])):
        st, scols, stimes, svals = mu.load_stored(bid)
        times = [t for t, _, _ in part]
        keep = [c for c in ccols if any(v.get(c) is not None for _, v, _ in part)]
        if keep != [c for c in scols if c in keep] or set(keep) != set(scols):
            raise ValueError(f"{bid}: variables changed: {sorted(set(keep) ^ set(scols))}")
        # same values in the same order as the brick it replaces (the later brick now stops before the API data, an hour of readings shorter)
        n = min(len(times), len(stimes))
        for c in scols:
            new_vals = [v.get(c) for _, v, _ in part][:n]
            if any((a is None) != (b is None) or (a is not None and abs(a - b) > 1e-9 * max(1.0, abs(a))) for a, b in zip(svals[c][:n], new_vals)):
                raise ValueError(f"{bid}: values of {c} differ from the loaded brick")
        moved = sum(1 for a, b in zip(stimes[:n], times[:n]) if (b - a) == dt.timedelta(hours=1))
        same = sum(1 for a, b in zip(stimes[:n], times[:n]) if a == b)
        if moved + same != n:
            raise ValueError(f"{bid}: times differ by something other than 0 or 1 hour")
        new = mu.assemble(st, mu.next_name(st["name"], times), mu.redate(st["description"], times),
                          [f"Replaces {st['name']} ({bid}): the Area 3 LI-COR export gives its times in Eastern Standard Time all year (it matches the LI-COR API data "
                           f"of late May 2024 exactly when read that way, and has no skipped or repeated hour at the clock changes), but was read as local time, so the "
                           f"{moved} readings taken during daylight-saving time were stamped one hour early; they are now one hour later, and no value changed"
                           + (f". The brick ends before the LI-COR API data begin, {len(stimes) - len(times)} readings shorter" if len(times) < len(stimes) else "")],
                          (times, [{c: v.get(c) for c in keep} for _, v, _ in part]), [c for c in scols], defs)
        ab.write_brick(new)
        updates.append((st["name"], new["name"]))
        report.append(f"| {bid} {st['name'].replace('.hndarray', '')} | {new['name'].replace('.hndarray', '')} | {len(times)} (was {len(stimes)}) | {iso(times[0])[:16]} | {iso(times[-1])[:16]} | {moved} |")
    report.append("")
    return []


def main() -> None:
    hy.stage_validator()
    ab.load_ontology_names()
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    ab.OUT = OUT
    ab.JSON_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT = (OUT / d for d in ("json", "process", "check", "reports"))
    for d in (ab.JSON_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT):
        d.mkdir(parents=True)
    with (LIVE / "Location.tsv").open() as h:
        locations = {r["name"] for r in csv.DictReader(h, delimiter="\t")}
    report = ["# Monitoring update 2026-11-24: build report", ""]
    rows, names, updates = [], [], []
    for fn in (build_efpw03, build_efpw06, build_ws3):
        for obj, locs, person, campaign, d0, d1 in fn(report, updates):
            if [l for l in locs if l not in locations]:
                raise ValueError(f"{obj['name']}: Location not in CORAL")
            names.append(obj["name"])
            rows.append({"process": "Assay Environment <PROCESS:0000004>", "person": person, "campaign": campaign, "protocol": "null", "date_start": d0, "date_end": d1,
                         "input_objects": ", ".join(f"Location: {l}" for l in locs), "output_objects": f"Generic: {obj['name']}"})
    today = dt.date.today().isoformat()
    proc_new, proc_upd = f"process_assay_environment_monitoring_update_{STAMP}.tsv", f"process_update_data_monitoring_update_{STAMP}.tsv"
    write_process(ab.PROCESS_OUT / proc_new, rows)
    write_process(ab.PROCESS_OUT / proc_upd, [{
        "process": "Update Data <PROCESS:0000053>", "person": "John-Marc Chandonia <ENIGMA:0000057>", "campaign": "Field Sampling <ENIGMA:0000095>", "protocol": "null",
        "date_start": today, "date_end": today, "input_objects": f"Generic: {old}", "output_objects": f"Generic: {new}"} for old, new in updates])
    new_json = [n.rsplit(".", 1)[0] + ".json" for n in names]
    rep_json = [n.rsplit(".", 1)[0] + ".json" for _, n in updates]
    files = [f"json/{f}" for f in new_json + rep_json] + [f"process/{proc_new}", f"process/{proc_upd}"]
    if [f for f in files if not (OUT / f).exists()]:
        raise FileNotFoundError(files)
    (OUT / "files_to_import.txt").write_text("\n".join(files) + "\n")
    (OUT / "import_to_coral.py").write_text("\n".join(
        ["# Run on the CORAL hub, in order, after copying every file in files_to_import.txt to /home/coral/prod/data_import/data/ on coral-enigma."]
        + [f"toolx.upload_brick('{f}')" for f in new_json] + [f"toolx.upload_process('Assay Environment', '{proc_new}')"]
        + [f"toolx.upload_brick('{f}')" for f in rep_json] + [f"toolx.upload_process('Update Data', '{proc_upd}')", ""]))
    (OUT / ".gitignore").write_text("json/\ncheck/\n")
    (ab.REPORT_OUT / "build_report.md").write_text("\n".join(report) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main()
