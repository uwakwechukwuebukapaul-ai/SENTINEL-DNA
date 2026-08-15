class OutcomeEvaluator:
    def resolution(self,outcome):
        if outcome.verification_status in {"SUCCESS","PARTIAL","FAILED"} and outcome.resolution_status=="UNKNOWN": return "UNKNOWN"
        return outcome.resolution_status
    def quality(self,outcome):
        enough=bool(outcome.evidence_references); known=outcome.verification_status!="UNKNOWN"; fp=outcome.false_positive_signal
        return {"detection_quality":"FALSE_POSITIVE_SIGNAL" if fp in {"confirmed","probable"} else "OBSERVED" if enough else "UNKNOWN","investigation_quality":"SUFFICIENT" if enough else "UNKNOWN","recommendation_quality":"UNKNOWN","action_effectiveness":"EFFECTIVE" if outcome.verification_status=="SUCCESS" else "PARTIALLY_EFFECTIVE" if outcome.verification_status=="PARTIAL" else "INEFFECTIVE" if outcome.verification_status=="FAILED" else "UNKNOWN","confidence":outcome.confidence if outcome.confidence is not None else None,"uncertainty":"Evidence or verification is insufficient." if not enough or not known else ""}
