from .models import SecurityDataSource, stable_id
class DataSourceRegistry:
    def __init__(self): self._sources={}
    def register(self, tenant_id, name, source_type="unknown", provenance=()):
        value=SecurityDataSource(tenant_id,stable_id(tenant_id,"source",name),name,source_type,"registered","insufficient_data",tuple(provenance),True); self._sources[(tenant_id,value.source_id)]=value; return value
    def get(self,tenant_id,source_id): return self._sources.get((tenant_id,source_id))
    def list(self,tenant_id): return tuple(v for (t,_),v in self._sources.items() if t==tenant_id)
