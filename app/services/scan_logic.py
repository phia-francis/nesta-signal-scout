from __future__ import annotations

import asyncio
import logging
import time
from difflib import SequenceMatcher
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from typing import Any

from dateutil import parser as date_parser

import keywords
from utils import normalize_url_for_deduplication
from app.core.config import SCAN_RESULT_LIMIT
from app.core.exceptions import ValidationError, SearchAPIError
from app.domain.models import RawSignal, ScoredSignal, SignalCard
from app.domain.taxonomy import TaxonomyService
from app.services.analytics_svc import HorizonAnalyticsService
from app.services.gtr_svc import GatewayResearchService
from app.services.openalex_svc import OpenAlexService
from app.services.search_svc import SearchService
from app.services.cluster_svc import ClusterService

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

# Source diversity allocation percentages
SOURCE_DIVERSITY_TARGET = {
    "social": 0.40,  # 40% Social media (Reddit, Twitter, HackerNews)
    "blog": 0.30,    # 30% Blogs (Medium, Substack)
    "international": 0.20,  # 20% International + Grey literature
    "academic": 0.10  # 10% Academic (lowest priority)
}


def build_novelty_query(base_query: str) -> str:
    """Enhance a query with forward-looking keywords from ``keywords.py``.

    Uses positive inclusion only (no exclusion operators) so that
    results are biased toward recent launches, pilots, and emerging
    developments rather than encyclopedic background content.

    Args:
        base_query: The original user search query.

    Returns:
        An enhanced query string with novelty modifiers appended, or
        the original query if no modifiers are available.

    Example::

        >>> build_novelty_query("alternative proteins")
        'alternative proteins (pilot OR trial OR prototype OR emerging OR startup)'
    """
    modifiers = keywords.get_trend_modifiers(base_query)
    if modifiers:
        modifiers_str = " OR ".join(modifiers)
        return f"{base_query} ({modifiers_str})"
    return base_query


