"""Validate keywords.py structure before prompt injection."""

from __future__ import annotations

import sys
from typing import Iterable

import keywords


def _validate_string_list(values: Iterable[object], label: str) -> list[str]:
    errors: list[str] = []
    seen = set()
    for value in values:
        if not isinstance(value, str):
            errors.append(f"{label} contains non-string value: {value!r}")
            continue
        if not value.strip():
            errors.append(f"{label} contains empty/blank string.")
            continue
        if value in seen:
            errors.append(f"{label} contains duplicate value: {value!r}")
            continue
        seen.add(value)
    if not seen:
        errors.append(f"{label} is empty.")
    return errors


def validate_keywords() -> list[str]:
    errors: list[str] = []

    if not hasattr(keywords, "MISSION_KEYWORDS"):
        errors.append("Missing MISSION_KEYWORDS in keywords.py.")
    elif not isinstance(keywords.MISSION_KEYWORDS, dict):
        errors.append("MISSION_KEYWORDS must be a dict.")
    else:
        for mission, terms in keywords.MISSION_KEYWORDS.items():
            if not isinstance(mission, str) or not mission.strip():
                errors.append("MISSION_KEYWORDS contains an empty mission name.")
                continue
            if not isinstance(terms, list):
                errors.append(f"MISSION_KEYWORDS[{mission!r}] must be a list.")
                continue
            errors.extend(_validate_string_list(terms, f"MISSION_KEYWORDS[{mission!r}]"))

    if not hasattr(keywords, "CROSS_CUTTING_KEYWORDS"):
        errors.append("Missing CROSS_CUTTING_KEYWORDS in keywords.py.")
    elif not isinstance(keywords.CROSS_CUTTING_KEYWORDS, list):
        errors.append("CROSS_CUTTING_KEYWORDS must be a list.")
    else:
        errors.extend(_validate_string_list(keywords.CROSS_CUTTING_KEYWORDS, "CROSS_CUTTING_KEYWORDS"))

    return errors


def main() -> int:
    errors = validate_keywords()
    if errors:
        print("Keyword validation failed:")
        for err in errors:
            print(f"- {err}")
        return 1
    print("Keyword validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
