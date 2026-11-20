#!/usr/bin/env python3
"""Monitoring update of 2026-11-17: hydrology gaps and the held continuous-monitoring fixes.

New bricks
  hazen_leveltroll400_DP06_20190728_20191206     the one 2019 Level TROLL log that was an .xlsx (its 17 siblings are Brick0000019-0000035)
  hazen_pump_log_sso_pump_test_2025              Pump Log sheet of 2025_PumpTest_Metadata.xlsx
  (EFPW01 / EFPW05 Aqua TROLL logs and the replacement monitoring bricks are added by later sections of this file)

Nothing here touches the CORAL hub.
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
import build_sso_batch_ab_coral_import as ab  # noqa: E402
import build_sso_hydrology_coral_import as hy  # noqa: E402
import build_sso_oneoff_16s_coral_import as hy_oo  # noqa: E402
from build_sso_batch_ab_coral_import import T, brick, comment, ctx, float_var, oterm_value, sval, typed, write_process  # noqa: E402

REPO = ab.REPO
TEAM = ab.DRIVE
STAMP = "20261117"
OUT = REPO / f"coral_import/monitoring_update_{STAMP}"
LIVE = REPO / "sync-coral-to-berdl/exports/sync-20261113-162127/coral_export/static_tsv"
EASTERN = ZoneInfo("America/New_York")
DP06 = TEAM / "FRC Well Metadata/Well monitoring and weather data/DP06_LT400_20190728_20191206.xlsx"
PUMP_2025 = TEAM / "2025_SSO_PumpTest2/2025_PumpTest_Metadata.xlsx"

T.update({"water pressure": "ME:0000315", "psi": "ME:0000296", "flow rate": "ME:0000528", "liter per minute": "ME:0000517",
          "mathematical context": "ME:0000018", "cumulative": "ME:0000477", "Field Sampling": "ENIGMA:0000095",
          "physical measurement": "DA:0000002", "parts per thousand": "UO:0000168", "datetime": "ME:0000180", "foot": "ME:0000310", "top": "ME:0000311", "bottom": "ME:0000312"})


def iso(t: dt.datetime) -> str:
    return t.astimezone(EASTERN).isoformat(timespec="milliseconds")


def time_dim(times: list[dt.datetime]) -> dict:
    return {"data_type": ab.term("time series"), "size": len(times), "typed_values": [typed("datetime", "string", [iso(t) for t in times], None, [])]}


# ----------------------------------------------------------------------------
# DP06 Level TROLL 400, 2019
# ----------------------------------------------------------------------------

def build_dp06(report):
    ws = openpyxl.load_workbook(DP06, data_only=True, read_only=True).worksheets[0]
    rows = [r for r in ws.iter_rows(values_only=True)]
    meta = {}
    for r in rows[:70]:
        cells = [c for c in r if c is not None]
        if len(cells) >= 2:
            meta.setdefault(str(cells[0]).strip(), cells[1])
    if meta.get("Device") != "Level TROLL 400" or meta.get("Device Name") != "DP06" or meta.get("Level Measurement Mode") != "Level Depth To Water":
        raise ValueError(f"DP06 log properties {meta.get('Device')}, {meta.get('Device Name')}, {meta.get('Level Measurement Mode')}")
    if not any(c == "Time Zone: Eastern Daylight Time/Eastern Standard Time" for r in rows[:90] for c in r if c is not None):
        raise ValueError("DP06 time zone line")
    i = next(k for k, r in enumerate(rows) if r and r[0] == "Date and Time" and r[1] != "Note")
    if [str(c).strip() for c in rows[i][:5]] != ["Date and Time", "Seconds", "Temperature (C)", "Pressure (PSI)", "Level Depth To Water (ft)"]:
        raise ValueError(f"DP06 header {rows[i][:5]}")
    data = [r for r in rows[i + 1:] if isinstance(r[0], dt.datetime)]
    if len(data) != 18942:
        raise ValueError(f"DP06 rows {len(data)}")
    # the instrument clock is local time with daylight saving; elapsed seconds are continuous, so the UTC time of each reading
    # is the first reading's (EDT) plus its elapsed seconds
    start = data[0][0].replace(tzinfo=EASTERN).astimezone(dt.timezone.utc)  # add elapsed time in UTC, not on the wall clock
    times = [start + dt.timedelta(seconds=round(float(r[1]))) for r in data]
    late = []  # the file's own clock must agree with that, to the minute; Win-Situ shows the hour after the 2019-11-03 change still in daylight time
    for r, t in zip(data, times):
        off = (r[0] - t.astimezone(EASTERN).replace(tzinfo=None)).total_seconds()
        if abs(off - 3600) <= 60 and r[0].date() == dt.date(2019, 11, 3):
            late.append(r[0])
        elif abs(off) > 60:
            raise ValueError(f"DP06 clock and elapsed time disagree at {r[0]}")
    if len(late) != 6:
        raise ValueError(f"DP06: {len(late)} readings shown an hour late around the clock change")
    name = "hazen_leveltroll400_DP06_20190728_20191206"
    obj = brick(name, "Hazen Lab Level TROLL 400 Data", "physical measurement",
                [ctx("instrument", sval("Level TROLL 400")),
                 {"value_type": ab.term("environmental sample location ID"), "value": {"scalar_type": "object_ref", "object_ref": "DP06", "string_value": "DP06"}},
                 comment("Level TROLL 400 (serial 645644) in well DP06, Area 2, read every 10 minutes from 2019-07-28 to 2019-12-06. The log was created 2019-06-06; "
                         "the downloaded file begins 2019-07-28. Logging was suspended 2019-10-04 09:16 to 10:06 for a download"),
                 comment("Depth to water is the instrument's 'Level Depth To Water', referenced to a manual reading of 12.503 ft below top of casing when the log was "
                         "created. Times are local (Eastern) with the UTC offset; the clock change of 2019-11-03 is taken from the log's elapsed seconds"),
                 comment(f"Source: {hy.rel(DP06)} (Win-Situ export). The other 2019 Level TROLL logs of this folder are hazen_leveltroll400_* bricks loaded earlier")],
                [time_dim(times)],
                [float_var("temperature", "degree Celsius", [], [r[2] for r in data]),
                 float_var("water pressure", "psi", [], [r[3] for r in data]),
                 float_var("depth", "foot", [ctx("top", sval("top of casing")), ctx("bottom", sval("water surface"))], [r[4] for r in data])])
    obj["array_context"][0]["value"] = oterm_value("environmental measurement")
    ab.write_brick(obj)
    gaps = Counter(round((b - a).total_seconds()) for a, b in zip(times, times[1:]))
    report += [f"## {name}", "", f"- {len(data)} readings, {iso(times[0])} to {iso(times[-1])}; intervals (s): {dict(gaps.most_common(3))}",
               f"- temperature {min(r[2] for r in data):.2f} to {max(r[2] for r in data):.2f} C; pressure {min(r[3] for r in data):.3f} to {max(r[3] for r in data):.3f} psi; "
               f"depth to water {min(r[4] for r in data):.2f} to {max(r[4] for r in data):.2f} ft", ""]
    return obj, ["DP06"], "Hazen Lab <ENIGMA:0000066>", "Field Sampling <ENIGMA:0000095>", f"{times[0].astimezone(EASTERN):%Y-%m-%d}", f"{times[-1].astimezone(EASTERN):%Y-%m-%d}"


# ----------------------------------------------------------------------------
# 2025 pump test: pump log
# ----------------------------------------------------------------------------
PUMP_TIME_FIX = {("M4-SZ2", 20250924, 1155.0): dt.time(11, 55)}  # the one time typed as a number
# two typing errors corrected from the neighbouring rows (user, 2026-11-17): (port, time as written, litres as written) -> (time, litres)
PUMP_ROW_FIX = {("L9-SZ2", dt.time(8, 53), 19.0): (dt.time(8, 53), 10.0),   # 9 L at 08:51, 12 L at 08:57, 0.5 L/min
                ("M5-SZ3", dt.time(8, 21), 9.0): (dt.time(8, 31), 9.0)}     # between 08:29 (8 L) and 08:33 (10 L)


def build_pump_log(report):
    wb = openpyxl.load_workbook(PUMP_2025, data_only=True)
    rows = [r for r in wb["Pump Log"].iter_rows(values_only=True) if any(c is not None for c in r)]
    if tuple(rows[0][:6]) != ("Well", "Date", "Liters Pumped", "Pump Rate (L/min)", "Time", "Reason for Pump"):
        raise ValueError(f"pump log header {rows[0]}")
    recs, fixed, corrected = [], [], []
    for r in rows[1:]:
        port, day, litres, rate, tm, reason = r[:6]
        if not hy.PORT_RE.match(port) or reason != "Pump Test":
            raise ValueError(f"pump log row {r}")
        if not isinstance(tm, dt.time):
            key = (port, int(day), tm)
            if key not in PUMP_TIME_FIX:
                raise ValueError(f"pump log time {r}")
            tm = PUMP_TIME_FIX[key]
            fixed.append(f"{port} {int(day)} {r[4]:g} read as {tm:%H:%M}")
        if (port, tm, float(litres)) in PUMP_ROW_FIX:
            new_tm, new_l = PUMP_ROW_FIX[(port, tm, float(litres))]
            corrected.append(f"{port} {tm:%H:%M} {float(litres):g} L corrected to {new_tm:%H:%M} {new_l:g} L")
            tm, litres = new_tm, new_l
        d = dt.datetime.strptime(str(int(day)), "%Y%m%d")
        recs.append((port, dt.datetime.combine(d.date(), tm, tzinfo=EASTERN), float(litres), round(float(rate), 6)))
    if len(corrected) != len(PUMP_ROW_FIX):
        raise ValueError(f"pump log corrections applied: {corrected}")
    if len(recs) != 242:
        raise ValueError(f"pump log rows {len(recs)}")
    order = []  # ports in the order pumped, rows in sheet order within a port
    for p, *_ in recs:
        if p not in order:
            order.append(p)
    recs.sort(key=lambda x: order.index(x[0]))  # stable: keeps the sheet's row order
    notes = []
    for p in order:
        mine = [x for x in recs if x[0] == p]
        back_t = sum(1 for a, b in zip(mine, mine[1:]) if b[1] < a[1])
        back_v = sum(1 for a, b in zip(mine, mine[1:]) if b[2] < a[2])
        if back_t or back_v:
            raise ValueError(f"{p}: values still run backwards after the corrections")
            notes.append(f"{p}: " + ", ".join(([f"{back_t} time(s) earlier than the row before"] if back_t else []) + ([f"{back_v} volume(s) lower than the row before"] if back_v else [])))
    fl = [r for r in wb["Field Log"].iter_rows(values_only=True) if r[0] and hy.PORT_RE.match(str(r[0]))]
    schedule = [f"{r[0]} {str(int(r[1]))[:4]}-{str(int(r[1]))[4:6]}-{str(int(r[1]))[6:]} {r[2]:%H:%M}-{r[4]:%H:%M}"
                + (f" and {r[6]:%H:%M}-{r[8]:%H:%M}" if r[6] else "") + f", {r[3]}, {r[10]}" for r in fl]
    port_rate = {p: next(q for x, _, _, q in recs if x == p) for p in order}
    field_rate = {r[0]: float(str(r[3]).replace("L/min", "")) for r in fl}
    ports = [p for p, *_ in recs]
    dim = hy.port_dim(ports, [typed("datetime", "string", [iso(t) for _, t, _, _ in recs], None, [])])
    name = "hazen_pump_log_sso_pump_test_2025"
    obj = brick(name, f"Hazen Lab pump log of the September 2025 SSO pump tests ({len(recs)} readings at nine ports)", "physical measurement",
                [ctx("personnel", oterm_value("Hazen Lab")),
                 ctx("ENIGMA campaign", oterm_value("Subsurface Observatory")),
                 comment("One row per pump log entry: the well Location, the pumped port, the port's screen midpoint below ground surface (SSO Cheat Sheet) and the local "
                         "date and time (EDT). Variables: the volume pumped from that port since the start of its test (liters, cumulative) and the pump's flow rate "
                         "(liters per minute; one value per port: " + ", ".join(f"{p} {port_rate[p]:g}" for p in order) + ")"),
                 comment("Rows are in the sheet's order within each port. Two typing errors in the sheet are corrected from the neighbouring rows: " + "; ".join(corrected)
                         + (". Time typed as a number: " + "; ".join(fixed) if fixed else "")),
                 comment("Pumping periods from the sheet 'Field Log' (port, date, start-stop, rate, total volume): " + "; ".join(schedule)
                         + "".join(f"; {p} is not in the Field Log" for p in order if p not in field_rate)),
                 comment(f"Source: {hy.rel(PUMP_2025)}, sheet Pump Log (columns Well, Date, Liters Pumped, Pump Rate (L/min), Time; 'Reason for Pump' is 'Pump Test' on every "
                         "row). The samples and field measurements of these tests are in pumptest_2025_field_measurements_v2")],
                [dim],
                [float_var("volume", "liter", [ctx("mathematical context", oterm_value("cumulative"))], [v for _, _, v, _ in recs]),
                 float_var("flow rate", "liter per minute", [ctx("instrument", sval("pump"))], [q for _, _, _, q in recs])])
    for p in order:  # the rate is one value per port, and agrees with the Field Log sheet where that sheet has the port
        rates = {q for x, _, _, q in recs if x == p}
        if len(rates) != 1 or abs(rates.pop() - field_rate.get(p, port_rate[p])) > 1e-9:
            raise ValueError(f"pump rate of {p} is not constant or differs from the Field Log")
    obj["array_context"][0]["value"] = oterm_value("environmental measurement")
    ab.write_brick(obj)
    report += [f"## {name}", "", f"- {len(recs)} readings; ports in order pumped: {', '.join(order)}", f"- typing errors corrected: {'; '.join(corrected)}",
               f"- time typed as a number: {'; '.join(fixed) or 'none'}", ""]
    locs = sorted({f"SSO-{p.split('-')[0]}" for p in ports}, key=lambda l: hy.WELLS.index(l[4:]))
    return obj, locs, "Hazen Lab <ENIGMA:0000066>", hy.CAMPAIGN, f"{min(t for _, t, _, _ in recs):%Y-%m-%d}", f"{max(t for _, t, _, _ in recs):%Y-%m-%d}"


# ----------------------------------------------------------------------------
# Replacement bricks for the held continuous-monitoring fixes (CORAL_FIXES_PENDING.md items 1, 2, 4, 5)
# ----------------------------------------------------------------------------
# CM_OUT is the output of `continuous_monitoring/cm_build.py --mode backfill --no-state --holdback-minutes 0`, the code that feeds
# enigma.continuous_monitoring: HydroVu timestamps +4 h at the SSO wells, real reading times at L8/L9/M6/U3, the dead WS3 anemometer
# nulled, the LI-COR exports parsed. STORED holds the hub's data_store copies of the bricks being replaced or used as templates.
SCRATCH = Path("/tmp/claude-1000/-scratch-jmc-BERDL-ENIGMA-CORAL/e08931f7-7c7d-4424-a1ff-a5f1bad88ee0/scratchpad/hydro")
CM_OUT = SCRATCH / "cmout"
STORED = SCRATCH / "stored"
EXPORT_DATA = REPO / "sync-coral-to-berdl/exports/sync-20261113-162127/berdl_upload/data"
TODAY = dt.date.today().isoformat()  # date of the Update Data processes
OLD_DEPTH = "depth_top_water_surface_bottom_instrument_foot"
NEW_DEPTH = "depth_top_ground_surface_bottom_water_surface_foot"
SHIFT_BRICKS = ["Brick0001367", "Brick0001411", "Brick0001420", "Brick0001594", "Brick0001598"]  # HydroVu Level TROLL VZ/VSZ, 4 h early
# WITHDRAWN 2026-11-19 (not rebuilt): the API's minute series at these wells is not interpolated, so thinning it to "real readings" loses data
INTERP_BRICKS = ["Brick0001957", "Brick0001964", "Brick0001624", "Brick0001976", "Brick0002010", "Brick0002011", "Brick0002015", "Brick0002019",
                 "Brick0002020", "Brick0002021", "Brick0002022", "Brick0002067", "Brick0002068", "Brick0002070", "Brick0002072", "Brick0002075",
                 "Brick0002076", "Brick0002080", "Brick0002083"]  # HydroVu Aqua TROLL at L8/L9/M6/U3: interpolated values
WS3_WIND_BRICKS = ["Brick0001359", "Brick0001360", "Brick0001361"]
WS3_DEAD = dt.datetime(2025, 3, 26, 18, 30, tzinfo=EASTERN)  # the last real anemometer reading (a gust of 2.25 mph); blank after it (user, 2026-11-19)


def tnew(t):
    name = ab.NAMES.get(t["oterm_ref"], t.get("oterm_name"))
    return {"term_name": name, "oterm_ref": t["oterm_ref"], "oterm_name": name}


def flat(v):
    while v and isinstance(v[0], list):
        v = [x for sub in v for x in sub]
    return v


def ctx_new(lst):
    out = []
    for c in lst or []:
        v = dict(c["value"])
        if v.get("scalar_type") == "oterm_ref":
            v["string_value"] = ab.NAMES[v["oterm_ref"]]
        if v.get("scalar_type") == "object_ref":
            v["string_value"] = v["object_ref"]
        if c["value_type"]["oterm_ref"] == "ME:0000293" and not v.get("oterm_ref", "").startswith("DA:"):
            v = oterm_value("environmental measurement")  # older bricks mark their data variables with a measurement term
        e = {"value_type": tnew(c["value_type"]), "value": v}
        if c.get("value_units"):
            e["value_units"] = tnew(c["value_units"])
        if c.get("value_context"):
            e["value_context"] = ctx_new(c["value_context"])
        out.append(e)
    return out


def var_def(t):
    """The definition of a stored variable (no values), as upload JSON."""
    out = {"value_type": tnew(t["value_type"])}
    if t.get("value_units"):
        out["value_units"] = tnew(t["value_units"])
    if t.get("value_context"):
        out["value_context"] = ctx_new(t["value_context"])
    return out


def next_name(name, times=None):
    """The next version of a brick name; with times, the name's two dates become the first and last local dates of the new data."""
    import re
    stem, ext = name.rsplit(".", 1)
    m = re.fullmatch(r"(.*)_v(\d+)", stem)
    base, version = (m.group(1), int(m.group(2)) + 1) if m else (stem, 2)
    if times is not None:
        d = re.fullmatch(r"(.*)_(\d{8})_(\d{8})", base)
        if not d:
            raise ValueError(f"no dates in {name}")
        base = f"{d.group(1)}_{times[0].astimezone(EASTERN):%Y%m%d}_{times[-1].astimezone(EASTERN):%Y%m%d}"
    return f"{base}_v{version}.{ext}"


