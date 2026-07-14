"""App-specific request/user/project log context backed by structlog contextvars.

This is a thin wrapper over ``structlog.contextvars`` so that middleware,
dependencies, and background jobs can bind context fields
(``request_id``/``user_id``/``workspace_id``/``project_id``/``route``) onto the
current context WITHOUT importing structlog internals directly. Every configured
log record — whether emitted through structlog's bound loggers or plain stdlib
``logging.getLogger(...).info(...)`` calls — picks these fields up via
``merge_contextvars`` in the ProcessorFormatter chain (see ``app/core/logging.py``).

WS2 owns the actual wiring inside middleware/deps; this module only provides the
machinery.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = [
    "bind_request_context",
    "bind_user_context",
    "bind_project_context",
    "clear_request_context",
    "request_log_scope",
]


def bind_request_context(request_id: str, route: str | None = None) -> None:
    """Bind per-request fields (call at the very start of request handling)."""
    structlog.contextvars.bind_contextvars(request_id=request_id)
    if route is not None:
        structlog.contextvars.bind_contextvars(route=route)


def bind_user_context(user_id: Any, workspace_id: Any = None, project_id: Any = None) -> None:
    """Bind identity fields once the authenticated user is known."""
    structlog.contextvars.bind_contextvars(user_id=user_id)
    if workspace_id is not None:
        structlog.contextvars.bind_contextvars(workspace_id=workspace_id)
    if project_id is not None:
        structlog.contextvars.bind_contextvars(project_id=project_id)


def bind_project_context(project_id: Any) -> None:
    """Bind (or update) the active project id on the current context."""
    structlog.contextvars.bind_contextvars(project_id=project_id)


def clear_request_context() -> None:
    """Drop ALL contextvars bound for this request/scope.

    Call in a ``finally`` block so context never leaks across requests.
    """
    structlog.contextvars.clear_contextvars()


@contextmanager
def request_log_scope(
    request_id: str | None = None,
    *,
    route: str | None = None,
    user_id: Any = None,
    workspace_id: Any = None,
    project_id: Any = None,
) -> Iterator[None]:
    """Bind a temporary log context, yield, then clear it.

    For non-ASGI code (background jobs, tests, scripts) where there is no
    middleware ``finally`` to clear contextvars. Always clears on exit, even on
    exception.
    """
    if request_id is not None:
        bind_request_context(request_id, route=route)
    elif route is not None:
        structlog.contextvars.bind_contextvars(route=route)
    if user_id is not None:
        bind_user_context(user_id, workspace_id=workspace_id, project_id=project_id)
    else:
        if workspace_id is not None:
            structlog.contextvars.bind_contextvars(workspace_id=workspace_id)
        if project_id is not None:
            structlog.contextvars.bind_contextvars(project_id=project_id)
    try:
        yield
    finally:
        clear_request_context()
