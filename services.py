from __future__ import annotations

import asyncio
import json
import os
import random
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlunparse

import gspread
import httpx
import openai
import pandas as pd
from async_lru import alru_cache
from google.oauth2.service_account import Credentials
from openai import AsyncOpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import Settings
from models import UpdateSignalRequest
from utils import get_logger, validate_url_security

LOGGER = get_logger(__name__)


class SheetService:
    def __init__(self, credentials_json: Optional[str], sheet_id: Optional[str]):
        self.credentials_json = credentials_json
        self.sheet_id = sheet_id
        self._executor = ThreadPoolExecutor(max_workers=3)

    async def _run_in_executor(self, func, *args):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, func, *args)
    
    def _get_sheet(self):
        if not self.credentials_json or not self.sheet_id:
            LOGGER.warning("Google Sheets credentials missing.")
            return None
        try:
            creds_dict = json.loads(self.credentials_json)
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            g_client = gspread.authorize(creds)
            return g_client.open_by_key(self.sheet_id).sheet1
        except Exception as exc:
            LOGGER.warning("Google Sheets auth error: %s", exc)
            return None

    def _ensure_headers(self, sheet) -> None:
        expected_headers = [
            "Title",
            "Score",
            "Hook",
            "Analysis",
            "Implication",
            "URL",
            "Mission",
            "Origin_Country",
            "Lenses",
            "Score_Impact",
            "Score_Novelty",
            "Score_Evidence",
            "User_Status",
            "User_Comment",
            "Shareable",
            "Feedback",
            "Source_Date",
        ]
        try:
            existing_headers = sheet.row_values(1)
            if existing_headers != expected_headers:
                sheet.update([expected_headers], "A1")
        except Exception as exc:
            LOGGER.warning("Header check failed: %s", exc)

    async def ensure_headers(self, sheet) -> None:
        await self._run_in_executor(self._ensure_headers, sheet)

    async def get_records(self, include_rejected: bool = False) -> List[Dict[str, Any]]:
        sheet = await self._run_in_executor(self._get_sheet)
        if not sheet:
            return []
        await self.ensure_headers(sheet)
        try:
            rows = await self._run_in_executor(sheet.get_all_values)
            if not rows:
                return []
            headers = rows[0]
            records = []
            for idx, row in enumerate(rows[1:], start=2):
                if all(cell == "" for cell in row):
                    continue
                while len(row) < len(headers):
                    row.append("")
                record = {headers[i]: row[i] for i in range(len(headers))}
                record["_row"] = idx
                status = str(record.get("User_Status", "")).lower()
                if not include_rejected and status == "rejected":
                    continue
                records.append(record)
            return records
        except Exception as exc:
            LOGGER.warning("Sheet read error: %s", exc)
            return []

    async def get_existing_urls(self) -> List[str]:
        records = await self.get_records(include_rejected=True)
        return [str(rec.get("URL", "")).strip() for rec in records if rec.get("URL")]

    async def upsert_signal(self, signal: Dict[str, Any]) -> None:
        sheet = await self._run_in_executor(self._get_sheet)
        if not sheet:
            return
        await self.ensure_headers(sheet)

        incoming_status = str(signal.get("user_status") or signal.get("User_Status") or "").strip()
        incoming_shareable = signal.get("shareable") or signal.get("Shareable") or "Maybe"
        normalized_status = incoming_status.title() if incoming_status else "Pending"
        normalized_shareable = incoming_shareable
        status_key = normalized_status.lower()
        if status_key == "shortlisted":
            normalized_status = "Shortlisted"
            normalized_shareable = "Yes"
        elif status_key == "rejected":
            normalized_status = "Rejected"
        elif status_key == "saved":
            normalized_status = "Saved"
        elif status_key == "generated":
            normalized_status = "Generated"

        row_data = [
            signal.get("title", ""),
            signal.get("score", 0),
            signal.get("hook", ""),
            signal.get("analysis", ""),
            signal.get("implication", ""),
            signal.get("url", ""),
            signal.get("mission", ""),
            signal.get("origin_country", ""),
            signal.get("lenses", ""),
            signal.get("score_impact", 0),
            signal.get("score_novelty", 0),
            signal.get("score_evidence", 0),
            normalized_status,
            signal.get("user_comment", "") or signal.get("feedback", ""),
            normalized_shareable,
            signal.get("feedback", ""),
            signal.get("source_date", "Recent"),
        ]

        try:
            records = await self.get_records(include_rejected=True)
            match_row = None
            incoming_url = str(signal.get("url", "")).strip().lower()
            for rec in records:
                if str(rec.get("URL", "")).strip().lower() == incoming_url:
                    match_row = rec.get("_row")
                    break
            if match_row:
                await self._run_in_executor(sheet.update, f"A{match_row}:Q{match_row}", [row_data])
            else:
                await self._run_in_executor(sheet.append_row, row_data)
        except Exception as exc:
            LOGGER.warning("Upsert error: %s", exc)

    async def update_signal_by_url(self, req: UpdateSignalRequest) -> Dict[str, str]:
        sheet = await self._run_in_executor(self._get_sheet)
        if not sheet:
            raise RuntimeError("Google Sheets unavailable")
        await self.ensure_headers(sheet)
        records = await self.get_records(include_rejected=True)
        target_url = str(req.url or "").strip().lower()
        if not target_url:
            raise ValueError("URL is required")
        match_row = None
        for rec in records:
            if str(rec.get("URL", "")).strip().lower() == target_url:
                match_row = rec.get("_row")
                break
        if not match_row:
            await self._run_in_executor(
                sheet.append_row,
                [
                    req.title or "",
                    req.score if req.score is not None else 0,
                    req.hook or "",
                    req.analysis or "",
                    req.implication or "",
                    req.url,
                    req.mission or "",
                    req.origin_country or "",
                    req.lenses or "",
                    req.score_impact if req.score_impact is not None else 0,
                    req.score_novelty if req.score_novelty is not None else 0,
                    req.score_evidence if req.score_evidence is not None else 0,
                    "Generated",
                    "",
                    "Maybe",
                    "",
                    req.source_date or "Recent",
                ]
            )
            return {"status": "success", "message": "Signal autosaved (created)"}

        headers = await self._run_in_executor(sheet.row_values, 1)
        header_lookup = {header: idx for idx, header in enumerate(headers)}
        field_map = {
            "title": "Title",
            "hook": "Hook",
            "analysis": "Analysis",
            "implication": "Implication",
            "score": "Score",
            "score_novelty": "Score_Novelty",
            "score_evidence": "Score_Evidence",
            "score_impact": "Score_Impact",
            "mission": "Mission",
            "lenses": "Lenses",
            "source_date": "Source_Date",
            "origin_country": "Origin_Country",
        }

        cells = []
        if req.score_impact is None and req.score_evocativeness is not None:
            req.score_impact = req.score_evocativeness
        for field_name, header in field_map.items():
            value = getattr(req, field_name)
            if value is None:
                continue
            col_idx = header_lookup.get(header)
            if col_idx is not None:
                cells.append(gspread.Cell(match_row, col_idx + 1, value))

        if cells:
            await self._run_in_executor(sheet.update_cells, cells)
        return {"status": "success", "message": "Signal autosaved"}

    async def update_sheet_enrichment(self, url: str, analysis: str, implication: str) -> bool:
        sheet = await self._run_in_executor(self._get_sheet)
        if not sheet:
            return False
        await self.ensure_headers(sheet)
        records = await self.get_records(include_rejected=True)
        target_url = str(url or "").strip().lower()
        match_row = None
        for rec in records:
            if str(rec.get("URL", "")).strip().lower() == target_url:
                match_row = rec.get("_row")
                break
        if not match_row:
            return False
        headers = await self._run_in_executor(sheet.row_values, 1)
        header_lookup = {header: idx for idx, header in enumerate(headers)}
        updates = []
        for field, value in (("Analysis", analysis), ("Implication", implication)):
            col_idx = header_lookup.get(field)
            if col_idx is not None:
                updates.append((col_idx + 1, value))
        if not updates:
            return False
        for col_idx, value in updates:
            await self._run_in_executor(sheet.update_cell, match_row, col_idx, value)
        return True

    def update_local_csv(
        self,
        url: str,
        analysis: str,
        implication: str,
        csv_path: str = "Nesta Signal Vault - Sheet1.csv",
    ) -> bool:
        if not os.path.exists(csv_path):
            return False
        try:
            df = pd.read_csv(csv_path)
        except Exception as exc:
            LOGGER.warning("CSV read error: %s", exc)
            return False
        if "URL" not in df.columns:
            return False
        normalized_url = str(url or "").strip().lower()
        if not normalized_url:
            return False
        url_series = df["URL"].astype(str).str.strip().str.lower()
        matches = df.index[url_series == normalized_url].tolist()
        if not matches:
            return False
        idx = matches[0]
        if "Analysis" in df.columns:
            df.at[idx, "Analysis"] = analysis
        if "Implication" in df.columns:
            df.at[idx, "Implication"] = implication
        df.to_csv(csv_path, index=False)
        return True

    def update_local_signal_by_url(
        self,
        req: UpdateSignalRequest,
        csv_path: str = "Nesta Signal Vault - Sheet1.csv",
    ) -> bool:
        if not os.path.exists(csv_path):
            return False
        try:
            df = pd.read_csv(csv_path)
        except Exception as exc:
            LOGGER.warning("CSV read error: %s", exc)
            return False
        if "URL" not in df.columns:
            return False
        for column in ["Hook", "Analysis", "Implication", "Origin_Country"]:
            if column not in df.columns:
                df[column] = ""
        normalized_url = str(req.url or "").strip().lower()
        if not normalized_url:
            return False
        url_series = df["URL"].astype(str).str.strip().str.lower()
        matches = df.index[url_series == normalized_url].tolist()
        if not matches:
            return False
        idx = matches[0]
        if req.hook is not None:
            df.at[idx, "Hook"] = req.hook
        if req.analysis is not None:
            df.at[idx, "Analysis"] = req.analysis
        if req.implication is not None:
            df.at[idx, "Implication"] = req.implication
        if req.origin_country is not None:
            df.at[idx, "Origin_Country"] = req.origin_country
        df.to_csv(csv_path, index=False)
        return True


