from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings
from app.domain.taxonomy import TaxonomyService
from app.services.analytics_svc import HorizonAnalyticsService
from app.services.openalex_svc import OpenAlexService
from app.services.gtr_svc import GatewayResearchService
from app.services.cluster_svc import ClusterService
from app.services.llm_svc import LLMService
from app.services.search_svc import SearchService
from app.services.sheet_svc import SheetService
from app.services.scan_logic import ScanOrchestrator


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
def get_openalex_service() -> OpenAlexService:
    return OpenAlexService(get_settings())


@lru_cache(maxsize=1)
def get_analytics_service() -> HorizonAnalyticsService:
    return HorizonAnalyticsService()




@lru_cache(maxsize=1)
def get_cluster_service() -> ClusterService:
    return ClusterService()


@lru_cache(maxsize=1)
def get_scan_orchestrator() -> ScanOrchestrator:
    return ScanOrchestrator(
        gateway_service=get_gateway_service(),
        openalex_service=get_openalex_service(),
        search_service=get_search_service(),
        analytics_service=get_analytics_service(),
        taxonomy=get_taxonomy(),
        llm_service=get_llm_service(),
    )


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    return LLMService()
