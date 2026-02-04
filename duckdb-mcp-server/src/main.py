import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from src.routes import delta, health
from src.service.models import ErrorResponse
from src.settings import get_settings


def create_application() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.api_version,
        responses={
            "4XX": {"model": ErrorResponse},
            "5XX": {"model": ErrorResponse},
        },
    )

    app.add_middleware(GZipMiddleware)
    app.include_router(health.router)
    app.include_router(delta.router)

    # Mount at /apis/mcp like the BERDL server does
    if settings.service_root_path:
        root_app = FastAPI()
        root_app.mount(settings.service_root_path, app)
        return root_app

    return app


if __name__ == "__main__":
    app_instance = create_application()

    uvicorn.run(app_instance, host="10.2.2.14", port=80)
