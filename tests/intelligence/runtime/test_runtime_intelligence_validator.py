"""
Runtime Intelligence Validator Tests
"""

from services.intelligence.runtime.runtime_intelligence_validator import (
    RuntimeIntelligenceValidator,
)



def test_validate_valid_signals():

    validator = RuntimeIntelligenceValidator()


    signals = [

        {
            "type":
                "domain",

            "value":
                "evil.com",

        }

    ]


    assert (
        validator.validate_signals(
            signals
        )
        is True
    )



def test_validate_invalid_signals():

    validator = RuntimeIntelligenceValidator()


    signals = [

        {
            "value":
                "evil.com"

        }

    ]


    assert (
        validator.validate_signals(
            signals
        )
        is False
    )



def test_validate_empty_signals():

    validator = RuntimeIntelligenceValidator()


    assert (
        validator.validate_signals(
            []
        )
        is False
    )