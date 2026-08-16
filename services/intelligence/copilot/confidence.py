class ConfidenceEngine:
    def assess(self,context):
        count=sum(bool(x) for x in (context.evidence,context.detection_intelligence,context.hunting_intelligence)); return {'level':'moderate' if count else 'insufficient_data','evidence_completeness':'available' if context.evidence else 'insufficient_data','uncertainty':() if count else ('evidence context is empty',)}
