from datetime import datetime, timedelta, timezone
from uuid import uuid4
from .models import Session
class SessionService:
    def __init__(self, repository, ttl_minutes=60): self.repository, self.ttl = repository, ttl_minutes
    def create(self, user_id, tenant_id, ttl_minutes=None):
        created = datetime.now(timezone.utc); expires = created + timedelta(minutes=ttl_minutes or self.ttl)
        return self.repository.save_session(Session(str(uuid4()), user_id, tenant_id, created.isoformat(), expires.isoformat()))
    def get(self, session_id, tenant_id):
        session = self.repository.get_session(session_id, tenant_id)
        if not session or not session.active or (session.expires_at and session.expires_at <= datetime.now(timezone.utc).isoformat()): return None
        return session
    def revoke(self, session_id, tenant_id):
        session = self.repository.get_session(session_id, tenant_id)
        if not session: return False
        session.active = False; return True
