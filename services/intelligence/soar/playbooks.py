from .models import SOARPlaybook, SOARAction
def _p(i,n,trigger,actions,severity="high"): return SOARPlaybook(i,n,"Safe analyst workflow",trigger,severity,[SOARAction(f"{i}-{x}",a,{},"high" if x==0 else "low",x==0) for x,a in enumerate(actions)])
PHISHING_RESPONSE_PLAYBOOK=_p("PHISHING_RESPONSE_PLAYBOOK","Phishing Response","phishing",["collect evidence summary","enrich IOC","update case","notify analyst"])
BRUTE_FORCE_RESPONSE_PLAYBOOK=_p("BRUTE_FORCE_RESPONSE_PLAYBOOK","Brute Force Response","brute_force",["summarize authentication activity","enrich account information","notify analyst"])
MALWARE_RESPONSE_PLAYBOOK=_p("MALWARE_RESPONSE_PLAYBOOK","Malware Response","malware",["collect indicators","create investigation note","request analyst review"],"critical")
NETWORK_ANOMALY_PLAYBOOK=_p("NETWORK_ANOMALY_PLAYBOOK","Network Anomaly Response","network",["gather context","create analyst task"],"medium")
STARTER_PLAYBOOKS=[PHISHING_RESPONSE_PLAYBOOK,BRUTE_FORCE_RESPONSE_PLAYBOOK,MALWARE_RESPONSE_PLAYBOOK,NETWORK_ANOMALY_PLAYBOOK]
