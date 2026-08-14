from ..connector import BaseConnector
class SyntheticThreatIntelConnector(BaseConnector):
    connector_name="synthetic_threat_intel"; capabilities=("lookup_indicators",)
    def lookup(self,indicator): return {"indicator":indicator,"matches":[],"synthetic_only":True}