class ScanOrchestrator:
    """
    Orchestrates multi-source horizon scanning operations.

    Coordinates search across multiple providers (Google, OpenAlex, GtR),
    applies scoring and filtering, and handles partial failures gracefully.
    Implements layered scanning to prioritise diversity, odd gems, and
    non-academic sources.
    """

    def __init__(
        self,
        gateway_service: GatewayResearchService,
        openalex_service: OpenAlexService,
        search_service: SearchService,
        analytics_service: HorizonAnalyticsService,
        taxonomy: TaxonomyService,
        llm_service: Any = None,
    ) -> None:
        self.gateway_service = gateway_service
        self.openalex_service = openalex_service
        self.search_service = search_service
        self.analytics_service = analytics_service
        self.taxonomy = taxonomy
        self.llm_service = llm_service
        self._fetch_cache: dict[str, tuple[float, list[RawSignal], list[str]]] = {}
        self._warnings: list[str] = []

    @property
    def cutoff_date(self) -> datetime:
        return datetime.now(timezone.utc) - timedelta(days=ONE_YEAR_DAYS)

    def _cache_key(self, *, topic: str, mode: str, friction_mode: bool, cutoff: datetime) -> str:
        return f"{topic.strip().lower()}|{mode}|{str(friction_mode).lower()}|{cutoff.date().isoformat()}"

    def _clone_raw_signals(self, signals: list[RawSignal]) -> list[RawSignal]:
        return [signal.model_copy(deep=True) for signal in signals]

    def _classify_source(self, signal: RawSignal) -> str:
        """
        Classify a signal into source categories for diversity management.
        
        Returns:
            One of: "social", "blog", "international", "academic"
        """
        source = (signal.source or "").lower()
        url = (signal.url or "").lower()
        
        # Academic sources
        if any(keyword in source for keyword in ["gtr", "openalex", "arxiv", "academic", "journal"]):
            return "academic"
        
        # Social media sources
        if any(domain in url for domain in ["reddit.com", "twitter.com", "x.com", "news.ycombinator.com", "producthunt.com"]):
            return "social"
        
        # Blog sources  
        if any(domain in url for domain in ["medium.com", "substack.com", "blog"]) or "blog" in source:
            return "blog"
        
        # Everything else is international/web
        return "international"

    def _prioritize_by_source_diversity(self, signals: list[RawSignal]) -> list[RawSignal]:
        """
        Reorder signals to ensure source diversity matches target allocations:
        - 40% Social media
        - 30% Blogs
        - 20% International/Web
        - 10% Academic
        """
        if not signals:
            return signals
        
        # Categorize all signals
        categorized: dict[str, list[RawSignal]] = {
            "social": [],
            "blog": [],
            "international": [],
            "academic": []
        }
        
        for signal in signals:
            category = self._classify_source(signal)
            categorized[category].append(signal)
        
        # Calculate target counts based on total signals
        total_signals = len(signals)
        target_counts = {
            category: int(total_signals * allocation)
            for category, allocation in SOURCE_DIVERSITY_TARGET.items()
        }
        
        # Build prioritized list
        prioritized: list[RawSignal] = []
        
        # Take signals from each category up to target count
        for category in ["social", "blog", "international", "academic"]:
            available = categorized[category]
            target = target_counts[category]
            prioritized.extend(available[:target])
        
        # Add remaining signals if we haven't hit the total yet
        for category in ["social", "blog", "international", "academic"]:
            available = categorized[category]
            target = target_counts[category]
            prioritized.extend(available[target:])
        
        return prioritized

    async def _fetch_from_all_sources(
        self, 
        queries: dict[str, str], 
        mission: str,
        cutoff_date: datetime
    ) -> list[RawSignal]:
        """
        Fetch from all sources in parallel with error handling.
        Returns partial results even if some sources fail.
        """
        self._warnings.clear()
        results = await asyncio.gather(
            self.search_service.search(queries.get("social", ""), num=10, freshness="month"),
            self.search_service.search(queries.get("blog", ""), num=8, freshness="year"),
            self.search_service.search(queries.get("general", ""), num=5, freshness="month", sort_by_date=True),
            self.gateway_service.fetch_projects(queries.get("topic", ""), min_start_date=cutoff_date),
            return_exceptions=True,
        )
        
        return self._normalize_results(results, mission)

    def _normalize_results(self, results: tuple[Any, ...], mission: str) -> list[RawSignal]:
        """Normalize results from all sources, handling failures gracefully."""
        social_res, blog_res, general_res, gtr_res = results
        raw_signals: list[RawSignal] = []
        
        # Handle each source with error checking
        if not isinstance(social_res, Exception):
            raw_signals.extend(self._normalise_google(social_res, mission=mission, source_label="Social/Forum", is_novel=True))
        else:
            self._warnings.append("Social media sources unavailable")
            logging.warning("Social search failed: %s", social_res)
        
        if not isinstance(blog_res, Exception):
            raw_signals.extend(self._normalise_google(blog_res, mission=mission, source_label="Niche/Blog", is_novel=True))
        else:
            self._warnings.append("Blog sources unavailable")
            logging.warning("Blog search failed: %s", blog_res)
        
        if not isinstance(general_res, Exception):
            raw_signals.extend(self._normalise_google(general_res, mission=mission, source_label="Web", is_novel=False))
        else:
            self._warnings.append("Web search unavailable")
            logging.warning("General search failed: %s", general_res)
        
        if not isinstance(gtr_res, Exception):
            raw_signals.extend(self._normalise_gtr(gtr_res, mission=mission))
        else:
            self._warnings.append("Academic sources unavailable")
            logging.warning("Academic search failed: %s", gtr_res)
        
        return raw_signals

    def _score_signal(self, raw_signal: RawSignal, effective_cutoff: datetime) -> ScoredSignal | None:
        """Score a single signal. Returns None if signal is too old."""
        if raw_signal.date < effective_cutoff:
            return None
        
        activity = self._calculate_activity(raw_signal)
        attention = self._calculate_attention(raw_signal)
        recency = self.analytics_service.calculate_recency_score(raw_signal.date)
        
        final = (
            (activity * ACTIVITY_WEIGHT)
            + (attention * ATTENTION_WEIGHT)
            + (recency * RECENCY_WEIGHT)
        )
        typology = self.analytics_service.classify_sweet_spot(activity, attention)
        
        return ScoredSignal(
            **raw_signal.model_dump(),
            score_activity=round(activity, 2),
            score_attention=round(attention, 2),
            score_recency=round(recency, 2),
            final_score=round(final, 2),
            typology=typology,
        )

    def _filter_by_threshold(self, signals: list[SignalCard], min_score: float) -> list[SignalCard]:
        """Filter signals by minimum score threshold."""
        return [s for s in signals if s.final_score >= min_score]

    def _sort_by_score(self, signals: list[SignalCard]) -> list[SignalCard]:
        """Sort signals by final score in descending order."""
        return sorted(signals, key=lambda s: s.final_score, reverse=True)

    async def execute_scan(self, query: str, mission: str, mode: str, existing_urls: set[str] | None = None) -> dict[str, Any]:
        """
        Unified agentic scan entrypoint.
        Valid modes: 'radar', 'research', 'governance'
        """
        clean_topic = query.strip()
        if not clean_topic:
            raise ValidationError("Query is required for scanning.")

        if mode not in ["radar", "research", "governance"]:
            mode = "radar"

        num_queries = {"radar": 3, "research": 6, "governance": 3}.get(mode, 3)

        self._warnings.clear()

        # 1. Generate unbiased search queries
        generated_queries = await self.llm_service.generate_agentic_queries(
            topic=clean_topic,
            mode=mode,
            mission=mission,
            num_queries=num_queries,
        )

        # 2. Execute searches concurrently with cascading freshness tiers
        raw_results: list[dict[str, Any]] = []
        freshness_tiers = ["m1", "m3", "m6", "y1"]
        search_tasks = []

        for i, q in enumerate(generated_queries):
            tier = freshness_tiers[i % len(freshness_tiers)]
            search_tasks.append(
                self.search_service.search(q, num=5, freshness=tier)
            )

        search_responses = await asyncio.gather(*search_tasks, return_exceptions=True)
        for i, response in enumerate(search_responses):
            if isinstance(response, Exception):
                logging.warning("Search failed for query '%s': %s", generated_queries[i], response)
            elif response:
                for item in response:
                    raw_results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                    })

        # Deduplicate by URL before verification to reduce LLM token usage
        unique_results = list({r["url"]: r for r in raw_results if r["url"]}.values())

        # Filter out URLs already in the database
        if existing_urls:
            unique_results = [
                r for r in unique_results
                if normalize_url_for_deduplication(r["url"]) not in existing_urls
            ]

        # 3. Verify and synthesise (anti-hallucination)
        cards: list[SignalCard] = []
        if unique_results:
            verified_signals = await self.llm_service.verify_and_synthesize(
                raw_results=unique_results,
                topic=clean_topic,
                mission=mission,
                mode=mode,
            )

            for sig in verified_signals:
                try:
                    score = float(sig.get("score", 7.0))
                    cards.append(SignalCard(
                        title=sig.get("title", "Unknown Signal")[:200],
                        url=sig.get("url", ""),
                        summary=sig.get("summary", "No summary provided.")[:500],
                        source="Agentic Scan",
                        mission=mission,
                        date=datetime.now(timezone.utc).date().isoformat(),
                        score_activity=score,
                        score_attention=score,
                        score_recency=10.0,
                        final_score=score,
                        typology=(
                            "Trend" if mode == "radar"
                            else "Insight" if mode == "research"
                            else "Policy"
                        ),
                        is_novel=True,
                        related_keywords=generated_queries,
                    ))
                except Exception as e:
                    logging.warning("Skipping malformed signal from LLM: %s", e)
                    continue

        cards.sort(key=lambda x: x.final_score, reverse=True)

        cluster_insights = []

        if len(cards) >= 3:
            try:
                cluster_service = ClusterService()

                cluster_input = [
                    {"title": c.title, "summary": c.summary, "index": i}
                    for i, c in enumerate(cards)
                ]

                narrative_clusters = cluster_service.cluster_signals(cluster_input)

                llm_cluster_payload = []
                for cluster in narrative_clusters:
                    clean_narrative = cluster["title"].replace("Narrative: ", "").strip()

                    signal_texts = [
                        cards[sig_ref["index"]].summary
                        for sig_ref in cluster["signals"]
                    ]

                    llm_cluster_payload.append({
                        "cluster_name": clean_narrative,
                        "signals": signal_texts
                    })

                    for sig_ref in cluster["signals"]:
                        cards[sig_ref["index"]].narrative_group = clean_narrative

                if llm_cluster_payload:
                    cluster_insights = await self.llm_service.analyze_trend_clusters(
                        clusters_data=llm_cluster_payload,
                        mission=mission
                    )

            except Exception as e:
                logging.warning(f"Auto-clustering and analysis failed: {e}")

        return {
            "signals": cards,
            "related_terms": generated_queries,
            "warnings": self._warnings if self._warnings else None,
            "mode": mode,
            "cluster_insights": cluster_insights
        }

    async def fetch_signals(
        self,
        topic: str,
        *,
        mission: str,
        mode: str,
        friction_mode: bool = False,
    ) -> tuple[list[RawSignal], list[str]]:
        """
        Fetch signals from multiple sources using a layered strategy.

        Implements source-diversity targeting:
          - Layer 5: Social & Forums (Reddit, HN, ProductHunt) — 40%
          - Layer 4: Niche Blogs (Substack, Medium, RSS) — 30%
          - Layer 3: International / General Web — 20%
          - Layer 1: Academic (deprioritised) — 10%

        Results are cached for 24 hours to avoid redundant API calls.

        Args:
            topic: Search query or topic to scan.
            mission: Nesta mission for tagging (e.g. 'A Healthy Life').
            mode: Scan mode identifier ('radar', 'research', 'policy').
            friction_mode: Legacy parameter, ignored.

        Returns:
            Tuple of (raw_signals, related_terms) where raw_signals is
            a list of RawSignal objects and related_terms is a list of
            keyword strings.

        Raises:
            ValidationError: If topic is empty.
            SearchAPIError: If all search sources fail.
        """
        clean_topic = topic.strip()
        if not clean_topic:
            raise ValidationError("Topic is required to fetch signals.")

        cutoff_date = self.cutoff_date
        cache_key = self._cache_key(topic=clean_topic, mode=mode, friction_mode=friction_mode, cutoff=cutoff_date)
        cached = self._fetch_cache.get(cache_key)
        if cached and (time.monotonic() - cached[0]) < FETCH_CACHE_TTL_SECONDS:
            _, cached_signals, cached_terms = cached
            return self._clone_raw_signals(cached_signals), list(cached_terms)

        # Generate related keywords (Layer 0)
        try:
            related_terms = keywords.get_trend_modifiers(clean_topic)
        except Exception as e:
            logging.warning("Keyword enrichment failed for topic '%s': %s", clean_topic, e)
            related_terms = []

        # Construct Layered Queries with adjusted result counts for diversity
        # Layer 5: Social / Forums (40% of results)
        social_query = f"{clean_topic} (site:reddit.com OR site:news.ycombinator.com OR site:producthunt.com OR site:twitter.com OR site:x.com)"

        # Layer 4: Niche Blogs / Thought Leadership (30% of results)
        blog_query = f"{clean_topic} (site:substack.com OR site:medium.com OR \"blog\" OR \"white paper\")"

        # Layer 3: General Web (20% of results) — novelty-enhanced
        general_query = build_novelty_query(clean_topic)

        # Execute Concurrently with adjusted result counts
        # Total ~25 results: 10 social (40%), 7 blog (30%), 5 general (20%), 3 academic (10%)
        results = await asyncio.gather(
            self.search_service.search(social_query, num=10, freshness="month"),  # Layer 5 - 40%
            self.search_service.search(blog_query, num=8, freshness="year"),      # Layer 4 - 30%
            self.search_service.search(general_query, num=5, freshness="month", sort_by_date=True),   # Layer 3 - 20%
            # Layer 1 (Academic) - Fetch fewer, lower priority - 10%
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

        # Apply source diversity prioritization
        raw_signals = self._prioritize_by_source_diversity(raw_signals)

        self._fetch_cache[cache_key] = (time.monotonic(), self._clone_raw_signals(raw_signals), list(related_terms))
        return raw_signals, related_terms

    def process_signals(
        self,
        raw_signals: list[RawSignal],
        *,
        mission: str,
        related_terms: list[str],
        override_cutoff_date: datetime | None = None,
        existing_urls: set[str] | None = None,
    ) -> Generator[SignalCard, None, None]:
        """Process and score signals using extracted scoring method."""
        effective_cutoff = override_cutoff_date or self.cutoff_date
        db_urls = existing_urls or set()
        candidate_cards: list[SignalCard] = []

        for raw_signal in raw_signals:
            normalised = normalize_url_for_deduplication(raw_signal.url)
            if normalised in db_urls:
                continue
            scored = self._score_signal(raw_signal, effective_cutoff)
            if scored:
                candidate_cards.append(self._to_signal_card(scored, related_terms=related_terms))

        for card in self._deduplicate_signals(candidate_cards):
            yield card

    async def fetch_research_deep_dive(self, query: str, mission: str = "Any") -> list[SignalCard]:
        """
        Perform a deep research dive combining OpenAlex and web sources.

        Fetches data from academic (OpenAlex) and blog sources, then uses
        the LLM service to produce a synthesised overview card followed
        by individual scored signal cards.

        Args:
            query: Research query string.
            mission: Nesta mission for focused analysis (default ``"Any"``).

        Returns:
            List of SignalCard objects — the first is the AI synthesis,
            followed by individually scored results.

        Raises:
            ValidationError: If query is empty.
        """
        if not query.strip():
            raise ValidationError("Research query is required.")

        # Step 1: Fetch Raw Data (The Context)
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

        # If no LLM service available, fall back to traditional processing
        if not self.llm_service:
            return list(
                self.process_signals(
                    raw_signals,
                    mission="Research",
                    related_terms=[],
                    override_cutoff_date=datetime.now(timezone.utc) - timedelta(days=FIVE_YEARS_DAYS),
                )
            )

        # Step 2: Convert to LLM input format
        llm_input_data = [
            {
                "title": s.title,
                "snippet": s.abstract,
                "displayLink": s.source
            }
            for s in raw_signals
        ]

        # Step 3: Call LLM with fresh context and mission awareness
        synthesis_result = await self.llm_service.synthesize_research(query, llm_input_data, mission=mission)

        # Step 4: Convert LLM Output to SignalCard
        synthesized_card = SignalCard(
            title=f"Synthesis: {query.title()}",
            url="",
            summary=synthesis_result.get("synthesis", "No synthesis available."),
            source="AI Analysis",
            mission="Research",
            date=datetime.now(timezone.utc).date().isoformat(),
            score_activity=0.0,
            score_attention=0.0,
            score_recency=10.0,
            final_score=9.5,
            typology="Synthesis",
            is_novel=True,
            related_keywords=[]
        )

        # Create signal cards from individual LLM results
        individual_cards = []
        llm_signals = synthesis_result.get("signals", [])

        # Use normalized URLs from the raw signals for robust matching
        url_to_raw = {
            normalize_url_for_deduplication(s.url): s
            for s in raw_signals
            if s.url
        }

        for sig_data in llm_signals:
            if not isinstance(sig_data, dict):
                continue

            # Prefer a dedicated 'url' field from the LLM output
            llm_url = sig_data.get("url") or sig_data.get("source", "")
            normalized_llm_url = (
                normalize_url_for_deduplication(llm_url)
                if isinstance(llm_url, str) and llm_url
                else ""
            )
            raw = url_to_raw.get(normalized_llm_url) if normalized_llm_url else None

            # Card URL: use LLM URL if it's a proper HTTP URL, otherwise fall back to raw.url
            if isinstance(llm_url, str) and llm_url.startswith("http"):
                card_url = llm_url
            elif raw and getattr(raw, "url", None):
                card_url = raw.url
            else:
                card_url = ""

            # Source name: prefer matched raw source or generic label
            card_source = raw.source if raw else "Web Synthesis"

            card = SignalCard(
                title=sig_data.get("title", "Research Signal"),
                url=card_url,
                summary=sig_data.get("summary", ""),
                source=card_source,
                mission="Research",
                date=raw.date.date().isoformat() if raw and raw.date else datetime.now(timezone.utc).date().isoformat(),
                score_activity=5.0,
                score_attention=5.0,
                score_recency=5.0,
                final_score=7.5,
                typology="Signal",
                is_novel=True,
                related_keywords=[]
            )
            individual_cards.append(card)

        # If LLM didn't return any sub-signals, fallback to generic parsing
        if not individual_cards:
            individual_cards = list(
                self.process_signals(
                    raw_signals[:10],
                    mission="Research",
                    related_terms=[],
                    override_cutoff_date=datetime.now(timezone.utc) - timedelta(days=FIVE_YEARS_DAYS),
                )
            )

        # Return synthesis first, then individual results
        return [synthesized_card] + individual_cards

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

    def _deduplicate_signals(self, signals: list[SignalCard]) -> list[SignalCard]:
        """Remove duplicate signals by canonical URL and fuzzy title similarity."""
        seen_urls: set[str] = set()
        kept: list[SignalCard] = []

        for signal in signals:
            normalised_url = normalize_url_for_deduplication(signal.url)
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
            parsed: Any = date_parser.parse(str(value))
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
