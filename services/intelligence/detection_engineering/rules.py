from .models import DetectionRule
PHISHING_LINK_DETECTION=DetectionRule("PHISHING_LINK_DETECTION","Phishing Link Detection","Detect suspicious credential-harvesting links","high",.91,"active","phishing",["T1566.002"],{"terms":["phishing","credential","malicious url"],"tlds":[".xyz",".top"]})
BRUTE_FORCE_AUTH_DETECTION=DetectionRule("BRUTE_FORCE_AUTH_DETECTION","Brute Force Authentication","Detect repeated authentication failures","high",.88,"active","authentication",["T1110"],{"terms":["failed login","authentication failure","brute force"]})
MALWARE_INDICATOR_DETECTION=DetectionRule("MALWARE_INDICATOR_DETECTION","Malware Indicator Detection","Detect malicious execution indicators","critical",.94,"active","malware",["T1204"],{"terms":["malware","ransomware","suspicious execution","malicious hash"]})
NETWORK_ANOMALY_DETECTION=DetectionRule("NETWORK_ANOMALY_DETECTION","Network Anomaly Detection","Detect suspicious communication patterns","medium",.79,"active","network",["T1071"],{"terms":["beaconing","suspicious communication","unusual outbound"]})
STARTER_RULES=[PHISHING_LINK_DETECTION,BRUTE_FORCE_AUTH_DETECTION,MALWARE_INDICATOR_DETECTION,NETWORK_ANOMALY_DETECTION]
