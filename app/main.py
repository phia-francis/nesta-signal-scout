from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes.cron import router as cron_router
from app.api.routes.policy import router as policy_router
from app.api.routes.radar import router as radar_router
from app.api.routes.research import router as research_router
from app.api.routes.system import router as system_router
from app.core.security import configure_cors


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    application = FastAPI()
    configure_cors(application)
    application.mount("/static", StaticFiles(directory="static"), name="static")
    application.include_router(radar_router)
    application.include_router(research_router)
    application.include_router(policy_router)
    application.include_router(system_router)
    application.include_router(cron_router)

    @application.get("/")
    def read_root() -> dict[str, str]:
        return {"status": "System Operational", "message": "Signal Scout Backend is Running"}

    return application


app = create_app()
