from __future__ import annotations

import asyncio
import logging
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

ACTIVITY_WEIGHT = 0.2  # Lowered to reduce academic bias
ATTENTION_WEIGHT = 0.5  # Increased to favour social/web buzz
RECENCY_WEIGHT = 0.3
ONE_YEAR_DAYS = 365
FIVE_YEARS_DAYS = 365 * 5
ATTENTION_CAP = 10.0
ACTIVITY_CAP = 10.0
GT_R_FUNDING_DIVISOR = 50_000.0
OPENALEX_CITATION_DIVISOR = 200.0
GOOGLE_BASELINE_ATTENTION = 6.0
FETCH_CACHE_TTL_SECONDS = 24 * 60 * 60
DEDUPE_SIMILARITY_THRESHOLD = 0.85


class ScanOrchestrator:
    """
    V2.0 Orchestrator: Implements 'Layered Scanning' to prioritise
    diversity, odd gems, and non-academic sources.
    """

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

    def _cache_key(self, *, topic: str, mode: str, friction_mode: bool, cutoff: datetime) -> str:
        return f"{topic.strip().lower()}|{mode}|{str(friction_mode).lower()}|{cutoff.date().isoformat()}"

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
        """
        Layered Fetch Strategy:
        - Layer 5: Social & Forums (Reddit, HN, ProductHunt)
        - Layer 4: Niche Blogs (Substack, Medium, RSS)
        - Layer 3: International/General Web
        - Layer 1: Academic (Deprioritised)
        """
        clean_topic = topic.strip()
        if not clean_topic:
            raise ValueError("Topic is required to fetch signals.")

        cutoff_date = self.cutoff_date
        cache_key = self._cache_key(topic=clean_topic, mode=mode, friction_mode=friction_mode, cutoff=cutoff_date)
        cached = self._fetch_cache.get(cache_key)
        if cached and (time.monotonic() - cached[0]) < FETCH_CACHE_TTL_SECONDS:
            _, cached_signals, cached_terms = cached
            return self._clone_raw_signals(cached_signals), list(cached_terms)

        # Generate related keywords (Layer 0)
        try:
            related_terms = keywords.generate_broad_scan_queries([clean_topic], num_signals=3)
        except Exception as e:
            logging.warning("Keyword enrichment failed for topic '%s': %s", clean_topic, e)
            related_terms = []

        # Construct Layered Queries
        # Layer 5: Social / Forums
        social_query = f"{clean_topic} (site:reddit.com OR site:news.ycombinator.com OR site:producthunt.com OR site:twitter.com OR site:x.com)"

        # Layer 4: Niche Blogs / Thought Leadership
        blog_query = f"{clean_topic} (site:substack.com OR site:medium.com OR \"blog\" OR \"white paper\")"

        # Layer 3: General Web (Broad)
        general_query = clean_topic

        # Execute Concurrently
        results = await asyncio.gather(
            self.search_service.search(social_query, num=8, freshness="month"),  # Layer 5
            self.search_service.search(blog_query, num=8, freshness="year"),     # Layer 4
            self.search_service.search(general_query, num=6, freshness="year"),  # Layer 3
            # Layer 1 (Academic) - Fetch fewer, lower priority
            self.gateway_service.fetch_projects(clean_topic, min_start_date=cutoff_date),
            return_exceptions=True,
        )

        social_res, blog_res, general_res, gtr_res = results

        raw_signals: list[RawSignal] = []

        # Normalise Layers
        raw_signals.extend(self._normalise_google(social_res, mission=mission, source_label="Social/Forum", is_novel=True))
        raw_signals.extend(self._normalise_google(blog_res, mission=mission, source_label="Niche/Blog", is_novel=True))
        raw_signals.extend(self._normalise_google(general_res, mission=mission, source_label="Web", is_novel=False))

        # Deprioritised Academic
        raw_signals.extend(self._normalise_gtr(gtr_res, mission=mission))

        self._fetch_cache[cache_key] = (time.monotonic(), self._clone_raw_signals(raw_signals), list(related_terms))
        return raw_signals, related_terms

    def process_signals(
        self,
        raw_signals: list[RawSignal],
        *,
        mission: str,
        related_terms: list[str],
        override_cutoff_date: datetime | None = None,
    ) -> Generator[SignalCard, None, None]:
        """Scoring logic updated to favour 'Attention' (Social/Web) over 'Activity' (Grants)."""
        effective_cutoff = override_cutoff_date or self.cutoff_date
        candidate_cards: list[SignalCard] = []

        for raw_signal in raw_signals:
            if raw_signal.date < effective_cutoff:
                continue

            activity = self._calculate_activity(raw_signal)
            attention = self._calculate_attention(raw_signal)
            recency = self.analytics_service.calculate_recency_score(raw_signal.date)

            # Weighted Score
            final = (
                (activity * ACTIVITY_WEIGHT)
                + (attention * ATTENTION_WEIGHT)
                + (recency * RECENCY_WEIGHT)
            )
            typology = self.analytics_service.classify_sweet_spot(activity, attention)

            scored = ScoredSignal(
                **raw_signal.model_dump(),
                score_activity=round(activity, 2),
                score_attention=round(attention, 2),
                score_recency=round(recency, 2),
                final_score=round(final, 2),
                typology=typology,
            )
            candidate_cards.append(self._to_signal_card(scored, related_terms=related_terms))

        # Dedupe and Yield
        for card in self._deduplicate_signals(candidate_cards):
            yield card

    async def fetch_research_deep_dive(self, query: str) -> list[SignalCard]:
        """Deep Dive uses OpenAlex + Niche Blogs to find synthesis."""
        if not query.strip():
            raise ValueError("Research query is required.")

        # Mix of academic and blog sources for synthesis
        blog_query = f"{query} (site:substack.com OR site:medium.com OR \"white paper\")"

        results = await asyncio.gather(
            self.openalex_service.search_works(query),
            self.search_service.search(blog_query, num=10, freshness="year"),
            return_exceptions=True
        )

        openalex_res, google_res = results
        raw_signals = []
        raw_signals.extend(self._normalise_openalex(openalex_res, mission="Research"))
        raw_signals.extend(self._normalise_google(google_res, mission="Research", source_label="Web", is_novel=False))

        return list(
            self.process_signals(
                raw_signals,
                mission="Research",
                related_terms=[],
                override_cutoff_date=datetime.now(timezone.utc) - timedelta(days=FIVE_YEARS_DAYS),
            )
        )

    async def fetch_policy_scan(self, topic: str) -> list[SignalCard]:
        """Policy Monitor: International & Grey Literature (PDFs)."""
        if not topic.strip():
            raise ValueError("Policy topic is required.")

        # International + Grey Lit (PDFs)
        query = f"{topic} (site:.gov OR site:.int OR site:.org OR filetype:pdf) -site:gov.uk"

        try:
            results = await self.search_service.search(query, num=SCAN_RESULT_LIMIT, freshness="year")
        except (ServiceError, Exception):
            results = []

        raw_signals = self._normalise_google(results, mission="Policy", source_label="Policy/Intl", is_novel=False)
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
            signals.append(RawSignal(
                source="UKRI GtR",
                title=project.get("title", "Untitled"),
                url=f"https://gtr.ukri.org/projects?ref={project.get('grantReference')}",
                abstract=project.get("abstract", ""),
                date=project.get("start_date") or datetime.now(timezone.utc),
                raw_score=float(project.get("fund_val", 0) or 0),
                mission=mission,
                metadata={"fund_val": float(project.get("fund_val", 0) or 0)},
            ))
        return signals

    def _normalise_openalex(self, result: Any, *, mission: str) -> list[RawSignal]:
        if isinstance(result, Exception) or not isinstance(result, list):
            return []
        signals: list[RawSignal] = []
        for work in result:
            signals.append(RawSignal(
                source="OpenAlex",
                title=work.get("title", "Untitled"),
                url=work.get("url", ""),
                abstract=work.get("summary", ""),
                date=self._parse_date(work.get("publication_date")) or datetime.now(timezone.utc),
                raw_score=float(work.get("cited_by_count", 0)),
                mission=mission,
                metadata={"cited_by_count": float(work.get("cited_by_count", 0))},
            ))
        return signals

    def _normalise_google(self, result: Any, *, mission: str, source_label: str, is_novel: bool) -> list[RawSignal]:
        if isinstance(result, Exception) or not isinstance(result, list):
            return []
        now = datetime.now(timezone.utc)
        signals: list[RawSignal] = []
        for rank, item in enumerate(result, start=1):
            signals.append(RawSignal(
                source=source_label,
                title=item.get("title", "Untitled"),
                url=item.get("link", ""),
                abstract=item.get("snippet", ""),
                date=now,
                raw_score=float(item.get("trust", 0) or 0),
                mission=mission,
                metadata={"trust": item.get("trust", 0), "rank": rank},
                is_novel=is_novel,
            ))
        return signals

    def _normalise_url(self, url: str) -> str:
        cleaned = (url or "").strip().lower()
        for prefix in ("https://", "http://"):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
        if cleaned.startswith("www."):
            cleaned = cleaned[4:]
        return cleaned.rstrip("/")

    # --- Helpers ---

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
                if similarity > DEDUPE_SIMILARITY_THRESHOLD:
                    is_fuzzy_duplicate = True
                    break

            if is_fuzzy_duplicate:
                continue

            if normalised_url:
                seen_urls.add(normalised_url)
            kept.append(signal)

        return kept

    def _calculate_activity(self, raw: RawSignal) -> float:
        if raw.source == "UKRI GtR": return min(ACTIVITY_CAP, raw.raw_score / GT_R_FUNDING_DIVISOR)
        if "Policy" in raw.source: return 8.0  # Boost policy
        return 0.0

    def _calculate_attention(self, raw: RawSignal) -> float:
        if raw.source == "OpenAlex": return min(ATTENTION_CAP, raw.raw_score / OPENALEX_CITATION_DIVISOR)
        if "Social" in raw.source: return 9.0  # Boost social
        if "Blog" in raw.source: return 7.0
        if "Web" in raw.source: return 5.0
        return 0.0

    @staticmethod
    def _parse_date(value: Any) -> datetime | None:
        if not value: return None
        try:
            parsed = date_parser.parse(str(value))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError, date_parser.ParserError):
            return None

    @staticmethod
    def _build_sparkline(scored: ScoredSignal) -> list[int]:
        base = max(0, min(100, int(round(scored.final_score * 10))))
        activity = max(0, min(100, int(round(scored.score_activity * 10))))
        attention = max(0, min(100, int(round(scored.score_attention * 10))))
        recency = max(0, min(100, int(round(scored.score_recency * 10))))
        return [
            max(0, base - 8),
            max(0, base - 4),
            base,
            min(100, base + 3),
            min(100, base + 6),
            activity,
            max(attention, recency),
        ]

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
            sparkline=ScanOrchestrator._build_sparkline(scored),
            related_keywords=related_terms,
        )
