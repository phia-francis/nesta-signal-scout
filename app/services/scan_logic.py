from __future__ import annotations

import asyncio
import time
from difflib import SequenceMatcher
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from typing import Any

from dateutil import parser as date_parser

from app import keywords
from app.core.config import SCAN_RESULT_LIMIT
from app.domain.models import RawSignal, ScoredSignal, SignalCard
from app.domain.taxonomy import TaxonomyService
from app.services.analytics_svc import HorizonAnalyticsService
from app.services.gtr_svc import GatewayResearchService
from app.services.openalex_svc import OpenAlexService
from app.services.search_svc import SearchService, ServiceError

ACTIVITY_WEIGHT = 0.3
ATTENTION_WEIGHT = 0.3
RECENCY_WEIGHT = 0.4
ONE_YEAR_DAYS = 365
FIVE_YEARS_DAYS = 365 * 5
ATTENTION_CAP = 10.0
ACTIVITY_CAP = 10.0
GT_R_FUNDING_DIVISOR = 25_000.0
OPENALEX_CITATION_DIVISOR = 100.0
GOOGLE_BASELINE_ATTENTION = 7.0
FETCH_CACHE_TTL_SECONDS = 24 * 60 * 60


class ScanOrchestrator:
    """Coordinates fetching, filtering, and scoring of scan signals."""

    def __init__(
        self,
        gateway_service: GatewayResearchService,
        openalex_service: OpenAlexService,
        search_service: SearchService,
        analytics_service: HorizonAnalyticsService,
        taxonomy: TaxonomyService,
    ) -> None:
        self.gateway_service = gateway_service
        self.openalex_service = openalex_service
        self.search_service = search_service
        self.analytics_service = analytics_service
        self.taxonomy = taxonomy
        self._fetch_cache: dict[str, tuple[float, list[RawSignal], list[str]]] = {}

    @property
    def cutoff_date(self) -> datetime:
        return datetime.now(timezone.utc) - timedelta(days=ONE_YEAR_DAYS)

    def _cache_key(self, *, topic: str, mode: str, cutoff: datetime) -> str:
        return f"{topic.strip().lower()}|{mode}|{cutoff.date().isoformat()}"

    def _clone_raw_signals(self, signals: list[RawSignal]) -> list[RawSignal]:
        return [signal.model_copy(deep=True) for signal in signals]

    async def fetch_signals(
        self,
        topic: str,
        *,
        mission: str,
        mode: str,
        friction_mode: bool = False,
    ) -> tuple[list[RawSignal], list[str]]:
        """Fetch radar-mode signals from all providers concurrently with 24h cache."""
        clean_topic = topic.strip()
        if not clean_topic:
            raise ValueError("Topic is required to fetch signals.")

        cutoff_date = self.cutoff_date
        cache_key = self._cache_key(topic=clean_topic, mode=mode, cutoff=cutoff_date)
        cached = self._fetch_cache.get(cache_key)
        if cached and (time.time() - cached[0]) < FETCH_CACHE_TTL_SECONDS:
            _, cached_signals, cached_terms = cached
            return self._clone_raw_signals(cached_signals), list(cached_terms)

        related_terms = keywords.generate_broad_scan_queries([clean_topic], num_signals=3)
        from_publication_date = cutoff_date.date().isoformat()

        gtr_result, openalex_result, google_year_result, google_month_result = await asyncio.gather(
            self.gateway_service.fetch_projects(clean_topic, min_start_date=cutoff_date),
            self.openalex_service.search_works(clean_topic, from_publication_date=from_publication_date),
            self.search_service.search(clean_topic, num=SCAN_RESULT_LIMIT, freshness="year", friction_mode=friction_mode),
            self.search_service.search(clean_topic, num=SCAN_RESULT_LIMIT, freshness="month", friction_mode=friction_mode),
            return_exceptions=True,
        )

        raw_signals: list[RawSignal] = []
        raw_signals.extend(self._normalise_gtr(gtr_result, mission=mission))
        raw_signals.extend(self._normalise_openalex(openalex_result, mission=mission))
        raw_signals.extend(
            self._normalise_google(
                google_year_result,
                mission=mission,
                source_label="Google Search",
                is_novel=False,
            )
        )
        raw_signals.extend(
            self._normalise_google(
                google_month_result,
                mission=mission,
                source_label="Google Search",
                is_novel=True,
            )
        )

        self._fetch_cache[cache_key] = (time.time(), self._clone_raw_signals(raw_signals), list(related_terms))
        return raw_signals, related_terms

    def process_signals(
        self,
        raw_signals: list[RawSignal],
        *,
        mission: str,
        related_terms: list[str],
    ) -> Generator[SignalCard, None, None]:
        """Apply strict recency filtering and weighted scoring, yielding UI-ready cards."""
        cutoff_date = self.cutoff_date
        candidate_cards: list[SignalCard] = []

        for raw_signal in raw_signals:
            if raw_signal.date < cutoff_date:
                continue

            activity = self._calculate_activity(raw_signal)
            attention = self._calculate_attention(raw_signal)
            recency = self.analytics_service.calculate_recency_score(raw_signal.date)
            final = (
                (activity * ACTIVITY_WEIGHT)
                + (attention * ATTENTION_WEIGHT)
                + (recency * RECENCY_WEIGHT)
            )
            typology = self.analytics_service.classify_sweet_spot(activity, attention)

            scored = ScoredSignal(
                **raw_signal.model_dump(),
                mission=mission,
                score_activity=round(activity, 2),
                score_attention=round(attention, 2),
                score_recency=round(recency, 2),
                final_score=round(final, 2),
                typology=typology,
            )
            candidate_cards.append(self._to_signal_card(scored, related_terms=related_terms))

        for card in self._deduplicate_signals(candidate_cards):
            yield card

    async def fetch_research_deep_dive(self, query: str) -> list[SignalCard]:
        """OpenAlex-driven deep-dive research cards over 5-year horizon."""
        if not query.strip():
            raise ValueError("Research query is required.")

        from_date = (datetime.now(timezone.utc) - timedelta(days=FIVE_YEARS_DAYS)).date().isoformat()
        try:
            works = await self.openalex_service.search_works(query, from_publication_date=from_date)
        except (ServiceError, Exception):
            works = []
        raw_signals = self._normalise_openalex(works, mission="Research")
        return list(self.process_signals(raw_signals, mission="Research", related_terms=[]))

    async def fetch_policy_scan(self, topic: str) -> list[SignalCard]:
        """Policy-focused cards from high-trust government search results."""
        if not topic.strip():
            raise ValueError("Policy topic is required.")

        query = f"{topic} site:gov.uk OR filetype:pdf policy"
        try:
            results = await self.search_service.search(query, num=SCAN_RESULT_LIMIT, freshness="year")
        except (ServiceError, Exception):
            results = []
        raw_signals = self._normalise_google(results, mission="Policy", source_label="Gov/Policy", is_novel=False)
        return list(self.process_signals(raw_signals, mission="Policy", related_terms=[]))

    async def fetch_intelligence_brief(self, topic: str) -> list[SignalCard]:
        """Fast high-level brief combining GtR and OpenAlex."""
        if not topic.strip():
            raise ValueError("Intelligence topic is required.")

        cutoff_date = self.cutoff_date
        from_publication_date = cutoff_date.date().isoformat()
        gtr_result, openalex_result = await asyncio.gather(
            self.gateway_service.fetch_projects(topic, min_start_date=cutoff_date),
            self.openalex_service.search_works(topic, from_publication_date=from_publication_date),
            return_exceptions=True,
        )
        raw_signals = [
            *self._normalise_gtr(gtr_result, mission="Intelligence")[: max(1, SCAN_RESULT_LIMIT // 2)],
            *self._normalise_openalex(openalex_result, mission="Intelligence")[: max(1, SCAN_RESULT_LIMIT // 2)],
        ]
        return list(self.process_signals(raw_signals, mission="Intelligence", related_terms=[]))

    def _normalise_gtr(self, result: Any, *, mission: str) -> list[RawSignal]:
        if isinstance(result, Exception) or not isinstance(result, list):
            return []
        signals: list[RawSignal] = []
        for project in result:
            project_date = project.get("start_date")
            if not isinstance(project_date, datetime):
                project_date = datetime.now(timezone.utc)
            url_ref = project.get("grantReference") or project.get("title", "")
            signals.append(
                RawSignal(
                    source="UKRI GtR",
                    title=project.get("title", "Untitled Project"),
                    url=f"https://gtr.ukri.org/projects?ref={url_ref}",
                    abstract=project.get("abstract", ""),
                    date=project_date,
                    raw_score=float(project.get("fund_val", 0.0) or 0.0),
                    mission=mission,
                    metadata={"fund_val": float(project.get("fund_val", 0.0) or 0.0)},
                )
            )
        return signals

    def _normalise_openalex(self, result: Any, *, mission: str) -> list[RawSignal]:
        if isinstance(result, Exception) or not isinstance(result, list):
            return []
        signals: list[RawSignal] = []
        for work in result:
            work_date = self._parse_date(work.get("publication_date"))
            if not work_date:
                continue
            cited_by_count = float(work.get("cited_by_count", 0) or 0)
            signals.append(
                RawSignal(
                    source="OpenAlex",
                    title=work.get("title", "Untitled Work"),
                    url=work.get("url", ""),
                    abstract=work.get("summary", ""),
                    date=work_date,
                    raw_score=cited_by_count,
                    mission=mission,
                    metadata={"cited_by_count": cited_by_count},
                )
            )
        return signals

    def _normalise_google(self, result: Any, *, mission: str, source_label: str, is_novel: bool) -> list[RawSignal]:
        if isinstance(result, Exception) or not isinstance(result, list):
            return []
        now = datetime.now(timezone.utc)
        signals: list[RawSignal] = []
        for rank, item in enumerate(result, start=1):
            trust = float(item.get("trust", 0) or 0)
            signals.append(
                RawSignal(
                    source=source_label,
                    title=item.get("title", "Untitled Result"),
                    url=item.get("link", ""),
                    abstract=item.get("snippet", ""),
                    date=now,
                    raw_score=trust,
                    mission=mission,
                    metadata={"trust": trust, "rank": rank, "freshness": "month" if is_novel else "year"},
                    is_novel=is_novel,
                )
            )
        return signals

    def _normalise_url(self, url: str) -> str:
        cleaned = (url or "").strip().lower()
        for prefix in ("https://", "http://"):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
        if cleaned.startswith("www."):
            cleaned = cleaned[4:]
        return cleaned.rstrip("/")

    def _deduplicate_signals(self, signals: list[SignalCard]) -> list[SignalCard]:
        """Remove duplicate signals by canonical URL and fuzzy title similarity."""
        seen_urls: set[str] = set()
        kept: list[SignalCard] = []

        for signal in signals:
            normalised_url = self._normalise_url(signal.url)
            if normalised_url and normalised_url in seen_urls:
                continue

            is_fuzzy_duplicate = False
            for existing in kept:
                similarity = SequenceMatcher(
                    None,
                    signal.title.strip().lower(),
                    existing.title.strip().lower(),
                ).ratio()
                if similarity > 0.85:
                    is_fuzzy_duplicate = True
                    break

            if is_fuzzy_duplicate:
                continue

            if normalised_url:
                seen_urls.add(normalised_url)
            kept.append(signal)

        return kept

    def _calculate_activity(self, raw_signal: RawSignal) -> float:
        if raw_signal.source == "UKRI GtR":
            return min(ACTIVITY_CAP, raw_signal.raw_score / GT_R_FUNDING_DIVISOR)
        if raw_signal.source == "OpenAlex":
            return 0.0
        if raw_signal.source in {"Google Search", "Gov/Policy"}:
            return min(ACTIVITY_CAP, float(raw_signal.metadata.get("trust", 0.0)))
        return 0.0

    def _calculate_attention(self, raw_signal: RawSignal) -> float:
        if raw_signal.source == "UKRI GtR":
            return 0.0
        if raw_signal.source == "OpenAlex":
            cited_by_count = float(raw_signal.metadata.get("cited_by_count", raw_signal.raw_score) or 0)
            return min(ATTENTION_CAP, cited_by_count / OPENALEX_CITATION_DIVISOR)
        if raw_signal.source in {"Google Search", "Gov/Policy"}:
            return GOOGLE_BASELINE_ATTENTION
        return 0.0

    @staticmethod
    def _parse_date(value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        try:
            parsed = date_parser.parse(str(value))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError, date_parser.ParserError):
            return None

    @staticmethod
    def _to_signal_card(scored: ScoredSignal, *, related_terms: list[str]) -> SignalCard:
        return SignalCard(
            title=scored.title,
            url=scored.url,
            summary=scored.abstract,
            source=scored.source,
            mission=scored.mission,
            date=scored.date.date().isoformat(),
            score_activity=scored.score_activity,
            score_attention=scored.score_attention,
            score_recency=scored.score_recency,
            final_score=scored.final_score,
            typology=scored.typology,
            is_novel=scored.is_novel,
            related_keywords=related_terms,
        )
