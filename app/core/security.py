from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS: list[str] = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://phia-francis.github.io",
    "https://phia-francis.github.io/",
    "https://nesta-signal-backend.onrender.com",
]


def configure_cors(application: FastAPI) -> None:
    """Apply strict CORS rules to the FastAPI application."""

    application.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
