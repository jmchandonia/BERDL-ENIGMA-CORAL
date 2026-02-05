from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Dict, List, Tuple

import sqlparse
from fastapi import APIRouter, status

from src.db import duckdb_conn
from src.service.errors import bad_request, not_found
from src.service.models import (
    DatabaseListRequest, DatabaseListResponse,
    DatabaseStructureRequest, DatabaseStructureResponse,
    TableCountRequest, TableCountResponse,
    TableListRequest, TableListResponse,
    TableQueryRequest, TableQueryResponse,
    TableSampleRequest, TableSampleResponse,
    TableSchemaRequest, TableSchemaResponse,
    TableSelectRequest, TableSelectResponse,
    PaginationInfo,
)
from src.settings import get_settings

router = APIRouter(prefix="/delta", tags=["Delta Lake"])

# ---- Safety checks (modeled after BERDL delta_service.py) ----
FORBIDDEN_KEYWORDS = {
    "drop", "truncate", "delete", "insert", "update", "create", "alter", "merge", "replace", "rename", "vacuum",
}
DISALLOW_SQL_META_CHARS = {"--", "/*", "*/", ";", "\\"}
ALLOWED_STATEMENTS = {"select"}

VALID_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

def _require_enigma_coral(db: str) -> None:
    if db != get_settings().berdl_database_name:
        raise not_found(f"Database [{db}] not found")

def _q_ident(name: str) -> str:
    # DuckDB supports standard SQL double-quote quoting
    if not VALID_IDENTIFIER_PATTERN.match(name):
        raise bad_request(f"Invalid identifier: {name}")
    return f'"{name}"'

def _q_any_ident(name: str) -> str:
    # Use for DuckDB-generated column names (e.g., from DESCRIBE); escape quotes defensively.
    safe = name.replace('"', '""')
    return f'"{safe}"'

def _check_query_is_valid_select_only(query: str) -> None:
    try:
        statements = sqlparse.parse(query)
    except Exception as e:
        raise bad_request(f"Query is not valid SQL: {e}")
    if len(statements) != 1:
        raise bad_request("Query must contain exactly one statement")
    st = statements[0]
    if st.get_type().lower() not in ALLOWED_STATEMENTS:
        raise bad_request(f"Only SELECT statements are allowed (got {st.get_type()})")
    qlow = query.lower()
    if any(schema in qlow for schema in ("pg_", "pg_catalog", "information_schema")):
        # keep parity with BERDL’s “forbidden schemas” spirit
        raise bad_request("Query references forbidden system schema")
    if any(m in query for m in DISALLOW_SQL_META_CHARS):
        bad = ", ".join(sorted([m for m in DISALLOW_SQL_META_CHARS if m in query]))
        raise bad_request(f"Query contains disallowed metacharacter(s): {bad}")
    if any(k in qlow for k in FORBIDDEN_KEYWORDS):
        bad = ", ".join(sorted([k for k in FORBIDDEN_KEYWORDS if k in qlow]))
        raise bad_request(f"Query contains forbidden keyword(s): {bad}")

# ---- Metadata helpers ----
def _list_tables() -> List[str]:
    with duckdb_conn() as con:
        rows = con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main' AND table_type='BASE TABLE' ORDER BY table_name"
        ).fetchall()
    return [r[0] for r in rows]

def _table_exists(table: str) -> bool:
    return table in set(_list_tables())

def _table_columns(table: str) -> List[str]:
    with duckdb_conn() as con:
        rows = con.execute(f"PRAGMA table_info({_q_ident(table)})").fetchall()
    # PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
    return [r[1] for r in rows]

@lru_cache(maxsize=256)
def _table_column_types(table: str) -> Dict[str, str]:
    with duckdb_conn() as con:
        rows = con.execute(f"PRAGMA table_info({_q_ident(table)})").fetchall()
    return {r[1]: str(r[2]) for r in rows}

def _is_float_type(type_name: str) -> bool:
    t = type_name.strip().lower()
    return ("float" in t) or ("double" in t) or (t == "real")

def _q_table_col(table: str, col: str) -> str:
    return f"{_q_ident(table)}.{_q_ident(col)}"

def _select_expr_for_column(
    table: str | None,
    col: str,
    alias: str | None,
    type_name: str | None,
) -> str:
    ref = _q_ident(col) if table is None else _q_table_col(table, col)
    if type_name and _is_float_type(type_name):
        out_name = alias or col
        return f"CAST({ref} AS DOUBLE) AS {_q_ident(out_name)}"
    if alias:
        return f"{ref} AS {_q_ident(alias)}"
    return ref


