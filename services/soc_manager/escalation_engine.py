class EscalationEngine:
 def should_escalate(self,priority,confidence=1,approval_required=False,sla_exceeded=False): return priority=="P1" or confidence<.6 or approval_required or sla_exceeded
