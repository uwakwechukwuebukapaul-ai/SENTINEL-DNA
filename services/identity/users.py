from .models import User
class UserService:
    def __init__(self, repository): self.repository = repository
    def create(self, **kwargs): return self.repository.save_user(User(**kwargs))
    def get(self, user_id, tenant_id): return self.repository.get_user(user_id, tenant_id)
    def list(self, tenant_id): return self.repository.list_users(tenant_id)
