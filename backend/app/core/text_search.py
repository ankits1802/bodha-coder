from __future__ import annotations

from app.core.errors import Invalid

__all__ = ["LIKE_ESCAPE", "MAX_SEARCH_LENGTH", "MIN_SEARCH_LENGTH", "contains_pattern", "search_term"]

MIN_SEARCH_LENGTH = 2
MAX_SEARCH_LENGTH = 100
LIKE_ESCAPE = "\\"


def search_term(text: str) -> str:
    term = text.strip()
    if len(term) < MIN_SEARCH_LENGTH:
        raise Invalid(f"type at least {MIN_SEARCH_LENGTH} characters")
    if len(term) > MAX_SEARCH_LENGTH:
        raise Invalid(f"type at most {MAX_SEARCH_LENGTH} characters")
    return term


def contains_pattern(term: str) -> str:
    escaped = term.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2).replace("%", f"{LIKE_ESCAPE}%").replace("_", f"{LIKE_ESCAPE}_")
    return f"%{escaped}%"
