from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Project, Workspace
from app.services.product.security import slugify

_ALLOWED_SLUG_FILTERS = {"workspace_id"}


def unique_slug(
    db: Session,
    model: type[Workspace] | type[Project],
    base: str,
    filter_field: str | None = None,
    filter_value: int | None = None,
) -> str:
    if filter_field and filter_field not in _ALLOWED_SLUG_FILTERS:
        raise ValueError(f"Invalid filter field: {filter_field}")
    candidate = slugify(base)
    suffix = 1
    while True:
        stmt = select(model).where(model.slug == candidate)
        if filter_field and filter_value is not None:
            stmt = stmt.where(getattr(model, filter_field) == filter_value)
        exists = db.scalar(stmt)
        if not exists:
            return candidate
        suffix += 1
        candidate = f"{slugify(base)}-{suffix}"
