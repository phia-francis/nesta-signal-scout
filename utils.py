from __future__ import annotations

import ipaddress
import json
import logging
import re
import socket
from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import urlparse

from dateutil.relativedelta import relativedelta
from dateutil import parser


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "path"):
            payload["path"] = record.path
        return json.dumps(payload)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


LOGGER = get_logger(__name__)


def validate_url_security(url: str) -> Tuple[object, str, str]:
    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise ValueError(f"URL parse error: {exc}") from exc

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Invalid URL scheme")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL is missing a hostname")

    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except Exception as exc:
        raise ValueError(f"Hostname resolution failed: {exc}") from exc

    for _, _, _, _, sockaddr in addr_info:
        ip_str = sockaddr[0]
        ip_obj = ipaddress.ip_address(ip_str)
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_unspecified
            or ip_obj.is_reserved
        ):
            raise ValueError("Non-public IP access blocked")

    ip = addr_info[0][4][0]
    return parsed, ip, hostname


def parse_source_date(date_str: Optional[str]) -> Optional[datetime]:
# 1. Immediate rejection of bad data
    if not date_str or str(date_str).lower() in {"recent", "unknown", "n/a", "na", "none"}:
        return None
    
    # 2. Basic Cleanup: Remove common separators that confuse parsers
    # This turns "2023 | Technology" into "2023   Technology"
    cleaned = re.sub(r"[|•]", " ", str(date_str)).strip()
    
    try:
        # 3. The Magic: parser.parse
        # fuzzy=True: Ignores non-date text (e.g., extracts date from "Published on May 1st")
        # dayfirst=True: IMPORTANT for UK. Interprets 01/02/23 as Feb 1st, not Jan 2nd.
        return parser.parse(cleaned, fuzzy=True, dayfirst=True)
        
    except (ValueError, TypeError, OverflowError):
        # If even the smart parser can't find a date, return None
        return None

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    month_year_formats = ["%B %Y", "%b %Y"]
    for fmt in month_year_formats:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.replace(day=1)
        except ValueError:
            continue

    if re.fullmatch(r"\d{4}", cleaned):
        return datetime(int(cleaned), 1, 1)
    return None


TIME_FILTER_OFFSETS = {
    "Past Month": relativedelta(months=1),
    "Past 3 Months": relativedelta(months=3),
    "Past 6 Months": relativedelta(months=6),
    "Past Year": relativedelta(years=1),
}


def is_date_within_time_filter(source_date: Optional[str], time_filter: str, request_date: datetime) -> bool:
    parsed = parse_source_date(source_date)
    if not parsed:
        LOGGER.warning("Date rejected (unparsable): %s", source_date)
        return False
    if parsed > request_date:
        return False
    offset = TIME_FILTER_OFFSETS.get(time_filter, TIME_FILTER_OFFSETS["Past Month"])
    cutoff_date = request_date - offset
    return parsed >= cutoff_date
