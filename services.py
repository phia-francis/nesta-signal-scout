from __future__ import annotations

import asyncio
import json
import random
from typing import Dict, List

import gspread
import httpx
from google.oauth2.service_account import Credentials
from tenacity import retry, stop_after_attempt, wait_exponential

from config import Settings
from keywords import BLOCKLIST_DOMAINS, TRUST_BOOST_TLDS

settings = Settings()


class SheetService:
    """Restored Google Sheet Integration"""

    def __init__(self):
        self.client = None
        if settings.GOOGLE_CREDENTIALS:
            try:
                creds = Credentials.from_service_account_info(
                    json.loads(settings.GOOGLE_CREDENTIALS),
                    scopes=["https://www.googleapis.com/auth/spreadsheets"],
                )
                self.client = gspread.authorize(creds)
            except Exception:
                self.client = None

    def get_sheet(self):
        if not self.client:
            return None
        return self.client.open_by_key(settings.SHEET_ID).sheet1

    async def save_signal(self, signal: Dict):
        sheet = self.get_sheet()
        if not sheet:
            return
        row = [
            signal.get("title", ""),
            signal.get("url", ""),
            signal.get("typology", "EMERGING"),
            signal.get("score_novelty", signal.get("novelty_score", 0)),
            "Generated",
            "Signal",
            signal.get("mission", ""),
        ]
        await asyncio.to_thread(sheet.append_row, row)

    async def update_status(self, url: str, status: str):
        sheet = self.get_sheet()
        if not sheet:
            return
        try:
            cell = await asyncio.to_thread(sheet.find, url)
            if cell:
                await asyncio.to_thread(sheet.update_cell, cell.row, 5, status)
        except Exception:
            return

    async def get_all(self):
        sheet = self.get_sheet()
        if not sheet:
            return []
        return await asyncio.to_thread(sheet.get_all_records)


class SearchService:
    """Upgraded Search with Trust Scoring"""

    def calculate_trust_score(self, url: str) -> int:
        score = 0
        if any(tld in url for tld in TRUST_BOOST_TLDS):
            score += 20
        if url.endswith(".pdf"):
            score += 10
        if any(b in url for b in BLOCKLIST_DOMAINS):
            score -= 1000
        return score

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def search(self, query: str, num: int = 10):
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": settings.GOOGLE_SEARCH_API_KEY,
            "cx": settings.GOOGLE_SEARCH_CX,
            "q": query,
            "num": num + 5,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            items = resp.json().get("items", [])

        for item in items:
            item["trust_score"] = self.calculate_trust_score(item.get("link", ""))
        items.sort(key=lambda x: x.get("trust_score", 0), reverse=True)
        return items[:num]


class HorizonAnalyticsService:
    """New Data Science Logic"""

    def classify_typology(self, novelty: float, magnitude: float) -> str:
        if novelty > 7 and magnitude > 7:
            return "HOT"
        if novelty > 7:
            return "EMERGING"
        if magnitude > 7:
            return "STABILISING"
        return "DORMANT"

    def generate_sparkline(self) -> List[int]:
        return [random.randint(10, 100) for _ in range(8)]
