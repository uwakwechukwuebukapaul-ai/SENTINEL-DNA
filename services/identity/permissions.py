from .models import Permission
class PermissionService:
    def __init__(self, repository): self.repository = repository
    def create(self, permission_id, resource, action, description=""): return self.repository.save_permission(Permission(permission_id, resource, action, description))
