"""Persistent storage for scans using Google Sheets with local file cache."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional
import uuid
import fcntl

import gspread
from google.oauth2.service_account import Credentials

from functools import lru_cache

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Local cache directory (fast reads, but ephemeral on Render)
STORAGE_DIR = Path("/tmp/signal_scout_scans")
STORAGE_DIR.mkdir(exist_ok=True, parents=True)

# Keep scans for 30 days
RETENTION_DAYS = 30


class ScanStorage:
    """Persistent scan storage using Google Sheets with local file cache."""
    
    SHEET_NAME = "Saved_Scans"
    
    def __init__(self, storage_dir: Path | None = None, sheets_client: gspread.Client | None = None, spreadsheet_id: str | None = None):
        self.storage_dir = storage_dir or STORAGE_DIR
        self.storage_dir.mkdir(exist_ok=True, parents=True)
        self.sheets_client = sheets_client
        self.spreadsheet_id = spreadsheet_id
    
    def _get_worksheet(self) -> Optional[gspread.Worksheet]:
        """Get or create the Saved_Scans worksheet."""
        if not self.sheets_client or not self.spreadsheet_id:
            return None
        try:
            spreadsheet = self.sheets_client.open_by_key(self.spreadsheet_id)
            try:
                return spreadsheet.worksheet(self.SHEET_NAME)
            except gspread.exceptions.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(
                    title=self.SHEET_NAME,
                    rows=1000,
                    cols=5
                )
                worksheet.update('A1:E1', [['scan_id', 'timestamp', 'query', 'mode', 'payload']])
                return worksheet
        except Exception as e:
            logger.error(f"Failed to get Saved_Scans worksheet: {e}")
            return None
    
    def _save_to_sheets(self, scan_id: str, query: str, mode: str, payload: dict[str, Any]) -> None:
        """Save scan to Google Sheets for persistent storage."""
        worksheet = self._get_worksheet()
        if not worksheet:
            return
        try:
            payload_json = json.dumps(payload)
            row = [
                scan_id,
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                query,
                mode,
                payload_json
            ]
            worksheet.append_row(row)
            logger.info(f"Saved scan {scan_id} to Google Sheets")
        except Exception as e:
            logger.error(f"Failed to save scan {scan_id} to Sheets: {e}")
    
    def _get_from_sheets(self, scan_id: str) -> Optional[dict[str, Any]]:
        """Retrieve scan from Google Sheets using batch column fetch."""
        worksheet = self._get_worksheet()
        if not worksheet:
            return None
        try:
            # Batch fetch all scan_ids in column 1 (single API call)
            scan_ids = worksheet.col_values(1)
            if scan_id not in scan_ids:
                return None
            row_index = scan_ids.index(scan_id) + 1  # 1-based row index
            row = worksheet.row_values(row_index)
            if len(row) >= 5:
                payload = json.loads(row[4])
                return payload
            return None
        except Exception as e:
            logger.error(f"Failed to load scan {scan_id} from Sheets: {e}")
            return None
    
    def save_scan(
        self,
        query: str,
        mode: str,
        signals: list[dict[str, Any]],
        themes: list[dict[str, Any]] | None = None,
        warnings: list[str] | None = None
    ) -> str:
        """
        Save a scan to local file cache and Google Sheets.
        
        Returns:
            scan_id: Unique identifier for the scan
        """
        scan_id = str(uuid.uuid4())
        
        scan_data = {
            "scan_id": scan_id,
            "query": query,
            "mode": mode,
            "signals": signals,
            "themes": themes or [],
            "warnings": warnings or [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "signal_count": len(signals)
        }
        
        scan_file = self.storage_dir / f"{scan_id}.json"
        
        try:
            # Write to local file cache
            with open(scan_file, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(scan_data, f, indent=2)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            logger.info(f"Saved scan {scan_id} with {len(signals)} signals")
            
        except Exception as e:
            logger.error(f"Failed to save scan to file: {e}")
            raise
        
        # Also save to Google Sheets for persistence across server restarts
        self._save_to_sheets(scan_id, query, mode, scan_data)
        
        return scan_id
    
    def get_scan(self, scan_id: str) -> dict[str, Any] | None:
        """
        Retrieve a scan by ID. Checks local cache first, then Google Sheets.
        
        Returns:
            Scan data dict or None if not found
        """
        # Try local file cache first (fast)
        scan_file = self.storage_dir / f"{scan_id}.json"
        
        if scan_file.exists():
            try:
                with open(scan_file, 'r') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    scan_data = json.load(f)
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                
                logger.info(f"Retrieved scan {scan_id} from local cache")
                return scan_data
                
            except Exception as e:
                logger.error(f"Failed to load scan {scan_id} from file: {e}")
        
        # Fallback to Google Sheets (survives server restarts)
        logger.info(f"Scan {scan_id} not in local cache, checking Google Sheets")
        scan_data = self._get_from_sheets(scan_id)
        
        if scan_data:
            # Re-cache locally for faster subsequent reads
            try:
                with open(scan_file, 'w') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    json.dump(scan_data, f, indent=2)
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                logger.info(f"Re-cached scan {scan_id} from Sheets to local file")
            except Exception as e:
                logger.warning(f"Failed to re-cache scan {scan_id}: {e}")
            
            return scan_data
        
        logger.warning(f"Scan {scan_id} not found in any storage")
        return None
    
    def update_themes(self, scan_id: str, themes: list[dict[str, Any]]) -> bool:
        """
        Update themes for an existing scan.
        
        Returns:
            True if successful, False otherwise
        """
        scan_data = self.get_scan(scan_id)
        
        if not scan_data:
            logger.warning(f"Cannot update themes: scan {scan_id} not found")
            return False
        
        scan_data["themes"] = themes
        scan_data["themes_updated_at"] = datetime.now(timezone.utc).isoformat()
        
        scan_file = self.storage_dir / f"{scan_id}.json"
        
        try:
            with open(scan_file, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(scan_data, f, indent=2)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            logger.info(f"Updated themes for scan {scan_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update themes for scan {scan_id}: {e}")
            return False
    
    def list_scans(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        List recent scans.
        
        Returns:
            List of scan metadata (without full signal data)
        """
        scans = []
        
        try:
            scan_files = sorted(
                self.storage_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            for scan_file in scan_files[:limit]:
                try:
                    with open(scan_file, 'r') as f:
                        scan_data = json.load(f)
                    
                    # Return metadata only
                    scans.append({
                        "scan_id": scan_data["scan_id"],
                        "query": scan_data["query"],
                        "mode": scan_data["mode"],
                        "signal_count": scan_data.get("signal_count", 0),
                        "theme_count": len(scan_data.get("themes", [])),
                        "created_at": scan_data["created_at"]
                    })
                except Exception as e:
                    logger.warning(f"Failed to read scan file {scan_file}: {e}")
                    continue
            
            return scans
            
        except Exception as e:
            logger.error(f"Failed to list scans: {e}")
            return []
    
    def delete_scan(self, scan_id: str) -> bool:
        """
        Delete a scan.
        
        Returns:
            True if deleted, False otherwise
        """
        scan_file = self.storage_dir / f"{scan_id}.json"
        
        if not scan_file.exists():
            return False
        
        try:
            scan_file.unlink()
            logger.info(f"Deleted scan {scan_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete scan {scan_id}: {e}")
            return False
    
    def cleanup_old_scans(self, days: int = RETENTION_DAYS) -> int:
        """
        Delete scans older than specified days.
        
        Returns:
            Number of scans deleted
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        deleted_count = 0
        
        try:
            for scan_file in self.storage_dir.glob("*.json"):
                try:
                    with open(scan_file, 'r') as f:
                        scan_data = json.load(f)
                    
                    created_at = datetime.fromisoformat(scan_data["created_at"])
                    
                    if created_at < cutoff:
                        scan_file.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted old scan {scan_data['scan_id']}")
                        
                except Exception as e:
                    logger.warning(f"Failed to check/delete scan {scan_file}: {e}")
                    continue
            
            logger.info(f"Cleanup completed: deleted {deleted_count} old scans")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old scans: {e}")
            return deleted_count


@lru_cache(maxsize=1)
def get_scan_storage() -> ScanStorage:
    """Get or create the singleton storage instance with Google Sheets integration."""
    sheets_client = None
    spreadsheet_id = None
    settings = get_settings()

    if settings.GOOGLE_CREDENTIALS and settings.SHEET_ID:
        try:
            credentials = Credentials.from_service_account_info(
                json.loads(settings.GOOGLE_CREDENTIALS),
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )
            sheets_client = gspread.authorize(credentials)
            spreadsheet_id = settings.SHEET_ID
            logger.info("ScanStorage initialised with Google Sheets persistence")
        except Exception as e:
            logger.error(f"Failed to initialise Google Sheets for ScanStorage: {e}")
    else:
        logger.warning("Google credentials or Sheet ID not configured; ScanStorage using local files only")

    return ScanStorage(
        sheets_client=sheets_client,
        spreadsheet_id=spreadsheet_id,
    )
