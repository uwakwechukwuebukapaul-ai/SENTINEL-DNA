"""Disposable provider Lambda boundary."""

from __future__ import annotations

from typing import Any, Mapping

from .external_replay_custody import DynamoDBReplayCustodyProvider, ExternalReplayProviderError

ALLOWED_OPERATIONS = frozenset({"RESERVE", "RECONCILE", "INSPECT", "VERIFY", "CONSUME", "ABORT"})


def handle(event: Mapping[str, Any], *, provider: DynamoDBReplayCustodyProvider) -> dict[str, Any]:
    operation = event.get("operation")
    if operation not in ALLOWED_OPERATIONS:
        raise ExternalReplayProviderError("provider_operation_not_allowed")
    reference, binding = event.get("reference"), event.get("binding")
    if operation == "INSPECT":
        if not isinstance(reference, str) or not reference:
            raise ExternalReplayProviderError("provider_reference_invalid")
        return provider.inspect(reference=reference)
    if operation == "RECONCILE" and (not isinstance(reference, str) or not reference):
        raise ExternalReplayProviderError("provider_reference_invalid")
    if not isinstance(binding, Mapping):
        raise ExternalReplayProviderError("provider_binding_required")
    if operation == "RESERVE":
        return {"custody_id": provider.reserve(binding=binding)}
    if operation == "RECONCILE":
        return provider.reconcile(reference=reference, binding=binding)
    if operation == "VERIFY":
        return {"valid": provider.verify(reference=reference, binding=binding)}
    if operation == "CONSUME":
        provider.consume(reference=reference, binding=binding, request_id=event.get("consume_request_id", ""))
        return {"accepted": True, "consume_request_id": event["consume_request_id"]}
    provider.abort(reference=reference, binding=binding)
    return {"accepted": True}


def lambda_handler(event, context):
    del context
    try:
        provider = DynamoDBReplayCustodyProvider.from_environment()
        provider.preflight_evidence_bucket()
        return handle(event, provider=provider)
    except Exception as exc:  # fail closed; no request payload is returned
        payload = {"error": type(exc).__name__}
        diagnostic = getattr(exc, "diagnostic", None)
        if isinstance(diagnostic, Mapping):
            payload["diagnostic"] = dict(diagnostic)
        return payload