def redate(description, times):
    import re
    return re.sub(r"from \d{4}-\d\d-\d\d to \d{4}-\d\d-\d\d( \(v\d+\))?", f"from {times[0].astimezone(EASTERN):%Y-%m-%d} to {times[-1].astimezone(EASTERN):%Y-%m-%d}", description)


def load_stored(bid):
    st = json.loads((STORED / bid).read_text())
    with (EXPORT_DATA / f"{bid}.tsv").open() as h:
        header = next(csv.reader(h, delimiter="\t"))
    cols = header[1:-1]  # between the time column and sdt_location_name
    if len(cols) != len(st["typed_values"]) or header[0] != "time_series_datetime" or header[-1] != "sdt_location_name":
        raise ValueError(f"{bid}: Lakehouse header does not line up with the stored variables")
    times = [dt.datetime.fromisoformat(x) for x in flat(st["dim_context"][0]["typed_values"][0]["values"]["string_values"])]
    values = {c: flat(t["values"]["float_values"]) for c, t in zip(cols, st["typed_values"])}
    return st, cols, times, values


def cm_table(table):
    with (CM_OUT / f"{table}.tsv").open() as h:
        rows = list(csv.reader(h, delimiter="\t"))
    head = rows[0]
    cols = head[1:head.index("sdt_location_name")]
    out = []
    for r in rows[1:]:
        out.append((dt.datetime.fromisoformat(r[0]), {c: (float(v) if v != "" else None) for c, v in zip(cols, r[1:1 + len(cols)])}, r[-2], r[-1]))
    return cols, out


