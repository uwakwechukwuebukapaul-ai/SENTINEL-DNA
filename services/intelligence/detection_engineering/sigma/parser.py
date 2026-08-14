from .models import SigmaRule, SigmaMetadata
class SigmaParser:
    def validate_rule(self,data): return bool(isinstance(data,dict) and data.get("title") and data.get("detection"))
    def parse_rule(self,data):
        if not self.validate_rule(data): raise ValueError("Invalid Sigma rule")
        source=data.get("logsource",{}); tags=list(data.get("tags",[])); techniques=[t[6:].upper() for t in tags if t.lower().startswith("attack.t")]
        return SigmaRule(str(data.get("id") or data["title"].upper().replace(" ","_")),data["title"],data.get("description", ""),data.get("author","synthetic"),data.get("status","stable"),SigmaMetadata(source.get("category",""),source.get("product",""),source.get("service",""),source.get("datasource","")),data["detection"],data.get("level","medium"),tags,techniques,list(data.get("references",[])),data.get("date",""),True)
    def export_rule(self,rule): return rule.to_dict() if hasattr(rule,"to_dict") else rule
