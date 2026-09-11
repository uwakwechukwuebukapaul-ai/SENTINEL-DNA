"""SAML federation foundation, intentionally inert until an approved SP is configured."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


class SamlConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class SamlProviderConfiguration:
    entity_id: str
    sso_url: str
    certificate_reference: str
    acs_url: str
    name_id_format: str = "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"

    def validate(self) -> None:
        if not all((self.entity_id.strip(), self.certificate_reference.strip())):
            raise SamlConfigurationError("saml_configuration_incomplete")
        for value in (self.sso_url, self.acs_url):
            parsed = urlparse(value)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                raise SamlConfigurationError("saml_endpoint_untrusted")


class SamlAssertionValidator:
    """Injection point for a vetted SAML library; never accepts browser claims directly."""

    def __init__(self, configuration: SamlProviderConfiguration, validator):
        configuration.validate()
        if validator is None or not callable(validator):
            raise SamlConfigurationError("saml_validator_required")
        self.configuration, self.validator = configuration, validator

    def validate(self, response: bytes, request_id: str):
        if not isinstance(response, bytes) or not response or not request_id.strip():
            raise SamlConfigurationError("saml_response_invalid")
        return self.validator(response, self.configuration, request_id)
