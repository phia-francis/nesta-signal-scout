"""File-based storage for scans and themes."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
import uuid
import fcntl

logger = logging.getLogger(__name__)

# Storage directory
STORAGE_DIR = Path("/tmp/signal_scout_scans")
STORAGE_DIR.mkdir(exist_ok=True, parents=True)

# Keep scans for 30 days
RETENTION_DAYS = 30


class ScanStorage:
    """File-based storage for scan results and themes."""
    
    def __init__(self, storage_dir: Path | None = None):
        self.storage_dir = storage_dir or STORAGE_DIR
        self.storage_dir.mkdir(exist_ok=True, parents=True)
    
    def save_scan(
        self,
        query: str,
        mode: str,
        signals: list[dict[str, Any]],
        themes: list[dict[str, Any]] | None = None,
        warnings: list[str] | None = None
    ) -> str:
        """
        Save a scan to storage.
        
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
            # Write with file locking for concurrent safety
            with open(scan_file, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(scan_data, f, indent=2)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            logger.info(f"Saved scan {scan_id} with {len(signals)} signals")
            return scan_id
            
        except Exception as e:
            logger.error(f"Failed to save scan: {e}")
            raise
    
    def get_scan(self, scan_id: str) -> dict[str, Any] | None:
        """
        Retrieve a scan by ID.
        
        Returns:
            Scan data dict or None if not found
        """
        scan_file = self.storage_dir / f"{scan_id}.json"
        
        if not scan_file.exists():
            logger.warning(f"Scan {scan_id} not found")
            return None
        
        try:
            with open(scan_file, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                scan_data = json.load(f)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            logger.info(f"Retrieved scan {scan_id}")
            return scan_data
            
        except Exception as e:
            logger.error(f"Failed to load scan {scan_id}: {e}")
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


# Singleton instance
_storage_instance: ScanStorage | None = None


def get_scan_storage() -> ScanStorage:
    """Get or create the singleton storage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = ScanStorage()
    return _storage_instance
