PLANNING_RULES = {
    "phishing": ("Validate phishing evidence and affected identities", ["inspect email artifacts", "extract indicators", "map initial access", "assess affected identities"], "high"),
    "brute_force": ("Assess authentication abuse and account exposure", ["review authentication events", "identify targeted accounts", "check source reputation", "map credential access"], "high"),
    "malware": ("Assess synthetic malware activity and endpoint impact", ["inspect endpoint artifacts", "classify malware indicators", "identify affected assets", "map execution behavior"], "critical"),
    "suspicious_communication": ("Assess suspicious external communication", ["review network artifacts", "classify destinations", "check related entities", "map command and control behavior"], "medium"),
}
