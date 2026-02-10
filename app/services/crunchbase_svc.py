from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)


class CrunchbaseService:
    """Compatibility shim for legacy imports.

    Deprecated: use OpenAlexService for research signal retrieval.
    """

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        logger.warning("CrunchbaseService is deprecated. Use OpenAlexService instead.")

    def search_company(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        """Legacy no-op method kept for backwards compatibility."""
        return []
