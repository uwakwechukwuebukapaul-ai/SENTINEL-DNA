from .models import CopilotContext
class CopilotContextBuilder:
    def build(self,tenant_id,case_id,**sources):
        return CopilotContext(tenant_id,case_id,tuple(sources.get('alerts',())),tuple(sources.get('cases',())),tuple(sources.get('evidence',())),tuple(sources.get('iocs',())),tuple(sources.get('detection_intelligence',())),tuple(sources.get('hunting_intelligence',())),tuple(sources.get('investigation_context',())),tuple(sources.get('command_center_insights',())),tuple(sources.get('provenance',())),True)
