from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from app.core.config import Settings
from app.services.search_svc import ServiceError


class SheetService:
    """Google Sheets persistence service."""

    STATUS_COLUMN_INDEX = 11

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = None
        if not self.settings.GOOGLE_CREDENTIALS:
            logging.warning("No Google credentials found.")
            return

        try:
            credentials = Credentials.from_service_account_info(
                json.loads(self.settings.GOOGLE_CREDENTIALS),
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )
            self.client = gspread.authorize(credentials)
        except Exception as exc:
            logging.error("Failed to authorise Google Sheets client: %s", exc)

    def get_sheet(self):
        if not self.client:
            raise ServiceError("Database connection not initialised.")
        try:
            return self.client.open_by_key(self.settings.SHEET_ID).sheet1
        except Exception as exc:
            raise ServiceError(f"Failed to open sheet: {exc}") from exc

    async def get_existing_urls(self) -> set[str]:
        sheet = self.get_sheet()
        try:
            records = await asyncio.to_thread(sheet.get_all_records)
            return {record.get("URL", "") for record in records if record.get("URL")}
        except Exception as exc:
            logging.error("Failed to get existing URLs: %s", exc)
            return set()

    async def save_signal(self, signal: dict[str, Any], existing_urls: set[str] | None = None) -> None:
        if existing_urls and signal.get("url") in existing_urls:
            return

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
        await asyncio.to_thread(self.get_sheet().append_row, row)

    async def update_status(self, url: str, status: str) -> None:
        try:
            sheet = self.get_sheet()
            cell = await asyncio.to_thread(sheet.find, url)
            if cell:
                await asyncio.to_thread(sheet.update_cell, cell.row, self.STATUS_COLUMN_INDEX, status)
        except Exception as exc:
            logging.error("Failed to update status for %s: %s", url, exc)
            raise ServiceError("Failed to update status.") from exc

    async def get_all(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self.get_sheet().get_all_records)
