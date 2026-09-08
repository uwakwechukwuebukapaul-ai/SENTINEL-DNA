"""Standards-compatible international phone normalization."""
import phonenumbers
from phonenumbers import NumberParseException

# ISO-3166 display metadata is deliberately kept at the server boundary.  The
# browser receives presentation data, while normalization still uses the ISO
# region code as its canonical value.
_COUNTRY_NAMES = {
    "AF":"Afghanistan","AE":"United Arab Emirates","AR":"Argentina","AT":"Austria","AU":"Australia","BD":"Bangladesh","BE":"Belgium","BR":"Brazil","CA":"Canada","CH":"Switzerland","CL":"Chile","CN":"China","CO":"Colombia","CZ":"Czechia","DE":"Germany","DK":"Denmark","EG":"Egypt","ES":"Spain","FI":"Finland","FR":"France","GB":"United Kingdom","GH":"Ghana","GR":"Greece","HK":"Hong Kong","ID":"Indonesia","IE":"Ireland","IL":"Israel","IN":"India","IT":"Italy","JP":"Japan","KE":"Kenya","KR":"South Korea","LU":"Luxembourg","MX":"Mexico","MY":"Malaysia","NG":"Nigeria","NL":"Netherlands","NO":"Norway","NZ":"New Zealand","PK":"Pakistan","PL":"Poland","PT":"Portugal","QA":"Qatar","RO":"Romania","RU":"Russia","SA":"Saudi Arabia","SE":"Sweden","SG":"Singapore","TH":"Thailand","TR":"Türkiye","TZ":"Tanzania","UA":"Ukraine","UG":"Uganda","US":"United States","VN":"Vietnam","ZA":"South Africa","ZW":"Zimbabwe"}

def _flag(region: str) -> str:
    return "".join(chr(127397 + ord(letter)) for letter in region)

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
            rows.append({"region": region, "code": region, "calling_code": f"+{code}", "name": _COUNTRY_NAMES.get(region, region), "flag": _flag(region)})
    rows.sort(key=lambda item: item["name"])
    return rows
