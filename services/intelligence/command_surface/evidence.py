class EvidenceContext:
    def normalize(self, item):
        refs=list(item.get("evidence_references", [])); return {"references":refs, "coverage":item.get("evidence_coverage"),
            "freshness":item.get("evidence_freshness"), "validity":item.get("evidence_validity"),
            "missing":item.get("missing_evidence", []), "available":bool(item.get("evidence_available", bool(refs))),
            "provenance":dict(item.get("provenance", {}))}
