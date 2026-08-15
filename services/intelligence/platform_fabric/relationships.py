from .models import IntelligenceRelationship
class RelationshipBuilder:
    def build(self,tenant_id,records):
        grouped={}
        for r in records: grouped.setdefault(r.entity_type,[]).append(r)
        order=["alert","investigation","evidence","ioc","threat","asset","exposure","incident","control","governance_decision"]
        result=[]
        for a,b in zip(order,order[1:]):
            for left in grouped.get(a,[]):
                for right in grouped.get(b,[]): result.append(IntelligenceRelationship(tenant_id,a,left.source_record_id,b,right.source_record_id,"related",{"source_subsystem":left.source_subsystem}))
        return result
