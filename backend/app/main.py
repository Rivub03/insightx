# app/main.py
#
# PURPOSE:
#   FastAPI application factory. Creates the app instance, registers
#   middleware, and mounts all routers. This is the entry point for uvicorn.
#
# USAGE:
#   Development:  uvicorn app.main:app --reload --port 8000
#   Production:   uvicorn app.main:app --workers 4 --port 8000

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.modules.datasources.router import router as datasources_router


def create_app() -> FastAPI:
    """
    Application factory function.
    Keeps app creation separate from the module-level `app` variable,
    which makes testing cleaner (you can call create_app() with different configs).
    """
    app = FastAPI(
        title="InsightX API",
        version="1.0.0",
        description="InsightX Agentic Reporting Platform — M1: Data Source Onboarding",
        # FastAPI auto-generates /docs (Swagger UI) and /redoc from route definitions
    )

    # CORS — allow the React dev server to reach the API
    # Adjust allow_origins for staging/production deployments
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,  # Required for cookie-based sessions
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount the datasources router under the /api/v1/datasources prefix
    app.include_router(
        datasources_router,
        prefix="/api/v1/datasources",
        tags=["Data Sources"],
    )

    return app


# Module-level app instance — uvicorn points at this
app = create_app()