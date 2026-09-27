"""Disposable AWS replay-custody provider with no production defaults."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import re
from typing import Any, Mapping

from .custody_binding import BINDING_FIELDS, CustodyBindingError, binding_hash, canonical_json, normalize_custody_binding

RESERVED, CONSUMED, ABORTED = "RESERVED", "CONSUMED", "ABORTED"
KNOWN_STATES = frozenset({RESERVED, CONSUMED, ABORTED})
CONTRACT = "sentinel-dna-b3-disposable-provider-v1"
_PROTECTED_ACCOUNT = "634" + "176594969"
_PROTECTED_RESOURCE_PREFIXES = ("SentinelDNA" + "-Trust", "sentinel-dna" + "-trust")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{22,128}$")


class ExternalReplayProviderError(RuntimeError):
    def __init__(self, message: str, *, diagnostic: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.diagnostic = dict(diagnostic) if isinstance(diagnostic, Mapping) else None


class ExternalReplayBindingMismatch(ExternalReplayProviderError):
    pass


class ExternalReplayAlreadyConsumed(ExternalReplayProviderError):
    pass


def _config() -> dict[str, str]:
    required = {
        "account": "SENTINEL_DNA_DISPOSABLE_AWS_ACCOUNT_ID",
        "region": "SENTINEL_DNA_DISPOSABLE_AWS_REGION",
        "environment": "SENTINEL_DNA_DISPOSABLE_PROVIDER_ENVIRONMENT",
        "table": "SENTINEL_DNA_DISPOSABLE_TABLE_NAME",
        "bucket": "SENTINEL_DNA_DISPOSABLE_EVIDENCE_BUCKET",
        "kms": "SENTINEL_DNA_DISPOSABLE_KMS_KEY_ARN",
    }
    values = {name: os.getenv(env, "").strip() for name, env in required.items()}
    if os.getenv("SENTINEL_DNA_DISPOSABLE_PROVIDER", "") != CONTRACT or any(not value for value in values.values()):
        raise ExternalReplayProviderError("disposable_provider_configuration_required")
    if values["account"] == _PROTECTED_ACCOUNT or any(any(marker in value for marker in _PROTECTED_RESOURCE_PREFIXES) for value in values.values()):
        raise ExternalReplayProviderError("protected_trust_scope_refused")
    return values


def _dynamo(value: Any) -> dict[str, Any]:
    if value is None:
        return {"NULL": True}
    if isinstance(value, bool):
        return {"BOOL": value}
    if isinstance(value, int):
        return {"N": str(value)}
    return {"S": str(value)}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DynamoDBReplayCustodyProvider:
    provider_mode = "DISPOSABLE_AWS_PROVIDER_BOUNDARY"

    def __init__(self, *, table_name: str, region: str, evidence_bucket: str, kms_key_arn: str,
                 dynamodb: Any, s3: Any, kms: Any, clock=_now, evidence_required: bool = True,
                 integrity_required: bool = True):
        self.table_name, self.region, self.evidence_bucket, self.kms_key_arn = table_name, region, evidence_bucket, kms_key_arn
        self.dynamodb, self.s3, self.kms = dynamodb, s3, kms
        self.clock, self.evidence_required, self.integrity_required = clock, evidence_required, integrity_required

    @classmethod
    def from_environment(cls):
        config = _config()
        import boto3
        session = boto3.Session(region_name=config["region"])
        return cls(table_name=config["table"], region=config["region"], evidence_bucket=config["bucket"], kms_key_arn=config["kms"],
                   dynamodb=session.client("dynamodb"), s3=session.client("s3"), kms=session.client("kms"))

    def preflight_evidence_bucket(self) -> dict[str, Any]:
        """Verify the disposable evidence controls before any provider operation."""
        location = self.s3.get_bucket_location(Bucket=self.evidence_bucket).get("LocationConstraint") or "us-east-1"
        versioning = self.s3.get_bucket_versioning(Bucket=self.evidence_bucket).get("Status")
        lock = self.s3.get_object_lock_configuration(Bucket=self.evidence_bucket).get("ObjectLockConfiguration", {})
        public = self.s3.get_public_access_block(Bucket=self.evidence_bucket).get("PublicAccessBlockConfiguration", {})
        default_retention = lock.get("Rule", {}).get("DefaultRetention", {})
        if location != self.region or versioning != "Enabled" or lock.get("ObjectLockEnabled") != "Enabled":
            raise ExternalReplayProviderError("disposable_evidence_controls_invalid")
        if default_retention.get("Mode") != "GOVERNANCE" or default_retention.get("Days") != 30 or "Years" in default_retention:
            raise ExternalReplayProviderError("disposable_evidence_retention_invalid")
        if not all(public.get(key) is True for key in ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")):
            raise ExternalReplayProviderError("disposable_evidence_public_access_invalid")
        return {"bucket": self.evidence_bucket, "region": location, "versioning": versioning, "object_lock": lock}

    def _record(self, binding: Mapping[str, str], custody_id: str, state: str = RESERVED, consumed_at: str | None = None, request_id: str | None = None) -> dict[str, Any]:
        record = {field: binding[field] for field in BINDING_FIELDS}
        record.update({"custody_id": custody_id, "state": state, "consumed_at": consumed_at, "consume_request_id": request_id, "provider_record_version": 1, "superseded": False})
        record["binding_hash"] = hashlib.sha256(canonical_json(binding)).hexdigest()
        record["record_integrity_hash"] = hashlib.sha256(canonical_json({key: record[key] for key in (*BINDING_FIELDS, "custody_id", "state", "consumed_at", "consume_request_id", "provider_record_version", "superseded")})).hexdigest()
        return {key: _dynamo(value) for key, value in record.items()}

    def _evidence(self, operation: str, result: str, custody_id: str, binding_digest: str, state_before=None, state_after=None, error=None):
        key = f"replay-custody/{self.clock().strftime('%Y/%m/%d')}/{custody_id}-{operation.lower()}.json"
        payload = {"schema": CONTRACT, "custody_id": custody_id, "operation": operation, "result": result, "state_before": state_before, "state_after": state_after, "binding_hash": binding_digest, "timestamp": self.clock().astimezone(timezone.utc).isoformat().replace("+00:00", "Z"), "evidence_object_key": key}
        if error:
            payload["error"] = str(error)[:128]
        envelope = {**payload, "kms_key_arn": self.kms_key_arn, "signing_algorithm": "ECDSA_SHA_256"}
        unsigned = canonical_json(envelope)
        if self.integrity_required:
            signed = self.kms.sign(KeyId=self.kms_key_arn, Message=unsigned, MessageType="RAW", SigningAlgorithm="ECDSA_SHA_256")
            signature = signed.get("Signature")
            if not isinstance(signature, (bytes, bytearray)):
                raise ExternalReplayProviderError("kms_signature_missing")
            verified = self.kms.verify(KeyId=self.kms_key_arn, Message=unsigned, MessageType="RAW", Signature=signature, SigningAlgorithm="ECDSA_SHA_256")
            if verified.get("SignatureValid") is not True:
                raise ExternalReplayProviderError("kms_integrity_verification_failed")
            envelope["signature_b64"] = base64.b64encode(signature).decode("ascii")
        if self.evidence_required:
            self.s3.put_object(Bucket=self.evidence_bucket, Key=key, Body=canonical_json(envelope), ContentType="application/json", ObjectLockMode="GOVERNANCE", ObjectLockRetainUntilDate=self.clock() + timedelta(days=30))
        return envelope

    def reserve(self, *, binding: Mapping[str, Any]) -> str:
        normalized = normalize_custody_binding(binding, now=self.clock())
        digest = hashlib.sha256(canonical_json(normalized)).hexdigest()
        custody_id = "rc-" + digest
        items = [
            {"Put": {"TableName": self.table_name, "Item": self._record(normalized, custody_id), "ConditionExpression": "attribute_not_exists(custody_id)"}},
            {"Put": {"TableName": self.table_name, "Item": {"custody_id": _dynamo(f"UNIQUE#INITIALIZATION#{normalized['initialization_id']}#{normalized['purpose']}#{normalized['role']}"), "record_type": _dynamo("UNIQUE"), "target": _dynamo(custody_id)}, "ConditionExpression": "attribute_not_exists(custody_id)"}},
            {"Put": {"TableName": self.table_name, "Item": {"custody_id": _dynamo(f"UNIQUE#ACTIVATION#{normalized['activation_id']}"), "record_type": _dynamo("UNIQUE"), "target": _dynamo(custody_id)}, "ConditionExpression": "attribute_not_exists(custody_id)"}},
        ]
        try:
            self.dynamodb.transact_write_items(TransactItems=items, ClientRequestToken=hashlib.sha256(custody_id.encode()).hexdigest()[:36])
            self._evidence("RESERVE", "accepted", custody_id, digest, state_after=RESERVED)
            return custody_id
        except Exception as exc:
            self._evidence("RESERVE", "rejected", custody_id, digest, error=type(exc).__name__)
            raise ExternalReplayProviderError("custody_reservation_rejected") from exc

    def _get(self, reference: str) -> dict[str, Any] | None:
        item = self.dynamodb.get_item(TableName=self.table_name, Key={"custody_id": {"S": reference}}, ConsistentRead=True).get("Item")
        if not item:
            return None
        decoded = {key: next(iter(value.values())) for key, value in item.items() if isinstance(value, Mapping) and value}
        return decoded

    def inspect(self, *, reference: str) -> dict[str, Any]:
        record = self._get(reference)
        if record is None:
            return {"custody_id": reference, "state": "UNKNOWN"}
        return record

    def reconcile(self, *, reference: str, binding: Mapping[str, Any]) -> dict[str, str]:
        record = self._get(reference)
        if record is None:
            return {"custody_id": reference, "state": "ABSENT"}
        expected = binding_hash(binding, now=self.clock(), allow_expired=True)
        if record.get("binding_hash") != expected:
            raise ExternalReplayBindingMismatch("custody_binding_mismatch")
        return {"custody_id": reference, "state": str(record.get("state", "UNKNOWN"))}

    def verify(self, *, reference: str, binding: Mapping[str, Any]) -> bool:
        record = self._get(reference)
        if not record or record.get("state") != RESERVED:
            return False
        normalized = normalize_custody_binding(binding, now=self.clock())
        return record.get("binding_hash") == hashlib.sha256(canonical_json(normalized)).hexdigest()

    def consume(self, *, reference: str, binding: Mapping[str, Any], request_id: str) -> None:
        if not _REQUEST_ID.fullmatch(request_id):
            raise ExternalReplayProviderError("consume_request_id_invalid")
        normalized = normalize_custody_binding(binding, now=self.clock(), allow_expired=True)
        digest = hashlib.sha256(canonical_json(normalized)).hexdigest()
        now = self.clock().astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        try:
            self.dynamodb.update_item(TableName=self.table_name, Key={"custody_id": {"S": reference}}, UpdateExpression="SET #state = :consumed, consumed_at = :now, consume_request_id = :request_id", ConditionExpression="#state = :reserved AND binding_hash = :binding AND expires_at > :current_time", ExpressionAttributeNames={"#state": "state"}, ExpressionAttributeValues={":consumed": _dynamo(CONSUMED), ":reserved": _dynamo(RESERVED), ":binding": _dynamo(digest), ":current_time": _dynamo(now), ":now": _dynamo(now), ":request_id": _dynamo(request_id)})
            self._evidence("CONSUME", "accepted", reference, digest, state_before=RESERVED, state_after=CONSUMED)
        except Exception as exc:
            record = self._get(reference)
            if record and record.get("state") == CONSUMED and record.get("consume_request_id") == request_id:
                return
            if record and record.get("state") == CONSUMED:
                raise ExternalReplayAlreadyConsumed("custody_already_consumed") from exc
            raise ExternalReplayProviderError("custody_consume_rejected") from exc

    def abort(self, *, reference: str, binding: Mapping[str, Any]) -> None:
        digest = binding_hash(binding, now=self.clock(), allow_expired=True)
        self.dynamodb.update_item(TableName=self.table_name, Key={"custody_id": {"S": reference}}, UpdateExpression="SET #state = :aborted", ConditionExpression="#state = :reserved AND binding_hash = :binding", ExpressionAttributeNames={"#state": "state"}, ExpressionAttributeValues={":aborted": _dynamo(ABORTED), ":reserved": _dynamo(RESERVED), ":binding": _dynamo(digest)})
        self._evidence("ABORT", "accepted", reference, digest, state_before=RESERVED, state_after=ABORTED)