@lru_cache(maxsize=1)
def _load_schema_markdown() -> Dict[str, Dict[str, Any]]:
    settings = get_settings()
    path = settings.schema_markdown_path
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            tables: Dict[str, Dict[str, Any]] = {}
            current_table = None
            in_schema = False
            for raw_line in handle:
                line = raw_line.rstrip("\n")
                if line.startswith("## Table:"):
                    current_table = line.split(":", 1)[1].strip()
                    tables.setdefault(current_table, {"description": None, "columns": {}})
                    in_schema = False
                    continue
                if line.startswith("**Table Description:**") and current_table:
                    desc = line.split(":", 1)[1].strip()
                    tables[current_table]["description"] = desc.replace("**", "").strip()
                    continue
                if line.startswith("### Schema"):
                    in_schema = True
                    continue
                if line.startswith("### Sample Data"):
                    in_schema = False
                    continue
                if not in_schema or not current_table:
                    continue
                if line.startswith("| Column Name |"):
                    continue
                if not line.startswith("|"):
                    continue
                parts = [part.strip() for part in line.strip().strip("|").split("|")]
                if len(parts) < 4:
                    continue
                col_name, col_type, nullable, comment = parts[:4]
                tables[current_table]["columns"][col_name] = {
                    "type": col_type,
                    "nullable": nullable,
                    "comment": comment,
                }
            return tables
    except OSError:
        return {}


def _table_schema_details(table: str) -> List[Dict[str, Any]]:
    schema_md = _load_schema_markdown()
    with duckdb_conn() as con:
        rows = con.execute(f"PRAGMA table_info({_q_ident(table)})").fetchall()
    # cid, name, type, notnull, dflt_value, pk
    results: List[Dict[str, Any]] = []
    for _, name, data_type, notnull, _default, _pk in rows:
        md_table = schema_md.get(table, {})
        md_col = md_table.get("columns", {}).get(name, {})
        nullable = md_col.get("nullable") or ("No" if notnull else "Yes")
        comment = md_col.get("comment", "")
        col_type = md_col.get("type") or data_type
        results.append(
            {
                "name": name,
                "type": col_type,
                "nullable": nullable,
                "comment": comment,
            }
        )
    return results

# ---- Routes ----
@router.post(
    "/databases/list",
    response_model=DatabaseListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all databases in the Hive metastore",
    description="Compatibility endpoint: returns only ['enigma_coral'] for DuckDB backend.",
    operation_id="list_databases",
)
def list_databases(_: DatabaseListRequest) -> DatabaseListResponse:
    return DatabaseListResponse(databases=[get_settings().berdl_database_name])

@router.post(
    "/databases/tables/list",
    response_model=TableListResponse,
    status_code=status.HTTP_200_OK,
    summary="List tables in a database",
    description="Lists all tables in the single DuckDB-backed database (enigma_coral).",
    operation_id="list_database_tables",
)
def list_database_tables(req: TableListRequest) -> TableListResponse:
    _require_enigma_coral(req.database)
    return TableListResponse(tables=_list_tables())

@router.post(
    "/databases/tables/schema",
    response_model=TableSchemaResponse,
    status_code=status.HTTP_200_OK,
    summary="Get table schema",
    description="Gets the schema (column names with types, nullability, and comments) of a specific table.",
    operation_id="get_table_schema",
)
def get_table_schema(req: TableSchemaRequest) -> TableSchemaResponse:
    _require_enigma_coral(req.database)
    if not _table_exists(req.table):
        raise not_found(f"Table [{req.table}] not found in database [{req.database}]")
    return TableSchemaResponse(columns=_table_schema_details(req.table))

@router.post(
    "/databases/structure",
    response_model=DatabaseStructureResponse,
    status_code=status.HTTP_200_OK,
    summary="Get database structure",
    description="Gets structure of enigma_coral; optionally includes table schemas.",
    operation_id="get_database_structure",
)
def get_database_structure(req: DatabaseStructureRequest) -> DatabaseStructureResponse:
    db = get_settings().berdl_database_name
    tables = _list_tables()
    schema_md = _load_schema_markdown()
    if not req.with_schema:
        return DatabaseStructureResponse(
            structure={
                db: {
                    "tables": [
                        {
                            "name": t,
                            **(
                                {"description": schema_md.get(t, {}).get("description")}
                                if schema_md.get(t, {}).get("description")
                                else {}
                            ),
                        }
                        for t in tables
                    ]
                }
            }
        )
    return DatabaseStructureResponse(
        structure={
            db: {
                "tables": [
                    {
                        "name": t,
                        "columns": _table_schema_details(t),
                        **(
                            {"description": schema_md.get(t, {}).get("description")}
                            if schema_md.get(t, {}).get("description")
                            else {}
                        ),
                    }
                    for t in tables
                ]
            }
        }
    )

