#!/usr/bin/env python3
"""CORAL typedef/OBO handling for the CORAL-to-BERDL sync.

This module mirrors the schema and ontology conventions in
``/h/jmc/src/CORAL/convert/spark-minio/make_tables.py`` and
``update_coral_ontologies.py`` without requiring a local Spark session.  It
stages the source metadata, builds BERDL ingest schemas with comments, and
normalizes CORAL static TSV exports into BERDL-ready table files.
"""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from repository_paths import normalize_repository_text

CURIE_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_]*:[A-Za-z0-9_.-]+\b")

SYS_OTERM_SCHEMA = [
    {
        "column": "sys_oterm_id",
        "type": "STRING",
        "nullable": False,
        "comment": json.dumps({
            "description": "Term identifier, aka CURIE (Primary key)",
            "type": "primary_key",
        }),
    },
    {
        "column": "parent_sys_oterm_id",
        "type": "STRING",
        "nullable": True,
        "comment": json.dumps({
            "description": "Parent term identifier",
            "type": "foreign_key",
            "references": "sys_oterm.sys_oterm_id",
        }),
    },
    {
        "column": "sys_oterm_ontology",
        "type": "STRING",
        "nullable": False,
        "comment": json.dumps({"description": "Ontology that each term is from"}),
    },
    {
        "column": "sys_oterm_name",
        "type": "STRING",
        "nullable": True,
        "comment": json.dumps({"description": "Term name"}),
    },
    {
        "column": "sys_oterm_synonyms",
        "type": "ARRAY<STRING>",
        "nullable": True,
        "comment": json.dumps({"description": "List of synonyms for a term"}),
    },
    {
        "column": "sys_oterm_definition",
        "type": "STRING",
        "nullable": True,
        "comment": json.dumps({"description": "Term definition"}),
    },
    {
        "column": "sys_oterm_links",
        "type": "ARRAY<STRING>",
        "nullable": True,
        "comment": json.dumps({
            "description": "Indicates that values are links to other tables (Ref) or ontological terms (ORef)"
        }),
    },
    {
        "column": "sys_oterm_properties",
        "type": "STRING",
        "nullable": True,
        "comment": json.dumps({
            "description": "Semicolon-separated map of properties to values for terms that are CORAL microtypes, including scalar data_type, is_valid_data_variable, is_valid_dimension, is_valid_data_variable, is_valid_dimension_variable, is_valid_property, valid_units, and valid_units_parent"
        }),
    },
]

SYS_TYPEDEF_SCHEMA = [
    {"column": "type_name", "type": "STRING", "nullable": False, "comment": json.dumps({"description": "CORAL typedef type name"})},
    {"column": "field_name", "type": "STRING", "nullable": False, "comment": json.dumps({"description": "CORAL typedef field name"})},
    {"column": "cdm_column_name", "type": "STRING", "nullable": False, "comment": json.dumps({"description": "BERDL column name derived from the CORAL field"})},
    {"column": "scalar_type", "type": "STRING", "nullable": True, "comment": json.dumps({"description": "CORAL scalar type"})},
    {"column": "is_required", "type": "BOOLEAN", "nullable": False, "comment": json.dumps({"description": "Whether the field is required in CORAL"})},
    {"column": "is_pk", "type": "BOOLEAN", "nullable": False, "comment": json.dumps({"description": "Whether the field is the primary key"})},
    {"column": "is_upk", "type": "BOOLEAN", "nullable": False, "comment": json.dumps({"description": "Whether the field is the user-facing unique key"})},
    {"column": "fk", "type": "STRING", "nullable": True, "comment": json.dumps({"description": "CORAL foreign-key descriptor"})},
    {"column": "constraint", "type": "STRING", "nullable": True, "comment": json.dumps({"description": "CORAL field constraint JSON"})},
    {"column": "comment", "type": "STRING", "nullable": True, "comment": json.dumps({"description": "Plain typedef field comment"})},
    {"column": "units_sys_oterm_id", "type": "STRING", "nullable": True, "comment": json.dumps({"description": "Units ontology term CURIE"})},
    {"column": "units_sys_oterm_name", "type": "STRING", "nullable": True, "comment": json.dumps({"description": "Units ontology term name"})},
    {"column": "type_sys_oterm_id", "type": "STRING", "nullable": True, "comment": json.dumps({"description": "Field type ontology term CURIE"})},
    {"column": "type_sys_oterm_name", "type": "STRING", "nullable": True, "comment": json.dumps({"description": "Field type ontology term name"})},
]


