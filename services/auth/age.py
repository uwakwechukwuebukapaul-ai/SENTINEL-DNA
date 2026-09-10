"""Server-side age and date-of-birth validation."""
from datetime import date

MINIMUM_AGE = 18

def parse_date_of_birth(value: str | date | None) -> str:
    if isinstance(value, date):
        dob = value
    else:
        try:
            dob = date.fromisoformat(str(value or "").strip())
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid_date_of_birth") from exc
    if dob > date.today():
        raise ValueError("future_date_of_birth")
    return dob.isoformat()

def calculate_age(value: str | date) -> int:
    dob = date.fromisoformat(parse_date_of_birth(value))
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

def validate_minimum_age(value: str | date | None) -> str:
    normalized = parse_date_of_birth(value)
    if calculate_age(normalized) < MINIMUM_AGE:
        raise ValueError("minimum_age_required")
    return normalized