def cm_name(st, zone):
    import re
    fam = re.match(r"hazen_([a-z0-9]+)_", st["name"]).group(1)
    loc = next(c["value"]["object_ref"] for c in st["array_context"] if c["value_type"]["oterm_ref"] == "ME:0000228")
    return re.sub(r"[^a-z0-9]+", "_", (f"hazen_{fam}_{loc}" + (f"_{zone}" if zone else "")).lower()).strip("_"), loc


def assemble(st, new_name_, description, extra_comments, times, columns, defs):
    """A one-dimensional time-series brick with the stored brick's context plus comments."""
    import re
    ver = re.search(r"_v(\d+)\.", new_name_)
    if ver:  # a description that names its version follows the new name
        description = re.sub(r"\(v\d+\)", f"(v{ver.group(1)})", description)
    context = ctx_new(st["array_context"]) + [comment(c) for c in extra_comments]
    variables = []
    for c in columns:
        vals = [row.get(c) for row in times[1]]
        variables.append(dict(defs[c], values={"scalar_type": "float", "float_values": vals}))
    return {"name": new_name_, "description": description, "data_type": tnew(st["data_type"]), "array_context": context, "n_dimensions": 1,
            "dim_context": [{"data_type": tnew(st["dim_context"][0]["data_type"]), "size": len(times[0]),
                             "typed_values": [{"value_type": tnew(st["dim_context"][0]["typed_values"][0]["value_type"]),
                                               "values": {"scalar_type": "string", "string_values": [iso(t) for t in times[0]]}}]}],
            "typed_values": variables}


def neighbours():
    """First and last timestamp of every current monitoring brick, by (family, location, zone)."""
    cur = json.loads((SCRATCH / "cur_bricks.json").read_text())
    out = {}
    for o in cur:
        with (EXPORT_DATA / f"{o['id']}.tsv").open() as h:
            first = last = None
            for i, line in enumerate(h):
                if i == 1:
                    first = line.split("\t", 1)[0]
                last = line.split("\t", 1)[0]
        out[o["id"]] = (o["fam"], o["loc"], o["zone"], dt.datetime.fromisoformat(first), dt.datetime.fromisoformat(last), o["name"])
    return out


