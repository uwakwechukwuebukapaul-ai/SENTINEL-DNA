"""Explicit configuration contract for a separately built disposable provider."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from .safety import TRUST_ACCOUNT_ID, TRUST_RESOURCES, SafetyError


DISPOSABLE_PROVIDER_CONTRACT = "sentinel-dna-b3-disposable-provider-v1"
_ACCOUNT = re.compile(r"[0-9]{12}\Z")
_REGION = re.compile(r"[a-z]{2}-[a-z]+-[0-9]\Z")
_ENVIRONMENT = re.compile(r"sentinel-dna-b3-disposable-[a-z0-9-]{8,48}\Z")


@dataclass(frozen=True)
class DisposableProviderConfig:
    account_id: str
    region: str
    environment: str
    table_name: str
    evidence_bucket: str
    kms_key_arn: str
    function_name: str
    role_name: str

    def __post_init__(self) -> None:
        if not _ACCOUNT.fullmatch(self.account_id) or self.account_id == TRUST_ACCOUNT_ID:
            raise SafetyError("disposable provider account is invalid or is the protected Trust account")
        if not _REGION.fullmatch(self.region):
            raise SafetyError("disposable provider region is invalid")
        if not _ENVIRONMENT.fullmatch(self.environment):
            raise SafetyError("disposable provider environment is invalid")
        values = (self.table_name, self.evidence_bucket, self.function_name, self.role_name, self.kms_key_arn)
        if any(not value or "SentinelDNA-Trust" in value or "sentinel-dna-trust" in value for value in values):
            raise SafetyError("Trust resource identifier entered disposable provider configuration")
        if not self.table_name.startswith("sentinel-dna-b3-disposable-"):
            raise SafetyError("disposable table name is outside the disposable namespace")
        if not self.evidence_bucket.startswith("sentinel-dna-b3-disposable-"):
            raise SafetyError("disposable evidence bucket is outside the disposable namespace")
        if not self.function_name.startswith("sentinel-dna-b3-disposable-"):
            raise SafetyError("disposable function name is outside the disposable namespace")
        if not self.role_name.startswith("sentinel-dna-b3-disposable-"):
            raise SafetyError("disposable role name is outside the disposable namespace")
        expected_kms_prefix = f"arn:aws:kms:{self.region}:{self.account_id}:key/"
        if not self.kms_key_arn.startswith(expected_kms_prefix):
            raise SafetyError("disposable KMS key is outside the configured account/region")
        if any(resource.lower() in " ".join(values).lower() for resource in TRUST_RESOURCES):
            raise SafetyError("protected Trust resource appears in disposable configuration")

    def environment_variables(self) -> dict[str, str]:
        return {
            "AWS_REGION": self.region,
            "SENTINEL_DNA_ENV": self.environment,
            "SENTINEL_DNA_EXTERNAL_REPLAY_PROVIDER": "AWS_DYNAMODB_S3_PROVIDER_BOUNDARY",
            "SENTINEL_DNA_CUSTODY_PROVIDER_AUTH_MODE": "AWS_IAM_ROLE",
            "SENTINEL_DNA_REPLAY_CUSTODY_TABLE": self.table_name,
            "SENTINEL_DNA_REPLAY_EVIDENCE_BUCKET": self.evidence_bucket,
            "SENTINEL_DNA_REPLAY_KMS_KEY_ID": self.kms_key_arn,
        }

    def contract(self) -> dict[str, object]:
        return {
            "contract": DISPOSABLE_PROVIDER_CONTRACT,
            "account_id": self.account_id,
            "region": self.region,
            "environment": self.environment,
            "table_name": self.table_name,
            "evidence_bucket": self.evidence_bucket,
            "kms_key_arn": self.kms_key_arn,
            "function_name": self.function_name,
            "role_name": self.role_name,
            "trust_account_forbidden": True,
        }


def config_from_mapping(values: Mapping[str, str]) -> DisposableProviderConfig:
    required = {
        "account_id": "SENTINEL_DNA_DISPOSABLE_AWS_ACCOUNT_ID",
        "region": "SENTINEL_DNA_DISPOSABLE_AWS_REGION",
        "environment": "SENTINEL_DNA_DISPOSABLE_PROVIDER_ENVIRONMENT",
        "table_name": "SENTINEL_DNA_DISPOSABLE_TABLE_NAME",
        "evidence_bucket": "SENTINEL_DNA_DISPOSABLE_EVIDENCE_BUCKET",
        "kms_key_arn": "SENTINEL_DNA_DISPOSABLE_KMS_KEY_ARN",
        "function_name": "SENTINEL_DNA_DISPOSABLE_FUNCTION_NAME",
        "role_name": "SENTINEL_DNA_DISPOSABLE_ROLE_NAME",
    }
    missing = [env_name for field, env_name in required.items() if not values.get(env_name, "").strip()]
    if missing:
        raise SafetyError("missing disposable provider configuration: " + ", ".join(missing))
    return DisposableProviderConfig(**{field: values[env_name].strip() for field, env_name in required.items()})

