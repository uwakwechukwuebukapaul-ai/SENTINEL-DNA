"""
Investigation API request/response schemas.

Maintains compatibility with:
- /api/investigations
- /investigate legacy endpoint
"""

from __future__ import annotations

from typing import Any


# ============================================================
# REQUEST NORMALIZATION
# ============================================================


def investigation_request(
    payload: dict[str, Any] | None,
):
    """
    Normalize incoming investigation payload.

    Supported:

    {
        "case_id": "CASE-001",
        "alert": {},
        "artifacts": []
    }

    Legacy clients may omit case_id.
    """

    payload = payload or {}


    case_id = payload.get(
        "case_id"
    )


    # Generate compatibility ID
    if not case_id:
        case_id = "AUTO-INVESTIGATION"


    alert = payload.get(
        "alert",
        {}
    )


    artifacts = payload.get(
        "artifacts",
        []
    )


    if not isinstance(
        artifacts,
        list,
    ):
        return (
            case_id,
            alert,
            [],
            "artifacts_must_be_list",
        )


    return (
        case_id,
        alert,
        artifacts,
        None,
    )



# ============================================================
# RESPONSE NORMALIZATION
# ============================================================


def investigation_response(
    result: Any,
) -> dict[str, Any]:
    """
    Convert investigation result into JSON response.
    """

    if result is None:
        return {
            "status": "completed",
            "result": None,
        }


    if isinstance(
        result,
        dict,
    ):
        return result


    if hasattr(
        result,
        "to_dict",
    ):
        return result.to_dict()


    return {
        "status": "completed",
        "result": str(result),
    }