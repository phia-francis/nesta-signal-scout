from app.main import app
from app.legacy_compat import (
    ChatRequest,
    build_allowed_keywords_menu,
    chat_endpoint,
    client,
    get_sheet_records,
    upsert_signal,
)
from utils import is_date_within_time_filter, parse_source_date

__all__ = [
    "app",
    "parse_source_date",
    "is_date_within_time_filter",
    "build_allowed_keywords_menu",
    "ChatRequest",
    "chat_endpoint",
    "client",
    "get_sheet_records",
    "upsert_signal",
]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
