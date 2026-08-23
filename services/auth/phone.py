"""Standards-oriented country calling-code and E.164 normalization helpers."""
from __future__ import annotations
import re

COUNTRIES = (
    ("NG", "Nigeria", "+234"), ("GH", "Ghana", "+233"), ("KE", "Kenya", "+254"), ("ZA", "South Africa", "+27"),
    ("UG", "Uganda", "+256"), ("TZ", "Tanzania", "+255"), ("RW", "Rwanda", "+250"), ("ET", "Ethiopia", "+251"),
    ("EG", "Egypt", "+20"), ("MA", "Morocco", "+212"), ("DZ", "Algeria", "+213"), ("TN", "Tunisia", "+216"),
    ("GB", "United Kingdom", "+44"), ("IE", "Ireland", "+353"), ("FR", "France", "+33"), ("DE", "Germany", "+49"),
    ("ES", "Spain", "+34"), ("IT", "Italy", "+39"), ("NL", "Netherlands", "+31"), ("BE", "Belgium", "+32"),
    ("CH", "Switzerland", "+41"), ("SE", "Sweden", "+46"), ("NO", "Norway", "+47"), ("DK", "Denmark", "+45"),
    ("FI", "Finland", "+358"), ("PL", "Poland", "+48"), ("PT", "Portugal", "+351"), ("UA", "Ukraine", "+380"),
    ("TR", "Türkiye", "+90"), ("IL", "Israel", "+972"), ("AE", "United Arab Emirates", "+971"), ("SA", "Saudi Arabia", "+966"),
    ("IN", "India", "+91"), ("PK", "Pakistan", "+92"), ("BD", "Bangladesh", "+880"), ("LK", "Sri Lanka", "+94"),
    ("NP", "Nepal", "+977"), ("CN", "China", "+86"), ("JP", "Japan", "+81"), ("KR", "South Korea", "+82"),
    ("SG", "Singapore", "+65"), ("MY", "Malaysia", "+60"), ("ID", "Indonesia", "+62"), ("PH", "Philippines", "+63"),
    ("TH", "Thailand", "+66"), ("VN", "Vietnam", "+84"), ("AU", "Australia", "+61"), ("NZ", "New Zealand", "+64"),
    ("US", "United States", "+1"), ("CA", "Canada", "+1"), ("MX", "Mexico", "+52"), ("BR", "Brazil", "+55"),
    ("AR", "Argentina", "+54"), ("CL", "Chile", "+56"), ("CO", "Colombia", "+57"), ("PE", "Peru", "+51"),
    ("VE", "Venezuela", "+58"), ("RU", "Russia", "+7"), ("KZ", "Kazakhstan", "+7"),
)
COUNTRY_CODES = {code: prefix for code, _name, prefix in COUNTRIES}

def normalize_phone(country: str, phone: str) -> str:
    prefix = COUNTRY_CODES.get(str(country or "").upper())
    digits = re.sub(r"\D", "", str(phone or ""))
    if not prefix or not 6 <= len(digits) <= 14: raise ValueError("invalid_phone")
    if digits.startswith("00"): digits = digits[2:]
    prefix_digits = prefix[1:]
    if not digits.startswith(prefix_digits):
        if digits.startswith("0"): digits = digits[1:]
        digits = prefix_digits + digits
    normalized = "+" + digits
    if not re.fullmatch(r"\+[1-9]\d{7,14}", normalized): raise ValueError("invalid_phone")
    return normalized
