import argparse
import hashlib
import json
import os
import sys
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import requests

DEFAULT_BASE_URL = "https://hub.berdl.kbase.us/apis/mcp"
BASE_URL = os.environ.get("BERDL_BASE_URL", DEFAULT_BASE_URL)
DB_NAME = os.environ.get("BERDL_DATABASE", "enigma_coral")
REQUEST_TIMEOUT = 180
REQUEST_RETRIES = 5
REQUEST_RETRY_DELAY = 4
_DEBUG = os.environ.get("BERDL_DEBUG", "").lower() in {"1", "true", "yes"}
CACHE_DISABLED = os.environ.get("BERDL_CACHE_DISABLE", "").lower() in {"1", "true", "yes"}
CACHE_DIR = os.environ.get("BERDL_CACHE_DIR", os.path.join(os.getcwd(), ".berdl_cache"))
_CACHE_TTL = os.environ.get("BERDL_CACHE_TTL_SECONDS")
CACHE_TTL_SECONDS = int(_CACHE_TTL) if _CACHE_TTL and _CACHE_TTL.isdigit() else None


def set_debug(enabled: bool) -> None:
    global _DEBUG
    _DEBUG = enabled


def debug(message: str) -> None:
    if _DEBUG:
        print(f"[debug] {message}", file=sys.stderr)


