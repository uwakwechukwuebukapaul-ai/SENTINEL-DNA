"""Explicit, injected crypto-provider sandbox validation boundary."""
from dataclasses import dataclass
from .exceptions import BillingConfigurationError, PaymentProviderError

@dataclass(frozen=True)
class CryptoSandboxValidation:
    state: str
    reason: str
    provider: str | None = None
    assets: tuple[str, ...] = ()
    networks: tuple[str, ...] = ()

    def as_dict(self):
        return {"state": self.state, "reason": self.reason, "provider": self.provider, "assets": self.assets, "networks": self.networks}

class CryptoSandboxValidator:
    """Performs no work until ``validate`` is explicitly called."""
    def __init__(self, configuration, provider=None):
        self.configuration, self.provider = configuration, provider

    def validate(self):
        reasons = self.configuration.reason_codes()
        if reasons == ("CRYPTO_DISABLED",): return CryptoSandboxValidation("BLOCKED", "CRYPTO_PROVIDER_DISABLED")
        if reasons != ("CRYPTO_READY",): return CryptoSandboxValidation("BLOCKED", "CRYPTO_CONFIGURATION_INCOMPLETE", self.configuration.provider)
        if not self.provider: return CryptoSandboxValidation("BLOCKED", "CRYPTO_SECRET_UNAVAILABLE", self.configuration.provider)
        try:
            data = self.provider.validate_sandbox()
            if not isinstance(data, dict): raise ValueError
            provider = data.get("provider")
            assets = tuple(data.get("assets", ()))
            networks = tuple(data.get("networks", ()))
            if provider != self.configuration.provider: return CryptoSandboxValidation("FAILED", "CRYPTO_PROVIDER_VALIDATION_FAILED", self.configuration.provider)
            if not set(self.configuration.assets).issubset(set(assets)) or not set(self.configuration.networks).issubset(set(networks)):
                return CryptoSandboxValidation("FAILED", "CRYPTO_PROVIDER_VALIDATION_FAILED", self.configuration.provider, assets, networks)
            return CryptoSandboxValidation("PROVIDER_VALIDATED", "CRYPTO_PROVIDER_VALIDATED", self.configuration.provider, tuple(self.configuration.assets), tuple(self.configuration.networks))
        except TimeoutError: return CryptoSandboxValidation("FAILED", "CRYPTO_PROVIDER_TIMEOUT", self.configuration.provider)
        except PaymentProviderError as exc:
            reason = "CRYPTO_PROVIDER_RESPONSE_INVALID" if "invalid" in str(exc).lower() else "CRYPTO_PROVIDER_UNREACHABLE"
            return CryptoSandboxValidation("FAILED", reason, self.configuration.provider)
        except Exception: return CryptoSandboxValidation("FAILED", "CRYPTO_PROVIDER_RESPONSE_INVALID", self.configuration.provider)