class MockSheetService:
    async def get_records(self, include_rejected: bool = False) -> List[Dict[str, Any]]:
        LOGGER.info("MockSheetService: get_records called (include_rejected=%s)", include_rejected)
        return []

    async def get_existing_urls(self) -> List[str]:
        LOGGER.info("MockSheetService: get_existing_urls called")
        return []

    async def upsert_signal(self, signal: Dict[str, Any]) -> None:
        LOGGER.info("MockSheetService: upsert_signal called for %s", signal.get("url"))

    async def update_signal_by_url(self, req: UpdateSignalRequest) -> Dict[str, str]:
        LOGGER.info("MockSheetService: update_signal_by_url called for %s", req.url)
        return {"status": "success", "message": "Mock update"}

    async def update_sheet_enrichment(self, url: str, analysis: str, implication: str) -> bool:
        LOGGER.info("MockSheetService: update_sheet_enrichment called for %s", url)
        return False

    def update_local_csv(self, url: str, analysis: str, implication: str, csv_path: str = "Nesta Signal Vault - Sheet1.csv") -> bool:
        LOGGER.info("MockSheetService: update_local_csv called for %s", url)
        return False

    def update_local_signal_by_url(self, req: UpdateSignalRequest, csv_path: str = "Nesta Signal Vault - Sheet1.csv") -> bool:
        LOGGER.info("MockSheetService: update_local_signal_by_url called for %s", req.url)
        return False


