import json
from dataclasses import asdict
from pathlib import Path

from sentinel_dna.case_management.models import Case, CaseEvent


class CaseStore:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)
        self.cases_dir = self.data_dir / "cases"
        self.cases_dir.mkdir(parents=True, exist_ok=True)

    def create_case(self, title: str, description: str, severity: str = "medium") -> Case:
        case = Case(title=title, description=description, severity=severity)
        case.add_event("case_created", "Case created")
        self.save(case)
        return case

    def save(self, case: Case) -> None:
        case_path = self.cases_dir / f"{case.case_id}.json"
        case_path.write_text(json.dumps(asdict(case), indent=2), encoding="utf-8")

    def get(self, case_id: str) -> Case:
        case_path = self.cases_dir / f"{case_id}.json"
        data = json.loads(case_path.read_text(encoding="utf-8"))
        events = [CaseEvent(**event) for event in data.pop("events", [])]
        return Case(**data, events=events)

    def list_cases(self) -> list[Case]:
        cases = []
        # Coordinator callers may supply their own stable external case IDs.
        for case_path in sorted(self.cases_dir.glob("*.json")):
            cases.append(self.get(case_path.stem))
        return cases
