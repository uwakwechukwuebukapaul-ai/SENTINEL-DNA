from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from .models import ThreatHunt
from .query_engine import HuntQueryEngine

class HuntManager:
    def __init__(self, query_engine=None): self.query_engine = query_engine or HuntQueryEngine(); self.hunts = {}
    def create_hunt(self, title, hypothesis, techniques=None):
        hunt_id="HUNT-"+hashlib.sha256(f"{title}|{hypothesis}".encode()).hexdigest()[:16]
        hunt=ThreatHunt(hunt_id,title,hypothesis,list(techniques or []),[],"open",datetime.now(timezone.utc).isoformat()); self.hunts[hunt_id]=hunt; return hunt
    def run_hunt(self, hunt_id, query, context=None, threat_report=None, memory_references=None):
        hunt=self.hunts[hunt_id]; result=self.query_engine.search_behavior(query,context,threat_report,memory_references); hunt.findings.extend(result.matches); hunt.status="completed"; return result