def read_dotenv_paths(env_path: Path) -> tuple[Path | None, Path | None]:
    values: dict[str, str] = {}
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("'\"")

    typedef = values.get("CORAL_TYPEDEF") or os.environ.get("CORAL_TYPEDEF")
    ontologies = values.get("CORAL_ONTOLOGIES") or os.environ.get("CORAL_ONTOLOGIES")
    return (Path(typedef).expanduser() if typedef else None,
            Path(ontologies).expanduser() if ontologies else None)


def normalize_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[ \-]+", "_", name)
    name = re.sub(r"[^0-9a-zA-Z_]", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.lower().strip("_")


def parse_fk(fk_str: str) -> tuple[str, bool]:
    is_array = False
    if fk_str.startswith("[") and fk_str.endswith("]"):
        is_array = True
        fk_str = fk_str[1:-1].strip()
    return fk_str.split(".", 1)[0], is_array


def rename_fk_column(original_name: str, ref_type: str, is_array: bool, type_to_table: dict[str, str]) -> str:
    target_table = type_to_table.get(ref_type, ref_type.lower())
    suffix = "_names" if is_array else "_name"
    lower_orig = original_name.lower()
    ref_singular = ref_type.lower()
    ref_plural = ref_singular + "s"

    idx = -1
    match_len = 0
    if ref_plural in lower_orig:
        idx = lower_orig.find(ref_plural)
        match_len = len(ref_plural)
    elif ref_singular in lower_orig:
        idx = lower_orig.find(ref_singular)
        match_len = len(ref_singular)

    if idx != -1:
        prefix = lower_orig[:idx]
        suffix_part = lower_orig[idx + match_len:]
        return normalize_name(f"{prefix}{target_table}{suffix}{suffix_part}")
    return normalize_name(f"{lower_orig}_{target_table}{suffix}")


def schema_type(scalar_type: str) -> str:
    if scalar_type.startswith("[") and scalar_type.endswith("]"):
        inner = scalar_type[1:-1].strip()
        return f"ARRAY<{schema_type(inner)}>"
    st = scalar_type.lower()
    if st in {"text", "term"}:
        return "STRING"
    if st == "int":
        return "INT"
    if st in {"float", "double"}:
        return "DOUBLE"
    if st == "bool":
        return "BOOLEAN"
    return "STRING"


def field_to_column_name(field: dict[str, Any], current_table: str, type_to_table: dict[str, str],
                         units_lookup: dict[str, str] | None = None) -> str:
    if field.get("PK", False):
        return normalize_name(f"{current_table}_id")
    if field.get("UPK", False):
        return normalize_name(f"{current_table}_name")
    fk = field.get("FK")
    if fk:
        ref_type, is_array = parse_fk(fk)
        return rename_fk_column(field["name"], ref_type, is_array, type_to_table)
    if normalize_name(field["name"]) == "description":
        return normalize_name(f"{current_table}_description")

    base_name = normalize_name(field["name"])
    scalar = field.get("scalar_type", "text").lower()
    if scalar in {"int", "float", "double"} and field.get("units_term") and units_lookup:
        unit_name = units_lookup.get(field["units_term"])
        if unit_name:
            base_name = f"{base_name}_{normalize_name(unit_name)}"
    return base_name


def build_json_comment(field: dict[str, Any], description: str, type_to_table: dict[str, str],
                       fk: str | None = None, is_pk: bool = False, is_upk: bool = False,
                       unit_name: str | None = None) -> str:
    comment = {"description": description}
    if unit_name:
        comment["unit"] = unit_name
    if is_pk:
        comment["type"] = "primary_key"
    elif is_upk:
        comment["type"] = "unique_key"
    elif fk:
        comment["type"] = "foreign_key"
        ref_type, _ = parse_fk(fk)
        if ref_type == "sys_oterm" or fk.startswith("sys_oterm."):
            comment["references"] = "sys_oterm.sys_oterm_id"
        else:
            ref_table = type_to_table.get(ref_type, ref_type.lower())
            comment["references"] = f"{ref_table}.{ref_table}_name"
    return json.dumps(comment)


def load_typedef(typedef_path: Path) -> dict[str, Any]:
    with typedef_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def typedef_context(typedef_data: dict[str, Any]) -> tuple[dict[str, str], list[dict[str, Any]]]:
    system_types = typedef_data.get("system_types", [])
    static_types = typedef_data.get("static_types", [])
    preferred = {t["name"]: t.get("preferred_name") or t["name"] for t in system_types + static_types}
    type_to_table: dict[str, str] = {}
    for tdef in system_types:
        type_to_table[tdef["name"]] = f"sys_{preferred[tdef['name']].lower()}"
    for tdef in static_types:
        type_to_table[tdef["name"]] = f"sdt_{preferred[tdef['name']].lower()}"
    return type_to_table, system_types + static_types


def parse_obo_file(path: Path) -> dict[str, dict[str, Any]]:
    terms: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] = {}
    in_term = False
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("!"):
                continue
            if line == "[Term]":
                if in_term and "id" in current:
                    terms[current["id"]] = current
                current = {"synonyms": [], "xrefs": [], "property_values": {}}
                in_term = True
                continue
            if line.startswith("["):
                if in_term and "id" in current:
                    terms[current["id"]] = current
                in_term = False
                continue
            if not in_term or ":" not in line:
                continue

            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key == "id":
                current["id"] = value
            elif key == "name":
                current["name"] = value
            elif key == "def":
                match = re.match(r'^"(.*)"(?:\s+\[.*\])?$', value)
                current["definition"] = match.group(1) if match else value
            elif key == "synonym":
                match = re.match(r'^"(.*)"\s+.*$', value)
                current["synonyms"].append(match.group(1) if match else value)
            elif key == "xref":
                current["xrefs"].append(value.split(" ", 1)[0])
            elif key == "is_a":
                current["parent"] = value.split(" ", 1)[0]
            elif key == "is_obsolete":
                current["is_obsolete"] = value.lower() == "true"
            elif key == "property_value":
                match = re.match(r'^(\S+)\s+"([^"]*)"', value)
                if match:
                    current["property_values"].setdefault(match.group(1), []).append(match.group(2))
    if in_term and "id" in current:
        terms[current["id"]] = current
    return terms


