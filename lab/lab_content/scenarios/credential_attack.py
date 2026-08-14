"""Repeatable SOC demo: authentication failures should trigger T1110."""
def events(hostname="lab-windows-01"):
    return [{"source": "windows", "event": {"hostname": hostname, "user": "administrator", "event_type": "authentication_failure", "severity": "high", "message": "failed login brute force"}} for _ in range(5)]