class SearchService:
    MAX_RETRIES = 3
    BASE_BLOCKLIST = [
        "bbc.co.uk",
        "cnn.com",
        "nytimes.com",
        "forbes.com",
        "bloomberg.com",
        "businessinsider.com",
    ]
    TOPIC_BLOCKS = {
        "tech": ["techcrunch.com", "theverge.com", "wired.com"],
        "policy": ["gov.uk", "parliament.uk", "whitehouse.gov"],
    }

    def __init__(self, api_key: Optional[str], cx: Optional[str]):
        self.api_key = api_key
        self.cx = cx

    @alru_cache(maxsize=256, ttl=3600)
    async def _cached_search(self, query: str, date_restrict: str, requested_results: int) -> str:
        if not self.api_key or not self.cx:
            return "System Error: Search Config Missing"
        target_results = max(1, min(20, requested_results))
        url = "https://www.googleapis.com/customsearch/v1"
        results = []
        start_index = 1
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            while len(results) < target_results:
                params = {
                    "key": self.api_key,
                    "cx": self.cx,
                    "q": query,
                    "num": 10,
                    "start": start_index,
                    "dateRestrict": date_restrict,
                }
                resp = await http_client.get(url, params=params)
                resp.raise_for_status()
                items = resp.json().get("items", [])
                if not items:
                    break
                for item in items:
                    results.append(
                        f"Title: {item.get('title')}\nLink: {item.get('link')}\nSnippet: {item.get('snippet', '')}"
                    )
                if len(items) < 10:
                    break
                start_index += 10
        if not results:
            return ""
        return "\n\n".join(results[:target_results])

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, RuntimeError)),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        stop=stop_after_attempt(3),
    )
    
    async def search_google(
        self,
        query: str,
        date_restrict: str = "m1",
        requested_results: int = 15,
    ) -> str:
        # Removed: scan_mode, source_types (Logic moved to main.py)
        sleep_time = random.uniform(2.0, 4.0)
        await asyncio.sleep(sleep_time)
        for attempt in range(self.MAX_RETRIES):
            try:
                return await self._cached_search(query, date_restrict, requested_results)
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code if exc.response else None
                if status_code == 429:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    LOGGER.warning("429 rate limit. Waiting %.2fs...", wait_time)
                    await asyncio.sleep(wait_time)
                    continue
                raise
        LOGGER.warning("Failed after %s retries. Skipping query.", self.MAX_RETRIES)
        return ""

