"""Canonical bounded validation and normalization primitives.

These helpers intentionally stop at validation/normalization. Authorization,
derivation of risk, and business decisions remain in their canonical services.
"""

from __future__ import annotations

import hashlib
import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit


class CanonicalValidationError(ValueError):
    def __init__(self, field: str, code: str) -> None:
        self.field = field
        self.code = code
        super().__init__(f"{field}:{code}")


@dataclass(frozen=True)
class NormalizedIOC:
    kind: str
    value: str
    source_digest: str

    def public(self) -> dict[str, str]:
        return {"type": self.kind, "value": self.value, "source_digest": self.source_digest}


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_HASH_LENGTHS = {32: "md5", 40: "sha1", 64: "sha256", 96: "sha384", 128: "sha512"}
_HASH_VALUE = re.compile(r"^[0-9a-fA-F]+$")


def normalize_identifier(value: object, *, field: str = "identifier") -> str:
    text = str(value or "").strip()
    if not text or not _IDENTIFIER.fullmatch(text):
        raise CanonicalValidationError(field, "invalid_identifier")
    return text


def normalize_limit(value: object, *, default: int = 50, maximum: int = 100) -> int:
    try:
        parsed = default if value in (None, "") else int(value)
    except (TypeError, ValueError) as exc:
        raise CanonicalValidationError("limit", "invalid_integer") from exc
    if parsed < 1 or parsed > maximum:
        raise CanonicalValidationError("limit", "out_of_range")
    return parsed


def _normalize_domain(value: str) -> str:
    candidate = value.rstrip(".").strip().lower()
    if len(candidate) > 253 or not candidate or ".." in candidate:
        raise CanonicalValidationError("ioc", "invalid_domain")
    try:
        ascii_domain = candidate.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise CanonicalValidationError("ioc", "invalid_domain") from exc
    labels = ascii_domain.split(".")
    valid_label = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")
    if len(labels) < 2 or any(
        not label or len(label) > 63 or not valid_label.fullmatch(label)
        for label in labels
    ):
        raise CanonicalValidationError("ioc", "invalid_domain")
    return ascii_domain


def normalize_ioc(value: object, *, ioc_type: str | None = None) -> NormalizedIOC:
    raw = str(value or "").strip()
    if not raw or len(raw) > 2048 or any(ord(char) < 32 for char in raw):
        raise CanonicalValidationError("ioc", "invalid_value")
    kind = (ioc_type or "").strip().lower()
    normalized = raw
    if kind in {"ip", "ipv4", "ipv6"} or not kind:
        try:
            address = ipaddress.ip_address(raw)
            kind, normalized = "ip", address.compressed
        except ValueError:
            if kind in {"ip", "ipv4", "ipv6"}:
                raise CanonicalValidationError("ioc", "invalid_ip")
    if not kind:
        if len(raw) in _HASH_LENGTHS and _HASH_VALUE.fullmatch(raw):
            kind, normalized = "hash", raw.lower()
        elif "://" in raw:
            kind = "url"
        else:
            kind, normalized = "domain", _normalize_domain(raw)
    if kind == "domain":
        normalized = _normalize_domain(raw)
    elif kind == "hash":
        if len(raw) not in _HASH_LENGTHS or not _HASH_VALUE.fullmatch(raw):
            raise CanonicalValidationError("ioc", "invalid_hash")
        normalized = raw.lower()
    elif kind == "url":
        parsed = urlsplit(raw)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise CanonicalValidationError("ioc", "invalid_url")
        hostname = parsed.hostname
        try:
            hostname = (
                _normalize_domain(hostname)
                if not ipaddress.ip_address(hostname)
                else ipaddress.ip_address(hostname).compressed
            )
        except ValueError:
            hostname = _normalize_domain(hostname)
        netloc = hostname
        if parsed.port:
            netloc = f"{hostname}:{parsed.port}"
        normalized = urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "/", parsed.query, ""))
    elif kind != "ip":
        raise CanonicalValidationError("ioc", "unsupported_type")
    return NormalizedIOC(
        kind=kind,
        value=normalized,
        source_digest=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    )


__all__ = [
    "CanonicalValidationError",
    "NormalizedIOC",
    "normalize_identifier",
    "normalize_ioc",
    "normalize_limit",
]
