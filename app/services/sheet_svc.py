from __future__ import annotations

import asyncio
import atexit
import json
import logging
import time
from datetime import datetime
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from app.core.config import Settings
from app.domain.models import SignalCard
from app.services.search_svc import ServiceError

QUEUE_FLUSH_INTERVAL_SECONDS = 60
QUEUE_FLUSH_BATCH_SIZE = 50


class SheetService:
    """Google Sheets persistence service with buffered background sync."""

    DATABASE_TAB_NAME = "Database"
    WATCHLIST_TAB_NAME = "Watchlist"
    STATUS_COLUMN_INDEX = 11

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client: gspread.Client | None = None
        self._sync_queue: list[dict[str, Any]] = []
        self._queue_lock = asyncio.Lock()
        self._last_sync_at = time.monotonic()
        atexit.register(self._flush_queue_on_exit)

        if not self.settings.GOOGLE_CREDENTIALS:
            logging.warning("No Google credentials found.")
            return

        try:
            credentials = Credentials.from_service_account_info(
                json.loads(self.settings.GOOGLE_CREDENTIALS),
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )
            self.client = gspread.authorize(credentials)
        except (json.JSONDecodeError, ValueError, TypeError) as credential_error:
            logging.error("Failed to parse Google credentials payload: %s", credential_error)
        except gspread.exceptions.GSpreadException as gspread_error:
            logging.error("Failed to authorise Google Sheets client: %s", gspread_error)

    def _open_spreadsheet(self):
        if not self.client or not self.settings.SHEET_ID:
            raise ServiceError("Database connection not initialised.")
        try:
            return self.client.open_by_key(self.settings.SHEET_ID)
        except gspread.exceptions.GSpreadException as sheet_error:
            raise ServiceError(f"Failed to open sheet: {sheet_error}") from sheet_error

    def _get_worksheet(self, tab_name: str):
        spreadsheet = self._open_spreadsheet()
        try:
            return spreadsheet.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            try:
                return spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=20)
            except gspread.exceptions.GSpreadException as create_error:
                raise ServiceError(f"Failed to create worksheet '{tab_name}': {create_error}") from create_error

    def get_database_sheet(self):
        return self._get_worksheet(self.DATABASE_TAB_NAME)

    def get_watchlist_sheet(self):
        return self._get_worksheet(self.WATCHLIST_TAB_NAME)

    async def get_existing_urls(self) -> set[str]:
        """Fetch URL set from both Database and Watchlist tabs for deduplication."""
        try:
            database_records = await asyncio.to_thread(self.get_database_sheet().get_all_records)
            watchlist_records = await asyncio.to_thread(self.get_watchlist_sheet().get_all_records)
            return {
                record.get("URL", "")
                for record in [*database_records, *watchlist_records]
                if record.get("URL")
            }
        except gspread.exceptions.GSpreadException as sheet_error:
            logging.error("Failed to get existing URLs: %s", sheet_error)
            return set()

    def _signal_to_row(self, signal: dict[str, Any]) -> list[Any]:
        return [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            signal.get("mode", "Radar"),
            signal.get("mission", "General"),
            signal.get("title", "Untitled"),
            signal.get("url", ""),
            (signal.get("summary", "") or "")[:500],
            signal.get("typology", "Unsorted"),
            signal.get("score_activity", 0),
            signal.get("score_attention", 0),
            signal.get("source", "Web"),
            signal.get("status", "New"),
        ]

    async def queue_signal_for_sync(self, signal: SignalCard | dict[str, Any]) -> None:
        """Queue a single signal for periodic background sync."""
        payload = signal.model_dump() if isinstance(signal, SignalCard) else signal
        async with self._queue_lock:
            self._sync_queue.append(payload)
            should_flush = (
                len(self._sync_queue) >= QUEUE_FLUSH_BATCH_SIZE
                or (time.monotonic() - self._last_sync_at) >= QUEUE_FLUSH_INTERVAL_SECONDS
            )
        if should_flush:
            await self.batch_sync_to_sheets()

    async def queue_signals_for_sync(self, signals: list[SignalCard | dict[str, Any]]) -> None:
        """Queue many signals for periodic background sync."""
        for signal in signals:
            await self.queue_signal_for_sync(signal)

    async def batch_sync_to_sheets(self, *, force: bool = False) -> None:
        """Flush queued signals to Google Sheets in batch calls."""
        async with self._queue_lock:
            if not self._sync_queue:
                self._last_sync_at = time.monotonic()
                return
            if force:
                batch = list(self._sync_queue)
                self._sync_queue = []
            else:
                batch = self._sync_queue[:QUEUE_FLUSH_BATCH_SIZE]
                self._sync_queue = self._sync_queue[QUEUE_FLUSH_BATCH_SIZE:]
            self._last_sync_at = time.monotonic()

        rows_to_append = [self._signal_to_row(signal) for signal in batch]
        try:
            await asyncio.to_thread(self.get_database_sheet().append_rows, rows_to_append)
        except gspread.exceptions.GSpreadException as sheet_error:
            logging.error("Failed to sync queued signals: %s", sheet_error)
            async with self._queue_lock:
                self._sync_queue = batch + self._sync_queue

    async def save_signal(self, signal: dict[str, Any], existing_urls: set[str] | None = None) -> None:
        """Backwards-compatible helper: queue one signal instead of immediate write."""
        if existing_urls and signal.get("url") in existing_urls:
            await self._update_existing_signal(signal.get("url", ""), signal)
            return
        await self.queue_signal_for_sync(signal)

    async def save_signals_batch(
        self,
        signals: list[dict[str, Any]],
        existing_urls: set[str] | None = None,
    ) -> None:
        """Queue many signals instead of writing during user request lifecycle."""
        if not signals:
            return
        for signal in signals:
            if existing_urls and signal.get("url") in existing_urls:
                await self._update_existing_signal(signal.get("url", ""), signal)
            else:
                await self.queue_signal_for_sync(signal)

    async def upsert_signal(self, signal: dict[str, Any], existing_urls: set[str] | None = None) -> None:
        """Compatibility wrapper for existing callers."""
        await self.save_signal(signal, existing_urls)

    async def _update_existing_signal(self, url: str, signal: dict[str, Any]) -> None:
        """Update existing signal row in the Database tab by URL."""
        try:
            sheet = self.get_database_sheet()
            cell = await asyncio.to_thread(sheet.find, url)
            if not cell:
                return
            updates = [
                (cell.row, 3, signal.get("mission", "General")),
                (cell.row, 4, signal.get("title", "Untitled")),
                (cell.row, 6, (signal.get("summary", "") or "")[:500]),
                (cell.row, 7, signal.get("typology", "Unsorted")),
                (cell.row, 8, signal.get("score_activity", 0)),
                (cell.row, 9, signal.get("score_attention", 0)),
                (cell.row, 10, signal.get("source", "Web")),
            ]
            for row_index, column_index, value in updates:
                await asyncio.to_thread(sheet.update_cell, row_index, column_index, value)
        except gspread.exceptions.GSpreadException as sheet_error:
            raise ServiceError(f"Failed to update signal: {sheet_error}") from sheet_error

    async def add_to_watchlist(self, signal: dict[str, Any]) -> None:
        """Persist starred signals into Watchlist tab for analyst triage."""
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            signal.get("mission", "General"),
            signal.get("title", "Untitled"),
            signal.get("url", ""),
            (signal.get("summary", "") or "")[:500],
            signal.get("typology", "Unsorted"),
            signal.get("score_activity", 0),
            signal.get("score_attention", 0),
            signal.get("source", "Web"),
            signal.get("status", "Starred"),
        ]
        try:
            await asyncio.to_thread(self.get_watchlist_sheet().append_row, row)
        except gspread.exceptions.GSpreadException as sheet_error:
            raise ServiceError(f"Failed to write watchlist row: {sheet_error}") from sheet_error

    async def update_status(self, url: str, status: str) -> None:
        """Update signal status in the Database tab by URL."""
        try:
            sheet = self.get_database_sheet()
            cell = await asyncio.to_thread(sheet.find, url)
            if cell:
                await asyncio.to_thread(sheet.update_cell, cell.row, self.STATUS_COLUMN_INDEX, status)
        except gspread.exceptions.GSpreadException as sheet_error:
            logging.error("Failed to update status for %s: %s", url, sheet_error)
            raise ServiceError("Failed to update status.") from sheet_error

    async def get_all(self) -> list[dict[str, Any]]:
        """Return all saved signals from Database tab."""
        try:
            return await asyncio.to_thread(self.get_database_sheet().get_all_records)
        except gspread.exceptions.GSpreadException as sheet_error:
            raise ServiceError(f"Failed to fetch saved signals: {sheet_error}") from sheet_error

    def _flush_queue_on_exit(self) -> None:
        """Best-effort queue flush during interpreter shutdown."""
        if not self._sync_queue:
            return
        try:
            asyncio.run(self.batch_sync_to_sheets(force=True))
        except RuntimeError:
            # Event loop state may prevent flush during shutdown.
            pass
