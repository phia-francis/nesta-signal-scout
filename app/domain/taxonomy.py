from __future__ import annotations

import keywords as keyword_source


class TaxonomyService:
    """Typed access to keyword taxonomy constants."""

    @property
    def mission_keywords(self) -> dict[str, list[str]]:
        return keyword_source.MISSION_KEYWORDS

    @property
    def cross_cutting_keywords(self) -> list[str]:
        return keyword_source.CROSS_CUTTING_KEYWORDS

    @property
    def mission_priorities(self) -> dict[str, list[str]]:
        return keyword_source.MISSION_PRIORITIES

    @property
    def signal_types(self) -> dict[str, list[str]]:
        return keyword_source.SIGNAL_TYPES

    @property
    def blacklist(self) -> list[str]:
        return keyword_source.BLACKLIST

    @property
    def generic_topics(self) -> list[str]:
        return keyword_source.GENERIC_TOPICS
