"""Server-side date-of-birth validation and age policy."""
from __future__ import annotations

from datetime import date

MINIMUM_AGE = 18


def parse_date_of_birth(value: str) -> date:
    """Parse an exact ISO calendar date and reject future/impossible dates."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("date_of_birth_required")
    try:
        parsed = date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError("invalid_date_of_birth") from exc
    if parsed > date.today():
        raise ValueError("future_date_of_birth")
    return parsed


def calculate_age(date_of_birth: date, today: date | None = None) -> int:
    today = today or date.today()
    if date_of_birth > today:
        raise ValueError("future_date_of_birth")
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


def validate_minimum_age(value: str) -> str:
    parsed = parse_date_of_birth(value)
    if calculate_age(parsed) < MINIMUM_AGE:
        raise ValueError("minimum_age_required")
    return parsed.isoformat()