def build_replacements(report, updates):
    """Fix 1: the HydroVu Level TROLL (VZ/VSZ) bricks, every timestamp 4 hours later; nothing else changes except the depth label.

    The values are taken from the stored brick, not from the feed's output: the feed also thins the 1-minute streams of L8/L9/M6/U3 to one
    reading an hour on the belief that the rest are interpolated, which the raw data do not support (see WITHDRAWN_INTERP below).
    """
    nb = neighbours()
    shift = dt.timedelta(hours=4)
    report += ["## HydroVu Level TROLL bricks, timestamps 4 hours later (fix 1)", "",
               "| replaces | new brick | rows | first reading | last reading | depth relabelled |", "|---|---|---|---|---|---|"]
    for bid in SHIFT_BRICKS:
        st, cols, otimes, ovals = load_stored(bid)
        zone = next(c["value"]["string_value"] for c in st["array_context"] if c["value_type"]["oterm_ref"] == "ME:0000011" and c["value"]["string_value"] in ("VZ", "VSZ"))
        loc = next(c["value"]["object_ref"] for c in st["array_context"] if c["value_type"]["oterm_ref"] == "ME:0000228")
        times = [t + shift for t in otimes]
        fam = nb[bid][0]
        for oid, (f2, l2, z2, a, b, name2) in nb.items():  # the shifted brick must not run into a neighbouring brick of the same instrument
            if oid != bid and (f2, l2, z2) == (fam, loc, zone) and not (b < times[0] or a > times[-1]):
                raise ValueError(f"{bid}: shifted readings overlap {name2}")
        defs = {c: var_def(t) for c, t in zip(cols, st["typed_values"])}
        why = []
        relabel = OLD_DEPTH in cols
        if relabel:
            tst, tcols, _, _ = load_stored("Brick0002010")
            cols = [NEW_DEPTH if c == OLD_DEPTH else c for c in cols]
            ovals[NEW_DEPTH] = ovals.pop(OLD_DEPTH)
            defs[NEW_DEPTH] = var_def(tst["typed_values"][tcols.index(NEW_DEPTH)])
            why.append("the depth variable is relabelled from 'water surface to instrument' to 'ground surface to water surface': the HydroVu value is the depth to "
                       "water below ground surface: it falls as the water pressure above the sensor rises, and the two add up to about 13 ft, the sensor's depth below ground "
                       "(12.5 ft nominal for VSZ; below top of casing it would be 2.6 to 3.0 ft more), and its values match the manual depths to water below ground")
        why.append("every timestamp is 4 hours later (HydroVu reported these Level TROLL readings 4 hours early, as it did the Aqua TROLL readings of the same wells; "
                   "checked against the manually downloaded logs); no value changed")
        new = assemble(st, next_name(st["name"], times), redate(st["description"], times),
                       [f"Replaces {st['name']} ({bid}): " + "; ".join(why)],
                       (times, [{c: ovals[c][k] for c in cols} for k in range(len(times))]), cols, defs)
        ab.write_brick(new)
        updates.append((st["name"], new["name"]))
        report.append(f"| {bid} {st['name'].replace('.hndarray', '')} | {new['name'].replace('.hndarray', '')} | {len(times)} | {iso(times[0])[:16]} | {iso(times[-1])[:16]} | {'yes' if relabel else 'no'} |")
    report += ["", "Fix 2 (interpolated values at L8, L9, M6, U3) is withdrawn (user, 2026-11-19): the API's minute series there is not an interpolation of the "
               "instrument's log (compared with the L8-SZ2 manual log of 2025-09-10 it scatters about the logged values, and it is a straight line on only 18 of about "
               "4,700 instrument-days), so the 19 Aqua TROLL bricks listed for it stay as loaded.", ""]


def build_ws3_wind(report, updates):
    report += ["## WS3 bricks with the dead anemometer (fix 5)", "", "| replaces | new brick | rows | wind speed / gust speed |", "|---|---|---|---|"]
    for bid in WS3_WIND_BRICKS:
        st, cols, times, vals = load_stored(bid)
        wind = [c for c in cols if c in ("wind_speed_mile_per_hour", "gust_speed_mile_per_hour")]
        if len(wind) != 2:
            raise ValueError(f"{bid}: wind columns {wind}")
        nulled = nonzero = 0
        for c in wind:
            for i, t in enumerate(times):
                if t > WS3_DEAD and vals[c][i] is not None:
                    nonzero += vals[c][i] != 0
                    vals[c][i] = None
                    nulled += 1
        if nonzero:
            raise ValueError(f"{bid}: {nonzero} nonzero wind values after {WS3_DEAD}")
        keep = [c for c in cols if any(x is not None for x in vals[c])]
        dropped = [c for c in cols if c not in keep]
        defs = {c: var_def(t) for c, t in zip(cols, st["typed_values"])}
        rows = [{c: vals[c][i] for c in keep} for i in range(len(times))]
        new = assemble(st, next_name(st["name"]), st["description"],
                       [f"Replaces {st['name']} ({bid}): the WS3 anemometer's last real reading was at 2025-03-26 18:30 (only zeros since), so wind speed and gust speed are blank "
                        "after that reading" + (" and are not variables of this brick" if dropped else "") + ". Wind direction is unchanged"],
                       (times, rows), keep, defs)
        ab.write_brick(new)
        updates.append((st["name"], new["name"]))
        report.append(f"| {bid} {st['name'].replace('.hndarray', '')} | {new['name'].replace('.hndarray', '')} | {len(times)} | {nulled} zero values blanked"
                      + (f"; variables removed: {', '.join(dropped)}" if dropped else "") + " |")
    report.append("")


TDS_OLD = "concentration_phase_solid_physiochemical_state_dissolved_parts_per_trillion"
COND = "conductivity_microsiemen_per_centimeter"
COND_FLOOR = 0.1  # uS/cm; the sensor's floor reading is 0.05 to 0.07 and only 172 of 1.09 million readings lie between 0.1 and 5
COND_DERIVED = ["specific_conductivity_microsiemen_per_centimeter", TDS_OLD, "concentration_phase_solid_physiochemical_state_dissolved_milligram_per_liter",
                "salinity_practical_salinity_unit"]


def blank_floor(cols, vals):
    """Blank conductivity and the values the instrument computes from it where conductivity is at the sensor's floor (user, 2026-11-19)."""
    if COND not in cols:
        return 0, None
    hit = [k for k, v in enumerate(vals[COND]) if v is not None and v < COND_FLOOR]
    for c in [COND] + [c for c in COND_DERIVED if c in cols]:
        for k in hit:
            vals[c][k] = None
    note = None
    if hit:
        note = (f"conductivity is blank in {len(hit)} readings where the sensor reported its floor value (below {COND_FLOOR} uS/cm, not a reading of the water; many of "
                "these periods coincide with rapid rises of the water level), together with the values the instrument computes from it (specific conductivity, total "
                "dissolved solids, salinity); the other sensors are unchanged")
    return len(hit), note