@router.post(
    "/tables/count",
    response_model=TableCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Count rows in a Delta table",
    description="Counts rows in a table (DuckDB).",
    operation_id="count_delta_table",
)
def count_table(req: TableCountRequest) -> TableCountResponse:
    _require_enigma_coral(req.database)
    if not _table_exists(req.table):
        raise not_found(f"Table [{req.table}] not found in database [{req.database}]")
    with duckdb_conn() as con:
        count = con.execute(f"SELECT COUNT(*) FROM {_q_ident(req.table)}").fetchone()[0]
    return TableCountResponse(count=int(count))

@router.post(
    "/tables/sample",
    response_model=TableSampleResponse,
    status_code=status.HTTP_200_OK,
    summary="Sample data from a Delta table",
    description="Returns a small sample of rows from a table (DuckDB).",
    operation_id="sample_delta_table",
)
def sample_table(req: TableSampleRequest) -> TableSampleResponse:
    _require_enigma_coral(req.database)
    if not _table_exists(req.table):
        raise not_found(f"Table [{req.table}] not found in database [{req.database}]")

    type_map = _table_column_types(req.table)
    cols = req.columns
    if cols:
        cols_sql = ", ".join(
            [_select_expr_for_column(req.table, c, None, type_map.get(c)) for c in cols]
        )
    else:
        cols_sql = ", ".join(
            [_select_expr_for_column(req.table, c, None, type_map.get(c)) for c in _table_columns(req.table)]
        )

    where_sql = ""
    if req.where_clause:
        # Validate by constructing a SELECT-only query; disallow metas, forbidden keywords
        test_query = f"SELECT 1 FROM {_q_ident(req.table)} WHERE {req.where_clause} LIMIT 1"
        _check_query_is_valid_select_only(test_query)
        where_sql = f" WHERE {req.where_clause}"

    q = f"SELECT {cols_sql} FROM {_q_ident(req.table)}{where_sql} LIMIT ?"
    with duckdb_conn() as con:
        rows = con.execute(q, [req.limit]).fetchall()
        colnames = [d[0] for d in con.description]
    result = [dict(zip(colnames, r)) for r in rows]
    return TableSampleResponse(sample=result)

@router.post(
    "/tables/query",
    response_model=TableQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query a Delta table",
    description="Executes a raw SELECT query (DuckDB).",
    operation_id="query_delta_table",
)
def query_table(req: TableQueryRequest) -> TableQueryResponse:
    _check_query_is_valid_select_only(req.query)
    with duckdb_conn() as con:
        desc_rows = con.execute(f"DESCRIBE SELECT * FROM ({req.query}) AS subq").fetchall()
        if desc_rows:
            select_exprs = []
            for name, type_name, *_rest in desc_rows:
                ref = _q_any_ident(str(name))
                if _is_float_type(str(type_name)):
                    select_exprs.append(f"CAST({ref} AS DOUBLE) AS {_q_any_ident(str(name))}")
                else:
                    select_exprs.append(ref)
            wrapped = f"SELECT {', '.join(select_exprs)} FROM ({req.query}) AS subq"
            rows = con.execute(wrapped).fetchall()
        else:
            rows = con.execute(req.query).fetchall()
        colnames = [d[0] for d in con.description]
    result = [dict(zip(colnames, r)) for r in rows]
    return TableQueryResponse(result=result)

# ---- Structured SELECT builder (/tables/select) ----
def _build_filter_sql(f, params: List[Any]) -> str:
    col = _q_ident(f.column)
    op = f.operator.upper()

    if op in ("IS NULL", "IS NOT NULL"):
        return f"{col} {op}"
    if op in ("IN", "NOT IN"):
        if not f.values:
            raise bad_request(f"{op} requires 'values'")
        placeholders = ", ".join(["?"] * len(f.values))
        params.extend(f.values)
        return f"{col} {op} ({placeholders})"
    if op == "BETWEEN":
        if not f.values or len(f.values) != 2:
            raise bad_request("BETWEEN requires exactly two values in 'values'")
        params.extend([f.values[0], f.values[1]])
        return f"{col} BETWEEN ? AND ?"
    # binary ops (=, !=, <, >, <=, >=, LIKE, NOT LIKE)
    if f.value is None:
        raise bad_request(f"Operator {op} requires 'value'")
    params.append(f.value)
    return f"{col} {op} ?"

