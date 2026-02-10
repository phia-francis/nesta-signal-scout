from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_search_service
from app.domain.models import PolicyRequest
from app.services.search_svc import SearchService

router = APIRouter(prefix="/api", tags=["policy"])


@router.post("/mode/policy")
async def policy_mode(
    request: PolicyRequest,
    search_service: SearchService = Depends(get_search_service),
) -> dict[str, Any]:
    """Run policy-specific search query and return standard response shape."""
    query = f"(site:gov.uk OR site:parliament.uk) {request.topic}"
    results = await search_service.search(query)
    return {"status": "success", "data": {"results": results}}
