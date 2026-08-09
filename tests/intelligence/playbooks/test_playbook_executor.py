"""
SOAR Playbook Engine Tests.
"""

from services.intelligence.playbooks import (
    Playbook,
    PlaybookStep,
    PlaybookExecutor,
)



class FakeConnector:


    def execute(
        self,
        action,
        parameters,
    ):

        return {

            "status":
                "executed",

            "action":
                action,

        }



def test_playbook_execution():


    playbook = Playbook(

        name="phishing_response",

        description="Phishing response workflow",

        steps=[

            PlaybookStep(

                name="quarantine_email",

                connector="email",

                action="quarantine",

            )

        ]

    )


    executor = PlaybookExecutor(

        connectors={

            "email":
                FakeConnector()

        }

    )


    result = executor.execute(

        playbook,

        {}

    )


    assert (
        result["status"]
        ==
        "completed"
    )


    assert (
        result["results"][0]["status"]
        ==
        "executed"
    )



def test_approval_gate():


    playbook = Playbook(

        name="account_response",

        description="Identity workflow",

        steps=[

            PlaybookStep(

                name="disable_user",

                connector="identity",

                action="disable",

                requires_approval=True,

            )

        ]

    )


    executor = PlaybookExecutor()


    result = executor.execute(

        playbook,

        {}

    )


    assert (

        result["results"][0]["status"]

        ==

        "approval_required"

    )



def test_audit_history():


    playbook = Playbook(

        name="audit_test",

        description="test",

        steps=[],

    )


    executor = PlaybookExecutor()


    executor.execute(

        playbook,

        {}

    )


    assert len(

        executor.audit.history()

    ) == 0