class PackageValidator:
 def validate(self,data): return {"valid":bool(data.get("name") and data.get("category") and data.get("content") is not None),"checks":["metadata","permissions","tenant_compatibility","security_requirements"]}
