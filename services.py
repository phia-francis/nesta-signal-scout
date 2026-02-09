from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import datetime
from typing import Dict, List

import gspread
import httpx
import numpy as np
from google.oauth2.service_account import Credentials
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer
from tenacity import retry, stop_after_attempt, wait_exponential

from config import Settings
from keywords import NICHE_DOMAINS, SIGNAL_KEYWORDS

settings = Settings()


class ServiceError(Exception):
    """Custom error for UI handling"""


class SheetService:
    """
    Handles Google Sheets. Raises ServiceError on failure.
    """

    STATUS_COLUMN_INDEX = 11

    def __init__(self):
        self.client = None
        if not settings.GOOGLE_CREDENTIALS:
            print("WARNING: No Google Credentials found.")
            return

        try:
            creds = Credentials.from_service_account_info(
                json.loads(settings.GOOGLE_CREDENTIALS),
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )
            self.client = gspread.authorize(creds)
        except Exception as exc:
            logging.error("Failed to authorize Google Sheets client: %s", exc)


    def get_sheet(self):
        if not self.client:
            raise ServiceError("Database connection not initialized.")
        try:
            return self.client.open_by_key(settings.SHEET_ID).sheet1
        except Exception as exc:
            raise ServiceError(f"Failed to open sheet: {exc}") from exc

    async def get_existing_urls(self) -> set[str]:
        """
        Fetch all URLs currently in the DB to prevent duplicates.
        Returns a Set for O(1) lookups.
        """
        sheet = self.get_sheet()
        try:
            records = await asyncio.to_thread(sheet.get_all_records)
            return {record.get("URL", "") for record in records if record.get("URL")}
        except Exception as exc:
            logging.error("Failed to get existing URLs from sheet: %s", exc)
            return set()


    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def save_signal(self, signal: Dict, existing_urls: set[str] | None = None):
        if existing_urls and signal.get("url") in existing_urls:
            print(f"Skipping Duplicate: {signal.get('title')}")
            return

        sheet = self.get_sheet()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            timestamp,
            signal.get("mode", "Radar"),
            signal.get("mission", "General"),
            signal.get("title", "Untitled"),
            signal.get("url", "#"),
            (signal.get("summary", "") or "")[:500],
            signal.get("typology", "Unsorted"),
            signal.get("score_activity", 0),
            signal.get("score_attention", 0),
            signal.get("source", "Web"),
            "New",
        ]
        await asyncio.to_thread(sheet.append_row, row)

    async def update_status(self, url: str, status: str):
        sheet = self.get_sheet()
        try:
            cell = await asyncio.to_thread(sheet.find, url)
            if cell:
                await asyncio.to_thread(
                    sheet.update_cell,
                    cell.row,
                    self.STATUS_COLUMN_INDEX,
                    status,
                )
        except Exception as exc:
            logging.error("Failed to update status for %s: %s", url, exc)
            raise ServiceError("Failed to update status.") from exc

    async def get_all(self):
        sheet = self.get_sheet()
        return await asyncio.to_thread(sheet.get_all_records)


class GatewayResearchService:
    """
    Methodology: Captures research trends via Gateway to Research (GtR).
    Focus: Projects supported by UKRI.
    """

    BASE_URL = "https://gtr.ukri.org/gtr/api"

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=6))
    async def fetch_projects(self, query: str) -> List[Dict]:
        if not query:
            raise ServiceError("GtR query missing.")
        url = f"{self.BASE_URL}/projects"
        params = {"term": query, "page": 1, "size": 10}
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                raise ServiceError(f"GtR API Error: {resp.status_code}")
            payload = resp.json()
        projects = payload.get("project", [])
        if not projects:
            raise ServiceError("GtR returned no projects for this topic.")
        results = []
        for project in projects:
            results.append(
                {
                    "title": project.get("title") or project.get("id"),
                    "abstract": project.get("abstractText") or project.get("abstract") or "",
                    "fund_val": float(project.get("fund", 0) or 0),
                }
            )
        return results


class CrunchbaseService:
    """
    Methodology: Examines investments via Crunchbase.
    Focus: Investment rounds, grants, seed funding.
    """

    BASE_URL = "https://api.crunchbase.com/api/v4"

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=6))
    async def fetch_deals(self, query: str) -> List[Dict]:
        if not settings.CRUNCHBASE_API_KEY:
            raise ServiceError("Crunchbase API Key missing configuration.")
        url = f"{self.BASE_URL}/searches/organizations"
        payload = {
            "field_ids": ["identifier", "funding_total", "num_funding_rounds"],
            "query": [
                {
                    "type": "predicate",
                    "field_id": "name",
                    "operator_id": "contains",
                    "values": [query],
                }
            ],
            "limit": 10,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, params={"user_key": settings.CRUNCHBASE_API_KEY}, json=payload)
            if resp.status_code != 200:
                raise ServiceError(f"Crunchbase API Error: {resp.status_code}")
            data = resp.json()
        entities = data.get("entities", [])
        if not entities:
            raise ServiceError("Crunchbase returned no deals for this topic.")
        results = []
        for entity in entities:
            identifier = (entity.get("properties") or {}).get("identifier", {})
            results.append(
                {
                    "company": identifier.get("value") or identifier.get("permalink") or "Unknown",
                    "amount": float((entity.get("properties") or {}).get("funding_total", 0) or 0),
                }
            )
        return results


