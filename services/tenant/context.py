from contextvars import ContextVar
from .models import TenantContext
class TenantContextManager:
    def __init__(self): self._context=ContextVar("tenant_context",default=None)
    def set_context(self,context): self._context.set(context); return context
    def get_context(self): return self._context.get()
    def clear_context(self): self._context.set(None)