def ontology_paths(ontology_dir: Path) -> list[Path]:
    return sorted(path for path in ontology_dir.iterdir() if path.is_file() and path.suffix.lower() == ".obo")


def load_ontology_terms(ontology_dir: Path) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, tuple[str, dict[str, Any]]], dict[str, str], dict[str, int]]:
    ontology_terms: dict[str, dict[str, dict[str, Any]]] = {}
    term_lookup: dict[str, tuple[str, dict[str, Any]]] = {}
    units_lookup: dict[str, str] = {}
    stats: dict[str, int] = {}
    for path in ontology_paths(ontology_dir):
        ontology_name = path.stem
        terms = parse_obo_file(path)
        ontology_terms[ontology_name] = terms
        stats[ontology_name] = len(terms)
        for term_id, term in terms.items():
            term_lookup[term_id] = (ontology_name, term)
            name = term.get("name", "")
            if name:
                units_lookup.setdefault(term_id, name)
    return ontology_terms, term_lookup, units_lookup, stats


def iter_reference_sources(data_dir: Path, schema_dir: Path) -> list[Path]:
    sources: list[Path] = []
    for path in sorted(data_dir.glob("*.tsv")):
        stem = path.stem
        if stem == "sys_oterm" or stem.startswith("Brick"):
            continue
        if stem.startswith(("sdt_", "sys_", "ddt_")):
            sources.append(path)
    sources.extend(sorted(schema_dir.glob("*_schema.py")))
    return sources


