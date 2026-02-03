from __future__ import annotations

import duckdb
from contextlib import contextmanager
from typing import Iterator

from src.settings import get_settings


@contextmanager
def duckdb_conn() -> Iterator[duckdb.DuckDBPyConnection]:
    settings = get_settings()
    # DuckDB connects directly to the file
    con = duckdb.connect(database=settings.duckdb_path, read_only=True)
    try:
        yield con
    finally:
        con.close()
