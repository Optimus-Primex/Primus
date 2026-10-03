"""Stellar Horizon check type.

Verifies that a Horizon endpoint is reachable and that it is ingesting new
ledgers: the latest ledger's close time must be within
``max_ledger_lag_seconds`` of now.
"""

from __future__ import annotations

from .. import _http_json
from ..base import DEFAULT_USER_AGENT, CheckResult, CheckType, truncate
from . import common


class StellarHorizonCheck(CheckType):
    slug = "stellar-horizon"
    label = "Stellar Horizon"
    description = "Check a Stellar Horizon endpoint and its ledger close lag."
    requires_url = True
    default_config = {
        "network": common.DEFAULT_NETWORK,
        "max_ledger_lag_seconds": common.DEFAULT_MAX_LEDGER_LAG,
    }

    def validate_config(self, config=None, app_config=None) -> dict:
        cleaned = dict(self.default_config)
        cleaned.update(config or {})
        cleaned["network"] = common.normalise_network(cleaned.get("network"))
        cleaned["max_ledger_lag_seconds"] = common.validate_max_lag(
            cleaned.get("max_ledger_lag_seconds")
        )
        return cleaned

    def run(self, monitor, *, allow_private=False, user_agent=DEFAULT_USER_AGENT):
        config = {**self.default_config, **(monitor.type_config or {})}
        max_lag = common.validate_max_lag(
            config.get("max_ledger_lag_seconds", common.DEFAULT_MAX_LEDGER_LAG)
        )
        base = (monitor.url or "").rstrip("/")
        target = f"{base}/ledgers?order=desc&limit=1"

        try:
            code, data, latency = _http_json.request_json(
                target,
                timeout=monitor.timeout_seconds,
                user_agent=user_agent,
                allow_private=allow_private,
            )
        except _http_json.HttpJsonError as exc:
            return CheckResult(False, None, None, truncate(str(exc)))

        if code != 200 or not isinstance(data, dict):
            return CheckResult(False, code, latency, truncate(f"Horizon returned HTTP {code}"))

        records = data.get("_embedded", {}).get("records", [])
        if not records:
            return CheckResult(False, code, latency, "Horizon returned no ledgers")

        latest = records[0] or {}
        sequence = latest.get("sequence")
        lag = common.ledger_lag_seconds(latest.get("closed_at"))
        detail = {
            "network": config.get("network", common.DEFAULT_NETWORK),
            "latest_ledger": sequence,
            "closed_at": latest.get("closed_at"),
            "ledger_lag_seconds": lag,
            "protocol_version": latest.get("protocol_version"),
        }

        if lag is None:
            return CheckResult(
                False, code, latency, "Latest ledger has no parseable close time", detail
            )
        if lag > max_lag:
            return CheckResult(
                False,
                code,
                latency,
                truncate(f"Ledger lag {lag:.0f}s exceeds {max_lag}s (ledger {sequence})"),
                detail,
            )
        return CheckResult(True, code, latency, detail=detail)