def _summarize_payload(payload: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in ["database", "table", "limit", "offset"]:
        if key in payload:
            parts.append(f"{key}={payload[key]}")
    columns = payload.get("columns")
    if isinstance(columns, list):
        parts.append(f"columns={len(columns)}")
    filters = payload.get("filters")
    if isinstance(filters, list):
        parts.append(f"filters={len(filters)}")
    order_by = payload.get("order_by")
    if isinstance(order_by, list):
        parts.append(f"order_by={len(order_by)}")
    return ", ".join(parts)


def _cache_path(url: str, payload: Dict[str, Any]) -> str:
    raw = json.dumps({"url": url, "payload": payload}, sort_keys=True, default=str).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return os.path.join(CACHE_DIR, f"{digest}.json")


def _build_cache_entry(url: str, payload: Dict[str, Any], response: Any) -> Dict[str, Any]:
    return {"query": {"url": url, "payload": payload}, "response": response}


def _load_cache(path: str, url: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    try:
        if CACHE_TTL_SECONDS is not None:
            age = time.time() - os.path.getmtime(path)
            if age > CACHE_TTL_SECONDS:
                return None
        with open(path, "r", encoding="utf-8") as handle:
            cached = json.load(handle)
        if isinstance(cached, dict) and "query" in cached and "response" in cached:
            return cached["response"]
        if url is not None and payload is not None:
            _store_cache(path, _build_cache_entry(url, payload, cached))
        return cached
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _store_cache(path: str, data: Any) -> None:
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        os.replace(tmp_path, path)
    except OSError:
        return


def post_json(path: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Any:
    url = f"{BASE_URL}{path}"
    cache_path = None
    if not CACHE_DISABLED:
        cache_path = _cache_path(url, payload)
        cached = _load_cache(cache_path, url, payload)
        if cached is not None:
            debug(f"BERDL cache hit {path} ({_summarize_payload(payload)})")
            return cached
    last_error: Optional[Exception] = None
    for attempt in range(REQUEST_RETRIES):
        try:
            debug(f"BERDL POST {path} ({_summarize_payload(payload)}) attempt={attempt + 1}")
            resp = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if cache_path is not None:
                _store_cache(cache_path, _build_cache_entry(url, payload, data))
            return data
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
            if isinstance(exc, requests.HTTPError):
                resp = exc.response
                if resp is not None and resp.status_code in {408, 504}:
                    print(
                        "[info] BERDL request timed out. "
                        f"path={path} payload={json.dumps(payload, sort_keys=True, default=str)}",
                        file=sys.stderr,
                    )
            last_error = exc
            if attempt < REQUEST_RETRIES - 1:
                time.sleep(REQUEST_RETRY_DELAY)
            else:
                raise
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Request failed for {url}")


def list_tables(headers: Dict[str, str]) -> List[str]:
    payload = {"database": DB_NAME, "use_hms": True}
    data = post_json("/delta/databases/tables/list", payload, headers)
    tables = data.get("tables") if isinstance(data, dict) else None
    if not isinstance(tables, list):
        raise ValueError(f"Unexpected tables response: {data}")
    return [str(table) for table in tables]


def get_table_schema(headers: Dict[str, str], table: str) -> List[str]:
    payload = {"database": DB_NAME, "table": table}
    data = post_json("/delta/databases/tables/schema", payload, headers)
    columns = data.get("columns") if isinstance(data, dict) else None
    if not isinstance(columns, list):
        raise ValueError(f"Unexpected schema response for {table}: {data}")
    return [str(col) for col in columns]


def count_table_rows(headers: Dict[str, str], table: str) -> int:
    payload = {"database": DB_NAME, "table": table}
    data = post_json("/delta/tables/count", payload, headers)
    if isinstance(data, dict) and "count" in data:
        return int(data["count"])
    raise ValueError(f"Unexpected count response for {table}: {data}")


def select_rows(
    headers: Dict[str, str],
    table: str,
    columns: Optional[Sequence[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    order_by: Optional[List[Dict[str, str]]] = None,
    limit: int = 1000,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    payload: Dict[str, Any] = {"database": DB_NAME, "table": table, "limit": limit, "offset": offset}
    if columns:
        payload["columns"] = [{"column": col} for col in columns]
    if filters:
        payload["filters"] = filters
    if order_by:
        payload["order_by"] = order_by
    data = post_json("/delta/tables/select", payload, headers)
    rows = data.get("data") if isinstance(data, dict) else None
    pagination = data.get("pagination") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not isinstance(pagination, dict):
        raise ValueError(f"Unexpected select response for {table}: {data}")
    return rows, pagination


def select_all_rows(
    headers: Dict[str, str],
    table: str,
    columns: Optional[Sequence[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    order_by: Optional[List[Dict[str, str]]] = None,
    limit: int = 1000,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    offset = 0
    while True:
        batch, pagination = select_rows(
            headers,
            table,
            columns=columns,
            filters=filters,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )
        rows.extend(batch)
        if not pagination.get("has_more") or not batch:
            break
        offset += len(batch)
    return rows


def discover_tables(headers: Dict[str, str]) -> List[str]:
    all_tables = list_tables(headers)
    matching_tables: List[str] = []
    for table in all_tables:
        if table.startswith("sdt_"):
            matching_tables.append(table)
        elif table.startswith("sys_"):
            matching_tables.append(table)
        elif table == "ddt_ndarray":
            matching_tables.append(table)
    return matching_tables


def find_process_metadata_columns(columns: Iterable[str]) -> Dict[str, Optional[str]]:
    process_term_name_col = next(
        (c for c in columns if "process" in c.lower() and "sys_oterm_name" in c.lower()), None
    )
    person_term_name_col = next(
        (c for c in columns if "person" in c.lower() and "sys_oterm_name" in c.lower()), None
    )
    protocol_col = next((c for c in columns if "protocol" in c.lower()), None)
    date_end_col = next((c for c in columns if "date_end" in c.lower()), None)
    return {
        "process_term_name": process_term_name_col,
        "person_term_name": person_term_name_col,
        "protocol": protocol_col,
        "date_end": date_end_col,
    }


def parse_object_ref_to_token(obj_ref: str, discovered_tables: Sequence[str]) -> Optional[str]:
    if not obj_ref or ":" not in obj_ref:
        return None
    parts = obj_ref.split(":", 1)
    if len(parts) != 2:
        return None
    type_part, id_part = parts
    if type_part.startswith("Brick-") or type_part == "Brick":
        return f"ddt_ndarray:{id_part}"
    for table in discovered_tables:
        normalized = table.lower().replace("sdt_", "").replace("ddt_", "")
        if type_part.lower() in table.lower() or normalized == type_part.lower():
            return f"{table}:{id_part}"
    type_lower = type_part.lower()
    if type_lower in ["strain", "sample", "genome", "asv", "assembly", "reads"]:
        return f"sdt_{type_lower}:{id_part}"
    return None


def parse_token(token: str) -> Tuple[Optional[str], Optional[str]]:
    if not token or ":" not in token:
        return None, None
    parts = token.split(":", 1)
    if len(parts) != 2:
        return None, None
    return parts[0], parts[1]


class ProcessDataCache:
    def __init__(
        self,
        process_rows: List[Dict[str, Any]],
        meta_columns: Dict[str, Optional[str]],
        out_lookup: Dict[str, List[Dict[str, Any]]],
    ) -> None:
        self.process_rows = process_rows
        self.meta_columns = meta_columns
        self.out_lookup = out_lookup


_PROCESS_CACHE: Optional[ProcessDataCache] = None


def load_process_cache(
    headers: Dict[str, str], discovered_tables: Sequence[str]
) -> ProcessDataCache:
    global _PROCESS_CACHE
    if _PROCESS_CACHE is not None:
        return _PROCESS_CACHE

    schema = get_table_schema(headers, "sys_process")
    meta_columns = find_process_metadata_columns(schema)
    columns = ["sys_process_id", "input_objects", "output_objects"]
    for col in meta_columns.values():
        if col and col not in columns:
            columns.append(col)
    if "sys_process_id" in schema:
        order_by = [{"column": "sys_process_id", "direction": "ASC"}]
    else:
        order_by = None
    debug("loading sys_process rows")
    process_rows = select_all_rows(headers, "sys_process", columns=columns, order_by=order_by)
    process_metadata = build_process_metadata(process_rows, meta_columns)
    out_lookup = build_provenance_lookup(process_rows, discovered_tables, process_metadata)
    debug(f"loaded {len(process_rows)} sys_process rows")

    _PROCESS_CACHE = ProcessDataCache(process_rows, meta_columns, out_lookup)
    return _PROCESS_CACHE


class NameResolver:
    def __init__(self, headers: Dict[str, str]) -> None:
        self.headers = headers
        self.schema_cache: Dict[str, List[str]] = {}
        self.table_meta: Dict[str, Tuple[str, str]] = {}
        self.name_to_id: Dict[Tuple[str, str], str] = {}
        self.id_to_name: Dict[Tuple[str, str], str] = {}

    def _load_table_meta(self, table: str) -> Tuple[str, str]:
        if table in self.table_meta:
            return self.table_meta[table]
        columns = self.schema_cache.get(table)
        if columns is None:
            columns = get_table_schema(self.headers, table)
            self.schema_cache[table] = columns
        id_col = f"{table}_id"
        name_col = f"{table}_name"
        if id_col not in columns or name_col not in columns:
            raise ValueError(f"Table '{table}' missing {id_col} or {name_col}")
        self.table_meta[table] = (id_col, name_col)
        return id_col, name_col

    def resolve_name_to_id(self, table: str, object_name: str) -> str:
        cache_key = (table, object_name)
        cached = self.name_to_id.get(cache_key)
        if cached is not None:
            return cached
        id_col, name_col = self._load_table_meta(table)
        filters = [{"column": name_col, "operator": "=", "value": object_name}]
        rows = select_all_rows(self.headers, table, columns=[id_col], filters=filters)
        if not rows:
            raise ValueError(f"Object name '{object_name}' not found in table '{table}'.")
        object_id = rows[0].get(id_col)
        if object_id is None:
            raise ValueError(f"Object name '{object_name}' returned no id in table '{table}'.")
        self.name_to_id[cache_key] = object_id
        return object_id

    def resolve_id_to_name(self, table: str, object_id: str) -> Optional[str]:
        cache_key = (table, object_id)
        cached = self.id_to_name.get(cache_key)
        if cached is not None:
            return cached
        id_col, name_col = self._load_table_meta(table)
        filters = [{"column": id_col, "operator": "=", "value": object_id}]
        rows = select_all_rows(self.headers, table, columns=[name_col], filters=filters)
        if not rows:
            return None
        name = rows[0].get(name_col)
        if name is not None:
            self.id_to_name[cache_key] = name
        return name


def object_token_from_name(resolver: NameResolver, table_name: str, object_name: str) -> str:
    object_id = resolver.resolve_name_to_id(table_name, object_name)
    return f"{table_name}:{object_id}"


def resolve_name(resolver: NameResolver, token: str) -> str:
    table_name, obj_id = parse_token(token)
    if not table_name or not obj_id:
        return token
    try:
        name = resolver.resolve_id_to_name(table_name, obj_id)
    except ValueError:
        return token
    return f"{token}  ({name})" if name else token


def build_process_metadata(
    process_rows: Iterable[Dict[str, Any]],
    meta_columns: Dict[str, Optional[str]],
) -> Dict[str, Dict[str, Any]]:
    metadata: Dict[str, Dict[str, Any]] = {}
    for row in process_rows:
        process_id = row.get("sys_process_id")
        if process_id is None:
            continue
        metadata[process_id] = {
            "process_term_name": row.get(meta_columns.get("process_term_name") or ""),
            "person_term_name": row.get(meta_columns.get("person_term_name") or ""),
            "protocol": row.get(meta_columns.get("protocol") or ""),
            "date_end": row.get(meta_columns.get("date_end") or ""),
        }
    return metadata


def build_provenance_lookup(
    process_rows: Iterable[Dict[str, Any]],
    discovered_tables: Sequence[str],
    process_metadata: Dict[str, Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    out_lookup: Dict[str, List[Dict[str, Any]]] = {}
    seen_pairs: set[Tuple[str, str]] = set()
    for row in process_rows:
        process_id = row.get("sys_process_id")
        if process_id is None:
            continue
        output_objects = row.get("output_objects") or []
        input_objects = row.get("input_objects") or []
        if not isinstance(output_objects, list):
            output_objects = [output_objects]
        if not isinstance(input_objects, list):
            input_objects = [input_objects]
        input_tokens: List[str] = []
        for inp_ref in input_objects:
            token = parse_object_ref_to_token(inp_ref, discovered_tables)
            if token:
                input_tokens.append(token)
        metadata = process_metadata.get(process_id, {})
        for out_ref in output_objects:
            token = parse_object_ref_to_token(out_ref, discovered_tables)
            if not token:
                continue
            pair_key = (token, process_id)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            out_lookup.setdefault(token, []).append(
                {
                    "id": process_id,
                    "process_term_name": metadata.get("process_term_name"),
                    "person_term_name": metadata.get("person_term_name"),
                    "protocol": metadata.get("protocol"),
                    "date_end": metadata.get("date_end"),
                    "input_objs": input_tokens,
                }
            )
    return out_lookup


def walk_provenance(
    output_obj: str,
    out_lookup: Dict[str, List[Dict[str, Any]]],
    resolver: NameResolver,
    depth: int = 0,
    visited: Optional[set] = None,
) -> None:
    if visited is None:
        visited = set()
    indent = "    " * depth
    proc_list = out_lookup.get(output_obj)
    if proc_list is None:
        print(f"{indent}{output_obj}  <-- (no upstream process)")
        return
    if _DEBUG and (depth == 0 or len(proc_list) > 1):
        debug(f"object {output_obj} has {len(proc_list)} producing process(es)")
    processes_traversed = 0
    for proc_idx, proc in enumerate(proc_list):
        process_key = (output_obj, proc["id"])
        if process_key in visited:
            if len(proc_list) > 1:
                print(f"{indent}[Process {proc_idx + 1} of {len(proc_list)}] (already traversed)")
            else:
                print(f"{indent}{output_obj} (already traversed via this process)")
            continue
        visited.add(process_key)
        processes_traversed += 1
        if len(proc_list) > 1:
            print(f"{indent}--- Process {proc_idx + 1} of {len(proc_list)} ---")
        print(
            f"{indent}Process: {proc.get('process_term_name')} | "
            f"Person: {proc.get('person_term_name')} | "
            f"Protocol: {proc.get('protocol')} | "
            f"Date: {proc.get('date_end')} | "
            f"ID: {proc.get('id')}"
        )
        input_objs = proc.get("input_objs", [])
        if input_objs:
            print(f"{indent}  Inputs ({len(input_objs)}):")
            for inp in input_objs:
                print(f"{indent}    - {resolve_name(resolver, inp)}")
                walk_provenance(inp, out_lookup, resolver, depth + 2, visited)
        else:
            print(f"{indent}  (no inputs)")
    if _DEBUG and len(proc_list) > 1 and processes_traversed < len(proc_list):
        debug(
            f"only {processes_traversed} of {len(proc_list)} processes were traversed for {output_obj}"
        )


def walk_provenance_by_name(
    resolver: NameResolver,
    out_lookup: Dict[str, List[Dict[str, Any]]],
    table_name: str,
    object_name: str,
) -> None:
    token = object_token_from_name(resolver, table_name, object_name)
    print(f"{object_name}  ({token})")
    walk_provenance(token, out_lookup, resolver, depth=1)


def build_downstream_lookup(
    out_lookup: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, List[Dict[str, Any]]]:
    downstream_lookup: Dict[str, List[Dict[str, Any]]] = {}
    for output_obj, processes in out_lookup.items():
        for proc in processes:
            for input_obj in proc.get("input_objs", []):
                downstream_lookup.setdefault(input_obj, []).append(
                    {
                        "id": proc.get("id"),
                        "process_term_name": proc.get("process_term_name"),
                        "person_term_name": proc.get("person_term_name"),
                        "protocol": proc.get("protocol"),
                        "date_end": proc.get("date_end"),
                        "output_obj": output_obj,
                    }
                )
    return downstream_lookup


def walk_downstream_provenance(
    input_obj: str,
    downstream_lookup: Dict[str, List[Dict[str, Any]]],
    resolver: NameResolver,
    depth: int = 0,
    visited: Optional[set] = None,
) -> None:
    if visited is None:
        visited = set()
    indent = "    " * depth
    proc_list = downstream_lookup.get(input_obj)
    if proc_list is None:
        print(f"{indent}{input_obj}  <-- (no downstream process)")
        return
    if _DEBUG and (depth == 0 or len(proc_list) > 1):
        debug(f"object {input_obj} has {len(proc_list)} downstream process(es)")
    processes_traversed = 0
    for proc_idx, proc in enumerate(proc_list):
        output_obj = proc.get("output_obj")
        process_key = (input_obj, proc.get("id"), output_obj)
        if process_key in visited:
            if len(proc_list) > 1:
                print(f"{indent}[Process {proc_idx + 1} of {len(proc_list)}] (already traversed)")
            else:
                print(f"{indent}{input_obj} (already traversed via this process)")
            continue
        visited.add(process_key)
        processes_traversed += 1
        if len(proc_list) > 1:
            print(f"{indent}--- Process {proc_idx + 1} of {len(proc_list)} ---")
        print(
            f"{indent}Process: {proc.get('process_term_name')} | "
            f"Person: {proc.get('person_term_name')} | "
            f"Protocol: {proc.get('protocol')} | "
            f"Date: {proc.get('date_end')} | "
            f"ID: {proc.get('id')}"
        )
        if output_obj:
            print(f"{indent}  Outputs (1):")
            print(f"{indent}    - {resolve_name(resolver, output_obj)}")
            walk_downstream_provenance(output_obj, downstream_lookup, resolver, depth + 2, visited)
        else:
            print(f"{indent}  (no outputs)")
    if _DEBUG and len(proc_list) > 1 and processes_traversed < len(proc_list):
        debug(
            f"only {processes_traversed} of {len(proc_list)} processes were traversed for {input_obj}"
        )


def walk_downstream_provenance_by_name(
    resolver: NameResolver,
    downstream_lookup: Dict[str, List[Dict[str, Any]]],
    table_name: str,
    object_name: str,
) -> None:
    token = object_token_from_name(resolver, table_name, object_name)
    print(f"{object_name}  ({token})")
    walk_downstream_provenance(token, downstream_lookup, resolver, depth=1)


def _is_coassembly_process(proc_info: Dict[str, Any], discovered_tables: Sequence[str]) -> bool:
    inputs = proc_info.get("input_objs") or []
    reads_tables = [table for table in discovered_tables if "reads" in table.lower()]
    reads_inputs = [
        inp for inp in inputs if isinstance(inp, str) and any(inp.startswith(f"{table}:") for table in reads_tables)
    ]
    return len(reads_inputs) > 1


def has_coassembled_assembly(
    output_obj: str,
    out_lookup: Dict[str, List[Dict[str, Any]]],
    discovered_tables: Sequence[str],
) -> bool:
    visited = set()

    def dfs_up(obj: str) -> bool:
        table_name, _ = parse_token(obj)
        if table_name and "assembly" in table_name.lower():
            proc_list_for_assembly = out_lookup.get(obj)
            if proc_list_for_assembly:
                for proc in proc_list_for_assembly:
                    if _is_coassembly_process(proc, discovered_tables):
                        return True
        producing_procs = out_lookup.get(obj)
        if not producing_procs:
            return False
        for proc in producing_procs:
            process_key = (obj, proc["id"])
            if process_key in visited:
                continue
            visited.add(process_key)
            for inp in proc.get("input_objs", []) or []:
                if dfs_up(inp):
                    return True
        return False

    return dfs_up(output_obj)


def has_coassembled_assembly_by_name(
    resolver: NameResolver,
    out_lookup: Dict[str, List[Dict[str, Any]]],
    discovered_tables: Sequence[str],
    table_name: str,
    object_name: str,
) -> bool:
    token = object_token_from_name(resolver, table_name, object_name)
    return has_coassembled_assembly(token, out_lookup, discovered_tables)


def query_raw_output_rows_for_object(
    headers: Dict[str, str],
    resolver: NameResolver,
    table_name: str,
    object_name: str,
) -> None:
    token = object_token_from_name(resolver, table_name, object_name)
    parsed_table, obj_id = parse_token(token)
    if not parsed_table or not obj_id:
        print("Invalid object name")
        return
    schema = get_table_schema(headers, "sys_process_output")
    id_col = f"{parsed_table}_id"
    if id_col not in schema:
        print(f"Column {id_col} not found in sys_process_output")
        return
    id_columns = [col for col in schema if col.endswith("_id")]
    columns = ["sys_process_id"] + [col for col in id_columns if col != "sys_process_id"]
    filters = [{"column": id_col, "operator": "=", "value": obj_id}]
    rows = select_all_rows(headers, "sys_process_output", columns=columns, filters=filters)
    print(f"Found {len(rows)} row(s) in sys_process_output for {object_name} ({token})")
    for idx, row in enumerate(rows, 1):
        print(f"Row {idx}:")
        print(f"  sys_process_id: {row.get('sys_process_id')}")
        for col in sorted(columns):
            if col == "sys_process_id":
                continue
            value = row.get(col)
            if value is not None:
                print(f"  {col}: {value}")


def query_sys_process_directly(
    process_rows: Iterable[Dict[str, Any]],
    resolver: NameResolver,
    meta_columns: Dict[str, Optional[str]],
    table_name: str,
    object_name: str,
) -> None:
    token = object_token_from_name(resolver, table_name, object_name)
    parsed_table, obj_id = parse_token(token)
    if not parsed_table or not obj_id:
        print("Invalid object name")
        return
    matching_rows: List[Dict[str, Any]] = []
    for row in process_rows:
        output_objs = row.get("output_objects") or []
        if not isinstance(output_objs, list):
            output_objs = [output_objs]
        if any(isinstance(obj_ref, str) and obj_ref.endswith(f":{obj_id}") for obj_ref in output_objs):
            matching_rows.append(row)
    print(f"Found {len(matching_rows)} row(s) in sys_process for {object_name} ({token})")
    for idx, row in enumerate(matching_rows, 1):
        print(f"Row {idx}:")
        print(f"  sys_process_id: {row.get('sys_process_id')}")
        for label in ("process_term_name", "person_term_name", "protocol", "date_end"):
            column = meta_columns.get(label)
            if column:
                print(f"  {label}: {row.get(column)}")
        print(f"  output_objects: {row.get('output_objects')}")


def list_all_processes_for_object(
    resolver: NameResolver,
    out_lookup: Dict[str, List[Dict[str, Any]]],
    table_name: str,
    object_name: str,
) -> None:
    token = object_token_from_name(resolver, table_name, object_name)
    proc_list = out_lookup.get(token)
    print(f"All processes for {object_name} ({token})")
    if not proc_list:
        print("  No processes found in lookup.")
        return
    print(f"  Total processes in lookup: {len(proc_list)}")
    for idx, proc in enumerate(proc_list, 1):
        print(f"  Process {idx}:")
        print(f"    ID: {proc.get('id')}")
        print(f"    Process Term: {proc.get('process_term_name')}")
        print(f"    Person: {proc.get('person_term_name')}")
        print(f"    Protocol: {proc.get('protocol')}")
        print(f"    Date End: {proc.get('date_end')}")
        input_objs = proc.get("input_objs", [])
        print(f"    Inputs ({len(input_objs)}):")
        for inp in input_objs[:5]:
            print(f"      - {inp}")
        if len(input_objs) > 5:
            print(f"      ... and {len(input_objs) - 5} more")


def show_available_tables(headers: Dict[str, str], discovered_tables: Sequence[str]) -> None:
    print("Available tables with name mappings:")
    for table in sorted(discovered_tables):
        try:
            columns = get_table_schema(headers, table)
        except ValueError as exc:
            debug(f"schema error for {table}: {exc}")
            continue
        id_col = f"{table}_id"
        name_col = f"{table}_name"
        if id_col not in columns or name_col not in columns:
            continue
        try:
            count = count_table_rows(headers, table)
        except ValueError as exc:
            debug(f"count error for {table}: {exc}")
            count = -1
        sample_payload = {"database": DB_NAME, "table": table, "limit": 3, "columns": [name_col]}
        data = post_json("/delta/tables/sample", sample_payload, headers)
        sample = data.get("sample") if isinstance(data, dict) else None
        sample_names = []
        if isinstance(sample, list):
            for row in sample:
                name = row.get(name_col)
                if name:
                    sample_names.append(str(name))
        count_str = str(count) if count >= 0 else "unknown"
        print(f"  {table}: {count_str} objects")
        if sample_names:
            print(f"    Example names: {', '.join(sample_names)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Walk CORAL provenance using the BERDL API.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BERDL_BASE_URL", DEFAULT_BASE_URL),
        help=f"MCP base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument("--show-tables", action="store_true", help="List tables with name mappings.")
    parser.add_argument(
        "--walk-provenance",
        nargs=2,
        metavar=("TABLE", "NAME"),
        help="Walk provenance starting from an object name.",
    )
    parser.add_argument(
        "--walk-downstream",
        nargs=2,
        metavar=("TABLE", "NAME"),
        help="Walk downstream provenance starting from an object name.",
    )
    parser.add_argument(
        "--coassembly",
        nargs=2,
        metavar=("TABLE", "NAME"),
        help="Check if provenance includes a co-assembled assembly.",
    )
    parser.add_argument(
        "--raw-output-rows",
        nargs=2,
        metavar=("TABLE", "NAME"),
        help="List rows from sys_process_output that contain the object.",
    )
    parser.add_argument(
        "--sys-process",
        nargs=2,
        metavar=("TABLE", "NAME"),
        help="List rows from sys_process that contain the object.",
    )
    parser.add_argument(
        "--list-processes",
        nargs=2,
        metavar=("TABLE", "NAME"),
        help="List all processes for the object from the provenance lookup.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debugging, including BERDL API calls.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    global BASE_URL
    BASE_URL = args.base_url
    token = os.environ.get("KB_AUTH_TOKEN")
    if not token:
        print("KB_AUTH_TOKEN is not set", file=sys.stderr)
        return 2
    headers = {"Authorization": f"Bearer {token}"}

    if args.debug:
        set_debug(True)
    any_action = any(
        [
            args.show_tables,
            args.walk_provenance,
            args.walk_downstream,
            args.coassembly,
            args.raw_output_rows,
            args.sys_process,
            args.list_processes,
        ]
    )
    if not any_action:
        print("No action requested. Use --help for options.", file=sys.stderr)
        return 2

    discovered_tables = discover_tables(headers)
    resolver = NameResolver(headers)

    if args.show_tables:
        show_available_tables(headers, discovered_tables)

    needs_process_data = any(
        [
            args.walk_provenance,
            args.walk_downstream,
            args.coassembly,
            args.sys_process,
            args.list_processes,
        ]
    )

    process_rows: List[Dict[str, Any]] = []
    out_lookup: Dict[str, List[Dict[str, Any]]] = {}
    downstream_lookup: Dict[str, List[Dict[str, Any]]] = {}
    meta_columns: Dict[str, Optional[str]] = {}
    if needs_process_data:
        cache = load_process_cache(headers, discovered_tables)
        process_rows = cache.process_rows
        out_lookup = cache.out_lookup
        downstream_lookup = build_downstream_lookup(out_lookup)
        meta_columns = cache.meta_columns

    if args.walk_provenance:
        table_name, object_name = args.walk_provenance
        walk_provenance_by_name(resolver, out_lookup, table_name, object_name)

    if args.walk_downstream:
        table_name, object_name = args.walk_downstream
        walk_downstream_provenance_by_name(
            resolver, downstream_lookup, table_name, object_name
        )

    if args.coassembly:
        table_name, object_name = args.coassembly
        result = has_coassembled_assembly_by_name(
            resolver, out_lookup, discovered_tables, table_name, object_name
        )
        if result:
            print(
                f'The {table_name} "{object_name}" has a co-assembled assembly in its provenance tree.'
            )
        else:
            print(
                f'The {table_name} "{object_name}" does not have a co-assembled assembly.'
            )

    if args.raw_output_rows:
        table_name, object_name = args.raw_output_rows
        query_raw_output_rows_for_object(headers, resolver, table_name, object_name)

    if args.sys_process:
        table_name, object_name = args.sys_process
        query_sys_process_directly(process_rows, resolver, meta_columns, table_name, object_name)

    if args.list_processes:
        table_name, object_name = args.list_processes
        list_all_processes_for_object(resolver, out_lookup, table_name, object_name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
