from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.cron import router as cron_router
from app.api.routes.policy import router as policy_router
from app.api.routes.intelligence import router as intelligence_router
from app.api.routes.radar import router as radar_router
from app.api.routes.research import router as research_router
from app.api.routes.system import router as system_router
from app.core.config import get_settings


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    try:
        settings = get_settings()
        missing: list[str] = []
        if not settings.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        if not settings.GOOGLE_SEARCH_API_KEY:
            missing.append("GOOGLE_SEARCH_API_KEY")
        if not settings.GOOGLE_SEARCH_CX:
            missing.append("GOOGLE_SEARCH_CX")

        if missing:
            logging.warning("Missing environment variables at startup: %s", ", ".join(missing))
    except Exception:
        logging.warning("Startup environment check failed; continuing without strict validation", exc_info=True)

    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    application = FastAPI(
        title="Nesta Signal Scout",
        version="1.0",
        lifespan=app_lifespan,
    )

    settings = get_settings()
    allowed_origins = [
        "https://phia-francis.github.io",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    if getattr(settings, "CORS_ORIGINS", None):
        allowed_origins.extend(str(origin).rstrip("/") for origin in settings.CORS_ORIGINS)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(dict.fromkeys(allowed_origins)),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
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