class ContentService:
    def __init__(self, timeout: float = 10.0, max_redirects: int = 3):
        self.timeout = timeout
        self.max_redirects = max_redirects

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, RuntimeError, ValueError)),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        stop=stop_after_attempt(3),
    )
    async def fetch_page_content(self, url: str) -> str:
        async with httpx.AsyncClient(follow_redirects=False, timeout=self.timeout) as client:
            current_url = url
            for _ in range(self.max_redirects):
                parsed, ip, hostname = await asyncio.to_thread(validate_url_security, current_url)
                host_header = hostname
                ip_host = f"[{ip}]" if ":" in ip else ip
                netloc = ip_host if not parsed.port else f"{ip_host}:{parsed.port}"
                request_url = urlunparse(
                    (parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
                )
                headers = {"User-Agent": "NestaSignalScout/1.0", "Host": host_header}
                resp = await client.get(request_url, headers=headers)
                if resp.is_redirect:
                    next_url = resp.headers.get("Location")
                    if not next_url:
                        raise RuntimeError("Redirect response missing Location header.")
                    current_url = urljoin(current_url, next_url)
                    continue
                if resp.status_code == 200:
                    return resp.text
                raise RuntimeError(f"Status {resp.status_code}")
        raise RuntimeError("Too many redirects")


class LLMService:
    def __init__(self, api_key: Optional[str], model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    @retry(
        retry=retry_if_exception_type(openai.RateLimitError),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(6),
    )
    async def chat_complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ):
        payload: Dict[str, Any] = {"model": self.model, "messages": messages, "stream": stream}
        if tools is not None:
            payload["tools"] = tools
        if response_format is not None:
            payload["response_format"] = response_format
        return await self.client.chat.completions.create(**payload)


def get_sheet_service(settings: Optional[Settings] = None) -> SheetService | MockSheetService:
    resolved = settings or Settings()
    if not resolved.GOOGLE_CREDENTIALS or not resolved.SHEET_ID:
        LOGGER.warning("Google Sheets credentials missing. Using MockSheetService.")
        return MockSheetService()
    return SheetService(resolved.GOOGLE_CREDENTIALS, resolved.SHEET_ID)
