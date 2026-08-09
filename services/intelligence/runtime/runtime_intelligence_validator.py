"""
Runtime Intelligence Validator

Validates intelligence execution inputs
and outputs.

Responsibilities:

- signal validation
- runtime safety checks
- result validation
- schema enforcement
"""

from typing import Any



class RuntimeIntelligenceValidator:
    """
    Validates Sentinel DNA intelligence runtime data.
    """



    def validate_signals(
        self,
        signals: list[dict[str, Any]],
    ) -> bool:

        """
        Validate incoming investigation signals.
        """

        if not isinstance(
            signals,
            list,
        ):

            return False



        if not signals:

            return False



        for signal in signals:

            if not isinstance(
                signal,
                dict,
            ):

                return False



            if "value" not in signal:

                return False



            if "type" not in signal:

                return False



        return True



    def validate_provider_records(
        self,
        records: list[Any],
    ) -> bool:

        """
        Validate intelligence provider output.
        """

        if records is None:

            return True



        if not isinstance(
            records,
            list,
        ):

            return False



        return True



    def validate_correlation(
        self,
        correlation: Any,
    ) -> bool:

        """
        Validate correlation output.
        """

        if correlation is None:

            return True



        return hasattr(
            correlation,
            "risk",
        )



    def validate_fusion(
        self,
        fusion_result: Any,
    ) -> bool:

        """
        Validate fusion result.
        """

        if fusion_result is None:

            return True



        required = [

            "risk",

            "confidence",

        ]



        for field in required:

            if not hasattr(
                fusion_result,
                field,
            ):

                return False



        return True



    def validate_result(
        self,
        result: Any,
    ) -> bool:

        """
        Validate final runtime result.
        """

        if result is None:

            return False



        return hasattr(
            result,
            "success",
        )