from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class MarketplacePackage:
 organization_id:str; name:str; description:str; category:str; publisher:str; version:str="1.0.0"; status:str="PUBLISHED"; security_rating:float=0; content:dict=field(default_factory=dict); id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=now)
 def public(self): return asdict(self)
@dataclass
class PackageInstallation:
 organization_id:str; package_id:str; installed_version:str; installed_by:str; status:str="ACTIVE"; id:str=field(default_factory=lambda:str(uuid4())); installed_at:str=field(default_factory=now)
 def public(self): return asdict(self)
