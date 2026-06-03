#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from coral_metadata import prepare_coral_metadata


BRICK_RE = re.compile(r"Brick\d{7}")
OBJECT_REF_RE = re.compile(r"\[([^\]]+)\]")
VERSION_RE = re.compile(r"(?i)(?:^|[ _.\-(])v(?:ersion)?[ _.-]?(\d+)(?:\)?$|$)")
TRAILING_VERSION_RE = re.compile(r"(?i)(?:[ _.\-(]+)(?:v|version)[ _.-]?(\d+)\)?$")
TRAILING_DATE_RE = re.compile(
    r"(?:^|[ _.\-(])((?:19|20)\d{2}[-_. ]?\d{2}[-_. ]?\d{2}|\d{2}[-_. ]?\d{2}[-_. ]?\d{2})([a-z])?\)?$"
)
ANY_DATE_RE = re.compile(r"(?:19|20)\d{2}[-_. ]?\d{2}[-_. ]?\d{2}|\b\d{2}[-_. ]?\d{2}[-_. ]?\d{2}\b")
EMBEDDED_VERSION_RE = re.compile(r"(?i)^(.+?)[ _.\-(]+v(?:ersion)?[ _.-]?(\d+)[ _.\-)]+(.+)$")
DATA_EXT_RE = re.compile(r"\.(h?ndarray|csv|tsv)$", re.IGNORECASE)
HTCP_RE = re.compile(r"_HTCP_", re.IGNORECASE)
RELOADS_RE = re.compile(r"_RELOADS_", re.IGNORECASE)
RELOADS_V2_RE = re.compile(r"_RELOADS_.*_v2$", re.IGNORECASE)
SCHEMA_FIELD_RE = re.compile(
    r'StructField\("([^"]+)",\s*(\w+)\(\).*?metadata=\{"comment":\s*"((?:[^"\\]|\\.)*)"\}',
    re.DOTALL,
)
SCHEMA_SIMPLE_FIELD_RE = re.compile(r'StructField\("([^"]+)",\s*(\w+)\(\)')
TYPE_MAP = {
    "StringType": "STRING",
    "IntegerType": "INT",
    "DoubleType": "DOUBLE",
    "FloatType": "FLOAT",
    "BooleanType": "BOOLEAN",
    "LongType": "BIGINT",
    "DateType": "DATE",
    "TimestampType": "TIMESTAMP",
}
DDT_NDARRAY_TABLE_COMMENT = "Metadata for CORAL dynamic data type n-dimensional arrays"
SYS_DDT_TYPEDEF_TABLE_COMMENT = "Column definitions for CORAL dynamic data type tables"
DDT_NDARRAY_COMMENTS = {
    "ddt_ndarray_id": {
        "description": "Primary key for dynamic data type (N-dimensional array)",
        "type": "primary_key",
    },
    "ddt_ndarray_name": {
        "description": "Name of the data brick (N-dimensional array)",
        "type": "unique_key",
    },
    "ddt_ndarray_description": {
        "description": "Description of the data brick (N-dimensional array)",
    },
    "ddt_ndarray_metadata": {
        "description": "Metadata for the data brick (N-dimensional array)",
    },
    "ddt_ndarray_type_sys_oterm_id": {
        "description": "Data type for this data brick, ontology term CURIE",
        "type": "foreign_key",
        "references": "sys_oterm.sys_oterm_id",
    },
    "ddt_ndarray_type_sys_oterm_name": {
        "description": "Data type for this data brick",
    },
    "ddt_ndarray_shape": {
        "description": "Shape of the N-dimensional array, array with one integer per dimension",
        "example": "[10,10]",
    },
    "ddt_ndarray_dimension_types_sys_oterm_id": {
        "description": "Array of dimension data types, ontology term CURIEs",
        "type": "foreign_key",
        "references": "[sys_oterm.sys_oterm_id]",
    },
    "ddt_ndarray_dimension_types_sys_oterm_name": {
        "description": "Array of dimension data types",
    },
    "ddt_ndarray_dimension_variable_types_sys_oterm_id": {
        "description": "Array of dimension variable types, ontology term CURIEs",
        "type": "foreign_key",
        "references": "[sys_oterm.sys_oterm_id]",
    },
    "ddt_ndarray_dimension_variable_types_sys_oterm_name": {
        "description": "Array of dimension variable types",
    },
    "ddt_ndarray_variable_types_sys_oterm_id": {
        "description": "Array of variable types, ontology term CURIEs",
        "type": "foreign_key",
        "references": "[sys_oterm.sys_oterm_id]",
    },
    "ddt_ndarray_variable_types_sys_oterm_name": {
        "description": "Array of variable types",
    },
    "withdrawn_date": {
        "description": "Date when this dataset was withdrawn, or null if the dataset is currently valid",
    },
    "superceded_by_ddt_ndarray_id": {
        "description": "Dataset that supercedes this one, if the dataset was withdrawn and replaced, or null if the dataset is currently valid",
        "type": "foreign_key",
        "references": "ddt_ndarray.ddt_ndarray_id",
    },
}
SYS_DDT_TYPEDEF_COMMENTS = {
    "ddt_ndarray_id": {
        "description": "Key for dynamic data type (N-dimensional array)",
        "type": "foreign_key",
        "references": "ddt_ndarray.ddt_ndarray_id",
    },
    "berdl_column_name": {"description": "BERDL column name"},
    "berdl_column_data_type": {
        "description": "BERDL column data type, variable or dimension_variable",
    },
    "scalar_type": {"description": "Scalar type"},
    "foreign_key": {"description": "Foreign key reference"},
    "comment": {"description": "Column comment"},
    "unit_sys_oterm_id": {
        "description": "Unit, ontology term CURIE",
        "type": "foreign_key",
        "references": "sys_oterm.sys_oterm_id",
    },
    "unit_sys_oterm_name": {"description": "Unit"},
    "dimension_number": {
        "description": "Dimension number, starting at 1, for dimension variables",
    },
    "dimension_oterm_id": {
        "description": "Dimension data type, ontology term CURIE",
        "type": "foreign_key",
        "references": "sys_oterm.sys_oterm_id",
    },
    "dimension_oterm_name": {"description": "Dimension data type"},
    "variable_number": {
        "description": "Variable number within a dimension, numbered starting at 1",
    },
    "variable_oterm_id": {
        "description": "Dimension variable data type, ontology term CURIE",
        "type": "foreign_key",
        "references": "sys_oterm.sys_oterm_id",
    },
    "variable_oterm_name": {"description": "Dimension variable data type"},
    "original_csv_string": {
        "description": "Original representation of this variable in the CORAL data dump CSV",
    },
}
MANUAL_WITHDRAWN_BRICKS = {
    "Brick0000001",
    "Brick0000002",
    "Brick0000003",
    "Brick0000004",
    "Brick0000005",
}
MANUAL_WITHDRAWN_DATE = "2026-05-27"
PROCESS_IMPORT_PERSON = "John-Marc Chandonia <ENIGMA:0000057>"
PROCESS_IMPORT_CAMPAIGN = "Field Sampling <ENIGMA:0000095>"
PROCESS_IMPORT_PROTOCOL = "null"
PROCESS_IMPORT_DATE = MANUAL_WITHDRAWN_DATE
PROCESS_UPDATE_DATA = "Update Data <PROCESS:0000053>"
PROCESS_WITHDRAW_DATA = "Withdraw Data <PROCESS:0000052>"
MANUAL_INFERRED_UPDATE_BRIDGES = {
    "Brick0000350": {
        "successor": "Brick0000379",
        "source": "inferred_manual_bridge",
        "family": "isolate genome links arkin to isolate sequence and quality arkin",
        "evidence": "later sequence_and_quality_arkin table preserves all 771 old strain keys and adds quality columns",
    },
}


