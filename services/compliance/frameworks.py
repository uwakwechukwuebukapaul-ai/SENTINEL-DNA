from .models import ComplianceFramework,SecurityControl
NIST_CSF=ComplianceFramework("NIST_CSF","NIST CSF","1.1","Identify, Protect, Detect, Respond, Recover")
CIS_CONTROLS=ComplianceFramework("CIS","CIS Controls"," v8","Inventory, configuration, accounts, logging")
MITRE=ComplianceFramework("MITRE","MITRE ATT&CK","14","Detection coverage and technique visibility")
DEFAULT_FRAMEWORKS=[NIST_CSF,CIS_CONTROLS,MITRE]
DEFAULT_CONTROLS=[SecurityControl("NIST-DE.CM","NIST_CSF","Security monitoring capability",category="Detect",requirements=["telemetry","detection"]),SecurityControl("MITRE-coverage","MITRE","Technique visibility",category="Detect",requirements=["mitre coverage"])]
