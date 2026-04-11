"""Slug generation utilities."""

from supabase import Client

from app.utils.security import slugify

_ALLOWED_SLUG_FILTERS = {"workspace_id"}


def unique_slug(
    supabase: Client,
    table: str,
    base: str,
    filter_field: str | None = None,
    filter_value: int | None = None,
) -> str:
    """Generate a unique slug by appending a suffix if needed.

    Args:
        supabase: Supabase client instance.
        table: Table name to check for existing slugs (e.g., "projects", "workspaces").
        base: Base string to slugify.
        filter_field: Optional field to filter by (only "workspace_id" allowed).
        filter_value: Optional value for the filter field.

    Returns:
        A unique slug string.

    Raises:
        ValueError: If an invalid filter field is provided.
    """
    if filter_field and filter_field not in _ALLOWED_SLUG_FILTERS:
        raise ValueError(f"Invalid filter field: {filter_field}")

    candidate = slugify(base)
    suffix = 1

    while True:
        query = supabase.table(table).select("id").eq("slug", candidate)
        if filter_field and filter_value is not None:
            query = query.eq(filter_field, filter_value)
        result = query.execute()

        if not result.data:
            return candidate

        suffix += 1
        candidate = f"{slugify(base)}-{suffix}"


