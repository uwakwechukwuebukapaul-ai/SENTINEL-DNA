from .models import MarketplacePackage
class PackagePublisher:
 def __init__(self,repository,validator): self.repository=repository; self.validator=validator
 def publish(self,org,data):
  x=MarketplacePackage(org,data.get("name",""),data.get("description",""),data.get("category","DETECTION_PACK"),data.get("publisher","Sentinel DNA"),data.get("version","1.0.0"),content=data.get("content",{})); x.security_rating=80 if self.validator.validate(data)["valid"] else 0; self.repository.packages.append(x); return x
