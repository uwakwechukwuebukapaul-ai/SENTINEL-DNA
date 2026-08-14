from .models import CorrelationRule

STARTER_RULES = (
    CorrelationRule("brute-force", "Brute force detection", ("failed_login", "authentication_failure"), .75),
    CorrelationRule("impossible-travel", "Impossible travel", ("login", "geo_change"), .8),
    CorrelationRule("malware-chain", "Malware execution chain", ("process", "file", "endpoint"), .8),
    CorrelationRule("outbound-transfer", "Suspicious outbound transfer", ("network", "dns", "data_transfer"), .75),
)
