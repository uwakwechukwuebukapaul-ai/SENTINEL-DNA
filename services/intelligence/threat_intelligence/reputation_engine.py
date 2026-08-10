"""
Offline Reputation Engine.

Production version can connect to:
- VirusTotal
- AbuseIPDB
- Recorded Future
- MISP
"""



class ReputationEngine:


    def analyze(
        self,
        iocs,
    ):

        results = {}


        for ioc in iocs:

            value = ioc["value"]


            results[value] = {

                "risk":
                    "unknown",

                "score":
                    0,

            }


        return results