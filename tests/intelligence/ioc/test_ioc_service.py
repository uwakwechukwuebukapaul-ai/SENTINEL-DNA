"""
IOC Intelligence Service Tests
"""


from services.intelligence.ioc import (
    IOCService,
)



def create_service():

    return IOCService()



def test_detect_domain_indicator():

    service = create_service()


    result = service.enrich(
        "example.com"
    )


    assert (
        result.indicator
        ==
        "example.com"
    )


    assert (
        result.indicator_type
        ==
        "domain"
    )



def test_detect_ip_indicator():

    service = create_service()


    result = service.enrich(
        "8.8.8.8"
    )


    assert (
        result.indicator_type
        ==
        "ip"
    )



def test_detect_url_indicator():

    service = create_service()


    result = service.enrich(
        "https://evil-login.xyz"
    )


    assert (
        result.indicator_type
        ==
        "url"
    )



def test_detect_sha256_indicator():

    service = create_service()


    result = service.enrich(
        "a" * 64
    )


    assert (
        result.indicator_type
        ==
        "sha256"
    )



def test_high_risk_reputation():

    service = create_service()


    result = service.enrich(
        "credential-login.xyz"
    )


    assert (
        result.risk
        ==
        "high"
    )


    assert (
        result.confidence
        >=
        0.8
    )



def test_low_risk_reputation():

    service = create_service()


    result = service.enrich(
        "company.local"
    )


    assert (
        result.risk
        ==
        "low"
    )



def test_result_export():

    service = create_service()


    result = service.enrich(
        "sample.com"
    )


    exported = result.to_dict()


    assert (
        exported["indicator"]
        ==
        "sample.com"
    )


    assert (
        "metadata"
        in exported
    )