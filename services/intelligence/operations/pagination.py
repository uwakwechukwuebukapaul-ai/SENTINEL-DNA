"""Safe, stable pagination for tenant-scoped governance projections."""
from __future__ import annotations


DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def paginate(items, *, page=1, page_size=DEFAULT_PAGE_SIZE):
    try:
        page = int(page)
        page_size = int(page_size)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_pagination") from exc
    if page < 1 or page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise ValueError("invalid_pagination")
    total = len(items)
    start = (page - 1) * page_size
    return {"items": list(items[start:start + page_size]), "page": page, "page_size": page_size, "total": total, "has_next": start + page_size < total}


def repository_page(repository, *, tenant_id: str, page=1, page_size=DEFAULT_PAGE_SIZE, method="page_for_tenant", **filters):
    reader = getattr(repository, method, None)
    if callable(reader):
        return reader(tenant_id=tenant_id, page=page, page_size=page_size, **filters)
    return paginate(getattr(repository, "list_for_tenant")(tenant_id=tenant_id), page=page, page_size=page_size)
