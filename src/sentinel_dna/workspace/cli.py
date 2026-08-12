import argparse
import os

from sentinel_dna.case_management.case_store import CaseStore
from sentinel_dna.evidence.evidence_engine import EvidenceEngine
from sentinel_dna.integrations.gmail_analyzer import GmailAnalyzer
from sentinel_dna.investigation.reporting import InvestigationReporter
from sentinel_dna.risk.risk_engine import RiskEngine


def run_demo(data_dir: str) -> None:
    case_store = CaseStore(data_dir)
    gmail_analyzer = GmailAnalyzer(EvidenceEngine(data_dir))
    risk_engine = RiskEngine()
    reporter = InvestigationReporter()

    case = case_store.create_case(
        title="Suspicious credential verification email",
        description=(
            "User reported a possible phishing email requesting "
            "MFA verification."
        ),
        severity="high",
    )

    evidence = gmail_analyzer.analyze_message(
        {
            "sender": "security-alert@example-login.com",
            "subject": "Urgent MFA password verification required",
            "body": (
                "Verify your password at "
                "https://example-login.com/security "
                "to avoid account lockout."
            ),
        }
    )

    case.attach_evidence(evidence.evidence_id)
    case_store.save(case)

    risk = risk_engine.assess([evidence])
    summary = reporter.summarize(case, [evidence], risk)

    print(summary.executive_summary)

    print("\nKey findings:")
    for finding in summary.key_findings:
        print(f"- {finding}")

    print("\nRecommended actions:")
    for action in summary.recommended_actions:
        print(f"- {action}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sentinel DNA analyst workspace"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run a complete sample investigation",
    )
    parser.add_argument(
        "--data-dir",
        default=os.getenv("SENTINEL_DNA_DATA_DIR", "data"),
    )

    args = parser.parse_args()

    if args.demo:
        run_demo(args.data_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()