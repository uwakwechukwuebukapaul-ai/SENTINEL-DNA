"""Customer-safe investigation report V2 and presentation adapters.

The builder is a pure projection over canonical read models.  Rendering is kept
outside the investigation domain so JSON, PDF, and future portal adapters share
one governed contract.
"""
from __future__ import annotations

from typing import Any

from services.intelligence.workspace.evidence_graph import _safe


class InvestigationReportV2Builder:
    VERSION = "investigation-report-v2"

    def build(self, case_id: str, view: dict[str, Any], explainability: dict[str, Any], graph: dict[str, Any], contradictions: dict[str, Any], audit_timeline=None, approval_history=None) -> dict[str, Any]:
        summary = view.get("summary") or {}
        conclusion = explainability.get("conclusion") or {}
        confidence = explainability.get("confidence_decomposition") or {}
        intelligence = explainability.get("threat_intelligence") or {}
        approval_history = sorted((_safe(item) for item in (approval_history or []) if isinstance(item, dict)), key=lambda item: (str(item.get("created_at") or ""), str(item.get("event_id") or "")))
        findings = sorted((_safe(item) for item in view.get("findings", []) if isinstance(item, dict)), key=lambda item: (str(item.get("finding_id") or item.get("id") or ""), str(item.get("finding") or "")))
        evidence = sorted((_safe(item) for item in explainability.get("evidence", []) if isinstance(item, dict)), key=lambda item: str(item.get("evidence_id") or ""))
        mitre = sorted((_safe(item) for item in explainability.get("mitre", []) if isinstance(item, dict)), key=lambda item: (str(item.get("technique_id") or ""), str(item.get("technique") or "")))
        timeline = sorted((_safe(item) for item in explainability.get("timeline", []) if isinstance(item, dict)), key=lambda item: (str(item.get("timestamp") or ""), str(item.get("event") or "")))
        approval = approval_history[-1] if approval_history else {}
        return {
            "version": self.VERSION,
            "case_id": str(case_id),
            "executive_summary": {"incident_summary": summary.get("title"), "conclusion": conclusion.get("conclusion"), "risk": summary.get("risk"), "confidence": summary.get("confidence"), "key_findings": findings},
            "incident_overview": _safe(view.get("investigation", {})),
            "investigation_scope": {"evidence_count": len(evidence), "finding_count": len(findings), "ioc_count": len(intelligence.get("indicators", [])), "provider_count": len(intelligence.get("providers", []))},
            "key_findings": findings,
            "risk_assessment": {"risk": summary.get("risk"), "disposition": summary.get("decision")},
            "confidence_assessment": {"overall": confidence.get("overall_confidence"), "limitations": confidence.get("missing_components", [])},
            "confidence_decomposition": confidence,
            "evidence_summary": {"inventory": evidence, "quality": confidence.get("components", {}).get("evidence_quality"), "coverage": confidence.get("components", {}).get("evidence_coverage"), "supporting": conclusion.get("supporting_factors", []), "contradicting": conclusion.get("contradicting_factors", [])},
            "threat_intelligence": intelligence,
            "mitre_attack": mitre,
            "timeline": timeline,
            "analyst_decisions": _safe(view.get("feedback", [])),
            "disposition": summary.get("decision"),
            "approval": {"state": approval.get("state", "draft"), "history": approval_history},
            "recommendations": _safe(view.get("recommendations", [])),
            "uncertainty_limitations": {"uncertainty": conclusion.get("uncertainty", []), "contradictions": contradictions.get("items", []), "stale_intelligence": intelligence.get("stale_indicators", []), "provider_unavailability": intelligence.get("provider_agreement", {}).get("unavailable_count", 0)},
            "audit_provenance": {"events": _safe(audit_timeline or []), "source": "canonical_investigation_read_model", "evidence_first": True},
            "evidence_graph_summary": {"version": graph.get("version"), "statistics": graph.get("statistics", {})},
            "deterministic": True,
        }


class ReportPresentationModel:
    """Flatten a report projection into bounded, human-readable PDF lines."""

    def lines(self, report: dict[str, Any]) -> list[str]:
        summary = report.get("executive_summary", {})
        lines = ["SENTINEL DNA", "AI INVESTIGATOR REPORT V2", "", f"Case: {report.get('case_id', 'Unavailable')}", f"Conclusion: {summary.get('conclusion', 'Needs analyst review')}", f"Risk: {summary.get('risk', 'Unavailable')}", f"Confidence: {summary.get('confidence', 'Unavailable')}", ""]
        sections = [("EXECUTIVE SUMMARY", summary.get("incident_summary")), ("KEY FINDINGS", [item.get("finding") or item.get("title") for item in report.get("key_findings", [])]), ("EVIDENCE SUMMARY", report.get("evidence_summary", {}).get("inventory", [])), ("THREAT INTELLIGENCE", report.get("threat_intelligence", {}).get("indicators", [])), ("MITRE ATT&CK", report.get("mitre_attack", [])), ("UNCERTAINTY / LIMITATIONS", report.get("uncertainty_limitations", {})), ("APPROVAL", report.get("approval", {})), ("AUDIT / PROVENANCE", report.get("audit_provenance", {}).get("source"))]
        for title, value in sections:
            lines.extend([title, self._text(value), ""])
        return lines

    @staticmethod
    def _text(value: Any) -> str:
        if isinstance(value, list):
            return "\n".join(f"- {ReportPresentationModel._text(item)}" for item in value[:30]) or "- None recorded"
        if isinstance(value, dict):
            return "\n".join(f"{key}: {ReportPresentationModel._text(item)}" for key, item in sorted(value.items(), key=lambda pair: str(pair[0])) if key not in {"events", "history"})[:4000] or "Unavailable"
        return str(value if value is not None else "Unavailable")


class PdfReportRenderer:
    """Dependency-free, deterministic PDF presentation adapter.

    This intentionally renders the governed presentation model only; it does
    not query repositories or execute investigation logic.
    """

    def render(self, report: dict[str, Any]) -> bytes:
        lines = ReportPresentationModel().lines(report)
        pages = [lines[index:index + 52] for index in range(0, len(lines), 52)] or [["No report content available."]]
        objects: list[bytes] = []
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        page_ids = [4 + index * 2 for index in range(len(pages))]
        objects.append(("<< /Type /Pages /Kids [" + " ".join(f"{item} 0 R" for item in page_ids) + f"] /Count {len(page_ids)} >>").encode())
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        for index, page in enumerate(pages):
            content_id = 5 + index * 2
            objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode())
            commands = ["BT", "/F1 10 Tf", "50 750 Td"]
            for line in page:
                safe = str(line).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")[:180]
                commands.append(f"({safe}) Tj")
                commands.append("0 -14 Td")
            commands.append("ET")
            stream = "\n".join(commands).encode("latin-1", "replace")
            objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
        output = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for number, obj in enumerate(objects, 1):
            offsets.append(len(output)); output.extend(f"{number} 0 obj\n".encode()); output.extend(obj); output.extend(b"\nendobj\n")
        xref = len(output); output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
        for offset in offsets[1:]: output.extend(f"{offset:010d} 00000 n \n".encode())
        output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
        return bytes(output)