def build_cond_floor(report, updates):
    """Bricks with floor conductivity readings that are not otherwise replaced in this update."""
    floor = json.loads((SCRATCH / "cond_floor.json").read_text())
    tds = {k for k, v in json.loads((SCRATCH / "tds_check.json").read_text()).items() if v == "parts_per_trillion"}
    ids = sorted(k for k in floor if k not in tds)
    report += ["## Conductivity at the sensor floor, bricks not otherwise replaced", "", "| replaces | new brick | rows | readings blanked | variables removed |", "|---|---|---|---|---|"]
    for bid in ids:
        st, cols, times, vals = load_stored(bid)
        n, note = blank_floor(cols, vals)
        if n != floor[bid]:
            raise ValueError(f"{bid}: {n} floor readings, expected {floor[bid]}")
        keep = [c for c in cols if any(x is not None for x in vals[c])]
        rows = [{c: vals[c][k] for c in keep} for k in range(len(times))]
        live = [k for k, r in enumerate(rows) if any(v is not None for v in r.values())]
        if len(live) != len(times):
            raise ValueError(f"{bid}: {len(times) - len(live)} rows would be empty")
        defs = {c: var_def(t) for c, t in zip(cols, st["typed_values"])}
        new = assemble(st, next_name(st["name"]), st["description"], [f"Replaces {st['name']} ({bid}): {note}"], (times, rows), keep, defs)
        ab.write_brick(new)
        updates.append((st["name"], new["name"]))
        report.append(f"| {bid} {st['name'].replace('.hndarray', '')} | {new['name'].replace('.hndarray', '')} | {len(times)} | {n} | {', '.join(c for c in cols if c not in keep) or 'none'} |")
    report.append("")


