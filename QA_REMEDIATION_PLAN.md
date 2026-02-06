# QA Remediation Plan

## Objectives
- Restore test coverage expectations for core search, keyword validation, and signal parsing workflows.
- Reconcile API/utility interfaces with the existing unit test suite.
- Stabilize date parsing and time-filter logic for deterministic QA outcomes.

## Findings
1. **Broken test contracts**: The prior refactor removed `ChatRequest`, `chat_endpoint`, and helper utilities expected by the test suite.
2. **Keyword schema drift**: `CROSS_CUTTING_KEYWORDS` and query generation helpers were removed, breaking keyword validation and menu rendering tests.
3. **Date parsing regressions**: The parser returned incorrect results for year-first and month-only formats, causing time-filter logic failures.

## Remediation Actions (Enacted)
- **Reintroduced QA-required interfaces**: Added `ChatRequest`, re-exposed `parse_source_date`/`is_date_within_time_filter`, and rebuilt `chat_endpoint` + keyword menu logic to match existing tests.
- **Restored keyword schema + query generator**: Added `CROSS_CUTTING_KEYWORDS` and `generate_broad_scan_queries` with deterministic fallbacks.
- **Fixed date parsing**: Implemented explicit format handling and fallbacks to ensure consistent parsing for QA fixtures.
- **Validated via test suite**: Ran `pytest -q` and confirmed all tests pass.

## Follow-Up Enhancements (Recommended)
- Add contract tests for new API endpoints (`/api/mode/radar`, `/api/mode/research`) to prevent interface drift.
- Add integration tests for the UI stepper/radar sweep workflow (Playwright) in CI to catch regressions.
- Introduce a linting step (ruff/black) to enforce consistent formatting and prevent dead code.
