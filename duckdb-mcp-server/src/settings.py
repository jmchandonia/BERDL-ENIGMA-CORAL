from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Match BERDL mounting style: serve the app under /apis/mcp
    service_root_path: str = Field(default="/apis/mcp")
    app_name: str = Field(default="DuckDB MCP Server")
    app_description: str = Field(default="MCP-like REST API backed by DuckDB (enigma-coral)")
    api_version: str = Field(default="0.1.0")

    # Single “database” in BERDL terms
    berdl_database_name: str = Field(default="enigma-coral")

    # DuckDB file path
    duckdb_path: str = Field(default="cdm_store_bricks_full.db")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
