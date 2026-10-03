"""Shared Stellar helpers: networks, strkey checks and timestamp parsing."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from ...validators import ValidationError

#: Well-known public endpoints per Stellar network.
NETWORKS: dict[str, dict[str, str]] = {
    "mainnet": {
        "horizon": "https://horizon.stellar.org",
        "rpc": "https://mainnet.sorobanrpc.com",
        "passphrase": "Public Global Stellar Network ; September 2015",
    },
    "testnet": {
        "horizon": "https://horizon-testnet.stellar.org",
        "rpc": "https://soroban-testnet.stellar.org",
        "passphrase": "Test SDF Network ; September 2015",
    },
    "futurenet": {
        "horizon": "https://horizon-futurenet.stellar.org",
        "rpc": "https://rpc-futurenet.stellar.org",
        "passphrase": "Test SDF Future Network ; October 2022",
    },
}

DEFAULT_NETWORK = "mainnet"
DEFAULT_MAX_LEDGER_LAG = 30
MAX_LEDGER_LAG = 86400

_STRKEY_RE = re.compile(r"^[A-Z2-7]{56}$")


def normalise_network(value) -> str:
    """Validate and normalise a Stellar network name."""

    network = str(value or DEFAULT_NETWORK).strip().lower()
    if network not in NETWORKS:
        allowed = ", ".join(sorted(NETWORKS))
        raise ValidationError(f"network must be one of: {allowed}")
    return network


def is_account_id(value) -> bool:
    """True for a Stellar account strkey (``G...``)."""

    return isinstance(value, str) and value.startswith("G") and bool(_STRKEY_RE.match(value))


def is_contract_id(value) -> bool:
    """True for a Soroban contract strkey (``C...``)."""

    return isinstance(value, str) and value.startswith("C") and bool(_STRKEY_RE.match(value))


def validate_max_lag(value, field: str = "max_ledger_lag_seconds") -> int:
    try:
        lag = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be an integer") from None
    if not 1 <= lag <= MAX_LEDGER_LAG:
        raise ValidationError(f"{field} must be between 1 and {MAX_LEDGER_LAG}")
    return lag


def parse_timestamp(value) -> datetime | None:
    """Parse an ISO-8601 string or unix epoch into a naive UTC datetime."""

    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=UTC).replace(tzinfo=None)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            try:
                return datetime.fromtimestamp(float(text), tz=UTC).replace(tzinfo=None)
            except (OverflowError, OSError, ValueError):
                return None
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(UTC).replace(tzinfo=None)
        return parsed
    return None


def ledger_lag_seconds(close_time, now: datetime | None = None) -> float | None:
    """Seconds between ``close_time`` and ``now`` (``None`` if unparseable)."""

    closed_at = parse_timestamp(close_time)
    if closed_at is None:
        return None
    reference = now or datetime.now(UTC).replace(tzinfo=None)
    return round((reference - closed_at).total_seconds(), 2)
