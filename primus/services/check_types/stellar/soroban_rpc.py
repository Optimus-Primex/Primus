"""Soroban RPC check type.

Calls a Soroban RPC node's ``getHealth`` / ``getLatestLedger`` / ``getNetwork``
JSON-RPC methods and verifies the node is healthy, ingesting recent ledgers and
(optionally) serving the expected network.
"""

from __future__ import annotations

from .. import _http_json
from ..base import DEFAULT_USER_AGENT, CheckResult, CheckType, truncate
from . import common


class SorobanRpcCheck(CheckType):
    slug = "soroban-rpc"
    label = "Soroban RPC"
    description = "Check a Soroban RPC node's health and latest ledger."
    requires_url = True
    default_config = {
        "network": common.DEFAULT_NETWORK,
        "max_ledger_lag_seconds": common.DEFAULT_MAX_LEDGER_LAG,
        "verify_passphrase": True,
    }

    def validate_config(self, config=None, app_config=None) -> dict:
        cleaned = dict(self.default_config)
        cleaned.update(config or {})
        cleaned["network"] = common.normalise_network(cleaned.get("network"))
        cleaned["max_ledger_lag_seconds"] = common.validate_max_lag(
            cleaned.get("max_ledger_lag_seconds")
        )
        cleaned["verify_passphrase"] = bool(cleaned.get("verify_passphrase", True))
        return cleaned

    def run(self, monitor, *, allow_private=False, user_agent=DEFAULT_USER_AGENT):
        config = {**self.default_config, **(monitor.type_config or {})}
        network = common.normalise_network(config.get("network"))
        max_lag = common.validate_max_lag(
            config.get("max_ledger_lag_seconds", common.DEFAULT_MAX_LEDGER_LAG)
        )
        url = monitor.url
        timeout = monitor.timeout_seconds

        def call(method):
            return _http_json.json_rpc(
                url,
                method,
                timeout=timeout,
                user_agent=user_agent,
                allow_private=allow_private,
            )

        latest, error, latency = call("getLatestLedger")
        if error is not None:
            return CheckResult(False, None, None, truncate(error))
        if not isinstance(latest, dict):
            return CheckResult(False, None, latency, "RPC getLatestLedger returned no data")

        sequence = latest.get("sequence")
        lag = common.ledger_lag_seconds(latest.get("closeTime") or latest.get("close_time"))
        detail = {
            "network": network,
            "latest_ledger": sequence,
            "protocol_version": latest.get("protocolVersion"),
            "ledger_lag_seconds": lag,
        }

        health, _, _ = call("getHealth")
        if isinstance(health, dict):
            detail["health"] = health.get("status")
            if health.get("status") not in (None, "healthy"):
                return CheckResult(
                    False, None, latency, truncate(f"RPC unhealthy: {health.get('status')}"), detail
                )

        if config.get("verify_passphrase", True):
            network_info, net_error, _ = call("getNetwork")
            if net_error is not None:
                return CheckResult(False, None, latency, truncate(net_error), detail)
            passphrase = (network_info or {}).get("passphrase")
            expected = common.NETWORKS[network]["passphrase"]
            if passphrase and passphrase != expected:
                return CheckResult(
                    False,
                    None,
                    latency,
                    "Network passphrase does not match configured network",
                    detail,
                )

        if lag is not None and lag > max_lag:
            return CheckResult(
                False,
                None,
                latency,
                truncate(f"Ledger lag {lag:.0f}s exceeds {max_lag}s (ledger {sequence})"),
                detail,
            )
        return CheckResult(True, None, latency, detail=detail)
