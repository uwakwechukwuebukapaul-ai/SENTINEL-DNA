from .models import PackageInstallation
class PackageInstaller:
 def __init__(self,repository): self.repository=repository
 def install(self,org,package_id,user):
  x=next((p for p in self.repository.scoped(self.repository.packages,org) if p.id==package_id),None)
  if not x:return None
  i=PackageInstallation(org,x.id,x.version,user); self.repository.installations.append(i); return i
