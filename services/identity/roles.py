from .models import Role
class RoleService:
    def __init__(self, repository): self.repository = repository
    def create(self, role_id, name, description="", permissions=None): return self.repository.save_role(Role(role_id, name, description, list(permissions or [])))
    def get(self, role_id): return self.repository.get_role(role_id)
