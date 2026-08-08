"""
Sentinel DNA ATT&CK Mapping Database

Initial internal knowledge base.
"""


MITRE_TECHNIQUES = {


    "malicious-domain":

        {

            "id":
                "T1583",

            "name":
                "Acquire Infrastructure",

            "tactic":
                "Resource Development",
        },


    "phishing":

        {

            "id":
                "T1566",

            "name":
                "Phishing",

            "tactic":
                "Initial Access",
        },


    "credential":

        {

            "id":
                "T1555",

            "name":
                "Credentials from Password Stores",

            "tactic":
                "Credential Access",
        },

}