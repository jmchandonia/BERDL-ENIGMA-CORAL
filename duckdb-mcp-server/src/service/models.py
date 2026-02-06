from typing import Annotated, Any, Dict, List, Literal
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: Annotated[int | None, Field(description="Error code")] = None
    error_type: Annotated[str | None, Field(description="Error type")] = None
    message: Annotated[str | None, Field(description="Error message")] = None


class ComponentHealth(BaseModel):
    name: Annotated[str, Field(description="Component name")]
    status: Annotated[Literal["healthy", "unhealthy", "degraded"], Field(description="Component health status")]
    message: Annotated[str | None, Field(description="Optional status message")] = None
    latency_ms: Annotated[float | None, Field(description="Response time in milliseconds")] = None


class DeepHealthResponse(BaseModel):
    status: Annotated[Literal["healthy", "unhealthy", "degraded"], Field(description="Overall health status")]
    components: Annotated[List[ComponentHealth], Field(description="Health status of each component")]
    message: Annotated[str | None, Field(description="Summary message about system health")] = None


class DatabaseListRequest(BaseModel):
    use_hms: Annotated[bool, Field(description="Ignored for DuckDB; kept for API compatibility")] = True
    filter_by_namespace: Annotated[bool, Field(description="Ignored for DuckDB; kept for API compatibility")] = True


class DatabaseListResponse(BaseModel):
    databases: Annotated[List[str], Field(description="List of database names")]


class TableListRequest(BaseModel):
    database: Annotated[str, Field(description="Name of the database to list tables from")]
    use_hms: Annotated[bool, Field(description="Ignored for DuckDB; kept for API compatibility")] = True


class TableListResponse(BaseModel):
    tables: Annotated[List[str], Field(description="List of table names in the specified database")]


class TableSchemaRequest(BaseModel):
    database: Annotated[str, Field(description="Name of the database containing the table")]
    table: Annotated[str, Field(description="Name of the table to get schema for")]


class TableSchemaResponse(BaseModel):
    columns: Annotated[
        List[str],
        Field(
            description="List of column names in the table",
        ),
    ]


class DatabaseStructureRequest(BaseModel):
    with_schema: Annotated[bool, Field(description="Whether to include table schemas in the response")] = False
    use_hms: Annotated[bool, Field(description="Ignored for DuckDB; kept for API compatibility")] = True


class DatabaseStructureResponse(BaseModel):
    structure: Annotated[Dict[str, Any], Field(description="Database structure with tables and optionally schemas")]


class TableQueryRequest(BaseModel):
    query: Annotated[str, Field(description="SQL query to execute (SELECT-only)")]


class TableQueryResponse(BaseModel):
    result: Annotated[List[Any], Field(description="List of rows returned by the query, each as a dictionary")]


class TableCountRequest(BaseModel):
    database: Annotated[str, Field(description="Name of the database containing the table")]
    table: Annotated[str, Field(description="Name of the table to count rows in")]


class TableCountResponse(BaseModel):
    count: Annotated[int, Field(description="Total number of rows in the table")]


class TableSampleRequest(BaseModel):
    database: Annotated[str, Field(description="Name of the database containing the table")]
    table: Annotated[str, Field(description="Name of the table to sample from")]
    limit: Annotated[int, Field(description="Max rows", gt=0, le=1000)] = 10
    columns: Annotated[List[str] | None, Field(description="Columns to return")] = None
    where_clause: Annotated[str | None, Field(description="SQL WHERE clause (no leading WHERE)")] = None


class TableSampleResponse(BaseModel):
    sample: Annotated[List[Any], Field(description="List of rows, each as a dictionary")]


class JoinClause(BaseModel):
    join_type: Annotated[Literal["INNER", "LEFT", "RIGHT", "FULL"], Field(description="JOIN type")]
    database: Annotated[str, Field(description="Database containing join table")]
    table: Annotated[str, Field(description="Table to join")]
    on_left_column: Annotated[str, Field(description="Left table join column")]
    on_right_column: Annotated[str, Field(description="Right table join column")]


class ColumnSpec(BaseModel):
    column: Annotated[str, Field(description="Column name to select")]
    table_alias: Annotated[str | None, Field(description="Alias for disambiguation")] = None
    alias: Annotated[str | None, Field(description="Output alias")] = None


class AggregationSpec(BaseModel):
    function: Annotated[Literal["COUNT", "SUM", "AVG", "MIN", "MAX"], Field(description="Aggregation fn")]
    column: Annotated[str, Field(description="Column to aggregate or '*' for COUNT(*)")]
    alias: Annotated[str | None, Field(description="Output alias")] = None


class FilterCondition(BaseModel):
    column: Annotated[str, Field(description="Column name to filter on")]
    operator: Annotated[
        Literal["=", "!=", "<", ">", "<=", ">=", "IN", "NOT IN", "LIKE", "NOT LIKE", "IS NULL", "IS NOT NULL", "BETWEEN"],
        Field(description="Operator")
    ]
    value: Annotated[Any | None, Field(description="Value for comparison")] = None
    values: Annotated[List[Any] | None, Field(description="Values for IN/NOT IN/BETWEEN")] = None


class OrderBySpec(BaseModel):
    column: Annotated[str, Field(description="Column to sort by")]
    direction: Annotated[Literal["ASC", "DESC"], Field(description="Direction")] = "ASC"


class PaginationInfo(BaseModel):
    limit: Annotated[int, Field(description="Rows requested")]
    offset: Annotated[int, Field(description="Rows skipped")]
    total_count: Annotated[int, Field(description="Total matching rows")]
    has_more: Annotated[bool, Field(description="More rows beyond this page")]


class TableSelectRequest(BaseModel):
    database: Annotated[str, Field(description="Primary database")]
    table: Annotated[str, Field(description="Primary table")]
    joins: Annotated[List[JoinClause] | None, Field(description="JOIN clauses")] = None
    columns: Annotated[List[ColumnSpec] | None, Field(description="Columns (None => *)")] = None
    distinct: Annotated[bool, Field(description="DISTINCT")] = False
    aggregations: Annotated[List[AggregationSpec] | None, Field(description="Aggregations")] = None
    filters: Annotated[List[FilterCondition] | None, Field(description="WHERE conditions")] = None
    group_by: Annotated[List[str] | None, Field(description="GROUP BY columns")] = None
    having: Annotated[List[FilterCondition] | None, Field(description="HAVING conditions")] = None
    order_by: Annotated[List[OrderBySpec] | None, Field(description="ORDER BY")] = None
    limit: Annotated[int, Field(description="LIMIT", gt=0, le=10000)] = 100
    offset: Annotated[int, Field(description="OFFSET", ge=0)] = 0


class TableSelectResponse(BaseModel):
    data: Annotated[List[Dict[str, Any]], Field(description="Rows")]
    pagination: Annotated[PaginationInfo, Field(description="Pagination metadata")]
