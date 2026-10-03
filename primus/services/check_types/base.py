"""Base classes for pluggable monitor check types.

A *check type* knows how to run a single check for a monitor and how to
validate/normalise its type-specific configuration.  Types are registered in
:mod:`primus.services.check_types` and resolved by ``Monitor.type`` at check
time, so new protocols (Stellar Horizon, Soroban RPC, ...) can be added
without touching the scheduler, API, or incident logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

DEFAULT_USER_AGENT = "Primus-Uptime-Monitor/1.0"
MAX_ERROR_LENGTH = 500


@dataclass
class CheckResult:
    """Outcome of a single check.

    ``status_code`` is the HTTP status when the type has one (it may be
    ``None`` for non-HTTP types).  ``detail`` carries type-specific metrics
    (for example a Stellar ledger lag) that are persisted alongside the check.
    """

    success: bool
    status_code: int | None
    latency_ms: float | None
    error: str | None = None
    detail: dict | None = None


def truncate(message: str | None, limit: int = MAX_ERROR_LENGTH) -> str | None:
    """Clamp an error message to a length the database column accepts."""

    if message is None:
        return None
    return message[:limit]


class CheckType(ABC):
    """Interface implemented by every monitor check type.

    Subclasses are registered as singletons, so they must be stateless.
    """

    #: Stable identifier stored in ``Monitor.type`` (lowercase, no spaces).
    slug: str = ""
    #: Human readable name shown in the dashboard.
    label: str = ""
    #: One-line explanation of what the type does.
    description: str = ""
    #: Whether ``Monitor.url`` is required for this type.
    requires_url: bool = False
    #: Default values merged into ``Monitor.type_config``.
    default_config: dict = {}

    @abstractmethod
    def run(self, monitor, *, allow_private: bool, user_agent: str) -> CheckResult:
        """Perform one check for ``monitor`` and classify the result.

        Implementations must never raise for network/validation failures; they
        return an unsuccessful :class:`CheckResult` describing the problem.
        """

    def validate_config(self, config: dict | None = None, app_config=None) -> dict:
        """Return a normalised copy of the type-specific configuration.

        Raises :class:`primus.services.validators.ValidationError` on bad input.
        """

        return dict(config or {})

    def config_defaults(self) -> dict:
        """Return a copy of the default ``type_config`` for this type."""

        return dict(self.default_config)