def read_tsv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle, delimiter="\t")


def write_tsv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_tsv_if_rows(path, rows, fieldnames):
    if not rows:
        if path.exists():
            path.unlink()
        return None
    write_tsv(path, rows, fieldnames)
    return path


def brick_ids(value):
    return BRICK_RE.findall(value or "")


def object_refs(value):
    refs = OBJECT_REF_RE.findall(value or "")
    return [re.sub(r"\s+", "", ref) for ref in refs]


def coral_brick_ref(brick_id, names_by_id):
    name = names_by_id.get(brick_id, "")
    if not name:
        raise ValueError(f"Missing ddt_ndarray_name for {brick_id}")
    return f"Generic: {name}"


def process_number(process_id):
    match = re.search(r"(\d+)$", process_id or "")
    return int(match.group(1)) if match else -1


def parse_yyyymmdd(token):
    token = re.sub(r"\D", "", token or "")
    if len(token) == 8:
        year = int(token[:4])
        month = int(token[4:6])
        day = int(token[6:8])
    elif len(token) == 6:
        yy = int(token[:2])
        year = 2000 + yy if yy < 70 else 1900 + yy
        month = int(token[2:4])
        day = int(token[4:6])
    else:
        return None
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    return year * 10000 + month * 100 + day


def clean_family(value):
    value = DATA_EXT_RE.sub("", value or "").lower()
    value = re.sub(r"[_\-.()]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def classify_name(name):
    base = DATA_EXT_RE.sub("", name or "")
    version_match = TRAILING_VERSION_RE.search(base)
    if version_match:
        family = clean_family(base[: version_match.start()])
        return ("version", family, int(version_match.group(1)))

    embedded_version_match = EMBEDDED_VERSION_RE.search(base)
    if embedded_version_match:
        family = clean_family(f"{embedded_version_match.group(1)} {embedded_version_match.group(3)}")
        return ("version", family, int(embedded_version_match.group(2)))

    date_matches = list(TRAILING_DATE_RE.finditer(base))
    if date_matches:
        match = date_matches[-1]
        parsed = parse_yyyymmdd(match.group(1))
        if parsed is not None:
            # Avoid treating date ranges as update versions.
            prior_dates = ANY_DATE_RE.findall(base[: match.start()])
            valid_prior = [d for d in prior_dates if parse_yyyymmdd(d) is not None]
            if not valid_prior:
                family = clean_family(base[: match.start()])
                suffix = (match.group(2) or "").lower()
                suffix_rank = ord(suffix) - ord("a") + 1 if suffix else 0
                parsed = parsed * 100 + suffix_rank
                return ("date", family, parsed)

    return ("none", clean_family(base), None)


def htcp_family(name):
    base = DATA_EXT_RE.sub("", name or "")
    if not HTCP_RE.search(base):
        return None
    return HTCP_RE.split(base, maxsplit=1)[0]


def reloads_family(name):
    base = DATA_EXT_RE.sub("", name or "")
    if not RELOADS_RE.search(base):
        return None
    return RELOADS_RE.split(base, maxsplit=1)[0]


def is_reloads_v2(name):
    return bool(RELOADS_V2_RE.search(DATA_EXT_RE.sub("", name or "")))


def reloads_v2_name(name):
    base = DATA_EXT_RE.sub("", name or "")
    if is_reloads_v2(base):
        return base
    return f"{base}_v2"


def growth_overlap_keys(path):
    keys = set()
    if not path.exists():
        return keys
    for row in read_tsv(path):
        time_value = row.get("time_series_time_since_inoculation_hour", "")
        try:
            time_value = f"{float(time_value):.8f}"
        except ValueError:
            pass
        od_value = row.get("optical_density_dimensionless_unit", "")
        try:
            od_value = f"{float(od_value):.6f}"
        except ValueError:
            pass
        keys.add((
            time_value,
            row.get("microplate_well_name", ""),
            row.get("sdt_strain_name", ""),
            od_value,
        ))
    return keys


def terminal_successor(start, successor_by_predecessor):
    seen = set()
    current = start
    while current and current not in seen and current in successor_by_predecessor:
        seen.add(current)
        current = successor_by_predecessor[current]
    return current


def load_ndarray_rows(path):
    if not path.exists():
        return {}
    return {row["ddt_ndarray_id"]: row for row in read_tsv(path)}


def aggregate_sidecars(sidecar_dir, data_dir):
    for suffix, output_name in [
        ("_ddt_ndarray.tsv", "ddt_ndarray.tsv"),
        ("_sys_ddt_typedef.tsv", "sys_ddt_typedef.tsv"),
    ]:
        out_path = data_dir / output_name
        first = True
        with out_path.open("w", newline="", encoding="utf-8") as out_handle:
            writer = None
            for path in sorted(sidecar_dir.glob(f"Brick*{suffix}")):
                with path.open(newline="", encoding="utf-8") as in_handle:
                    reader = csv.DictReader(in_handle, delimiter="\t")
                    if first:
                        writer = csv.DictWriter(out_handle, delimiter="\t", fieldnames=reader.fieldnames)
                        writer.writeheader()
                        first = False
                    for row in reader:
                        writer.writerow(row)


def filter_sys_ddt_typedef_to_current_bricks(data_dir, reports_dir):
    ndarray_path = data_dir / "ddt_ndarray.tsv"
    typedef_path = data_dir / "sys_ddt_typedef.tsv"
    if not ndarray_path.exists() or not typedef_path.exists():
        return {"sys_ddt_typedef_rows_removed": 0, "sys_ddt_typedef_rows_kept": 0}

    current_bricks = set()
    obsolete_bricks = set()
    for row in read_tsv(ndarray_path):
        brick_id = row.get("ddt_ndarray_id", "")
        if not brick_id:
            continue
        if (row.get("withdrawn_date") or row.get("superceded_by_ddt_ndarray_id")):
            obsolete_bricks.add(brick_id)
        else:
            current_bricks.add(brick_id)

    kept = []
    removed = []
    with typedef_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames or []
        for row in reader:
            brick_id = row.get("ddt_ndarray_id", "")
            if brick_id in current_bricks:
                kept.append(row)
            else:
                removed.append(row)

    write_tsv(typedef_path, kept, fieldnames)
    if removed:
        report_rows = [
            {
                "ddt_ndarray_id": row.get("ddt_ndarray_id", ""),
                "berdl_column_name": row.get("berdl_column_name", ""),
                "reason": "withdrawn_or_superceded_brick",
            }
            for row in removed
        ]
        write_tsv(
            reports_dir / "sys_ddt_typedef_removed_obsolete_rows.tsv",
            report_rows,
            ["ddt_ndarray_id", "berdl_column_name", "reason"],
        )
    return {
        "sys_ddt_typedef_rows_removed": len(removed),
        "sys_ddt_typedef_rows_kept": len(kept),
        "current_bricks_with_typedefs": len({row.get("ddt_ndarray_id", "") for row in kept}),
        "obsolete_bricks": len(obsolete_bricks),
    }


def infer_htcp_growth_lifecycle(ndarray, data_dir, explicit, explicit_pairs):
    reloads_by_family = defaultdict(list)
    reloads_v2_by_name = {}
    for brick_id, row in ndarray.items():
        name = row.get("ddt_ndarray_name", "")
        family = reloads_family(name)
        if not family:
            continue
        reloads_by_family[family].append((brick_id, row))
        if is_reloads_v2(name):
            reloads_v2_by_name[DATA_EXT_RE.sub("", name)] = (brick_id, row)

    key_cache = {}

    def keys_for(brick_id):
        if brick_id not in key_cache:
            key_cache[brick_id] = growth_overlap_keys(data_dir / f"{brick_id}.tsv")
        return key_cache[brick_id]

    inferred = []
    review_rows = []
    for brick_id, row in sorted(ndarray.items()):
        try:
            number = int(brick_id.replace("Brick", ""))
        except ValueError:
            continue
        if number < 215 or number > 343 or brick_id in explicit:
            continue

        name = row.get("ddt_ndarray_name", "")
        family = htcp_family(name)
        if not family:
            continue

        old_keys = keys_for(brick_id)
        candidates = [
            (candidate_id, candidate_row)
            for candidate_id, candidate_row in reloads_by_family.get(family, [])
            if not is_reloads_v2(candidate_row.get("ddt_ndarray_name", ""))
        ]
        if not candidates:
            inferred.append({
                "source": "inferred_htcp_withdraw",
                "family": family,
                "predecessor": brick_id,
                "successor": "",
                "lifecycle_successor": "",
                "predecessor_name": name,
                "successor_name": "",
                "lifecycle_successor_name": "",
                "process": "Withdraw Data",
                "review_status": "accepted_inference",
                "evidence": "no_later_reload_same_prefix",
            })
            continue

        best = None
        for candidate_id, candidate_row in candidates:
            if (brick_id, candidate_id) in explicit_pairs:
                continue
            candidate_keys = keys_for(candidate_id)
            overlap = len(old_keys & candidate_keys)
            old_coverage = overlap / len(old_keys) if old_keys else 0
            new_coverage = overlap / len(candidate_keys) if candidate_keys else 0
            score = (new_coverage, old_coverage, overlap)
            if best is None or score > best[0]:
                best = (score, candidate_id, candidate_row)

        if best is None:
            continue

        (new_coverage, old_coverage, overlap), successor, successor_row = best
        if new_coverage >= 0.999 and old_coverage >= 0.98:
            evidence = "near_exact_reload_replacement"
        elif new_coverage >= 0.999 and old_coverage >= 0.75:
            evidence = "reload_clean_subset"
        elif new_coverage >= 0.97 and old_coverage >= 0.97:
            evidence = "near_same_reload_replacement"
        else:
            evidence = "same_prefix_but_no_row_overlap" if overlap == 0 else "ambiguous_reload_overlap"
            if overlap:
                review_rows.append({
                    "reason": evidence,
                    "family": family,
                    "predecessor": brick_id,
                    "successor": successor,
                    "predecessor_name": name,
                    "successor_name": successor_row.get("ddt_ndarray_name", ""),
                })
            inferred.append({
                "source": "inferred_htcp_withdraw",
                "family": family,
                "predecessor": brick_id,
                "successor": "",
                "lifecycle_successor": "",
                "predecessor_name": name,
                "successor_name": "",
                "lifecycle_successor_name": "",
                "process": "Withdraw Data",
                "review_status": "accepted_inference",
                "evidence": evidence,
            })
            continue

        successor_name = successor_row.get("ddt_ndarray_name", "")
        v2_row = reloads_v2_by_name.get(reloads_v2_name(successor_name))
        lifecycle_successor, lifecycle_successor_row = v2_row if v2_row else (successor, successor_row)
        inferred.append({
            "source": "inferred_htcp_reload_update",
            "family": family,
            "predecessor": brick_id,
            "successor": successor,
            "lifecycle_successor": lifecycle_successor,
            "predecessor_name": name,
            "successor_name": successor_name,
            "lifecycle_successor_name": lifecycle_successor_row.get("ddt_ndarray_name", ""),
            "process": "Update Data <PROCESS:0000053>",
            "review_status": "accepted_inference",
            "evidence": f"{evidence};old_coverage={old_coverage:.3f};new_coverage={new_coverage:.3f}",
        })

    return inferred, review_rows


def classify_lifecycle(process_path, ndarray_path, run_id, reports_dir, metadata_dir):
    rows = list(read_tsv(process_path))
    ndarray = load_ndarray_rows(ndarray_path)
    data_dir = ndarray_path.parent

    explicit = {}
    explicit_pairs = set()
    explicit_report = []

    for row in rows:
        process_name = row.get("process", "")
        lower_process = process_name.lower()
        is_update = "update data" in lower_process
        is_withdraw = "withdraw data" in lower_process
        if not (is_update or is_withdraw):
            continue

        inputs = brick_ids(row.get("input_objects", ""))
        outputs = brick_ids(row.get("output_objects", ""))
        withdrawn_date = row.get("date_end") or row.get("date_start") or ""
        for input_brick in inputs:
            successors = outputs if is_update else []
            if is_update:
                for output_brick in outputs:
                    explicit_pairs.add((input_brick, output_brick))
            status = "obsolete"
            source = "explicit_update" if is_update else "explicit_withdraw"
            review = ""
            successor = ""
            if len(successors) == 1:
                successor = successors[0]
            elif len(successors) > 1:
                review = "multiple_successors"

            previous = explicit.get(input_brick)
            if previous and previous.get("successor") != successor:
                review = "conflicting_lifecycle"

            explicit[input_brick] = {
                "ddt_ndarray_id": input_brick,
                "status": status,
                "source": source,
                "withdrawn_date": withdrawn_date,
                "superceded_by_ddt_ndarray_id": successor,
                "process_id": row.get("id", ""),
                "process": process_name,
                "input_objects": row.get("input_objects", ""),
                "output_objects": row.get("output_objects", ""),
                "review_status": review,
            }
            explicit_report.append(explicit[input_brick])

    for brick_id in sorted(MANUAL_WITHDRAWN_BRICKS):
        if brick_id in explicit:
            continue
        explicit[brick_id] = {
            "ddt_ndarray_id": brick_id,
            "status": "obsolete",
            "source": "manual_test_withdraw",
            "withdrawn_date": MANUAL_WITHDRAWN_DATE,
            "superceded_by_ddt_ndarray_id": "",
            "process_id": "",
            "process": "Withdraw Data (manual dry-run test)",
            "input_objects": f"[Brick-0000002:{brick_id}]",
            "output_objects": "",
            "review_status": "manual_test_withdraw",
        }
        explicit_report.append(explicit[brick_id])

    inferred = []
    review_rows = []
    families = defaultdict(list)
    for brick_id, row in ndarray.items():
        kind, family, ordinal = classify_name(row.get("ddt_ndarray_name", ""))
        if kind in {"version", "date"} and family:
            families[(kind, family)].append((ordinal, brick_id, row, kind))
        elif family:
            families[("version", family)].append((1, brick_id, row, "implicit_v1"))

    for (kind, family), members in sorted(families.items()):
        if len(members) < 2:
            continue
        if kind == "version" and not any(source == "version" and ordinal > 1 for ordinal, _, _, source in members):
            continue
        members.sort(key=lambda item: (item[0], item[1]))
        for prev, curr in zip(members, members[1:]):
            old_ord, old_id, old_row, old_source = prev
            new_ord, new_id, new_row, new_source = curr
            if old_id in explicit or (old_id, new_id) in explicit_pairs:
                continue
            if new_ord <= old_ord:
                review_rows.append({
                    "reason": "ambiguous_same_version_or_date",
                    "family": family,
                    "predecessor": old_id,
                    "successor": new_id,
                    "predecessor_name": old_row.get("ddt_ndarray_name", ""),
                    "successor_name": new_row.get("ddt_ndarray_name", ""),
                })
                continue
            if kind == "version" and new_ord != old_ord + 1:
                review_rows.append({
                    "reason": "non_consecutive_version",
                    "family": family,
                    "predecessor": old_id,
                    "successor": new_id,
                    "predecessor_name": old_row.get("ddt_ndarray_name", ""),
                    "successor_name": new_row.get("ddt_ndarray_name", ""),
                })
                continue
            inferred.append({
                "source": f"inferred_{kind}",
                "family": family,
                "predecessor": old_id,
                "successor": new_id,
                "lifecycle_successor": new_id,
                "predecessor_name": old_row.get("ddt_ndarray_name", ""),
                "successor_name": new_row.get("ddt_ndarray_name", ""),
                "lifecycle_successor_name": new_row.get("ddt_ndarray_name", ""),
                "process": "Update Data <PROCESS:0000053>",
                "review_status": "candidate",
                "evidence": "",
            })

    for predecessor, bridge in MANUAL_INFERRED_UPDATE_BRIDGES.items():
        successor = bridge["successor"]
        if predecessor in explicit or (predecessor, successor) in explicit_pairs:
            continue
        if predecessor not in ndarray or successor not in ndarray:
            review_rows.append({
                "reason": "manual_bridge_missing_brick",
                "family": bridge["family"],
                "predecessor": predecessor,
                "successor": successor,
                "predecessor_name": ndarray.get(predecessor, {}).get("ddt_ndarray_name", ""),
                "successor_name": ndarray.get(successor, {}).get("ddt_ndarray_name", ""),
            })
            continue
        inferred.append({
            "source": bridge["source"],
            "family": bridge["family"],
            "predecessor": predecessor,
            "successor": successor,
            "lifecycle_successor": successor,
            "predecessor_name": ndarray[predecessor].get("ddt_ndarray_name", ""),
            "successor_name": ndarray[successor].get("ddt_ndarray_name", ""),
            "lifecycle_successor_name": ndarray[successor].get("ddt_ndarray_name", ""),
            "process": "Update Data <PROCESS:0000053>",
            "review_status": "accepted_inference",
            "evidence": bridge["evidence"],
        })

    htcp_inferred, htcp_review_rows = infer_htcp_growth_lifecycle(ndarray, data_dir, explicit, explicit_pairs)
    inferred.extend(htcp_inferred)
    review_rows.extend(htcp_review_rows)

    names_by_id = {
        brick_id: row.get("ddt_ndarray_name", "")
        for brick_id, row in ndarray.items()
    }
    successor_by_predecessor = {
        row["predecessor"]: row["successor"]
        for row in inferred
        if row.get("process", "").lower().startswith("update data") and row.get("successor")
    }
    for row in inferred:
        if not row.get("successor"):
            continue
        direct_successor = terminal_successor(row["predecessor"], successor_by_predecessor)
        row["lifecycle_successor"] = direct_successor
        row["lifecycle_successor_name"] = names_by_id.get(direct_successor, row.get("successor_name", ""))

    inferred_by_predecessor = {
        row["predecessor"]: row
        for row in inferred
        if row["predecessor"] not in explicit
    }
    lifecycle_rows = []
    resolved_lifecycle_rows = []
    updated_ndarray_rows = []
    for brick_id, row in sorted(ndarray.items()):
        entry = explicit.get(brick_id)
        inferred_entry = inferred_by_predecessor.get(brick_id)
        if entry:
            updated_row = dict(row)
            updated_row["withdrawn_date"] = entry.get("withdrawn_date", "")
            updated_row["superceded_by_ddt_ndarray_id"] = entry.get("superceded_by_ddt_ndarray_id", "")
            updated_ndarray_rows.append(updated_row)
            out = {
                **entry,
                "ddt_ndarray_name": row.get("ddt_ndarray_name", ""),
                "ddt_ndarray_description": row.get("ddt_ndarray_description", ""),
            }
        elif inferred_entry:
            updated_row = dict(row)
            updated_row["withdrawn_date"] = inferred_entry.get("withdrawn_date", "")
            updated_row["superceded_by_ddt_ndarray_id"] = inferred_entry.get(
                "lifecycle_successor", inferred_entry.get("successor", "")
            )
            updated_ndarray_rows.append(updated_row)
            out = {
                "ddt_ndarray_id": brick_id,
                "ddt_ndarray_name": row.get("ddt_ndarray_name", ""),
                "ddt_ndarray_description": row.get("ddt_ndarray_description", ""),
                "status": "obsolete_candidate",
                "source": inferred_entry["source"],
                "withdrawn_date": inferred_entry.get("withdrawn_date", ""),
                "superceded_by_ddt_ndarray_id": inferred_entry.get(
                    "lifecycle_successor", inferred_entry.get("successor", "")
                ),
                "process_id": "",
                "process": inferred_entry.get("process", "Update Data <PROCESS:0000053>"),
                "input_objects": f"[Brick-0000002:{brick_id}]",
                "output_objects": (
                    f"[Brick-0000002:{inferred_entry.get('successor')}]"
                    if inferred_entry.get("successor") else ""
                ),
                "review_status": inferred_entry.get("review_status", "candidate_inference"),
            }
        else:
            updated_ndarray_rows.append(row)
            out = {
                "ddt_ndarray_id": brick_id,
                "ddt_ndarray_name": row.get("ddt_ndarray_name", ""),
                "ddt_ndarray_description": row.get("ddt_ndarray_description", ""),
                "status": "current",
                "source": "none",
                "withdrawn_date": row.get("withdrawn_date", ""),
                "superceded_by_ddt_ndarray_id": row.get("superceded_by_ddt_ndarray_id", ""),
                "process_id": "",
                "process": "",
                "input_objects": "",
                "output_objects": "",
                "review_status": "",
            }
        lifecycle_rows.append(out)
        resolved_lifecycle_rows.append(out)

    for row in inferred:
        if row["predecessor"] not in explicit:
            lifecycle_rows.append({
                "ddt_ndarray_id": row["predecessor"],
                "ddt_ndarray_name": row["predecessor_name"],
                "ddt_ndarray_description": "",
                "status": "obsolete_candidate",
                "source": row["source"],
                "withdrawn_date": row.get("withdrawn_date", ""),
                "superceded_by_ddt_ndarray_id": row.get("lifecycle_successor", row.get("successor", "")),
                "process_id": "",
                "process": row.get("process", "Update Data <PROCESS:0000053>"),
                "input_objects": f"[Brick-0000002:{row['predecessor']}]",
                "output_objects": f"[Brick-0000002:{row['successor']}]" if row.get("successor") else "",
                "review_status": row.get("review_status", "candidate_inference"),
            })

    lifecycle_fields = [
        "ddt_ndarray_id", "ddt_ndarray_name", "ddt_ndarray_description", "status",
        "source", "withdrawn_date", "superceded_by_ddt_ndarray_id", "process_id",
        "process", "input_objects", "output_objects", "review_status",
    ]
    write_tsv(reports_dir / "brick_lifecycle.tsv", lifecycle_rows, lifecycle_fields)
    write_tsv(reports_dir / "brick_lifecycle_with_inference.tsv", resolved_lifecycle_rows, lifecycle_fields)
    if updated_ndarray_rows:
        write_tsv(reports_dir / "ddt_ndarray_lifecycle_preview.tsv", updated_ndarray_rows, list(updated_ndarray_rows[0].keys()))
        write_tsv(data_dir / "ddt_ndarray.tsv", updated_ndarray_rows, list(updated_ndarray_rows[0].keys()))
    write_tsv(reports_dir / "explicit_brick_lifecycle.tsv", explicit_report, [
        "ddt_ndarray_id", "status", "source", "withdrawn_date",
        "superceded_by_ddt_ndarray_id", "process_id", "process",
        "input_objects", "output_objects", "review_status",
    ])
    explicit_review_rows = [row for row in explicit_report if row.get("review_status")]
    write_tsv(reports_dir / "explicit_brick_lifecycle_review.tsv", explicit_review_rows, [
        "ddt_ndarray_id", "status", "source", "withdrawn_date",
        "superceded_by_ddt_ndarray_id", "process_id", "process",
        "input_objects", "output_objects", "review_status",
    ])
    write_tsv(reports_dir / "brick_lifecycle_inference.tsv", inferred, [
        "source", "family", "predecessor", "successor", "lifecycle_successor",
        "predecessor_name", "successor_name", "lifecycle_successor_name",
        "process", "review_status", "evidence",
    ])
    write_tsv(reports_dir / "brick_lifecycle_review.tsv", review_rows, [
        "reason", "family", "predecessor", "successor", "predecessor_name", "successor_name",
    ])

    inferred_process_rows = []
    inferred_withdraw_rows = []
    for row in inferred:
        is_withdraw = row.get("process", "").lower().startswith("withdraw data")
        process_row = {
            "process": PROCESS_WITHDRAW_DATA if is_withdraw else PROCESS_UPDATE_DATA,
            "person": PROCESS_IMPORT_PERSON,
            "campaign": PROCESS_IMPORT_CAMPAIGN,
            "protocol": PROCESS_IMPORT_PROTOCOL,
            "date_start": row.get("withdrawn_date", "") or PROCESS_IMPORT_DATE,
            "date_end": row.get("withdrawn_date", "") or PROCESS_IMPORT_DATE,
            "input_objects": coral_brick_ref(row["predecessor"], names_by_id),
            "output_objects": coral_brick_ref(row["successor"], names_by_id) if row.get("successor") else "",
        }
        if is_withdraw:
            inferred_withdraw_rows.append(process_row)
        else:
            inferred_process_rows.append(process_row)

    for brick_id in sorted(MANUAL_WITHDRAWN_BRICKS):
        if brick_id in explicit:
            continue
        if brick_id not in names_by_id:
            continue
        inferred_withdraw_rows.append({
            "process": PROCESS_WITHDRAW_DATA,
            "person": PROCESS_IMPORT_PERSON,
            "campaign": PROCESS_IMPORT_CAMPAIGN,
            "protocol": PROCESS_IMPORT_PROTOCOL,
            "date_start": MANUAL_WITHDRAWN_DATE,
            "date_end": MANUAL_WITHDRAWN_DATE,
            "input_objects": coral_brick_ref(brick_id, names_by_id),
            "output_objects": "",
        })

    process_import_fields = [
        "process", "person", "campaign", "protocol", "date_start",
        "date_end", "input_objects", "output_objects",
    ]
    pending_process_import_files = []
    update_path = write_tsv_if_rows(
        metadata_dir / f"process_update_data_{run_id}.tsv",
        inferred_process_rows,
        process_import_fields,
    )
    if update_path:
        pending_process_import_files.append(str(update_path))
    withdraw_path = write_tsv_if_rows(
        metadata_dir / f"process_withdraw_data_{run_id}.tsv",
        inferred_withdraw_rows,
        process_import_fields,
    )
    if withdraw_path:
        pending_process_import_files.append(str(withdraw_path))

    obsolete_ids = sorted(explicit)
    (reports_dir / "obsolete_berdl_tables_to_drop.sql").write_text(
        "\n".join(f"DROP TABLE IF EXISTS enigma_coral.ddt_{brick.lower()};" for brick in obsolete_ids)
        + ("\n" if obsolete_ids else ""),
        encoding="utf-8",
    )

    return {
        "total_bricks_with_metadata": len(ndarray),
        "explicit_obsolete": len(explicit),
        "explicit_lifecycle_rows": len(explicit_report),
        "inferred_update_candidates": len(inferred),
        "review_needed": sum(1 for row in explicit_report if row.get("review_status")) + len(review_rows),
        "pending_process_import_files": pending_process_import_files,
    }


def process_cleanup(process_path, reports_dir):
    rows = list(read_tsv(process_path))
    by_signature = defaultdict(list)
    for row in rows:
        inputs = tuple(sorted(object_refs(row.get("input_objects", ""))))
        outputs = tuple(sorted(object_refs(row.get("output_objects", ""))))
        by_signature[(inputs, outputs)].append(row)

    delete_rows = []
    keep_ids = set()
    delete_ids = set()
    for (inputs, outputs), group in by_signature.items():
        if not outputs:
            continue
        if len(group) <= 1:
            continue
        group.sort(key=lambda row: process_number(row.get("id", "")))
        keep = group[-1]
        keep_ids.add(keep.get("id", ""))
        for old in group[:-1]:
            delete_ids.add(old.get("id", ""))
            delete_rows.append({
                "delete_process_id": old.get("id", ""),
                "keep_process_id": keep.get("id", ""),
                "reason": "identical_inputs_outputs",
                "input_count": len(inputs),
                "output_count": len(outputs),
            })

    survivors = [row for row in rows if row.get("id", "") not in delete_ids]
    by_input = defaultdict(list)
    for row in survivors:
        inputs = tuple(sorted(object_refs(row.get("input_objects", ""))))
        outputs = frozenset(object_refs(row.get("output_objects", "")))
        by_input[inputs].append((outputs, row))

    for inputs, group in by_input.items():
        group.sort(key=lambda item: process_number(item[1].get("id", "")))
        for i, (outputs_i, row_i) in enumerate(group):
            if row_i.get("id", "") in delete_ids or not outputs_i:
                continue
            for outputs_j, row_j in group[i + 1:]:
                if outputs_i < outputs_j:
                    delete_ids.add(row_i.get("id", ""))
                    delete_rows.append({
                        "delete_process_id": row_i.get("id", ""),
                        "keep_process_id": row_j.get("id", ""),
                        "reason": "same_inputs_output_subset",
                        "input_count": len(inputs),
                        "output_count": len(outputs_i),
                    })
                    break

    consolidated = [row for row in rows if row.get("id", "") not in delete_ids]
    with (reports_dir / "Process_consolidated.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(consolidated)

    write_tsv(reports_dir / "process_cleanup_report.tsv", delete_rows, [
        "delete_process_id", "keep_process_id", "reason", "input_count", "output_count",
    ])
    (reports_dir / "processes_to_delete.txt").write_text(
        "".join(f"{pid}\n" for pid in sorted(delete_ids, key=process_number)),
        encoding="utf-8",
    )
    delete_script = reports_dir / "delete_processes.sh"
    delete_script.write_text("""#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROCESS_LIST="${PROCESS_LIST:-$SCRIPT_DIR/processes_to_delete.txt}"
DATABASE="${CORAL_ARANGO_DATABASE:-ENIGMA_PROD}"
PASSWORD="${CORAL_ARANGO_PASSWORD:-}"
ARANGOSH="${ARANGOSH:-arangosh}"

usage() {
  cat <<'USAGE'
Usage: delete_processes.sh [--execute]

Deletes process records listed in processes_to_delete.txt, including
SYS_ProcessInput and SYS_ProcessOutput edges.

By default this is a dry run and prints the process IDs that would be deleted.
Set CORAL_ARANGO_PASSWORD and pass --execute to actually run arangosh.

Environment:
  PROCESS_LIST             Path to process ID list. Defaults beside this script.
  CORAL_ARANGO_DATABASE    Arango database. Default: ENIGMA_PROD
  CORAL_ARANGO_PASSWORD    Arango password. Required with --execute.
  ARANGOSH                 arangosh executable. Default: arangosh
USAGE
}

execute=0
case "${1:-}" in
  --execute) execute=1 ;;
  -h|--help) usage; exit 0 ;;
  "") ;;
  *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
esac

if [[ ! -f "$PROCESS_LIST" ]]; then
  echo "Process list not found: $PROCESS_LIST" >&2
  exit 1
fi

mapfile -t process_ids < <(grep -E '^Process[0-9]+$' "$PROCESS_LIST" || true)
if [[ ${#process_ids[@]} -eq 0 ]]; then
  echo "No process IDs found in $PROCESS_LIST"
  exit 0
fi

echo "Process list: $PROCESS_LIST"
echo "Database: $DATABASE"
echo "Process IDs: ${#process_ids[@]}"

if [[ "$execute" -ne 1 ]]; then
  echo "Dry run. Re-run with --execute after setting CORAL_ARANGO_PASSWORD."
  printf '%s\\n' "${process_ids[@]}"
  exit 0
fi

if [[ -z "$PASSWORD" ]]; then
  echo "CORAL_ARANGO_PASSWORD is required with --execute." >&2
  exit 1
fi

tmp_js="$(mktemp)"
trap 'rm -f "$tmp_js"' EXIT

{
  printf '%s\\n' "const processIds = ["
  for process_id in "${process_ids[@]}"; do
    printf "  '%s',\\n" "$process_id"
  done
  cat <<'JS'
];

const inputEdges = db._collection('SYS_ProcessInput');
const outputEdges = db._collection('SYS_ProcessOutput');
const processes = db._collection('SYS_Process');

let totalInputEdges = 0;
let totalOutputEdges = 0;
let totalProcesses = 0;

for (const processId of processIds) {
  const processRef = 'SYS_Process/' + processId;
  const inputRemoved = inputEdges.removeByExample({_to: processRef});
  const outputRemoved = outputEdges.removeByExample({_from: processRef});
  const processRemoved = processes.removeByExample({id: processId});
  totalInputEdges += inputRemoved;
  totalOutputEdges += outputRemoved;
  totalProcesses += processRemoved;
  print(processId + '\tinput_edges=' + inputRemoved + '\toutput_edges=' + outputRemoved + '\tprocess_docs=' + processRemoved);
}

print('TOTAL\tinput_edges=' + totalInputEdges + '\toutput_edges=' + totalOutputEdges + '\tprocess_docs=' + totalProcesses);
JS
} > "$tmp_js"

"$ARANGOSH" --server.database "$DATABASE" --server.password "$PASSWORD" --javascript.execute-string "$(cat "$tmp_js")"
""", encoding="utf-8")
    delete_script.chmod(0o755)
    return {
        "process_rows": len(rows),
        "consolidated_rows": len(consolidated),
        "delete_candidates": len(delete_ids),
    }


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_schema_file(path):
    text = path.read_text(encoding="utf-8")
    by_name = {}
    for name, py_type, comment in SCHEMA_FIELD_RE.findall(text):
        by_name[name] = {
            "name": name,
            "type": TYPE_MAP.get(py_type, "STRING"),
            "nullable": True,
            "comment": comment.replace('\\"', '"'),
        }
    for name, py_type in SCHEMA_SIMPLE_FIELD_RE.findall(text):
        by_name.setdefault(name, {
            "name": name,
            "type": TYPE_MAP.get(py_type, "STRING"),
            "nullable": True,
            "comment": "",
        })
    return list(by_name.values())


def _schema_from_comments(path, comments):
    if not path.exists():
        return []
    with path.open(encoding="utf-8", errors="replace") as handle:
        header = handle.readline().rstrip("\n\r").split("\t")
    return [
        {
            "column": column,
            "type": "STRING",
            "nullable": column not in {"ddt_ndarray_id", "cdm_column_name"},
            "comment": json.dumps(comments.get(column, {"description": column.replace("_", " ")})),
        }
        for column in header
        if column
    ]


def _brick_table_comments(ddt_ndarray_path):
    comments = {}
    if not ddt_ndarray_path.exists():
        return comments
    for row in read_tsv(ddt_ndarray_path):
        brick_id = row.get("ddt_ndarray_id")
        if not brick_id:
            continue
        parts = [
            (row.get("ddt_ndarray_name") or "").strip(),
            (row.get("ddt_ndarray_description") or "").strip(),
        ]
        comments[f"ddt_{brick_id.lower()}"] = " - ".join(part for part in parts if part)
    return comments


def static_table_name(path):
    mapping = {
        "Process": "sys_process",
        "Protocol": "sdt_protocol",
        "Assembly": "sdt_assembly",
        "Bin": "sdt_bin",
        "Community": "sdt_community",
        "Condition": "sdt_condition",
        "DubSeq_Library": "sdt_dubseq_library",
        "ENIGMA": "sdt_enigma",
        "Gene": "sdt_gene",
        "Genome": "sdt_genome",
        "Image": "sdt_image",
        "Location": "sdt_location",
        "OTU": "sdt_asv",
        "Reads": "sdt_reads",
        "Sample": "sdt_sample",
        "Strain": "sdt_strain",
        "Taxon": "sdt_taxon",
        "TnSeq_Library": "sdt_tnseq_library",
    }
    return mapping.get(path.stem, path.stem.lower())


def build_ingest_preview(data_dir, schema_dir, ingest_dir, reports_dir):
    metadata_dir = reports_dir.parent / "metadata"
    table_schemas_path = metadata_dir / "table_schemas.json"
    table_comments_path = metadata_dir / "table_comments.json"
    coral_type_to_table_path = metadata_dir / "coral_type_to_table.json"
    table_schemas = json.loads(table_schemas_path.read_text(encoding="utf-8")) if table_schemas_path.exists() else {}
    table_comments = json.loads(table_comments_path.read_text(encoding="utf-8")) if table_comments_path.exists() else {}
    coral_type_to_table = json.loads(coral_type_to_table_path.read_text(encoding="utf-8")) if coral_type_to_table_path.exists() else {}
    brick_table_comments = _brick_table_comments(data_dir / "ddt_ndarray.tsv")

    lifecycle = {}
    lifecycle_path = reports_dir / "brick_lifecycle_with_inference.tsv"
    if not lifecycle_path.exists():
        lifecycle_path = reports_dir / "brick_lifecycle.tsv"
    if lifecycle_path.exists():
        for row in read_tsv(lifecycle_path):
            lifecycle[row["ddt_ndarray_id"]] = row

    tables = []
    for path in sorted(data_dir.glob("*.tsv")):
        stem = path.stem
        if stem in coral_type_to_table:
            continue
        if stem.endswith("_ddt_ndarray") or stem.endswith("_sys_ddt_typedef") or stem.endswith("_schema"):
            continue
        if stem.startswith("Brick"):
            brick_id = stem
            table = f"ddt_{brick_id.lower()}"
            life = lifecycle.get(brick_id, {})
            enabled = life.get("status") not in {"obsolete", "obsolete_candidate", "review_needed"}
            schema_path = schema_dir / f"{brick_id}_schema.py"
            schema = parse_schema_file(schema_path) if schema_path.exists() else []
            source_kind = "brick"
        elif stem in {"ddt_ndarray", "sys_ddt_typedef"}:
            table = stem
            enabled = True
            if table == "ddt_ndarray":
                schema = table_schemas.get(table, []) or _schema_from_comments(path, DDT_NDARRAY_COMMENTS)
            else:
                schema = table_schemas.get(table, []) or _schema_from_comments(path, SYS_DDT_TYPEDEF_COMMENTS)
            source_kind = "ddt_metadata"
        elif stem == "sys_oterm":
            table = stem
            enabled = True
            schema = table_schemas.get(table, [])
            source_kind = "ontology"
        elif stem == "sys_typedef":
            table = stem
            enabled = True
            schema = table_schemas.get(table, [])
            source_kind = "typedef"
        elif stem in table_schemas:
            table = stem
            enabled = True
            schema = table_schemas.get(table, [])
            source_kind = "coral_static"
        else:
            table = static_table_name(path)
            enabled = True
            schema = table_schemas.get(table, [])
            source_kind = "coral_static"
        tables.append({
            "name": table,
            "enabled": enabled,
            "source_kind": source_kind,
            "local_path": str(path),
            "format": "tsv",
            "csv": {
                "header": True,
                "delimiter": "\t",
                "quote": "\u0000",
                "escape": "\\",
                "multiLine": False,
                "inferSchema": False,
            },
            "schema": schema,
            "table_comment": (
                brick_table_comments.get(table)
                or table_comments.get(table)
                or (DDT_NDARRAY_TABLE_COMMENT if table == "ddt_ndarray" else "")
                or (SYS_DDT_TYPEDEF_TABLE_COMMENT if table == "sys_ddt_typedef" else "")
            ),
        })

    config = {
        "tenant": "enigma",
        "dataset": "coral",
        "namespace": "enigma_coral",
        "mode": "overwrite",
        "dry_run": True,
        "source_files": json.loads(
            (metadata_dir / "coral_metadata_summary.json").read_text(encoding="utf-8")
        ).get("source", {}).get("upload_files", []) if (metadata_dir / "coral_metadata_summary.json").exists() else [],
        "notes": [
            "Preview only. Do not upload, ingest, or delete from this config without review.",
            "TSV is used instead of CSV to avoid quoted comma/newline parser failures.",
            "Obsolete brick tables are disabled; review brick_lifecycle.tsv before applying.",
            "source_files must be uploaded to the same Bronze run prefix before creating sys_oterm/sys_typedef-derived tables.",
        ],
        "tables": tables,
    }
    ingest_dir.mkdir(parents=True, exist_ok=True)
    (ingest_dir / "config.dry_run.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    with (ingest_dir / "enabled_tables.txt").open("w", encoding="utf-8") as handle:
        for table in tables:
            if table["enabled"]:
                handle.write(table["name"] + "\n")


def build_manifest(data_dir, reports_dir, manifests_dir, lifecycle_stats, cleanup_stats):
    metadata_dir = reports_dir.parent / "metadata"
    table_schemas_path = metadata_dir / "table_schemas.json"
    table_comments_path = metadata_dir / "table_comments.json"
    coral_metadata_path = metadata_dir / "coral_metadata_summary.json"
    coral_type_to_table_path = metadata_dir / "coral_type_to_table.json"
    table_schemas = json.loads(table_schemas_path.read_text(encoding="utf-8")) if table_schemas_path.exists() else {}
    table_comments = json.loads(table_comments_path.read_text(encoding="utf-8")) if table_comments_path.exists() else {}
    coral_metadata = json.loads(coral_metadata_path.read_text(encoding="utf-8")) if coral_metadata_path.exists() else {}
    coral_type_to_table = json.loads(coral_type_to_table_path.read_text(encoding="utf-8")) if coral_type_to_table_path.exists() else {}
    existing_manifest_path = manifests_dir / "current.json"
    previous_by_path = {}
    if existing_manifest_path.exists():
        try:
            previous_manifest = json.loads(existing_manifest_path.read_text(encoding="utf-8"))
            previous_by_path = {
                row.get("data_path"): row
                for row in previous_manifest.get("tables", [])
                if row.get("data_path")
            }
        except json.JSONDecodeError:
            previous_by_path = {}
    tables = []
    for path in sorted(data_dir.glob("*.tsv")):
        if path.stem in coral_type_to_table:
            continue
        byte_count = path.stat().st_size
        previous = previous_by_path.get(str(path))
        if previous and previous.get("byte_count") == byte_count:
            header = previous.get("columns", [])
            row_count = previous.get("row_count")
            hashes = previous.get("hashes", {})
        else:
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle, delimiter="\t")
                header = next(reader, [])
                row_count = sum(1 for _ in reader)
            hashes = {"data_sha256": file_sha256(path)}
        target_table = path.stem
        if path.stem.startswith("Brick"):
            source_kind = "brick"
            target_table = f"ddt_{path.stem.lower()}"
        elif path.stem in {"ddt_ndarray", "sys_ddt_typedef"}:
            source_kind = "ddt_metadata"
        elif path.stem == "sys_oterm":
            source_kind = "ontology"
        elif path.stem == "sys_typedef":
            source_kind = "typedef"
        else:
            source_kind = "coral_static"
        tables.append({
            "table": target_table,
            "source_kind": source_kind,
            "data_path": str(path),
            "format": "tsv",
            "delimiter": "\\t",
            "row_count": row_count,
            "byte_count": byte_count,
            "hashes": hashes,
            "columns": header,
            "schema": table_schemas.get(target_table, []),
            "table_comment": table_comments.get(target_table, ""),
            "change_status": "dry_run_not_compared",
        })

    manifest = {
        "manifest_version": 1,
        "run_id": manifests_dir.parent.name,
        "tenant": "enigma",
        "dataset": "coral",
        "namespace": "enigma_coral",
        "dry_run": True,
        "tables": tables,
        "source_metadata": coral_metadata.get("source", {}),
        "lifecycle_stats": lifecycle_stats,
        "process_cleanup_stats": cleanup_stats,
    }
    manifests_dir.mkdir(parents=True, exist_ok=True)
    (manifests_dir / "current.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    data_dir = run_dir / "berdl_upload" / "data"
    schema_dir = run_dir / "berdl_upload" / "schema"
    metadata_dir = run_dir / "metadata"
    sidecar_dir = run_dir / "metadata" / "brick_sidecars"
    reports_dir = run_dir / "reports"
    manifests_dir = run_dir / "manifests"
    ingest_dir = run_dir / "ingest"

    aggregate_sidecars(sidecar_dir, data_dir)
    coral_metadata_stats = prepare_coral_metadata(run_dir, Path.cwd())
    process_path = run_dir / "coral_export" / "static_tsv" / "Process.tsv"
    if not process_path.exists():
        process_path = data_dir / "Process.tsv"
    lifecycle_stats = classify_lifecycle(
        process_path,
        data_dir / "ddt_ndarray.tsv",
        args.run_id,
        reports_dir,
        metadata_dir,
    )
    if lifecycle_stats.get("pending_process_import_files"):
        summary = {
            **lifecycle_stats,
            "coral_metadata": coral_metadata_stats,
            "status": "coral_process_import_required",
            "next_step": (
                "Import the generated process TSV file(s) into CORAL, then rerun "
                "the CORAL export so the updated Process table is reflected before "
                "building or importing the BERDL package."
            ),
        }
        reports_dir.mkdir(parents=True, exist_ok=True)
        (reports_dir / "dry_run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        raise SystemExit(2)
    typedef_filter_stats = filter_sys_ddt_typedef_to_current_bricks(data_dir, reports_dir)
    cleanup_stats = process_cleanup(process_path, reports_dir)
    build_ingest_preview(data_dir, schema_dir, ingest_dir, reports_dir)
    build_manifest(data_dir, reports_dir, manifests_dir, lifecycle_stats, cleanup_stats)
    summary = {
        **lifecycle_stats,
        **typedef_filter_stats,
        **cleanup_stats,
        "coral_metadata": coral_metadata_stats,
    }
    (reports_dir / "dry_run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
