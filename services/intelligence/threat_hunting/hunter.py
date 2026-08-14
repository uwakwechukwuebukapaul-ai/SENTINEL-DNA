from .models import HuntingEvidence, HuntingQuery, HuntingResult
class HuntingEngine:
    def execute(self, query: HuntingQuery, context=None):
        data=str(context or {}).lower(); matches=[]
        if query.query_type in data or any(tech.lower() in data for tech in query.mitre_techniques): matches.append(HuntingEvidence(f"{query.query_id}-e1", query.tenant_id, "investigation_intelligence", context, .8))
        return HuntingResult(query.query_id, query.tenant_id, matches, .8 if matches else .1, f"Found {len(matches)} match(es) for {query.query_type} hunting")
