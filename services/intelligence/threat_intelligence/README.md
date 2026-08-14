# Threat intelligence correlation

This layer correlates indicators with prior cases and recurring infrastructure patterns. Evidence collection remains the Evidence Engine’s responsibility; MemoryService stores investigation intelligence, while this repository focuses on indicator relationships and enrichment. Analysts receive correlation and scoring context before decisions are generated.

Future adapters can connect VirusTotal, MISP, OpenCTI, STIX/TAXII feeds, threat actors, malware intelligence, and hunting workflows without changing the correlation contract.
