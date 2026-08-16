"""Deprecated compatibility surface; performs no network access."""
import warnings

def extract_domain(text):
    warnings.warn("use an IOC parser", DeprecationWarning, stacklevel=2)
    return None

def check_domain(domain):
    warnings.warn("direct provider access is disabled; use ThreatIntelligenceGateway", DeprecationWarning, stacklevel=2)
    return {"domain": domain, "status": "UNAVAILABLE", "error": "direct provider access is disabled"}

def analyze_indicator(text):
    warnings.warn("direct provider access is disabled; use ThreatIntelligenceGateway", DeprecationWarning, stacklevel=2)
    return {"status": "UNAVAILABLE", "error": "direct provider access is disabled"}
