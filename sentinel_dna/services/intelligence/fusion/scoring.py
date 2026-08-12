from typing import Any


def clamp_score(
    value: float,
) -> float:
    """
    Keep confidence values between 0 and 1.
    """

    return round(
        max(
            0.0,
            min(
                1.0,
                value,
            ),
        ),
        2,
    )



def calculate_fusion_score(
    signals: list[dict[str, Any]],
) -> float:
    """
    Calculate combined intelligence confidence.

    Uses weighted evidence confidence.
    """

    if not signals:
        return 0.0


    scores = []

    for signal in signals:

        confidence = signal.get(
            "confidence",
            0.0,
        )

        try:
            scores.append(
                float(confidence)
            )

        except (
            TypeError,
            ValueError,
        ):
            scores.append(
                0.0
            )


    if not scores:
        return 0.0


    return clamp_score(
        sum(scores)
        /
        len(scores)
    )



def determine_verdict(
    confidence: float,
    signals: list[dict[str, Any]],
) -> str:
    """
    Produce fusion verdict.
    """

    suspicious = any(
        signal.get(
            "severity"
        )
        in {
            "high",
            "critical",
        }
        for signal in signals
    )


    if suspicious and confidence >= 0.7:
        return "malicious"


    if confidence >= 0.5:
        return "suspicious"


    return "unknown"