from .models import AttackPath

class AttackPathAnalyzer:
    def analyze(self, organization_id, assets, vulnerabilities):
        paths = []
        for vuln in vulnerabilities:
            asset = next((a for a in assets if a.id == vuln.asset_id), None)
            if not asset: continue
            paths.append(AttackPath(organization_id, [{"stage": "Initial Access", "name": "Internet Exposure"}, {"stage": "Vulnerable Asset", "name": asset.hostname}, {"stage": "Privilege Escalation", "name": "Compromised Account"}], ["T1190", "T1068", "T1078"], min(100, vuln.cvss_score * 10)))
        return paths
