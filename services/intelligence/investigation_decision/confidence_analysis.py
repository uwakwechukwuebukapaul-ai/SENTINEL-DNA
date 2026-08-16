class ConfidenceAnalysis:
 def analyze(self,context):
  evidence=context.get('evidence',()) if isinstance(context,dict) else ();return {'level':'moderate' if evidence else 'insufficient_evidence','evidence_completeness':'available' if evidence else 'insufficient_evidence','uncertainty':() if evidence else ('evidence context is empty',)}