def build_tds_unit(report, updates):
    """Total dissolved solids: the instrument's 'ppt' is parts per thousand (UO:0000168), loaded as parts per trillion (UO:0000171)."""
    ids = sorted(k for k, v in json.loads((SCRATCH / "tds_check.json").read_text()).items() if v == "parts_per_trillion")
    replaced_here = set(SHIFT_BRICKS + WS3_WIND_BRICKS)
    if len(ids) != 109 or replaced_here & set(ids):
        raise ValueError(f"TDS bricks: {len(ids)}")
    report += ["## Total dissolved solids unit (109 bricks)", "",
               "The unit term changes from parts per trillion to parts per thousand; no value changes. In every brick TDS divided by specific conductivity (uS/cm) is 0.00065, "
               "the instruments' factor of 0.65 mg/L per uS/cm expressed in g/L.", "", "| replaces | new brick | rows | TDS / specific conductivity |", "|---|---|---|---|"]
    floor = json.loads((SCRATCH / "cond_floor.json").read_text())
    total_floor = 0
    for bid in ids:
        st, cols, times, vals = load_stored(bid)
        i = cols.index(TDS_OLD)
        unit = st["typed_values"][i].get("value_units", {})
        if unit.get("oterm_ref") != "UO:0000171":
            raise ValueError(f"{bid}: TDS unit is {unit}")
        sc = next((c for c in cols if c.startswith("specific_conductivity")), None)
        ratios = sorted(a / b for a, b in zip(vals[TDS_OLD], vals[sc]) if a is not None and b is not None and b > 5) if sc else []
        med = ratios[len(ratios) // 2] if ratios else None
        if med is not None and abs(med - 0.00065) > 2e-5:
            raise ValueError(f"{bid}: TDS / specific conductivity is {med}")
        defs = {c: var_def(t) for c, t in zip(cols, st["typed_values"])}
        defs[TDS_OLD]["value_units"] = ab.term("parts per thousand")
        n_floor, note = blank_floor(cols, vals)
        if n_floor != floor.get(bid, 0):
            raise ValueError(f"{bid}: {n_floor} floor readings, expected {floor.get(bid, 0)}")
        total_floor += n_floor
        keep = [c for c in cols if any(x is not None for x in vals[c])]
        new = assemble(st, next_name(st["name"]), st["description"],
                       [f"Replaces {st['name']} ({bid}): the unit of total dissolved solids is parts per thousand (the instrument's 'ppt'), not parts per trillion"
                        + (f"; {note}" if note else "; no value changed")],
                       (times, [{c: vals[c][k] for c in keep} for k in range(len(times))]), keep, defs)
        ab.write_brick(new)
        updates.append((st["name"], new["name"]))
        report.append(f"| {bid} {st['name'].replace('.hndarray', '')} | {new['name'].replace('.hndarray', '')} | {len(times)} | {'no conductivity above 5 uS/cm to compare' if med is None else f'{med:.5f}'}"
                      + (f"; {n_floor} floor conductivity readings blanked" if n_floor else "") + (f"; variables removed: {', '.join(c for c in cols if c not in keep)}" if len(keep) != len(cols) else "") + " |")
    report += ["", f"Floor conductivity readings blanked in this group: {total_floor}", ""]


MMHG_OLD = "air_pressure_millimetres_of_mercury"


def build_inhg_unit(report, updates):
    """The 2018-19 weather bricks label a pressure in inches of mercury as millimetres of mercury."""
    inhg = template_def("air_pressure_inhg", "Brick0001359")["value_units"]
    report += ["## Air pressure unit in the 2018-19 weather bricks", "",
               "The variable labelled millimetres of mercury holds inches of mercury (it equals the brick's millibar value / 33.8639); only the unit term changes.", "",
               "| replaces | new brick | rows | largest difference from millibar / 33.8639 (inHg) |", "|---|---|---|---|"]
    for bid in ("Brick0000046", "Brick0000047"):
        st, cols, times, vals = load_stored(bid)
        i = cols.index(MMHG_OLD)
        if st["typed_values"][i]["value_units"]["oterm_ref"] != "UO:0000272":
            raise ValueError(f"{bid}: unit {st['typed_values'][i]['value_units']}")
        pairs = [(a, b) for a, b in zip(vals[MMHG_OLD], vals["air_pressure_millibar"]) if a is not None and b is not None]
        worst = max(abs(a - b / 33.8639) for a, b in pairs)
        if worst > 0.01 or len(pairs) < 1000:
            raise ValueError(f"{bid}: the pressure column is not inches of mercury (largest difference {worst})")
        defs = {c: var_def(t) for c, t in zip(cols, st["typed_values"])}
        defs[MMHG_OLD]["value_units"] = inhg
        new = assemble(st, next_name(st["name"]), st["description"],
                       [f"Replaces {st['name']} ({bid}): the unit of the first air pressure variable is inches of mercury, not millimetres of mercury (its values are "
                        "the millibar values divided by 33.8639); no value changed"],
                       (times, [{c: vals[c][k] for c in cols} for k in range(len(times))]), cols, defs)
        ab.write_brick(new)
        updates.append((st["name"], new["name"]))
        report.append(f"| {bid} {st['name'].replace('.hndarray', '')} | {new['name'].replace('.hndarray', '')} | {len(times)} | {worst:.5f} over {len(pairs)} readings |")
    report.append("")


BUILDERS_REPLACE = [build_replacements, build_ws3_wind, build_tds_unit, build_cond_floor, build_inhg_unit]


# ----------------------------------------------------------------------------
# Weather periods missing from CORAL (fix 4): LI-COR exports the old builder did not parse
# ----------------------------------------------------------------------------

RAIN = ("rainfall_inch", "rainfall_mathematical_context_cumulative_inch")
BATTERY = "charge_instrument_battery_volt"


def weather_builder(station, table, after_brick, before_brick, what, part=None):
    """part: None for everything, "rain" for the readings before the first non-rainfall value, "full" for those from it on."""
    def build(report):
        tst, tcols, _, _ = load_stored("Brick0001359")  # variable definitions of the current WS3 bricks
        defs = {c: var_def(t) for c, t in zip(tcols, tst["typed_values"])}
        ccols, crows = cm_table(table)
        # the earlier brick's clock runs a minute behind the export's (its last reading, 15:39, is the export's 15:40), so skip that reading too
        lo = load_stored(after_brick)[2][-1] + dt.timedelta(minutes=2) if after_brick else None
        hi = load_stored(before_brick)[2][0] if before_brick else None
        rows = [(t, v, src) for t, v, prov, src in crows if (lo is None or t > lo) and (hi is None or t < hi)]
        if {prov for t, v, prov, src in crows if (lo is None or t > lo) and (hi is None or t < hi)} != {"licor export"}:
            raise ValueError(f"{station}: rows not from a LI-COR export")
        if part:
            first_full = next(i for i, (_, v, _) in enumerate(rows) if any(v.get(c) is not None for c in ccols if c not in RAIN))
            rows = rows[:first_full] if part == "rain" else rows[first_full:]
        # the battery is logged twice as often as the sensors: drop the rows that hold nothing but the battery voltage
        n_all = len(rows)
        rows = [r for r in rows if any(r[1].get(c) is not None for c in ccols if c != BATTERY)]
        battery_only = n_all - len(rows)
        keep = [c for c in ccols if any(v.get(c) is not None for _, v, _ in rows)]
        if part == "rain" and set(keep) - set(RAIN):
            raise ValueError(f"{station}: rain-only part has {keep}")
        missing = [c for c in keep if c not in defs]
        if missing:
            raise ValueError(f"{station}: no variable definition for {missing}")
        sources = sorted({src for _, _, src in rows})
        times = [t for t, _, _ in rows]
        name = f"hazen_hobo_{station}_{times[0].astimezone(EASTERN):%Y%m%d}_{times[-1].astimezone(EASTERN):%Y%m%d}"
        st = dict(tst, array_context=[c for c in tst["array_context"] if c["value_type"]["oterm_ref"] != "ME:0000011"])
        for c in st["array_context"]:
            if c["value_type"]["oterm_ref"] == "ME:0000228":
                c["value"] = {"scalar_type": "object_ref", "object_ref": station}
        obj = assemble(st, f"{name}.hndarray", f"Hazen Lab HOBO Weather Station Data for {station} from {times[0].astimezone(EASTERN):%Y-%m-%d} to {times[-1].astimezone(EASTERN):%Y-%m-%d}",
                       [f"Provenance: licor_export, {', '.join(sources)}", what + (
                           f". The export logs the battery voltage every 5 minutes and the sensors every 10; the {battery_only} rows holding only the battery voltage "
                           "are not stored" if battery_only else "")],
                       (times, [v for _, v, _ in rows]), keep, defs)
        ab.write_brick(obj)
        report += [f"## {name}", "", f"- {len(rows)} rows, {iso(times[0])} to {iso(times[-1])}; source {', '.join(sources)}; battery-only rows dropped: {battery_only}", "",
                   "| variable | values | min | max |", "|---|---|---|---|"]
        for c in keep:
            vals = [v[c] for _, v, _ in rows if v.get(c) is not None]
            report.append(f"| {c} | {len(vals)} | {min(vals):g} | {max(vals):g} |")
        report.append("")
        return obj, [station], "Hazen Lab <ENIGMA:0000066>", "Field Sampling <ENIGMA:0000095>", f"{times[0].astimezone(EASTERN):%Y-%m-%d}", f"{times[-1].astimezone(EASTERN):%Y-%m-%d}"
    return build


WS3_EXPORT = ("The WS3 record before the LI-COR API data begin (hazen_hobo_WS3_20240522_20250408), from the Area 3 LI-COR export, which the earlier builder "
              "could not read (its Date column holds date and time). ")
build_ws3_rain = weather_builder("WS3", "hazen_hobo_ws3", None, "Brick0001359",
                                 WS3_EXPORT + "Until 2023-07-25 the station recorded rainfall only; this brick is that period, and the full station record "
                                 "continues in the next WS3 brick", "rain")
build_ws3_early = weather_builder("WS3", "hazen_hobo_ws3", None, "Brick0001359",
                                  WS3_EXPORT + "The station's other sensors begin 2023-07-25; the rainfall-only record before that is the preceding WS3 brick. "
                                  "Soil water content is as recorded, including negative readings", "full")
build_ws2_2019 = weather_builder("WS2", "hazen_hobo_ws2", "Brick0000046", None,
                                 "The WS2 record after hazen_hobo_WS2_20180730_20190622 ends: the 'Background Site A' columns of the Area 2 LI-COR export, which the "
                                 "earlier builder skipped. The export's earlier readings (from 2019-02-25) overlap that brick and are not repeated here")


# ----------------------------------------------------------------------------
# EFPW01 (HydroVu export) and EFPW05 (direct download), 2022-23
# ----------------------------------------------------------------------------
# Clocks checked against the WS1 weather station's barometric pressure (3-hour pressure changes, 2022-23): the EFPW HydroVu data
# reads true as UTC (EFPW01 r=0.75 at 0 h; the loaded EFPW03 bricks r=0.96 at 0 h), and the EFPW05 Win-Situ export, labelled
# Central time, is Eastern (r=0.93 at Eastern against 0.82 at Central).
EFPW01_HTM = TEAM / "2020_Cone Penetrometer Sampling/Manuscript/cpt paper data/HydroVu_EFPW01_2022-08-17_02-24-00_Export.htm"
EFPW05_XLSX = TEAM / "Hazen SSO Continuous Monitoring/AQUATROLL DATA/Download Zips/AT600 download_05092023/EFPW05_09292022_2023-05-09_10-36-20-270.xlsx"
BLOCK_GAP = dt.timedelta(days=5)  # the continuous-monitoring builder starts a new brick after a gap of more than 5 days
NITRATE = "concentration_molecule_from_list_nitrate_milligram_per_liter"
EFPW01_COLS = {  # export header -> (Lakehouse column of the definition, template brick, factor)
    "pH (pH)": ("ph_ph", "Brick0001231", 1), "pH MV (mV)": ("ph_millivolt", "Brick0001231", 1), "ORP (mV)": ("redox_potential_millivolt", "Brick0001231", 1),
    "Actual Conductivity (µS/cm)": ("conductivity_microsiemen_per_centimeter", "Brick0001231", 1),
    "Specific Conductivity (µS/cm)": ("specific_conductivity_microsiemen_per_centimeter", "Brick0001231", 1),
    "Salinity (psu)": ("salinity_practical_salinity_unit", "Brick0001231", 1), "Resistivity (Ω-cm)": ("resistivity_ohm_cm", "Brick0001231", 1),
    "Density (g/cm³)": ("density_molecule_from_list_water_gram_per_cubic_centimeter", "Brick0001231", 1),
    "Total Dissolved Solids (mg/L)": ("concentration_phase_solid_physiochemical_state_dissolved_milligram_per_liter", "Brick0001231", 1),
    "NO₃⁻ as N (mg/L)": (NITRATE, "Brick0002052", 1), "Temperature (C)": ("temperature_degree_celsius", "Brick0001231", 1),
    "External Voltage (V)": ("charge_instrument_external_power_source_volt", "Brick0001231", 1), "Battery Level (%)": ("charge_instrument_battery_percent", "Brick0001231", 1),
    "Baro (psi)": ("air_pressure_pound_per_square_inch", "Brick0001231", 1), "Pressure (psi)": ("water_pressure_pound_per_square_inch", "Brick0001231", 1),
    "Depth (m)": ("depth_top_water_surface_bottom_instrument_meter", "Brick0001231", 1),
}
EFPW01_SKIP = ["NO₃⁻ mV (mV)", "Level: Depth to Water (m)", "Level: Elevation (m)"]
EFPW05_COLS = {  # (column index, header) -> (definition column, template brick, factor)
    (2, "pH (pH)"): ("ph_ph", "Brick0001231", 1), (3, "pH(mV) (mV)"): ("ph_millivolt", "Brick0001231", 1),
    (4, "Oxidation Reduction Potential (ORP) (mV)"): ("redox_potential_millivolt", "Brick0001231", 1), (5, "Temperature (C)"): ("temperature_degree_celsius", "Brick0001231", 1),
    (6, "Actual Conductivity"): ("conductivity_microsiemen_per_centimeter", "Brick0001231", 1), (7, "Specific Conductivity"): ("specific_conductivity_microsiemen_per_centimeter", "Brick0001231", 1),
    (8, "Salinity (PSU)"): ("salinity_practical_salinity_unit", "Brick0001231", 1), (9, "Resistivity (ohm-cm)"): ("resistivity_ohm_cm", "Brick0001231", 1),
    (10, "Water Density (g/cm3)"): ("density_molecule_from_list_water_gram_per_cubic_centimeter", "Brick0001231", 1),
    (11, "Total Dissolved Solids (ppt)"): ("concentration_phase_solid_physiochemical_state_dissolved_milligram_per_liter", "Brick0001231", 1000.0),  # parts per thousand -> mg/L
    (12, "Battery Percentage (%)"): ("charge_instrument_battery_percent", "Brick0001231", 1),
    (14, "Pressure (PSI)"): ("water_pressure_pound_per_square_inch", "Brick0001231", 1),
    (15, "Depth (ft)"): ("depth_top_water_surface_bottom_instrument_meter", "Brick0001231", 0.3048),
    (16, "Barometric Pressure (mmHg)"): ("air_pressure_millimetres_of_mercury", "Brick0002052", 1),
    (18, "Rhodamine Concentration"): ("concentration_molecule_from_list_rhodamine_b_milligram_per_liter", "Brick0001362", 0.001),  # ug/L -> mg/L
}
_DEF_CACHE = {}


def template_def(col, bid):
    if bid not in _DEF_CACHE:
        st, cols, _, _ = load_stored(bid)
        _DEF_CACHE[bid] = {c: var_def(t) for c, t in zip(cols, st["typed_values"])}
    return _DEF_CACHE[bid][col]


def efpw_brick(location, instrument, provenance, comments, times, columns, values):
    """An Aqua TROLL 600 brick in the layout of hazen_aquatroll600_EFPW02_* (values: column -> list)."""
    keep = [c for c in sorted(columns) if any(v is not None for v in values[c])]
    name = f"hazen_aquatroll600_{location}_{times[0].astimezone(EASTERN):%Y%m%d}_{times[-1].astimezone(EASTERN):%Y%m%d}"
    obj = {"name": f"{name}.hndarray",
           "description": f"Hazen Lab Aqua TROLL 600 Data for {location} from {times[0].astimezone(EASTERN):%Y-%m-%d} to {times[-1].astimezone(EASTERN):%Y-%m-%d}",
           "data_type": ab.term("physical measurement"),
           "array_context": [ctx("instrument", sval(instrument)),
                             {"value_type": ab.term("environmental sample location ID"), "value": {"scalar_type": "object_ref", "object_ref": location, "string_value": location}},
                             {"value_type": ab.term("data variables type"), "value": oterm_value("environmental measurement")},
                             comment(f"Provenance: {provenance}")] + [comment(c) for c in comments],
           "n_dimensions": 1, "dim_context": [time_dim(times)],
           "typed_values": [dict(columns[c], values={"scalar_type": "float", "float_values": values[c]}) for c in keep]}
    ab.write_brick(obj)
    return obj, name, keep


def blocks(times):
    out, start = [], 0
    for i in range(1, len(times)):
        if times[i] - times[i - 1] > BLOCK_GAP:
            out.append((start, i))
            start = i
    out.append((start, len(times)))
    return out


def build_efpw01(report):
    import re
    html = EFPW01_HTM.read_text(errors="ignore")
    rows = [[re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, flags=re.S)] for r in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.S)]
    flatrows = [c for r in rows[:12] for c in r]
    if "Location Name = EFPW01" not in flatrows or "Time shown in UTC" not in flatrows:
        raise ValueError("EFPW01 export properties")
    import unicodedata
    nf = lambda x: unicodedata.normalize("NFKC", x)  # noqa: E731  (the export mixes the micro and ohm signs with the Greek letters)
    heads = [[nf(c) for c in r] for r in rows if r and r[0] == "Date Time"]
    wanted = {nf(k): v for k, v in EFPW01_COLS.items()}
    if len(heads) != 1 or set(heads[0][1:]) != set(wanted) | {nf(k) for k in EFPW01_SKIP}:
        raise ValueError(f"EFPW01 export header {heads}")
    head = heads[0]
    data = [r for r in rows if r and re.match(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d", r[0])]
    if len(data) != 29665 or any(len(r) != len(head) for r in data):
        raise ValueError(f"EFPW01 rows {len(data)}")
    times = [dt.datetime.strptime(r[0][:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc) for r in data]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("EFPW01 times not increasing")
    cols, vals, nulled = {}, {}, 0
    for h, (col, bid, f) in wanted.items():
        j = head.index(h)
        cols[col] = template_def(col, bid)
        v = [None if r[j] == "" else float(r[j]) * f for r in data]
        if col == NITRATE:  # the builder's rule: below 0, or at or above 49,000 mg/L, is a sentinel
            nulled = sum(1 for x in v if x is not None and (x < 0 or x >= 49000))
            v = [None if x is not None and (x < 0 or x >= 49000) else x for x in v]
        vals[col] = v
    out = []
    report += ["## EFPW01 Aqua TROLL 600, HydroVu export", "", f"- {len(data)} readings in the export; nitrate sentinels blanked: {nulled}", ""]
    for a, b in blocks(times):
        t = times[a:b]
        gaps = Counter(round((y - x).total_seconds() / 60) for x, y in zip(t, t[1:]))
        obj, name, keep = efpw_brick(
            "EFPW01", "Aqua TROLL 600", f"hydrovu export, {EFPW01_HTM.name}",
            ["HydroVu export of the EFPW01 Aqua TROLL 600 (Area 3), downloaded for the 2020 cone penetrometer manuscript; the export's times are UTC and are stored as "
             "Eastern time with the offset. The timing was checked against the WS1 weather station's barometric pressure and needs no shift",
             "Nitrate is the instrument's nitrate reading in mg/L (the export header 'NO3- as N' is the instrument's label; the values are nitrate), stored as recorded. The nitrate readings drift upward over the "
             "deployment (monthly medians about 570 mg/L in August 2022, 1,200 in February 2023, 4,700 in July 2023) while conductivity stays between about 1,200 and "
             "2,200 uS/cm; from about spring 2023 they are higher than the conductivity and dissolved solids can account for and should not be relied on. Not stored: the nitrate "
             "electrode millivolts and the export's two derived level columns (depth to water and elevation, present only to February 2023)",
             f"Source: {hy.rel(EFPW01_HTM)}"],
            t, cols, {c: v[a:b] for c, v in vals.items()})
        report += [f"- {name}: {len(t)} readings, {iso(t[0])[:16]} to {iso(t[-1])[:16]}; intervals (min) {dict(gaps.most_common(3))}; {len(keep)} variables"]
        out.append((obj, ["EFPW01"], "Hazen Lab <ENIGMA:0000066>", "Field Sampling <ENIGMA:0000095>", f"{t[0].astimezone(EASTERN):%Y-%m-%d}", f"{t[-1].astimezone(EASTERN):%Y-%m-%d}"))
    report.append("")
    return out


def build_efpw05(report):
    ws = openpyxl.load_workbook(EFPW05_XLSX, data_only=True, read_only=True).worksheets[0]
    rows = [r for r in ws.iter_rows(values_only=True)]
    cells = [str(c) for r in rows[:70] for c in r if c is not None]
    if "Aqua TROLL 600 Non-Vented" not in cells or "EFPW05_09292022" not in cells:
        raise ValueError("EFPW05 log properties")
    i = next(k for k, r in enumerate(rows) if r and r[0] == "Date and Time" and r[1] != "Note")
    head = [str(c).strip() if c is not None else "" for c in rows[i]]
    for (j, h) in EFPW05_COLS:
        if not head[j].startswith(h):
            raise ValueError(f"EFPW05 column {j} is {head[j]!r}, expected {h!r}")
    data = [r for r in rows[i + 1:] if isinstance(r[0], dt.datetime) and isinstance(r[2], (int, float))]
    if len(data) != 9894:
        raise ValueError(f"EFPW05 rows {len(data)}")
    start = data[0][0].replace(tzinfo=EASTERN).astimezone(dt.timezone.utc)  # the export says Central; the clock is Eastern (see above)
    times = [start + dt.timedelta(seconds=round(float(r[1]) - float(data[0][1]))) for r in data]
    for r, t in zip(data, times):
        if abs((t.astimezone(EASTERN).replace(tzinfo=None) - r[0]).total_seconds()) > 60:
            raise ValueError(f"EFPW05 clock and elapsed time disagree at {r[0]}")
    cols, vals = {}, {}
    for (j, h), (col, bid, f) in EFPW05_COLS.items():
        cols[col] = template_def(col, bid)
        vals[col] = [None if r[j] is None else float(r[j]) * f for r in data]
    obj, name, keep = efpw_brick(
        "EFPW05", "Aqua TROLL 600 Non-Vented", f"manual download, {EFPW05_XLSX.name}",
        ["Direct download (Win-Situ) of the EFPW05 Aqua TROLL 600 log, read every 10 minutes. The export labels its times Central; compared with the WS1 weather "
         "station's barometric pressure the clock is Eastern, and the times are stored as Eastern with the offset",
         "Converted from the export's units: total dissolved solids from parts per thousand to mg/L, depth of water above the instrument from feet to meters, rhodamine "
         "from micrograms to milligrams per liter (no tracer was present; the values are at most 0.000003 mg/L). Not stored: rhodamine fluorescence (all zero) and the "
         "rhodamine sensor's temperature",
         f"Source: {hy.rel(EFPW05_XLSX)}"],
        times, cols, vals)
    gaps = Counter(round((y - x).total_seconds() / 60) for x, y in zip(times, times[1:]))
    report += ["## EFPW05 Aqua TROLL 600, direct download", "", f"- {name}: {len(times)} readings, {iso(times[0])[:16]} to {iso(times[-1])[:16]}; intervals (min) {dict(gaps.most_common(3))}; {len(keep)} variables", ""]
    return [(obj, ["EFPW05"], "Hazen Lab <ENIGMA:0000066>", "Field Sampling <ENIGMA:0000095>", f"{times[0].astimezone(EASTERN):%Y-%m-%d}", f"{times[-1].astimezone(EASTERN):%Y-%m-%d}")]


BUILDERS = [build_dp06, build_pump_log, build_ws3_rain, build_ws3_early, build_ws2_2019, build_efpw01, build_efpw05]


COMO_PATCHED = REPO / "coral_import/ontology_update_20261117_flow_rate/production/context_measurement_ontology.obo"  # adds ME:0000528 flow rate


def main() -> None:
    hy.stage_validator()
    for d in ("names", "ont"):  # validate against the patched COMO (unlink first: never write through a link)
        staged = hy.STAGED / d / "context_measurement_ontology.obo"
        staged.unlink()
        staged.write_bytes(COMO_PATCHED.read_bytes())
    ab.load_ontology_names()
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    ab.OUT = OUT
    ab.JSON_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT = (OUT / d for d in ("json", "process", "check", "reports"))
    for d in (ab.JSON_OUT, ab.PROCESS_OUT, ab.CHECK_OUT, ab.REPORT_OUT):
        d.mkdir(parents=True)
    with (LIVE / "Location.tsv").open() as h:
        locations = {r["name"] for r in csv.DictReader(h, delimiter="\t")}
    report = ["# Monitoring update 2026-11-17: build report", ""]
    rows, names = [], []
    for fn in BUILDERS:
        result = fn(report)
        for obj, locs, person, campaign, d0, d1 in (result if isinstance(result, list) else [result]):
            missing = [l for l in locs if l not in locations]
            if missing:
                raise ValueError(f"{obj['name']}: Locations not in CORAL {missing}")
            names.append(obj["name"])
            rows.append({"process": "Assay Environment <PROCESS:0000004>", "person": person, "campaign": campaign, "protocol": "null",
                         "date_start": d0, "date_end": d1, "input_objects": ", ".join(f"Location: {l}" for l in locs), "output_objects": f"Generic: {obj['name']}"})
    write_process(ab.PROCESS_OUT / f"process_assay_environment_monitoring_update_{STAMP}.tsv", rows)
    updates = []
    for fn in BUILDERS_REPLACE:
        fn(report, updates)
    write_process(ab.PROCESS_OUT / f"process_update_data_monitoring_update_{STAMP}.tsv", [{
        "process": "Update Data <PROCESS:0000053>", "person": "John-Marc Chandonia <ENIGMA:0000057>", "campaign": "Field Sampling <ENIGMA:0000095>", "protocol": "null",
        "date_start": TODAY, "date_end": TODAY, "input_objects": f"Generic: {old}", "output_objects": f"Generic: {new}"} for old, new in updates])
    new_json = [n.rsplit(".", 1)[0] + ".json" for n in names]
    rep_json = [n.rsplit(".", 1)[0] + ".json" for _, n in updates]
    proc_new = f"process_assay_environment_monitoring_update_{STAMP}.tsv"
    proc_upd = f"process_update_data_monitoring_update_{STAMP}.tsv"
    files = [f"json/{f}" for f in new_json + rep_json] + [f"process/{proc_new}", f"process/{proc_upd}"]
    missing = [f for f in files if not (OUT / f).exists()]
    if missing:
        raise FileNotFoundError(missing)
    (OUT / "files_to_import.txt").write_text("\n".join(files) + "\n")
    (OUT / "import_to_coral.py").write_text("\n".join(
        ["# Run on the CORAL hub, in order, after copying every file in files_to_import.txt to /home/coral/prod/data_import/data/ on coral-enigma.", "",
         "# New bricks and their Assay Environment processes."] + [f"toolx.upload_brick('{f}')" for f in new_json]
        + [f"toolx.upload_process('Assay Environment', '{proc_new}')", "", "# Replacement bricks and their Update Data processes."]
        + [f"toolx.upload_brick('{f}')" for f in rep_json] + [f"toolx.upload_process('Update Data', '{proc_upd}')", ""]))
    (ab.REPORT_OUT / "build_report.md").write_text("\n".join(report) + "\n")
    (ab.REPORT_OUT / "bricks.json").write_text(json.dumps(names, indent=1) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main()
