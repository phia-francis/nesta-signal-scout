from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.cron import router as cron_router
from app.api.routes.policy import router as policy_router
from app.api.routes.intelligence import router as intelligence_router
from app.api.routes.radar import router as radar_router
from app.api.routes.research import router as research_router
from app.api.routes.system import router as system_router
from app.core.security import configure_cors


def _has_any_env(*names: str) -> bool:
    return any(bool(os.getenv(name)) for name in names)


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    missing: list[str] = []
    if not _has_any_env("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    if not _has_any_env("Google Search_API_KEY", "Google_Search_API_KEY", "GOOGLE_SEARCH_API_KEY", "GOOGLE_SEARCH_KEY"):
        missing.append("Google Search_API_KEY")
    if not _has_any_env("Google Search_CX", "Google_Search_CX", "GOOGLE_SEARCH_CX"):
        missing.append("Google Search_CX")

    if missing:
        raise RuntimeError(f"Missing critical environment variables: {', '.join(missing)}")

    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    application = FastAPI(lifespan=app_lifespan)
    configure_cors(application)
    application.mount("/static", StaticFiles(directory="static"), name="static")
    application.include_router(radar_router)
    application.include_router(research_router)
    application.include_router(policy_router)
    application.include_router(intelligence_router)
    application.include_router(system_router)
    application.include_router(cron_router)

    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logging.error("Unhandled exception at %s", request.url.path, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "msg": "An internal system error occurred. Please check server logs.",
            },
        )

    @application.get("/")
    def read_root() -> dict[str, str]:
        return {"status": "System Operational", "message": "Signal Scout Backend is Running"}

    return application


app = create_app()
