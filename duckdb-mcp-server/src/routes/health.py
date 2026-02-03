import time
from fastapi import APIRouter

from src.db import duckdb_conn
from src.service.models import ComponentHealth, DeepHealthResponse

router = APIRouter(tags=["health"])


def _timed(name: str, fn):
    start = time.time()
    try:
        res = fn()
        latency_ms = (time.time() - start) * 1000
        if res is True:
            return ComponentHealth(name=name, status="healthy", latency_ms=round(latency_ms, 2))
        return ComponentHealth(name=name, status="degraded", message=str(res), latency_ms=round(latency_ms, 2))
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        return ComponentHealth(name=name, status="unhealthy", message=str(e)[:200], latency_ms=round(latency_ms, 2))


@router.get(
    "/health",
    response_model=DeepHealthResponse,
    summary="Health check",
    description="Returns detailed health status of backend services (DuckDB).",
)
async def health_check() -> DeepHealthResponse:
    def check_duckdb():
        with duckdb_conn() as con:
            con.execute("SELECT 1").fetchone()
        return True

    components = [_timed("duckdb", check_duckdb)]
    statuses = [c.status for c in components]
    overall = "healthy" if all(s == "healthy" for s in statuses) else ("degraded" if any(s == "degraded" for s in statuses) else "unhealthy")
    return DeepHealthResponse(status=overall, components=components)
