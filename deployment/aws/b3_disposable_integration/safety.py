"""Fail-closed configuration and identity gates for disposable B3 tests."""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from typing import Any, Mapping


TRUST_ACCOUNT_ID = "634176594969"
TRUST_REGION = "eu-west-1"
TRUST_RESOURCES = frozenset(
    {
        "SentinelDNA-Trust-CustodyProvider",
        "SentinelDNA-Trust-ReplayCustody",
        "sentinel-dna-trust-evidence-634176594969-eu-west-1",
        "SentinelDNA-Trust-CustodyProviderExecution",
    }
)
RUN_FLAG = "SENTINEL_DNA_RUN_AWS_CUSTODY_TESTS"
ACCOUNT_ACK = "SENTINEL_DNA_DISPOSABLE_ACCOUNT_ACK"
RESOURCE_ACK = "SENTINEL_DNA_DISPOSABLE_RESOURCE_ACK"
ACCOUNT_ENV = "SENTINEL_DNA_DISPOSABLE_AWS_ACCOUNT_ID"
REGION_ENV = "SENTINEL_DNA_DISPOSABLE_AWS_REGION"
PREFIX_ENV = "SENTINEL_DNA_DISPOSABLE_RESOURCE_PREFIX"
ACK_VALUE = "I_UNDERSTAND_THIS_IS_A_DISPOSABLE_ACCOUNT"
RESOURCE_ACK_VALUE = "I_UNDERSTAND_UNIQUE_DISPOSABLE_RESOURCES"


class SafetyError(RuntimeError):
    """A safety gate prevented execution."""


@dataclass(frozen=True)
class DisposableConfig:
    account_id: str
    region: str
    resource_prefix: str
    run_id: str

    @property
    def names(self) -> dict[str, str]:
        base = f"{self.resource_prefix}-{self.run_id}"
        return {
            "table": f"{base}-custody",
            "bucket": f"{base}-evidence",
            "kms_alias": f"alias/{base}-signing",
            "role": f"{base}-provider",
            "policy": f"{base}-provider-least-privilege",
        }


def _required(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise SafetyError(f"missing required disposable configuration: {key}")
    return value


def load_config(env: Mapping[str, str] | None = None) -> DisposableConfig:
    env = os.environ if env is None else env
    if env.get(RUN_FLAG) != "1":
        raise SafetyError(f"{RUN_FLAG}=1 is required")
    if env.get(ACCOUNT_ACK) != ACK_VALUE:
        raise SafetyError(f"{ACCOUNT_ACK} acknowledgement is required")
    if env.get(RESOURCE_ACK) != RESOURCE_ACK_VALUE:
        raise SafetyError(f"{RESOURCE_ACK} acknowledgement is required")

    account_id = _required(env, ACCOUNT_ENV)
    if not re.fullmatch(r"[0-9]{12}", account_id):
        raise SafetyError("disposable account ID must be a 12-digit AWS account ID")
    if account_id == TRUST_ACCOUNT_ID:
        raise SafetyError("the Sentinel DNA Trust account is never disposable")

    region = _required(env, REGION_ENV)
    prefix = _required(env, PREFIX_ENV).lower()
    if not re.fullmatch(r"sentinel-dna-b3-disposable-[a-z0-9-]{8,32}", prefix):
        raise SafetyError("resource prefix must be a unique sentinel-dna-b3-disposable-* value")
    if any(value.lower() in prefix for value in TRUST_RESOURCES):
        raise SafetyError("resource prefix overlaps a protected Trust resource")

    run_id = env.get("SENTINEL_DNA_DISPOSABLE_RUN_ID", "").strip().lower()
    if not run_id:
        run_id = uuid.uuid4().hex[:12]
    if not re.fullmatch(r"[a-z0-9]{8,32}", run_id):
        raise SafetyError("run ID must contain only lowercase letters and digits")
    return DisposableConfig(account_id, region, prefix, run_id)


def verify_caller_account(sts_client: Any, config: DisposableConfig) -> dict[str, str]:
    identity = sts_client.get_caller_identity()
    account = str(identity.get("Account", ""))
    if account != config.account_id:
        raise SafetyError(
            f"STS account mismatch: expected disposable {config.account_id}, got {account or 'missing'}"
        )
    if account == TRUST_ACCOUNT_ID:
        raise SafetyError("STS resolved to the protected Sentinel DNA Trust account")
    return {
        "account_id": account,
        "caller_arn": str(identity.get("Arn", "")),
        "user_id": str(identity.get("UserId", "")),
    }


def assert_safe_name(name: str, config: DisposableConfig) -> None:
    if name in TRUST_RESOURCES or name.lower() in {x.lower() for x in TRUST_RESOURCES}:
        raise SafetyError(f"protected Trust resource name refused: {name}")
    if not name.startswith(f"{config.resource_prefix}-{config.run_id}-"):
        raise SafetyError(f"resource is outside this run prefix: {name}")

