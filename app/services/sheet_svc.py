from __future__ import annotations

import asyncio
import atexit
import json
import logging
import time
from datetime import datetime, timezone
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
    URL_COLUMN_INDEX = 5
    MODE_COLUMN_INDEX = 2
    MISSION_COLUMN_INDEX = 3
    TITLE_COLUMN_INDEX = 4
    SUMMARY_COLUMN_INDEX = 6
    TYPOLOGY_COLUMN_INDEX = 7
    ACTIVITY_COLUMN_INDEX = 8
    ATTENTION_COLUMN_INDEX = 9
    SOURCE_COLUMN_INDEX = 10
    NARRATIVE_GROUP_COLUMN_INDEX = 12
    SOURCE_DATE_COLUMN_INDEX = 13

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
        """Fetch existing URLs by reading URL column directly from both tabs."""
        try:
            db_urls = await asyncio.to_thread(self.get_database_sheet().col_values, self.URL_COLUMN_INDEX)
            wl_urls = await asyncio.to_thread(self.get_watchlist_sheet().col_values, self.URL_COLUMN_INDEX)
            combined = {url.strip() for url in [*db_urls, *wl_urls] if isinstance(url, str) and url.strip()}
            combined.discard("URL")
            return combined
        except Exception as sheet_error:
            logging.error("Failed to fetch existing URLs: %s", sheet_error)
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
            signal.get("narrative_group") or "Unclustered",
            signal.get("source_date") or signal.get("date") or "Unknown",
        ]

    @staticmethod
    def _normalise_headers(headers: list[str]) -> list[str]:
        """Make headers deterministic even with blanks/duplicates."""
        seen: dict[str, int] = {}
        normalised: list[str] = []
        for index, header in enumerate(headers, start=1):
            base = (header or "").strip() or f"Column_{index}"
            seen[base] = seen.get(base, 0) + 1
            normalised.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
        return normalised

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
            await self.batch_sync_to_sheets(force=True)

    async def queue_signals_for_sync(self, signals: list[SignalCard | dict[str, Any]]) -> None:
        """Queue many signals for periodic background sync."""
        if not signals:
            return
        payloads = [s.model_dump() if isinstance(s, SignalCard) else s for s in signals]
        async with self._queue_lock:
            self._sync_queue.extend(payloads)
        await self.batch_sync_to_sheets(force=True)

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

    async def save_signals_batch(self, signals: list[dict[str, Any]]) -> None:
        """Append signals as new rows, preserving full scan history."""
        if not signals:
            return
        try:
            rows_to_append = [self._signal_to_row(signal) for signal in signals]
            await asyncio.to_thread(
                self.get_database_sheet().append_rows,
                rows_to_append,
                value_input_option="USER_ENTERED",
                insert_data_option="INSERT_ROWS",
            )
        except gspread.exceptions.GSpreadException as sheet_error:
            raise ServiceError(f"Failed to save signal batch: {sheet_error}") from sheet_error

    async def add_to_watchlist(self, signal: dict[str, Any]) -> None:
        """Persist starred signals into Watchlist tab for analyst triage."""
        row = [
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
            signal.get("status", "Starred"),
            signal.get("narrative_group") or "Unclustered",
            signal.get("source_date") or signal.get("date") or "Unknown",
        ]
        try:
            await asyncio.to_thread(self.get_watchlist_sheet().append_row, row)
        except gspread.exceptions.GSpreadException as sheet_error:
            raise ServiceError(f"Failed to write watchlist row: {sheet_error}") from sheet_error

    async def update_status(self, url: str, status: str) -> None:
        """Update signal status in the Database tab by URL."""
        try:
            sheet = self.get_database_sheet()
            url_column = await asyncio.to_thread(sheet.col_values, self.URL_COLUMN_INDEX)
            row_index = next(
                (idx for idx, value in enumerate(url_column, start=1) if str(value).strip() == str(url).strip()),
                None,
            )
            if row_index:
                await asyncio.to_thread(sheet.update_cell, row_index, self.STATUS_COLUMN_INDEX, status)
        except gspread.exceptions.GSpreadException as sheet_error:
            logging.error("Failed to update status for %s: %s", url, sheet_error)
            raise ServiceError("Failed to update status.") from sheet_error


    async def get_rows_by_mission(self, mission: str) -> list[dict[str, Any]]:
        """Fetch only rows matching a specific mission by filtering all records."""
        all_records = await self.get_all()
        return [record for record in all_records if record.get("Mission") == mission]

    async def get_all(self) -> list[dict[str, Any]]:
        """Return all saved signals as raw records from Database tab."""
        try:
            values = await asyncio.to_thread(self.get_database_sheet().get_all_values)
            if not values:
                return []

            headers = self._normalise_headers(values[0])
            records: list[dict[str, Any]] = []
            for row in values[1:]:
                padded = row + [""] * (len(headers) - len(row))
                records.append({header: padded[index] for index, header in enumerate(headers)})
            return records
        except gspread.exceptions.GSpreadException as sheet_error:
            raise ServiceError(f"Failed to fetch saved signals: {sheet_error}") from sheet_error

    async def get_signal_by_url(self, url: str) -> dict[str, Any] | None:
        """Fetch a specific signal by its exact URL."""
        if not url:
            return None
        try:
            sheet = self.get_database_sheet()
            cell = await asyncio.to_thread(sheet.find, url.strip(), in_column=self.URL_COLUMN_INDEX)
            if not cell:
                return None
            
            headers = self._normalise_headers(await asyncio.to_thread(sheet.row_values, 1))
            row_values = await asyncio.to_thread(sheet.row_values, cell.row)
            
            padded_row = row_values + [""] * (len(headers) - len(row_values))
            return dict(zip(headers, padded_row))
        except gspread.exceptions.CellNotFound:
            return None
        except gspread.exceptions.GSpreadException as sheet_error:
            logging.error(f"Error fetching signal by URL '{url}': {sheet_error}")
            raise ServiceError(f"Failed to fetch signal by URL: {sheet_error}") from sheet_error

    async def flush_pending_sync(self) -> None:
        """Force-flush any queued signals, including partial batches."""
        await self.batch_sync_to_sheets(force=True)

    async def save_trend_analysis(self, cluster_name: str, analysis_text: str, strength: str) -> None:
        """Append a trend analysis row to the 'Trend Analysis' worksheet."""
        try:
            worksheet = self._get_worksheet("Trend Analysis")
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            await asyncio.to_thread(
                worksheet.append_row,
                [date_str, cluster_name, strength, analysis_text],
            )
        except Exception as e:
            logging.error("Failed to save trend analysis to sheet: %s", e)

    def _flush_queue_on_exit(self) -> None:
        """Best-effort queue flush during interpreter shutdown."""
        if not self._sync_queue:
            return
        try:
            asyncio.run(self.batch_sync_to_sheets(force=True))
        except RuntimeError:
            # Event loop state may prevent flush during shutdown.
            pass
