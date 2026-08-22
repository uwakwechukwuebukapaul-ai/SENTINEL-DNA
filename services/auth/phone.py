"""Standards-compatible international phone normalization."""
import phonenumbers
from phonenumbers import NumberParseException

def normalize_phone(country: str, local_number: str) -> str:
    try:
        parsed = phonenumbers.parse(str(local_number or "").strip(), str(country or "").upper())
    except NumberParseException as exc:
        raise ValueError("invalid_phone") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError("invalid_phone")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

def country_options() -> list[dict[str, str]]:
    rows = []
    for region in sorted(phonenumbers.SUPPORTED_REGIONS):
        code = phonenumbers.country_code_for_region(region)
        if code:
            rows.append({"region": region, "calling_code": f"+{code}", "name": region})
    return rows
