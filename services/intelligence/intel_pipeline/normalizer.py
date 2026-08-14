import hashlib,re
class IndicatorNormalizer:
 def normalize(self,item,source_id="synthetic"):
  value=str(item.get("value") if isinstance(item,dict) else item).strip().lower(); typ=(item.get("type") if isinstance(item,dict) else "") or ("email" if "@" in value else "url" if value.startswith("http") else "ip" if re.match(r"^\d+\.\d+\.\d+\.\d+$",value) else "hash" if len(value) in {32,40,64} else "domain"); return {"indicator_id":"IND-"+hashlib.sha256(f"{typ}|{value}".encode()).hexdigest()[:16],"indicator_type":typ,"value":value,"source_id":source_id,"confidence":float(item.get("confidence",.5) if isinstance(item,dict) else .5)}
