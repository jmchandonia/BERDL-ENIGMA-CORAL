#!/usr/bin/env python3
"""Build staged per-table TSVs for enigma.continuous_monitoring.

Reads HydroVu API JSON, LI-COR API JSON and (for backfills) the LI-COR CSV
exports, and applies the same cleaning as the CORAL continuous-monitoring
bricks by reusing tools/build_continuous_monitoring_coral.py from the EDR
tree:

* header normalisation and measurement labels (Java translation map);
* sentinel, implausible-value and nitrate-N -> nitrate handling;
* HydroVu sparse/partial-timestamp and extreme-temperature row dropping;
* HydroVu interpolated 1-minute streams reduced to the inferred real
  measurement phase (one phase per raw daily file, as in the bricks).

Unlike the bricks, API data is always used (no manual-data precedence), and
the July 2026 corrections are applied here instead of after the fact:

* HydroVu SSO Aqua TROLL (SZ1/SZ2/SZ3) timestamps are shifted by +4 h;
* their depth channel is labelled ground surface -> water surface;
* value ranges listed in corrections.json (e.g. the dead WS3 anemometer)
  are nulled.

Output is one TSV per location/zone table, with the brick column names from
column_map.json, plus a manifest.json describing the run.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import cm_common as cm

SSO_SHIFT = timedelta(hours=4)
MISLABELED_DEPTH = "depth, top=water surface, bottom=instrument, ft"
CORRECTED_DEPTH = "depth, top=ground surface, bottom=water surface, ft"
HYDROVU_SOURCES = {"hydrovu_regular", "hydrovu_vz", "hydrovu_archive"}
PROVENANCE = {
    "hydrovu_regular": "hydrovu api",
    "hydrovu_vz": "hydrovu api",
    "hydrovu_archive": "hydrovu api",
    "licor_api": "licor api",
    "licor_root": "licor export",
}
STREAM_MAX_MEDIAN_GAP = timedelta(minutes=2)
# Candidate real-reading intervals (minutes) for interpolated 1-minute streams.
READING_INTERVALS = (60, 30, 20, 15, 10, 5)
KINK_FACTOR = 10.0          # a slope break is >= 10x the median |second difference|
MIN_SCHEDULE_SCORE = 0.3    # band coverage above chance needed to accept a schedule
MIN_SCHEDULE_KINKS = 3
MIN_SCHEDULE_RECURRENCE = 0.6  # share of a window's reading slots that must show a break
SCHEDULE_WINDOW = 6 * 3600  # seconds; schedules are inferred per 6-hour window of a daily file

TIMESTAMP_NOTE = (
    "HydroVu API timestamps for the SSO wells are 4 hours early (the instrument "
    "clock is fixed at UTC-4 and HydroVu treats it as UTC); 4 hours were added to "
    "every timestamp. Verified against manually downloaded VuSitu logs for both "
    "Aqua TROLL 600 (SZ) and Level TROLL 500 (VZ/VSZ) channels."
)
CADENCE_NOTE = (
    "HydroVu returns this instrument as a 1-minute series interpolated between "
    "real readings; only the timestamps of the real readings (interval and minute "
    "detected from slope breaks, typically hourly) are kept."
)
NITRATE_NOTE = (
    "Nitrate values are reported as measured, in mg/L nitrate (NO3-). The "
    "instrument header reads 'Nitrate (NO3- - N) (mg/L)', but the values are "
    "nitrate, so no nitrate-N conversion is applied. Raw readings below 0 or at "
    "or above 49,000 mg/L are instrument sentinels and are null."
)
BORROWED_NOTE = (
    "On some days this instrument's values changed too little to detect its "
    "reading times; hourly values were then kept at the reading minute of "
    "another instrument in the same well."
)
DEPTH_NOTE = (
    "The HydroVu depth channel for SSO Aqua TROLL 600 sondes is depth to water "
    "below ground surface; it is labelled top=ground surface, bottom=water surface."
)


# Site names used in LI-COR export headers ("Background Site A" before "Background A").
EXPORT_SITES = [("Background Site A", "WS2"), ("Background A", "WS2"), ("Area 2", "WS1"), ("Area 3", "WS3")]
EXPORT_TIME_FORMATS = ("%m/%d/%y %H:%M:%S %z", "%m/%d/%Y %H:%M:%S %z", "%m/%d/%y %H:%M:%S", "%m/%d/%Y %H:%M:%S")


def breaks(second: list[tuple[int, float]]) -> list[int]:
    """Epoch seconds whose |second difference| is a slope break (>= KINK_FACTOR x median)."""
    nonzero = sorted(x for _, x in second if x > 0)
    if len(nonzero) < 20:
        return []
    threshold = KINK_FACTOR * statistics.median(nonzero)
    return [t for t, x in second if x > threshold]


def strong_kinks(readings: list[tuple[int, float | None]]) -> list[int]:
    """Epoch seconds where the slope of an interpolated series breaks."""
    second = []
    for (_, a), (t, c), (_, d) in zip(readings, readings[1:], readings[2:]):
        if a is not None and c is not None and d is not None:
            second.append((t, abs(d - 2 * c + a)))
    return breaks(second)


def schedule_from_counts(counts: Counter, window_minutes: int = SCHEDULE_WINDOW // 60) -> dict | None:
    """Infer (interval, minute) of real readings from slope-break counts per epoch minute.

    Real readings show up as slope breaks in every changing channel at the
    same minute (often split over two adjacent minutes).  For each candidate
    interval P, the best band of two adjacent minutes is scored by the share of
    slope breaks it holds minus the share expected by chance (2/P).  A
    candidate also has to recur: at least MIN_SCHEDULE_RECURRENCE of the
    window's P-minute slots must hold a break in the band, so a handful of
    noise breaks cannot produce a short interval.  The best-scoring candidate
    wins.  Returns None when the breaks are too few or show no schedule (for
    example genuine 1-minute data or a noisy channel).
    """
    total = sum(counts.values())
    if total < MIN_SCHEDULE_KINKS:
        return None
    best = None
    for interval in READING_INTERVALS:
        by_minute = Counter()
        for minute, n in counts.items():
            by_minute[minute % interval] += n
        slots_needed = MIN_SCHEDULE_RECURRENCE * window_minutes / interval
        for start in range(interval):
            band_minutes = {start, (start + 1) % interval}
            band = sum(by_minute[m] for m in band_minutes)
            score = band / total - 2 / interval
            if best is not None and score <= best[0]:
                continue
            slots = {m // interval for m in counts if m % interval in band_minutes}
            if len(slots) < slots_needed:
                continue
            minute = start if by_minute[start] >= by_minute[(start + 1) % interval] else (start + 1) % interval
            best = (score, interval, minute)
    if best is None or best[0] < MIN_SCHEDULE_SCORE:
        return None
    return {"interval": best[1], "minute": best[2], "score": round(best[0], 3), "kinks": total}


def schedule_fit(counts: Counter, schedule: dict) -> float | None:
    """Score of an existing schedule on new slope-break counts (None if too few breaks)."""
    total = sum(counts.values())
    if total < MIN_SCHEDULE_KINKS:
        return None
    interval, minute = schedule["interval"], schedule["minute"]
    band = sum(n for m, n in counts.items() if min((m - minute) % interval, (minute - m) % interval) <= 1)
    return band / total - 3 / interval


def reading_schedule(params: list[list[tuple[int, float | None]]]) -> dict | None:
    """Whole-series schedule (used by the analysis scripts)."""
    counts: Counter = Counter()
    for readings in params:
        counts.update(t // 60 for t in strong_kinks(readings))
    span = (max(counts) - min(counts) + 1) if counts else 0
    return schedule_from_counts(counts, max(span, 60))


def same_schedule(a: dict, b: dict, tolerance: int = 2) -> bool:
    if a["interval"] != b["interval"]:
        return False
    d = abs(a["minute"] - b["minute"]) % a["interval"]
    return min(d, a["interval"] - d) <= tolerance


def parse_export_timestamp(raw: str) -> datetime | None:
    for fmt in EXPORT_TIME_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt)
        except ValueError:
            pass
    return None


def log(msg: str) -> None:
    print(msg, flush=True)


class Builder:
    def __init__(self, holdback: timedelta | None, now: datetime):
        self.b = cm.builder_module()
        self.b.START_AFTER = None
        self.b.CUTOFF = datetime(9999, 1, 1, tzinfo=timezone.utc)
        # The Aqua TROLL nitrate channel reports nitrate, not nitrate-N (the
        # "NO3- - N" header is wrong; user, 2026-10-19), so do not apply the
        # CORAL builder's nitrate-N -> nitrate factor.  Its sentinel nulling
        # (below 0, or at or above 49,000 mg/L) still applies.
        self.b.NITRATE_NO3_PER_N = 1.0
        self.translation_map = self.b.parse_translation_map()
        self.hydrovu_lookup = self.b.load_hydrovu_lookup()
        self.column_map = cm.load_column_map()["measurements"]
        corrections = cm.load_corrections()
        self.null_ranges = corrections.get("null_ranges", [])
        self.holdback_cutoff = now - holdback if holdback is not None else None
        # (table, timestamp) -> label -> (priority, path, value, source kind)
        self.cells: dict[tuple[str, datetime], dict[str, tuple[int, str, float | None, str]]] = defaultdict(dict)
        self.table_info: dict[str, dict[str, object]] = {}
        self.unknown_labels: dict[str, set[str]] = defaultdict(set)
        self.files_used: list[str] = []
        self.files_deferred: list[str] = []
        self.stats: dict[str, int] = defaultdict(int)
        # "location|instrument" -> dated history of real-reading schedules,
        # oldest first; each entry applies from its "since" epoch on.
        self.schedules: dict[str, list[dict]] = {}
        self.schedule_changes: list[dict] = []
        self.stream_instruments: set[tuple[str, str]] = set()
        self.borrowed_instruments: set[tuple[str, str]] = set()

    # ---------------------------------------------------------------- records
    def _accept(self, rec, source_kind: str) -> None:
        b = self.b
        zone = b.measurement_comment_value(rec.measurement)
        label = b.measurement_output_label(rec.measurement, zone)
        timestamp = rec.timestamp
        shifted = relabeled = False
        if source_kind in HYDROVU_SOURCES and rec.location.startswith("SSO-"):
            timestamp = b.fixed_offset_local(timestamp.astimezone(timezone.utc) + SSO_SHIFT)
            shifted = True
            if label == MISLABELED_DEPTH:
                label = CORRECTED_DEPTH
                relabeled = True
        if self.holdback_cutoff is not None and timestamp > self.holdback_cutoff:
            self.stats["values_held_back"] += 1
            return
        table = cm.table_name(rec.family, rec.location, zone)
        info = self.table_info.setdefault(
            table,
            {"family": rec.family, "location": rec.location, "zone": zone, "provenance": set(), "shifted": False, "relabeled": False, "labels": set()},
        )
        info["provenance"].add(PROVENANCE[source_kind])
        info["shifted"] = info["shifted"] or shifted
        info["relabeled"] = info["relabeled"] or relabeled
        info["labels"].add(label)
        value = rec.value
        for rng in self.null_ranges:
            if rng["table"] == table and label in rng["labels"] and rng["start"] <= timestamp.date().isoformat() <= rng["end"]:
                if value not in (None, 0.0):
                    self.stats["nonzero_values_nulled_by_corrections"] += 1
                value = None
                self.stats["values_nulled_by_corrections"] += 1
        cell = self.cells[(table, timestamp)]
        current = cell.get(label)
        candidate = (rec.source_priority, rec.source_path, value, source_kind)
        if current is None or candidate[:2] < current[:2]:
            cell[label] = candidate

    def _add_records(self, records: list, source_kind: str) -> None:
        for rec in records:
            self._accept(rec, source_kind)
        self.stats[f"records_{source_kind}"] += len(records)

    # ---------------------------------------------------------------- HydroVu
    def add_hydrovu_file(self, path: Path, complete: bool) -> bool:
        """Parse one raw HydroVu daily JSON file; returns False if deferred."""
        b = self.b
        info = b.hydrovu_source_info(path)
        if info is None:
            return True
        source_kind, location = info
        obj = json.loads(path.read_text())
        epochs = sorted({r["timestamp"] for p in obj.get("parameters", []) for r in p.get("readings", []) if r.get("timestamp") is not None})
        stream = len(epochs) > 2 and timedelta(seconds=statistics.median(y - x for x, y in zip(epochs, epochs[1:]))) <= STREAM_MAX_MEDIAN_GAP
        windows: dict[str, list] = {}
        day_start = epochs[0] - epochs[0] % 3600 if epochs else 0
        if stream:
            windows = self._stream_schedules(location, obj, day_start, epochs[-1], complete)
            if windows is None:
                self.files_deferred.append(str(path))
                return False
        phase = int(b.infer_hydrovu_phase(obj)["selected_phase"])
        sparse = b.infer_sparse_hydrovu_timestamps(obj)
        records: list = []
        for param in obj.get("parameters", []):
            header = b.hydrovu_column_header(param, self.hydrovu_lookup)
            measurement = b.canonical_from_header(header, self.translation_map)
            instrument = b.measurement_comment_value(measurement or "")
            per_window = windows.get(b.hydrovu_parameter_instrument(str(param.get("parameterId", "")))) if stream else None
            for reading in param.get("readings", []):
                ts = reading.get("timestamp")
                if ts is None:
                    continue
                timestamp = b.utc_epoch_to_eastern(ts)
                if (instrument, timestamp) in sparse:
                    self.stats["hydrovu_sparse_values_dropped"] += 1
                    continue
                if per_window is not None:
                    schedule = per_window[min((ts - day_start) // SCHEDULE_WINDOW, len(per_window) - 1)]
                    if schedule is None:
                        continue  # trailing window of a partial day without a usable schedule yet
                    if schedule == "fallback":
                        if not b.should_keep_hydrovu_timestamp(timestamp, phase):
                            continue
                    elif schedule[0] > 1 and (ts // 60) % schedule[0] != schedule[1]:
                        continue
                elif not b.should_keep_hydrovu_timestamp(timestamp, phase):
                    continue
                b.add_record(records, location, timestamp, measurement, b.parse_float(reading.get("value")), source_kind, str(path), header)
        self._add_records(records, source_kind)
        self.files_used.append(str(path))
        for instrument in windows:
            if instrument:
                self.stream_instruments.add((location, instrument))
        return True

    def schedule_at(self, key: str, t: int) -> dict | None:
        current = None
        for entry in self.schedules.get(key, []):
            if entry["since"] <= t:
                current = entry
        return current

    def set_schedule(self, key: str, t: int, found: dict) -> dict:
        history = [e for e in self.schedules.get(key, []) if e["since"] < t]
        entry = {**found, "since": t}
        self.schedules[key] = history + [entry]
        return entry

    def _stream_schedules(self, location: str, obj: dict, day_start: int, last: int, complete: bool) -> dict[str, list] | None:
        """Per-instrument reading schedule for each SCHEDULE_WINDOW of a daily file.

        Each window entry is (interval, minute), "fallback" (use the bricks'
        15-minute phase rule) or None (skip: trailing window of a partial day
        whose schedule is not yet clear).  A window that is fully present gives
        the same answer whether it is seen in a partial or a full-day fetch,
        so rows appended from partial days are never contradicted later.
        Returns None if the file should wait for more data.
        """
        b = self.b
        n_windows = max(1, (last - day_start) // SCHEDULE_WINDOW + 1)
        # Slope breaks per instrument and window; the threshold is computed within
        # each window so a complete window gives the same breaks in any fetch.
        kinks: dict[str, list[Counter]] = {}
        for param in obj.get("parameters", []):
            instrument = b.hydrovu_parameter_instrument(str(param.get("parameterId", "")))
            per_window = kinks.setdefault(instrument, [Counter() for _ in range(n_windows)])
            readings = [(r["timestamp"], b.parse_float(r.get("value"))) for r in param.get("readings", []) if r.get("timestamp") is not None]
            by_window: dict[int, list] = defaultdict(list)
            for (_, a), (t, c), (_, d) in zip(readings, readings[1:], readings[2:]):
                if a is not None and c is not None and d is not None:
                    by_window[min((t - day_start) // SCHEDULE_WINDOW, n_windows - 1)].append((t, abs(d - 2 * c + a)))
            for w, second in by_window.items():
                per_window[w].update(t // 60 for t in breaks(second))
        result: dict[str, list] = {}
        undetected: list[tuple[str, int]] = []
        for instrument, window_kinks in kinks.items():
            key = f"{location}|{instrument}"
            entries: list = []
            for w in range(n_windows):
                lo = day_start // 60 + w * SCHEDULE_WINDOW // 60
                current = self.schedule_at(key, lo * 60)
                window_counts = window_kinks[w]
                found = schedule_from_counts(window_counts)
                window_complete = complete or day_start + (w + 1) * SCHEDULE_WINDOW <= last
                fit = schedule_fit(window_counts, current) if current is not None else None
                if current is not None and (found is None or same_schedule(found, current) or (fit is not None and fit >= MIN_SCHEDULE_SCORE)):
                    use = current  # the saved schedule still explains this window
                elif found is not None and window_complete:
                    if current is not None:
                        self.schedule_changes.append({"instrument": key, "window_start": lo * 60, "from": current, "to": found})
                    use = self.set_schedule(key, lo * 60, found)
                elif found is not None:
                    use = "skip"  # partial window contradicting (or without) a saved schedule
                elif current is not None:
                    use = current
                else:
                    use = None
                if use is None:
                    undetected.append((instrument, w))
                entries.append(None if use == "skip" else use)
            result[instrument] = entries
        for instrument, w in undetected:
            # Channels that barely change (e.g. Level TROLL pressure) show no slope
            # breaks; use the clearest hourly schedule of another instrument in the well.
            donors = [entries[w] for other, entries in result.items() if other != instrument and isinstance(entries[w], dict)]
            window_start = day_start + w * SCHEDULE_WINDOW
            donors += [
                d for k in self.schedules
                if k.startswith(f"{location}|") and k != f"{location}|{instrument}"
                and (d := self.schedule_at(k, window_start)) is not None
            ]
            donors = sorted((d for d in donors if d["interval"] == 60), key=lambda d: -d["score"])
            if donors:
                result[instrument][w] = donors[0]
                self.borrowed_instruments.add((location, instrument))
                self.stats["hydrovu_schedule_windows_borrowed"] += 1
            elif complete:
                result[instrument][w] = "fallback"
                self.stats["hydrovu_schedule_windows_fallback"] += 1
            # else: stays None (skipped until more data arrives)
        return {
            instrument: [e if e in (None, "fallback") else (e["interval"], e["minute"]) for e in entries]
            for instrument, entries in result.items()
        }

    # ---------------------------------------------------------------- LI-COR
    def add_licor_api_file(self, path: Path) -> bool:
        b = self.b
        obj = json.loads(path.read_text())
        rows_by_ts: dict[datetime, dict[str, float | None]] = defaultdict(dict)
        for entry in obj.get("data", []):
            timestamp = b.utc_string_to_eastern(str(entry.get("timestamp", "")))
            if timestamp is None:
                continue
            header = f"{str(entry.get('sensor_measurement_type', '')).strip()}, {str(entry.get('unit', '')).strip()}"
            rows_by_ts[timestamp][header] = b.parse_float(entry.get("value"))
        records: list = []
        for timestamp, row_map in rows_by_ts.items():
            non_empty = [h for h, v in row_map.items() if v is not None]
            if len(non_empty) == 1 and non_empty[0] == "Battery, V":
                continue
            for header, value in row_map.items():
                measurement = b.canonical_from_header(header, self.translation_map)
                b.add_record(records, "WS3", timestamp, measurement, value, "licor_api", str(path), header)
        self._add_records(records, "licor_api")
        self.files_used.append(str(path))
        return True

    def add_licor_exports(self) -> None:
        """Parse every LI-COR CSV export in licor/.

        The CORAL builder's parse_licor_root only reads files with separate
        Date and Time columns and site names "Area 2"/"Background A", which
        silently skips the Area 3 export (date and time in one column) and
        the "Background Site A" columns.  This parser handles both layouts.
        """
        b = self.b
        for path in sorted((cm.FAM_ROOT / "licor").glob("*.csv")):
            if "DO NOT USE" in path.name.upper():
                continue
            records: list = []
            with path.open(newline="", errors="ignore") as handle:
                reader = csv.reader(handle)
                headers = next((row for row in reader if row and row[0] == "Line#"), None)
                if headers is None:
                    continue
                has_time = len(headers) > 2 and headers[2] == "Time"
                first = 3 if has_time else 2
                columns = []
                for idx, header in enumerate(headers[first:], start=first):
                    for area, location in EXPORT_SITES:
                        if f",{area}" in header or f", {area}" in header:
                            measurement = b.licor_measurement_from_header(header, area, self.translation_map)
                            if measurement:
                                columns.append((idx, location, measurement, header))
                            break
                for row in reader:
                    if len(row) <= first or not row[1]:
                        continue
                    raw_ts = f"{row[1]} {row[2]}" if has_time else row[1]
                    timestamp = parse_export_timestamp(raw_ts)
                    if timestamp is None:
                        self.stats["licor_export_unparsed_rows"] += 1
                        continue
                    timestamp = b.local_naive_from_source(timestamp, None)
                    for idx, location, measurement, header in columns:
                        value = b.parse_float(row[idx]) if idx < len(row) else None
                        b.add_record(records, location, timestamp, measurement, value, "licor_root", str(path), header)
            self._add_records(records, "licor_root")
            self.files_used.append(str(path))

    # ---------------------------------------------------------------- output
    def table_metadata(self, table: str) -> dict[str, object]:
        b = self.b
        info = self.table_info[table]
        family, location, zone = info["family"], info["location"], info["zone"]
        notes = []
        if family == "aquatroll600" and any("molecule from list=nitrate" in label for label in info["labels"]):
            notes.append(NITRATE_NOTE)
        if info["shifted"]:
            notes.append(TIMESTAMP_NOTE)
        if info["relabeled"]:
            notes.append(DEPTH_NOTE)
        if (location, zone) in self.stream_instruments:
            notes.append(CADENCE_NOTE)
        if (location, zone) in self.borrowed_instruments:
            notes.append(BORROWED_NOTE)
        for rng in self.null_ranges:
            if rng["table"] == table:
                notes.append(f"{', '.join(rng['labels'])} nulled from {rng['start']} to {rng['end']}: {rng['reason']}")
        depth_ft = None
        if zone:
            key = location[4:] if location.startswith("SSO-") else location
            depth_ft = b.DEPLOYMENT_DEPTH_BGS_FT.get(key, {}).get(zone)
        instrument = {"aquatroll600": "Aqua TROLL 600", "leveltroll500": "Level TROLL 500", "weather": "HOBO Weather Station"}[family]
        return {
            "table_name": table,
            "sdt_location_name": location,
            "instrument": instrument,
            "instrument_zone": zone or None,
            "deployment_depth_m": round(b.feet_to_meter(depth_ft), 5) if depth_ft is not None else None,
            "description": f"Hazen Lab {instrument} data for {location}{' ' + zone if zone else ''} (API-derived, appended daily)",
            "notes": notes,
            "provenance": sorted(info["provenance"]),
        }

    def write(self, out_dir: Path) -> dict[str, object]:
        out_dir.mkdir(parents=True, exist_ok=True)
        by_table: dict[str, list[datetime]] = defaultdict(list)
        for table, timestamp in self.cells:
            by_table[table].append(timestamp)
        manifest: dict[str, object] = {"tables": {}, "unknown_labels": {}, "stats": dict(self.stats)}
        for table in sorted(by_table):
            labels = sorted({label for ts in by_table[table] for label in self.cells[(table, ts)]})
            unknown = [label for label in labels if label not in self.column_map]
            if unknown:
                manifest["unknown_labels"][table] = unknown
                log(f"HOLDING BACK {table}: labels not in column_map.json: {unknown}")
                continue
            columns = [self.column_map[label]["column"] for label in labels]
            location = self.table_info[table]["location"]
            path = out_dir / f"{table}.tsv"
            rows = 0
            written: list[datetime] = []
            with path.open("w", newline="") as handle:
                writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
                writer.writerow([cm.TIMESTAMP_COLUMN, *columns, cm.LOCATION_COLUMN, cm.PROVENANCE_COLUMN, cm.SOURCE_COLUMN])
                for timestamp in sorted(by_table[table]):
                    cell = self.cells[(table, timestamp)]
                    values = [cell[label][2] if label in cell else None for label in labels]
                    if all(v is None for v in values):
                        continue
                    sources = sorted({Path(cell[label][1]).name for label in cell})
                    provenance = sorted({PROVENANCE[cell[label][3]] for label in cell})
                    writer.writerow(
                        [
                            self.b.iso_with_offset(timestamp),
                            *["" if v is None else f"{v:.10g}" for v in values],
                            location,
                            "; ".join(provenance),
                            "; ".join(sources),
                        ]
                    )
                    rows += 1
                    written.append(timestamp)
            if not written:
                path.unlink()
                continue
            first, last = written[0], written[-1]
            manifest["tables"][table] = {
                "tsv": path.name,
                "rows": rows,
                "first_timestamp": self.b.iso_with_offset(first),
                "last_timestamp": self.b.iso_with_offset(last),
                "columns": {self.column_map[label]["column"]: label for label in labels},
                "metadata": self.table_metadata(table),
            }
        manifest["files_used"] = len(self.files_used)
        manifest["files_deferred"] = self.files_deferred
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=sorted) + "\n")
        (out_dir / "files_used.txt").write_text("".join(f"{p}\n" for p in self.files_used))
        return manifest



def load_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default


def file_signature(path: Path) -> list[float]:
    st = path.stat()
    return [st.st_mtime, st.st_size]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mode", choices=["incremental", "backfill"], required=True)
    parser.add_argument("--out", type=Path, required=True, help="staging directory for this run")
    parser.add_argument("--holdback-minutes", type=int, default=60)
    parser.add_argument("--no-state", action="store_true", help="do not read or update build_state.json")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    builder = Builder(timedelta(minutes=args.holdback_minutes) if args.holdback_minutes > 0 else None, now)
    fetch_state = load_json(cm.STATE_DIR / "fetch_state.json", {"files": {}})["files"]
    state_path = cm.STATE_DIR / "build_state.json"
    build_state = {} if args.no_state else load_json(state_path, {})
    schedule_path = cm.STATE_DIR / "reading_schedule.json"
    if not args.no_state:
        builder.schedules = load_json(schedule_path, {})
    processed: dict[str, list[float]] = {}

    hydrovu_files: list[tuple[Path, bool]] = []
    licor_files: list[Path] = []
    if args.mode == "backfill":
        for path in sorted((cm.FAM_ROOT / "hydrovu/data").rglob("*.json")):
            hydrovu_files.append((path, True))
        licor_files += sorted(p for p in (cm.FAM_ROOT / "licor/data").rglob("*.json"))
    for rel, entry in sorted(fetch_state.items()):
        path = cm.FETCH_DIR / rel
        if not path.exists():
            continue
        if args.mode == "incremental" and build_state.get(rel) == file_signature(path):
            continue
        if rel.startswith("hydrovu/"):
            hydrovu_files.append((path, bool(entry.get("complete"))))
        elif rel.startswith("licor/"):
            licor_files.append(path)

    log(f"{args.mode}: {len(hydrovu_files)} HydroVu files, {len(licor_files)} LI-COR API files")
    for i, (path, complete) in enumerate(hydrovu_files, 1):
        if path.name.endswith(("_coral.json", "_coral_a.json")):
            continue
        if builder.add_hydrovu_file(path, complete) and path.is_relative_to(cm.FETCH_DIR):
            processed[str(path.relative_to(cm.FETCH_DIR))] = file_signature(path)
        if i % 1000 == 0:
            log(f"  HydroVu {i}/{len(hydrovu_files)}")
    for path in licor_files:
        if path.name.endswith(("_coral.json", "_coral_a.json")) or not path.name[:6].isdigit():
            continue
        builder.add_licor_api_file(path)
        if path.is_relative_to(cm.FETCH_DIR):
            processed[str(path.relative_to(cm.FETCH_DIR))] = file_signature(path)
    if args.mode == "backfill":
        log("Parsing LI-COR CSV exports")
        builder.add_licor_exports()

    manifest = builder.write(args.out)
    manifest["mode"] = args.mode
    manifest["reading_schedules"] = builder.schedules
    manifest["reading_schedule_changes"] = builder.schedule_changes
    manifest["built_at"] = now.isoformat()
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2, default=sorted) + "\n")
    total = sum(t["rows"] for t in manifest["tables"].values())
    log(f"Wrote {len(manifest['tables'])} tables, {total} rows to {args.out}; deferred {len(builder.files_deferred)} 1-minute files with too little data to see their reading schedule")
    for change in builder.schedule_changes:
        log(
            f"reading schedule changed for {change['instrument']} at "
            f"{datetime.fromtimestamp(change['window_start'], timezone.utc):%Y-%m-%d %H:%M}Z (raw HydroVu time): "
            f"{change['from']['interval']}/{change['from']['minute']} -> {change['to']['interval']}/{change['to']['minute']}"
        )
    if manifest["unknown_labels"]:
        log(f"Unknown labels held back: {manifest['unknown_labels']}")
    if manifest["stats"].get("nonzero_values_nulled_by_corrections"):
        log(
            f"WARNING: {manifest['stats']['nonzero_values_nulled_by_corrections']} nonzero values fell in a "
            "corrections.json null range; a sensor may have been repaired"
        )
    if not args.no_state:
        build_state.update(processed)
        (args.out / "build_state_pending.json").write_text(json.dumps(build_state, indent=1) + "\n")
    horizon = int(now.timestamp()) - 90 * 86400
    for key, history in builder.schedules.items():
        builder.schedules[key] = [e for i, e in enumerate(history) if e["since"] >= horizon or i == len(history) - 1 or history[i + 1]["since"] > horizon]
    (args.out / "reading_schedule_pending.json").write_text(json.dumps(builder.schedules, indent=1, sort_keys=True) + "\n")
    if manifest["unknown_labels"]:
        sys.exit(3)


if __name__ == "__main__":
    main()
