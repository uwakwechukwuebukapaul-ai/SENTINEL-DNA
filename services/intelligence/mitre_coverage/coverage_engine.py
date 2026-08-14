from .models import DetectionGapReport
from .metrics import calculate_attack_coverage
class MITRECoverageEngine:
    def calculate_coverage(self,rules,techniques):
        covered=sorted({t for r in rules for t in getattr(r,"mitre_techniques",[]) }); missing=sorted(set(techniques)-set(covered)); return {"coverage_score":calculate_attack_coverage(covered,techniques),"covered":covered,"missing":missing}
    def get_missing_techniques(self,rules,techniques): return DetectionGapReport((x:=self.calculate_coverage(rules,techniques))["missing"],[],"Create detection coverage for missing ATT&CK techniques","high" if x["missing"] else "low")
    def get_rule_coverage(self,rules): return {r.rule_id:list(r.mitre_techniques) for r in rules}
