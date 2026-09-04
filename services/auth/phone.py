"""Standards-compatible international phone normalization."""
import phonenumbers
from phonenumbers import NumberParseException

# Calling codes and supported regions remain sourced from phonenumbers.  This
# small presentation map only supplies stable English labels where the library
# intentionally exposes ISO region identifiers rather than UI names.
_DISPLAY_NAMES = {
    "NG": "Nigeria", "GH": "Ghana", "US": "United States",
    "GB": "United Kingdom", "CA": "Canada", "DE": "Germany",
    "FR": "France", "IN": "India", "KE": "Kenya", "ZA": "South Africa",
}

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
            name = _DISPLAY_NAMES.get(region, region)
            rows.append({"region": region, "calling_code": f"+{code}", "name": name, "display_name": name})
    return rows