def collect_referenced_terms(data_dir: Path, schema_dir: Path, term_ids: set[str], extra_terms: list[dict[str, Any]]) -> set[str]:
    referenced: set[str] = set()
    for row in extra_terms:
        for key in ["units_sys_oterm_id", "type_sys_oterm_id"]:
            value = row.get(key)
            if value in term_ids:
                referenced.add(value)

    for path in iter_reference_sources(data_dir, schema_dir):
        with path.open(encoding="utf-8", errors="replace") as handle:
            for raw_line in handle:
                # CORAL typedefs use ORef:TERM:ID wrappers; sys_oterm stores the inner CURIE.
                line = raw_line.replace("ORef:", "")
                for value in CURIE_RE.findall(line):
                    if value in term_ids:
                        referenced.add(value)
    return referenced


def expand_with_ancestors(referenced: set[str], term_lookup: dict[str, tuple[str, dict[str, Any]]]) -> set[str]:
    included = set(referenced)
    pending = list(referenced)
    while pending:
        term_id = pending.pop()
        entry = term_lookup.get(term_id)
        if not entry:
            continue
        parent = entry[1].get("parent")
        if parent and parent in term_lookup and parent not in included:
            included.add(parent)
            pending.append(parent)
    return included


def write_sys_oterm(ontology_terms: dict[str, dict[str, dict[str, Any]]], included_terms: set[str], out_path: Path) -> dict[str, dict[str, int]]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    stats: dict[str, dict[str, int]] = {}
    for ontology_name, terms in ontology_terms.items():
        included_count = 0
        for term_id, term in terms.items():
            if term_id not in included_terms:
                continue
            included_count += 1
            name = term.get("name", "")
            properties = None
            if term.get("property_values"):
                properties = {k: ";".join(v) for k, v in term["property_values"].items()}
            rows.append({
                "sys_oterm_id": term_id,
                "parent_sys_oterm_id": term.get("parent", ""),
                "sys_oterm_ontology": ontology_name,
                "sys_oterm_name": name,
                "sys_oterm_synonyms": json.dumps(term.get("synonyms") or []),
                "sys_oterm_definition": term.get("definition", ""),
                "sys_oterm_links": json.dumps(term.get("xrefs") or []),
                "sys_oterm_properties": json.dumps(properties, sort_keys=True) if properties else "",
            })
        stats[ontology_name] = {
            "available_terms": len(terms),
            "included_terms": included_count,
        }

    with out_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [col["column"] for col in SYS_OTERM_SCHEMA]
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return stats


