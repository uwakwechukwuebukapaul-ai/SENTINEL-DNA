from .models import Alert, SigmaRule
class DetectionEngine:
    def __init__(self, rules=None, alert_sink=None): self.rules = rules or self.default_rules(); self.alerts = []; self.alert_sink = alert_sink
    @staticmethod
    def default_rules(): return [
        SigmaRule("Brute force authentication", ["authentication_failure", "failed_login"], ["failed", "brute"], "T1110", "Credential Access", "Repeated authentication failures", "high"),
        SigmaRule("Suspicious PowerShell", ["process_creation", "powershell"], ["powershell", "-enc", "encodedcommand"], "T1059.001", "Execution", "Suspicious PowerShell execution", "high"),
        SigmaRule("Suspicious external IP", ["network_connection", "external_connection"], ["external_ip", "public_ip"], "T1071", "Command and Control", "Connection to an external address", "medium"),
        SigmaRule("Privilege escalation", ["privilege_change", "role_change", "sudo"], ["admin", "root", "elevated"], "T1068", "Privilege Escalation", "Unexpected privilege elevation", "critical")]
    def match(self, event):
        text = str(event.raw_data).lower(); result = []
        for rule in self.rules:
            type_match = not rule.event_types or event.event_type.lower() in {x.lower() for x in rule.event_types}
            keyword_match = not rule.keywords or any(k.lower() in text for k in rule.keywords)
            if type_match and keyword_match: result.append(Alert(rule.id, rule.name, event.public(), rule.severity, rule.technique_id, rule.tactic, rule.description))
        return result
    def process(self, event):
        found = self.match(event); self.alerts.extend(found)
        for alert in found:
            if self.alert_sink: self.alert_sink(alert.public())
        return found
