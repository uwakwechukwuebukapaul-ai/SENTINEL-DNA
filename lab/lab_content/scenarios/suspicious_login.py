"""Repeatable SOC demo: an external login should enter investigation."""
def events(hostname="lab-linux-01"):
    return [{"source": "linux", "event": {"hostname": hostname, "user": "root", "event_type": "privilege_change", "severity": "critical", "message": "sudo elevated login from external_ip"}}]
