from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings
from app.domain.taxonomy import TaxonomyService
from app.services.analytics_svc import HorizonAnalyticsService
from app.services.crunchbase_svc import CrunchbaseService
from app.services.gtr_svc import GatewayResearchService
from app.services.ml_svc import ClusterService, TopicModellingService
from app.services.search_svc import SearchService
from app.services.sheet_svc import SheetService


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


@lru_cache(maxsize=1)
def get_taxonomy() -> TaxonomyService:
    return TaxonomyService()


@lru_cache(maxsize=1)
def get_search_service() -> SearchService:
    return SearchService(get_settings())


@lru_cache(maxsize=1)
def get_sheet_service() -> SheetService:
    return SheetService(get_settings())


@lru_cache(maxsize=1)
def get_gateway_service() -> GatewayResearchService:
    return GatewayResearchService()


@lru_cache(maxsize=1)
def get_crunchbase_service() -> CrunchbaseService:
    return CrunchbaseService(get_settings())


@lru_cache(maxsize=1)
def get_analytics_service() -> HorizonAnalyticsService:
    return HorizonAnalyticsService()


@lru_cache(maxsize=1)
def get_topic_service() -> TopicModellingService:
    return TopicModellingService()


@lru_cache(maxsize=1)
def get_cluster_service() -> ClusterService:
    return ClusterService()
