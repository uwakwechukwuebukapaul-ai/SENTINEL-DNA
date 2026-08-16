import hashlib
def stable_id(tenant_id,kind): return f"{kind}-{hashlib.sha256(f'{tenant_id}:{kind}'.encode()).hexdigest()[:20]}"
