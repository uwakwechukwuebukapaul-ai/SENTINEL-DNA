import pytest

from services.validation.canonical import (
    CanonicalValidationError,
    normalize_identifier,
    normalize_ioc,
    normalize_limit,
)


def test_identifiers_and_limits_are_bounded():
    assert normalize_identifier("EXE-1", field="execution_id") == "EXE-1"
    assert normalize_limit("25") == 25
    with pytest.raises(CanonicalValidationError):
        normalize_identifier("../../secret", field="execution_id")
    with pytest.raises(CanonicalValidationError):
        normalize_limit("not-a-number")
    with pytest.raises(CanonicalValidationError):
        normalize_limit(101)


def test_ioc_normalization_is_deterministic_and_provenance_bounded():
    domain = normalize_ioc("Example.COM")
    assert domain.kind == "domain"
    assert domain.value == "example.com"
    assert len(domain.source_digest) == 64
    assert normalize_ioc("2001:0db8::1", ioc_type="ip").value == "2001:db8::1"
    assert normalize_ioc("A" * 64, ioc_type="hash").value == "a" * 64
    assert normalize_ioc("HTTPS://Example.COM/path?x=1", ioc_type="url").value == "https://example.com/path?x=1"


@pytest.mark.parametrize(
    "value, ioc_type",
    [("127.0.0.1/24", "ip"), ("not a domain", "domain"), ("ftp://example.com", "url"), ("abc", "hash")],
)
def test_invalid_iocs_fail_closed(value, ioc_type):
    with pytest.raises(CanonicalValidationError):
        normalize_ioc(value, ioc_type=ioc_type)