def _build_select(req: TableSelectRequest) -> Tuple[str, List[Any], str, List[Any]]:
    _require_enigma_coral(req.database)
    if not _table_exists(req.table):
        raise not_found(f"Table [{req.table}] not found in database [{req.database}]")

    params: List[Any] = []
    base_type_map = _table_column_types(req.table)
    join_tables = [j.table for j in req.joins] if req.joins else []
    join_type_maps = {t: _table_column_types(t) for t in join_tables}

    # SELECT list
    parts: List[str] = ["SELECT"]
    if req.distinct:
        parts.append("DISTINCT")

    select_exprs: List[str] = []
    if req.aggregations:
        for a in req.aggregations:
            fn = a.function.upper()
            col = "*" if a.column == "*" else _q_ident(a.column)
            expr = f"{fn}({col})"
            if a.alias:
                expr += f" AS {_q_ident(a.alias)}"
            select_exprs.append(expr)

    if req.columns:
        for c in req.columns:
            source_table = None
            if c.table_alias:
                source_table = c.table_alias
            elif c.column in base_type_map:
                source_table = req.table
            else:
                matches = [t for t, m in join_type_maps.items() if c.column in m]
                if len(matches) == 1:
                    source_table = matches[0]
            type_name = None
            if source_table == req.table:
                type_name = base_type_map.get(c.column)
            elif source_table in join_type_maps:
                type_name = join_type_maps[source_table].get(c.column)
            expr = _select_expr_for_column(source_table, c.column, c.alias, type_name)
            select_exprs.append(expr)

    if not select_exprs:
        if join_tables:
            select_exprs = ["*"]
        else:
            select_exprs = [
                _select_expr_for_column(req.table, c, None, base_type_map.get(c))
                for c in _table_columns(req.table)
            ]

    parts.append(", ".join(select_exprs))
    parts.append(f"FROM {_q_ident(req.table)}")

    # JOINs
    if req.joins:
        for j in req.joins:
            _require_enigma_coral(j.database)
            if not _table_exists(j.table):
                raise not_found(f"Join table [{j.table}] not found in database [{j.database}]")
            jt = j.join_type.upper()
            parts.append(f"{jt} JOIN {_q_ident(j.table)} ON {_q_ident(j.on_left_column)} = {_q_ident(j.on_right_column)}")

    # WHERE
    if req.filters:
        where_params: List[Any] = []
        clauses = [_build_filter_sql(f, where_params) for f in req.filters]
        parts.append("WHERE " + " AND ".join(clauses))
        params.extend(where_params)

    # GROUP BY / HAVING
    if req.group_by:
        parts.append("GROUP BY " + ", ".join([_q_ident(c) for c in req.group_by]))
    if req.having:
        having_params: List[Any] = []
        clauses = [_build_filter_sql(f, having_params) for f in req.having]
        parts.append("HAVING " + " AND ".join(clauses))
        params.extend(having_params)

    # ORDER BY
    if req.order_by:
        parts.append(
            "ORDER BY " + ", ".join([f"{_q_ident(o.column)} {o.direction.upper()}" for o in req.order_by])
        )

    # Base query (no LIMIT/OFFSET) for COUNT(*)
    base_sql = " ".join(parts)
    base_params = list(params)

    # Pagination
    parts.append("LIMIT ? OFFSET ?")
    params.extend([req.limit, req.offset])

    sql = " ".join(parts)
    return sql, params, base_sql, base_params

@router.post(
    "/tables/select",
    response_model=TableSelectResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute a structured SELECT query",
    description="Builds and executes a SELECT query from structured parameters, with pagination metadata.",
    operation_id="select_delta_table",
)
def select_table(req: TableSelectRequest) -> TableSelectResponse:
    sql, params, base_sql, base_params = _build_select(req)

    with duckdb_conn() as con:
        # total_count
        count_sql = f"SELECT COUNT(*) FROM ({base_sql}) AS subq"
        total_count = int(con.execute(count_sql, base_params).fetchone()[0])

        rows = con.execute(sql, params).fetchall()
        colnames = [d[0] for d in con.description]

    data = [dict(zip(colnames, r)) for r in rows]
    has_more = (req.offset + req.limit) < total_count
    pagination = PaginationInfo(limit=req.limit, offset=req.offset, total_count=total_count, has_more=has_more)
    return TableSelectResponse(data=data, pagination=pagination)
