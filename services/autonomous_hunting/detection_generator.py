from .models import GeneratedDetection
class DetectionGenerator:
 def generate(self,org,finding): return GeneratedDetection(org,finding.id,"Suspicious Activity Discovered",{"title":"Suspicious Activity Discovered","status":"draft","detection":{"selection":{"event_type":"suspicious"}},"condition":"selection"},finding.severity,[finding.mitre_technique])
