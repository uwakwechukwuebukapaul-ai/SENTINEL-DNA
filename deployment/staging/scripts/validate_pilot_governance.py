"""Validate a non-authorizing controlled-pilot governance checklist.

This tool checks status vocabulary and decision consistency only. It never
authenticates people, verifies external authority, provisions access, or
returns READY based on repository evidence alone.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


STATUSES = {"READY", "BLOCKED", "PENDING_EXTERNAL_REVIEW", "NOT_MEASURED"}
NON_READY = STATUSES - {"READY"}


def validate(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "BLOCKED", "errors": ["checklist:unreadable_or_invalid_json"]}

    errors: list[str] = []
    if not isinstance(payload, dict):
        return {"status": "BLOCKED", "errors": ["checklist:object_required"]}
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        errors.append("items:non_empty_array_required")
        items = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"items[{index}]:object_required")
            continue
        if not str(item.get("control", "")).strip():
            errors.append(f"items[{index}].control:required")
        if item.get("status") not in STATUSES:
            errors.append(f"items[{index}].status:invalid")
    if payload.get("decision") not in {"READY", "BLOCKED"}:
        errors.append("decision:READY_or_BLOCKED_required")

    statuses = {item.get("status") for item in items if isinstance(item, dict)}
    if payload.get("decision") == "READY" and statuses & NON_READY:
        errors.append("decision:READY_requires_all_controls_READY")
    if payload.get("decision") == "READY" and payload.get("external_authority_status") != "EXTERNALLY_VERIFIED":
        errors.append("decision:external_authority_must_be_EXTERNALLY_VERIFIED")
    if payload.get("external_authority_status") != "EXTERNALLY_VERIFIED":
        errors.append("external_authority:external_verification_required")

    return {
        "status": "PASS" if not errors else "BLOCKED",
        "errors": sorted(set(errors)),
        "authorizes_pilot": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("checklist", type=Path)
    args = parser.parse_args()
    result = validate(args.checklist)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