class TopicModellingService:
    """
    Methodology: Unsupervised ML (LDA/Top2Vec) to refine granularity.
    """

    def perform_lda(self, documents: list[str], n_topics: int = 2) -> list[str]:
        if not documents:
            raise ServiceError("No abstracts available for topic modelling.")
        tf_vectorizer = CountVectorizer(max_df=0.95, min_df=2, stop_words="english")
        tf = tf_vectorizer.fit_transform(documents)
        lda = LatentDirichletAllocation(n_components=n_topics, random_state=0)
        lda.fit(tf)
        feature_names = tf_vectorizer.get_feature_names_out()
        topics = []
        for topic in lda.components_:
            top_words = [feature_names[i] for i in topic.argsort()[:-6:-1]]
            topics.append(" ".join(top_words))
        return topics

    def recommend_top2vec_seeds(self, documents: list[str]) -> list[str]:
        if not documents:
            raise ServiceError("No documents available for topic seeds.")
        vectorizer = CountVectorizer(stop_words="english", max_features=20)
        tf = vectorizer.fit_transform(documents)
        scores = np.asarray(tf.sum(axis=0)).ravel()
        terms = vectorizer.get_feature_names_out()
        ranked = sorted(zip(terms, scores), key=lambda x: x[1], reverse=True)
        return [term for term, _ in ranked[:5]]


class SearchService:
    """
    Includes Heuristic Trust Scoring & Niche Discovery Mode.
    """

    def calculate_trust(self, url: str) -> int:
        score = 0
        if any(x in url for x in [".gov", ".edu", ".ac.uk", ".org"]):
            score += 20
        if url.endswith(".pdf"):
            score += 10
        return score

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=6))
    async def search(self, query: str, num: int = 10):
        if not settings.GOOGLE_SEARCH_API_KEY or not settings.GOOGLE_SEARCH_CX:
            raise ServiceError("Search API Key missing configuration.")

        url = "https://www.googleapis.com/customsearch/v1"
        params = {"key": settings.GOOGLE_SEARCH_API_KEY, "cx": settings.GOOGLE_SEARCH_CX, "q": query, "num": num}
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                raise ServiceError(f"Search API Error: {resp.status_code}")
            items = resp.json().get("items", [])
        for item in items:
            item["trust"] = self.calculate_trust(item.get("link", ""))
        return sorted(items, key=lambda x: x.get("trust", 0), reverse=True)

    async def search_niche(self, query: str):
        novelty_query = f"{query} ({' OR '.join(SIGNAL_KEYWORDS[:3])})"
        results = await self.search(novelty_query, num=10)
        for item in results:
            item["is_niche"] = any(domain in item.get("link", "") for domain in NICHE_DOMAINS)
            if item["is_niche"]:
                item["trust"] = item.get("trust", 0) + 15
        return sorted(results, key=lambda x: x.get("trust", 0), reverse=True)


class HorizonAnalyticsService:
    """
    Methodology: Nesta Innovation Sweet Spots.
    """

    RESEARCH_FUNDING_DIVISOR = 1_000_000
    INVESTMENT_FUNDING_DIVISOR = 2_000_000
    MAINSTREAM_WEIGHT = 0.9
    NICHE_WEIGHT = 1.4

    def calculate_activity_score(self, research_funds: float, investment_funds: float) -> float:
        score = (research_funds / self.RESEARCH_FUNDING_DIVISOR) + (
            investment_funds / self.INVESTMENT_FUNDING_DIVISOR
        )
        return min(10.0, score)

    def calculate_attention_score(self, mainstream_count: int, niche_count: int) -> float:
        score = (mainstream_count * self.MAINSTREAM_WEIGHT) + (niche_count * self.NICHE_WEIGHT)
        return min(10.0, score)

    def classify_sweet_spot(self, activity: float, attention: float) -> str:
        if activity > 6.0:
            return "Hidden Gem" if attention < 5.0 else "Established"
        return "Hype" if attention > 6.0 else "Nascent"

    def generate_sparkline(self, activity: float, attention: float) -> List[int]:
        base = max(1.0, min(10.0, (activity + attention) / 2))
        direction = 1 if attention >= activity else -1
        slope = 0.4 * direction
        values = np.linspace(base - slope * 4, base + slope * 4, 8)
        return [int(max(1, min(10, round(v)))) for v in values]