def process_field(field: dict[str, Any], type_name: str, current_table: str, type_to_table: dict[str, str],
                  units_lookup: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    unit_name = units_lookup.get(field.get("units_term", ""))

    def build(col_name: str, col_type: str, nullable: bool, plain_comment: str,
              fk: str | None = None, is_pk: bool = False, is_upk: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
        schema_col = {
            "column": col_name,
            "type": col_type,
            "nullable": nullable,
            "comment": build_json_comment(field, plain_comment, type_to_table, fk, is_pk, is_upk, unit_name),
        }
        typedef_row = {
            "type_name": type_name,
            "field_name": field.get("name"),
            "cdm_column_name": col_name,
            "scalar_type": field.get("scalar_type", "text"),
            "is_required": bool(field.get("required", False)),
            "is_pk": bool(field.get("PK", False)),
            "is_upk": bool(field.get("UPK", False)),
            "fk": fk or "",
            "constraint": json.dumps(field.get("constraint")) if isinstance(field.get("constraint"), (list, dict)) else (field.get("constraint") or ""),
            "comment": plain_comment,
            "units_sys_oterm_id": field.get("units_term", ""),
            "units_sys_oterm_name": unit_name or "",
            "type_sys_oterm_id": field.get("type_term", ""),
            "type_sys_oterm_name": units_lookup.get(field.get("type_term", ""), ""),
        }
        return schema_col, typedef_row

    if field.get("scalar_type") == "term":
        base = normalize_name(field.get("name", ""))
        user_comment = field.get("comment")
        id_comment = f"{user_comment}, ontology term CURIE" if user_comment else f"Foreign key to `sys_oterm` (term id for field `{field.get('name')}`), ontology term CURIE"
        name_comment = user_comment or f"Term name for field `{field.get('name')}`"
        id_field, id_typedef = build(f"{base}_sys_oterm_id", "STRING", not field.get("required", False), id_comment, fk="sys_oterm.id")
        name_field, name_typedef = build(f"{base}_sys_oterm_name", "STRING", not field.get("required", False), name_comment)
        return [id_field, name_field], [id_typedef, name_typedef], [{
            "orig_name": field.get("name"),
            "id_col": id_field["column"],
            "name_col": name_field["column"],
        }]

    col_name = field_to_column_name(field, current_table, type_to_table, units_lookup)
    col_type = schema_type(field.get("scalar_type", "text"))
    nullable = not field.get("required", False)
    if field.get("PK", False):
        plain = field.get("comment") or f"Primary key for table `{current_table}`"
        schema_col, typedef = build(col_name, col_type, nullable, plain, is_pk=True)
    elif field.get("UPK", False):
        plain = field.get("comment") or f"User-defined unique key for table `{current_table}`"
        schema_col, typedef = build(col_name, col_type, nullable, plain, is_upk=True)
    elif field.get("FK"):
        ref_type, _ = parse_fk(field["FK"])
        plain = field.get("comment") or f"Foreign key to `{type_to_table.get(ref_type, ref_type.lower())}`"
        schema_col, typedef = build(col_name, col_type, nullable, plain, fk=field.get("FK"))
    else:
        plain = field.get("comment") or f"Field `{field.get('name')}`"
        schema_col, typedef = build(col_name, col_type, nullable, plain)
    return [schema_col], [typedef], []


def generate_schema(type_def: dict[str, Any], table_name: str, type_to_table: dict[str, str],
                    units_lookup: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    schema: list[dict[str, Any]] = []
    typedef_rows: list[dict[str, Any]] = []
    term_mappings: list[dict[str, Any]] = []
    for field in type_def.get("fields", []):
        fields, rows, terms = process_field(field, type_def.get("name", ""), table_name, type_to_table, units_lookup)
        schema.extend(fields)
        typedef_rows.extend(rows)
        term_mappings.extend(terms)

    pk_name = f"{table_name}_id"
    if not any(col["column"] == pk_name for col in schema):
        plain = f"Primary key for table `{table_name}`"
        schema.insert(0, {
            "column": pk_name,
            "type": "STRING",
            "nullable": False,
            "comment": json.dumps({"description": plain, "type": "primary_key"}),
        })
        typedef_rows.insert(0, {
            "type_name": type_def.get("name", ""),
            "field_name": "id",
            "cdm_column_name": pk_name,
            "scalar_type": "text",
            "is_required": True,
            "is_pk": True,
            "is_upk": False,
            "fk": "",
            "constraint": "",
            "comment": plain,
            "units_sys_oterm_id": "",
            "units_sys_oterm_name": "",
            "type_sys_oterm_id": "",
            "type_sys_oterm_name": "",
        })
    return schema, typedef_rows, term_mappings


def split_term(value: str) -> tuple[str, str]:
    value = value or ""
    match = re.search(r"<([^>]+)>", value)
    term_id = match.group(1) if match else ""
    name = re.sub(r"\s*<[^>]+>\s*", "", value).strip()
    return term_id, name


def array_to_json(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "[]"
    if value.startswith("[") and value.endswith("]"):
        body = value[1:-1].strip()
        if not body:
            return "[]"
        return json.dumps([part.strip() for part in re.split(r",\s*", body) if part.strip()])
    return json.dumps([value])


def replace_id_prefix(value: str, old_prefix: str, new_prefix: str, is_array: bool) -> str:
    if not value:
        return value
    if is_array:
        try:
            items = json.loads(array_to_json(value))
        except json.JSONDecodeError:
            return value
        return json.dumps([re.sub(f"^{re.escape(old_prefix)}", new_prefix, item) for item in items])
    return re.sub(f"^{re.escape(old_prefix)}", new_prefix, value)


def normalize_static_row(row: dict[str, str], tdef: dict[str, Any], table_name: str, schema: list[dict[str, Any]],
                         term_mappings: list[dict[str, Any]], type_to_table: dict[str, str],
                         preferred_name: dict[str, str], units_lookup: dict[str, str]) -> dict[str, str]:
    working = {}
    for key, value in row.items():
        working[key] = normalize_repository_text(value)
    final: dict[str, str] = {}
    schema_cols = {col["column"]: col for col in schema}

    if "name" in working and f"{table_name}_name" in schema_cols:
        final[f"{table_name}_name"] = working["name"]
    if "description" in working and f"{table_name}_description" in schema_cols:
        final[f"{table_name}_description"] = working["description"]

    for field in tdef.get("fields", []):
        if field.get("scalar_type") == "term":
            continue
        orig = field["name"]
        new_name = field_to_column_name(field, table_name, type_to_table, units_lookup)
        source_value = working.get(orig)
        if source_value is None and field.get("FK"):
            ref_type, is_array = parse_fk(field["FK"])
            source_value = working.get(f"{ref_type.lower()}{'_ids' if is_array else '_id'}")
        if source_value is None:
            continue
        if schema_cols.get(new_name, {}).get("type", "").startswith("ARRAY<"):
            source_value = array_to_json(source_value)
        final[new_name] = source_value

    for mapping in term_mappings:
        term_id, term_name = split_term(working.get(mapping["orig_name"], ""))
        final[mapping["id_col"]] = term_id
        final[mapping["name_col"]] = term_name

    original_type = tdef.get("name", "")
    preferred_type = preferred_name.get(original_type, original_type)
    pk_col = f"{table_name}_id"
    if pk_col in schema_cols:
        pk_value = final.get(pk_col, working.get("id", ""))
        final[pk_col] = replace_id_prefix(pk_value, original_type, preferred_type, False)

    for field in tdef.get("fields", []):
        fk = field.get("FK")
        if not fk:
            continue
        ref_type, is_array = parse_fk(fk)
        pref_ref = preferred_name.get(ref_type, ref_type)
        if pref_ref == ref_type:
            continue
        col_name = field_to_column_name(field, table_name, type_to_table, units_lookup)
        if col_name in final:
            final[col_name] = replace_id_prefix(final[col_name], ref_type, pref_ref, is_array)

    return {col["column"]: final.get(col["column"], "") for col in schema}


def write_sys_typedef(rows: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [col["column"] for col in SYS_TYPEDEF_SCHEMA]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def stage_source_files(run_dir: Path, typedef_path: Path, ontology_dir: Path, used_ontologies: set[str]) -> dict[str, Any]:
    source_schema_dir = run_dir / "coral_export" / "schema"
    source_ontology_dir = run_dir / "coral_export" / "ontologies"
    upload_source_data_dir = run_dir / "berdl_upload" / "source" / "data"
    upload_source_ontology_dir = run_dir / "berdl_upload" / "source" / "ontologies"
    for directory in [source_schema_dir, source_ontology_dir, upload_source_data_dir, upload_source_ontology_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    for directory in [source_ontology_dir, upload_source_ontology_dir]:
        for stale_obo in directory.glob("*.obo"):
            stale_obo.unlink()

    typedef_dst = source_schema_dir / "typedef.json"
    shutil.copy2(typedef_path, typedef_dst)
    upload_typedef = upload_source_data_dir / "typedef.json"
    shutil.copy2(typedef_path, upload_typedef)

    copied_ontologies = []
    upload_files = [{
        "local_path": str(upload_typedef),
        "bronze_path": "source/data/typedef.json",
        "source_kind": "typedef",
    }]
    for path in ontology_paths(ontology_dir):
        if path.stem not in used_ontologies:
            continue
        dst = source_ontology_dir / path.name
        shutil.copy2(path, dst)
        upload_ontology = upload_source_ontology_dir / path.name
        shutil.copy2(path, upload_ontology)
        copied_ontologies.append(str(dst))
        upload_files.append({
            "local_path": str(upload_ontology),
            "bronze_path": f"source/ontologies/{path.name}",
            "source_kind": "ontology",
        })
    upload_manifest = run_dir / "berdl_upload" / "source" / "upload_manifest.json"
    upload_manifest.write_text(json.dumps({"files": upload_files}, indent=2), encoding="utf-8")
    return {
        "typedef": str(typedef_dst),
        "ontologies": copied_ontologies,
        "upload_typedef": str(upload_typedef),
        "upload_ontologies": str(upload_source_ontology_dir),
        "upload_manifest": str(upload_manifest),
        "upload_files": upload_files,
    }


def prepare_coral_metadata(run_dir: Path, repo_root: Path | None = None) -> dict[str, Any]:
    repo_root = repo_root or Path.cwd()
    typedef_path, ontology_dir = read_dotenv_paths(repo_root / ".env")
    if not typedef_path or not typedef_path.exists():
        raise FileNotFoundError("CORAL_TYPEDEF must point to an existing typedef.json")
    if not ontology_dir or not ontology_dir.exists():
        raise FileNotFoundError("CORAL_ONTOLOGIES must point to an existing ontology directory")

    data_dir = run_dir / "berdl_upload" / "data"
    metadata_dir = run_dir / "metadata"
    data_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    ontology_terms, term_lookup, units_lookup, raw_ontology_stats = load_ontology_terms(ontology_dir)

    typedef_data = load_typedef(typedef_path)
    type_to_table, type_defs = typedef_context(typedef_data)
    preferred_name = {t["name"]: t.get("preferred_name") or t["name"] for t in type_defs}

    table_schemas: dict[str, list[dict[str, Any]]] = {"sys_oterm": SYS_OTERM_SCHEMA}
    table_comments: dict[str, str] = {"sys_oterm": "Ontology terms used in CORAL"}
    type_to_table_json: dict[str, str] = {}
    all_typedef_rows: list[dict[str, Any]] = []

    for tdef in type_defs:
        coral_type = tdef.get("name")
        if not coral_type:
            continue
        table_name = type_to_table[coral_type]
        schema, typedef_rows, term_mappings = generate_schema(tdef, table_name, type_to_table, units_lookup)
        table_schemas[table_name] = schema
        table_comments[table_name] = (tdef.get("comment") or "").strip() or f"CDM table for CORAL type `{coral_type}`"
        type_to_table_json[coral_type] = table_name
        all_typedef_rows.extend(typedef_rows)

        source = run_dir / "coral_export" / "static_tsv" / f"{coral_type}.tsv"
        fallback = data_dir / f"{coral_type}.tsv"
        if not source.exists() and fallback.exists():
            source = fallback
        if not source.exists():
            continue

        target = data_dir / f"{table_name}.tsv"
        with source.open(newline="", encoding="utf-8") as in_handle, target.open("w", newline="", encoding="utf-8") as out_handle:
            reader = csv.DictReader(in_handle, delimiter="\t")
            fieldnames = [col["column"] for col in schema]
            writer = csv.DictWriter(out_handle, delimiter="\t", fieldnames=fieldnames)
            writer.writeheader()
            for row in reader:
                writer.writerow(normalize_static_row(
                    row, tdef, table_name, schema, term_mappings,
                    type_to_table, preferred_name, units_lookup,
                ))

    table_schemas["sys_typedef"] = SYS_TYPEDEF_SCHEMA
    table_comments["sys_typedef"] = "CORAL type definitions"
    write_sys_typedef(all_typedef_rows, data_dir / "sys_typedef.tsv")

    referenced_terms = collect_referenced_terms(
        run_dir / "berdl_upload" / "data",
        run_dir / "berdl_upload" / "schema",
        set(term_lookup),
        all_typedef_rows,
    )
    included_terms = expand_with_ancestors(referenced_terms, term_lookup)
    ontology_stats = write_sys_oterm(ontology_terms, included_terms, data_dir / "sys_oterm.tsv")
    used_ontologies = {ontology for ontology, stats in ontology_stats.items() if stats["included_terms"] > 0}
    staged = stage_source_files(run_dir, typedef_path, ontology_dir, used_ontologies)

    (metadata_dir / "table_schemas.json").write_text(json.dumps(table_schemas, indent=2), encoding="utf-8")
    (metadata_dir / "table_comments.json").write_text(json.dumps(table_comments, indent=2), encoding="utf-8")
    (metadata_dir / "coral_type_to_table.json").write_text(json.dumps(type_to_table_json, indent=2), encoding="utf-8")
    report = {
        "source": staged,
        "ontology_stats": ontology_stats,
        "raw_ontology_stats": raw_ontology_stats,
        "referenced_ontology_terms": len(referenced_terms),
        "included_ontology_terms": len(included_terms),
        "tables_with_schemas": len(table_schemas),
        "static_tables_normalized": sorted(type_to_table_json.values()),
    }
    (metadata_dir / "coral_metadata_summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
