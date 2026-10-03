"""Registry of pluggable monitor check types.

Built-in types are imported and registered on first import of this package.
Third-party/ecosystem types (Stellar Horizon, Soroban RPC, ...) call
:func:`register` at import time.
"""

from __future__ import annotations

from .base import (
    DEFAULT_USER_AGENT,
    MAX_ERROR_LENGTH,
    CheckResult,
    CheckType,
    truncate,
)

DEFAULT_TYPE = "http"

_REGISTRY: dict[str, CheckType] = {}


def register(check_type: CheckType) -> CheckType:
    """Register ``check_type`` under its slug (idempotent, last one wins)."""

    slug = (check_type.slug or "").strip().lower()
    if not slug:
        raise ValueError("check type must define a non-empty slug")
    check_type.slug = slug
    _REGISTRY[slug] = check_type
    return check_type


def get_check_type(slug: str | None) -> CheckType | None:
    """Return the registered type for ``slug`` or ``None`` if unknown."""

    if not slug:
        return None
    return _REGISTRY.get(str(slug).strip().lower())


def is_registered(slug: str) -> bool:
    return get_check_type(slug) is not None


def available_types() -> list[CheckType]:
    """Return every registered type ordered by slug (stable for the UI)."""

    return sorted(_REGISTRY.values(), key=lambda check_type: check_type.slug)


def default_check_type() -> CheckType:
    check_type = get_check_type(DEFAULT_TYPE)
    if check_type is None:  # pragma: no cover - built-ins always registered
        raise RuntimeError(f"default check type {DEFAULT_TYPE!r} is not registered")
    return check_type


def _load_builtin_types() -> None:
    from .http import HttpCheckType

    register(HttpCheckType())


_load_builtin_types()


__all__ = [
    "DEFAULT_TYPE",
    "DEFAULT_USER_AGENT",
    "MAX_ERROR_LENGTH",
    "CheckResult",
    "CheckType",
    "available_types",
    "default_check_type",
    "get_check_type",
    "is_registered",
    "register",
    "truncate",
]
