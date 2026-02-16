from __future__ import annotations

import os
from secrets import compare_digest

from fastapi import APIRouter, Depends, Header, HTTPException, status

router = APIRouter(prefix="/api/cron", tags=["cron"])


def verify_cron_secret(x_cron_auth: str | None = Header(default=None)) -> None:
    """Require a shared secret header for cron-triggered endpoints."""
    expected_secret = os.getenv("CRON_SECRET")
    if not expected_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cron secret is not configured.",
        )

    if not x_cron_auth or not compare_digest(x_cron_auth, expected_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized cron invocation.",
        )


@router.post("/briefing", dependencies=[Depends(verify_cron_secret)])
async def create_briefing() -> dict[str, str]:
    """Compatibility endpoint for scheduled briefing jobs."""
    return {"status": "queued"}
