from .models import DigitalTwin
class DigitalTwinBuilder:
 def build(self,assets=None,identities=None,vulnerabilities=None,controls=None,attack_paths=None): return DigitalTwin(list(assets or []),list(identities or []),list(vulnerabilities or []),list(controls or []),list(attack_paths or []))
