from .models import DataQualityReport, stable_id
class DataQualityService:
    def report(self,tenant_id,events=()):
        events=tuple(events); count=len(events); complete=sum(bool(e.normalized) for e in events)
        return DataQualityReport(tenant_id,stable_id(tenant_id,"quality","events"),round(complete/count*100,2) if count else None,"complete" if count and complete==count else "insufficient_data","available" if count else "insufficient_data","moderate" if count else "insufficient_data",count,("event history is empty",) if not count else (),tuple(sorted({str(x) for e in events for x in e.provenance})),True)
