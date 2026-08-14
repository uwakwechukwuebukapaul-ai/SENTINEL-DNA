class SOARPlanner:
    def generate_plan(self,result):
        text=str(result).lower(); pid="PHISHING_RESPONSE_PLAYBOOK" if "phish" in text else "MALWARE_RESPONSE_PLAYBOOK" if "malware" in text else "BRUTE_FORCE_RESPONSE_PLAYBOOK" if "brute" in text else "NETWORK_ANOMALY_PLAYBOOK"
        return {"playbook":pid,"approval_required":True}
