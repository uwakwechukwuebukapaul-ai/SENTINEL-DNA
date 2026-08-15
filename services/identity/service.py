from .repository import IdentityRepository
from .users import UserService
from .roles import RoleService
from .permissions import PermissionService
from .sessions import SessionService
from .policy import IdentityPolicy
class IdentityService:
    def __init__(self, repository=None, audit=None):
        self.repository = repository or IdentityRepository(); self.users = UserService(self.repository); self.roles = RoleService(self.repository); self.permissions = PermissionService(self.repository); self.sessions = SessionService(self.repository); self.policy = IdentityPolicy(self.repository); self.audit = audit
    def create_user(self, **kwargs):
        user = self.users.create(**kwargs); self._audit("identity_user_created", user.tenant_id, user_id=user.user_id); return user
    def assign_role(self, user_id, tenant_id, role_id):
        user = self.repository.get_user(user_id, tenant_id)
        if not user or not self.repository.get_role(role_id): raise LookupError("identity_resource_not_found")
        if role_id not in user.roles: user.roles.append(role_id)
        self._audit("identity_role_assigned", tenant_id, user_id=user_id, role_id=role_id); return user
    def _audit(self, event, tenant_id, **details):
        if self.audit and hasattr(self.audit, "record"): self.audit.record(event, tenant_id=tenant_id, **details)
