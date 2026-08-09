"""
Sentinel DNA MITRE ATT&CK Technique Database

Enterprise technique knowledge base.
"""


MITRE_TECHNIQUES = {

    "credential_phishing": {

        "technique_id":
            "T1566.002",

        "technique_name":
            "Phishing: Spearphishing Link",

        "tactic":
            "Initial Access",

        "description":
            "Adversaries send phishing links to obtain access or credentials.",

    },


    "phishing": {

        "technique_id":
            "T1566",

        "technique_name":
            "Phishing",

        "tactic":
            "Initial Access",

        "description":
            "Adversaries use phishing techniques to gain initial access.",

    },


    "malicious_file": {

        "technique_id":
            "T1204.002",

        "technique_name":
            "Malicious File",

        "tactic":
            "Execution",

        "description":
            "Adversaries rely on users executing malicious files.",

    },


    "credential_access": {

        "technique_id":
            "T1555",

        "technique_name":
            "Credentials from Password Stores",

        "tactic":
            "Credential Access",

        "description":
            "Adversaries attempt to steal credentials.",

    },

}