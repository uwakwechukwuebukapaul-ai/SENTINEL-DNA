"""
Sentinel DNA Connector Framework Tests.

Validates:

- connector execution
- connector responses
- connector contracts
- security action handling
"""

from services.intelligence.connectors import (
    FirewallConnector,
    EndpointConnector,
    EmailConnector,
    IdentityConnector,
)



def test_firewall_connector():

    connector = FirewallConnector()


    result = connector.execute(
        "block_ip",
        {
            "target":
                "1.2.3.4"
        },
    )


    assert (
        result["status"]
        ==
        "executed"
    )


    assert (
        result["connector"]
        ==
        "firewall"
    )


    assert (
        result["action"]
        ==
        "block_ip"
    )



def test_endpoint_connector():

    connector = EndpointConnector()


    result = connector.execute(
        "isolate",
        {
            "endpoint":
                "HOST-001"
        },
    )


    assert (
        result["status"]
        ==
        "executed"
    )


    assert (
        result["connector"]
        ==
        "endpoint"
    )


    assert (
        result["endpoint"]
        ==
        "HOST-001"
    )



def test_email_connector():

    connector = EmailConnector()


    result = connector.execute(
        "quarantine",
        {
            "mailbox":
                "analyst@example.com"
        },
    )


    assert (
        result["status"]
        ==
        "executed"
    )


    assert (
        result["connector"]
        ==
        "email"
    )


    assert (
        result["mailbox"]
        ==
        "analyst@example.com"
    )



def test_identity_connector():

    connector = IdentityConnector()


    result = connector.execute(
        "disable_account",
        {
            "user":
                "admin"
        },
    )


    assert (
        result["status"]
        ==
        "executed"
    )


    assert (
        result["connector"]
        ==
        "identity"
    )


    assert (
        result["user"]
        ==
        "admin"
    )



def test_all_connectors_return_execution_status():

    connectors = [

        FirewallConnector(),

        EndpointConnector(),

        EmailConnector(),

        IdentityConnector(),

    ]


    for connector in connectors:

        result = connector.execute(
            "test_action",
            {},
        )


        assert (
            result["status"]
            ==
            "executed"
        )