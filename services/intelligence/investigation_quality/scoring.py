from datetime import datetime, timezone
from .models import InvestigationQualityAssessment

class QualityScoringEngine:
    def assess(self, investigation_id, tenant_id, result):
        data = result.to_dict() if hasattr(result, "to_dict") else (result or {})
        evidence = data.get("evidence", data.get("artifacts", [])) or []
        artifacts = data.get("artifacts", []) or []
        iocs = data.get("iocs", data.get("indicators", [])) or []
        reasoning = data.get("reasoning_report", data.get("reasoning"))
        mitre = data.get("mitre", []) or []
        timeline = data.get("timeline", []) or []
        confidence = data.get("confidence", data.get("ai_confidence"))
        scores = {
            "evidence": 100 if evidence else 0,
            "enrichment": 100 if iocs and data.get("threat_intelligence_report") else 50 if iocs else 0,
            "reasoning": 100 if reasoning and confidence is not None else 50 if reasoning else 0,
            "mitre_mapping": 100 if mitre else 0,
            "timeline": 100 if len(timeline) > 1 else 50 if timeline else 0,
            "confidence": min(100, float(confidence) * 100) if confidence is not None else 0,
            "completeness": 100 if all(data.get(key) for key in ("evidence", "timeline", "mitre")) else 50 if any(data.get(key) for key in ("evidence", "timeline", "mitre")) else 0,
        }
        values = list(scores.values())
        overall = round(sum(values) / len(values), 2)
        quality_status = "high" if overall >= 80 else "review" if overall >= 50 else "insufficient_data"

        def mapping(value):
            if isinstance(value, dict): return value
            return value.to_dict() if hasattr(value, "to_dict") else {}

        evidence_refs = set()
        for item in evidence:
            current = mapping(item)
            evidence_refs.update(str(ref) for ref in current.get("evidence_refs", []) or [] if ref)
            for key in ("evidence_id", "reference", "id"):
                if current.get(key): evidence_refs.add(str(current[key]))
        artifact_refs = {
            str(current[key])
            for item in artifacts
            for current in [mapping(item)]
            for key in ("artifact_id", "id")
            if current.get(key)
        }
        tenant_context = data.get("tenant_context") if isinstance(data.get("tenant_context"), dict) else {}
        actor_id = tenant_context.get("actor_id") or (data.get("metadata") or {}).get("actor_id")
        created_at = datetime.now(timezone.utc).isoformat()
        return InvestigationQualityAssessment(
            investigation_id=str(investigation_id), tenant_id=str(tenant_id) if tenant_id else None,
            case_id=str(data.get("case_id") or investigation_id), overall_score=overall,
            evidence_score=scores["evidence"], enrichment_score=scores["enrichment"], reasoning_score=scores["reasoning"],
            mitre_mapping_score=scores["mitre_mapping"], timeline_score=scores["timeline"], confidence_score=scores["confidence"],
            completeness_score=scores["completeness"], created_at=created_at, quality_status=quality_status,
            evidence_refs=sorted(evidence_refs), artifact_refs=sorted(artifact_refs),
            provenance={"tenant_id": tenant_id, "actor_id": actor_id, "source": "investigation_quality_engine"},
            metadata={"scoring_version": "investigation-quality-v1", "score_basis": "investigation_result"},
        )
