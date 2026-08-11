from sentinel_dna.ai_investigation.investigation_engine import InvestigationEngine
from sentinel_dna.case_management.case_store import CaseStore
from sentinel_dna.evidence.evidence_engine import EvidenceEngine
from sentinel_dna.risk.risk_engine import RiskEngine


def test_complete_investigation_flow(tmp_path):
    case_store = CaseStore(tmp_path)
    evidence_engine = EvidenceEngine(tmp_path)
    risk_engine = RiskEngine()
    investigation_engine = InvestigationEngine()

    case = case_store.create_case("Suspicious email", "Reported credential verification email", "high")
    evidence = evidence_engine.normalize_email(
        {
            "sender": "security@example-login.com",
            "subject": "Urgent password verification",
            "body": "Verify at https://example-login.com now.",
        }
    )
    evidence_engine.save(evidence)
    case.attach_evidence(evidence.evidence_id)
    case_store.save(case)

    loaded_case = case_store.get(case.case_id)
    loaded_evidence = evidence_engine.get(evidence.evidence_id)
    risk = risk_engine.assess([loaded_evidence])
    summary = investigation_engine.summarize(loaded_case, [loaded_evidence], risk)

    assert loaded_case.evidence_ids == [evidence.evidence_id]
    assert risk.score > 0
    assert summary.case_id == case.case_id
    assert summary.recommended_actions

