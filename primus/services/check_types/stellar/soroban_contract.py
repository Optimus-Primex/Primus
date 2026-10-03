"""Soroban smart-contract check type.

Watches a deployed Soroban contract's event stream via the RPC ``getEvents``
method.  The monitor can simply assert the RPC answers for the contract, or
require that at least one event was emitted recently (``expect_events``).
"""

from __future__ import annotations

from ...validators import ValidationError
from .. import _http_json
from ..base import DEFAULT_USER_AGENT, CheckResult, CheckType, truncate
from . import common

DEFAULT_LOOKBACK_LEDGERS = 1000
MAX_LOOKBACK_LEDGERS = 17280  # ~a day of ledgers


class SorobanContractCheck(CheckType):
    slug = "soroban-contract"
    label = "Soroban Contract"
    description = "Watch a Soroban smart contract's event stream."
    requires_url = True
    default_config = {
        "network": common.DEFAULT_NETWORK,
        "contract_id": "",
        "lookback_ledgers": DEFAULT_LOOKBACK_LEDGERS,
        "expect_events": False,
    }

    def validate_config(self, config=None, app_config=None) -> dict:
        cleaned = dict(self.default_config)
        cleaned.update(config or {})
        cleaned["network"] = common.normalise_network(cleaned.get("network"))

        contract_id = str(cleaned.get("contract_id") or "").strip()
        if not common.is_contract_id(contract_id):
            raise ValidationError("contract_id must be a Soroban contract id (C...)")
        cleaned["contract_id"] = contract_id

        try:
            lookback = int(cleaned.get("lookback_ledgers", DEFAULT_LOOKBACK_LEDGERS))
        except (TypeError, ValueError):
            raise ValidationError("lookback_ledgers must be an integer") from None
        if not 1 <= lookback <= MAX_LOOKBACK_LEDGERS:
            raise ValidationError(f"lookback_ledgers must be between 1 and {MAX_LOOKBACK_LEDGERS}")
        cleaned["lookback_ledgers"] = lookback
        cleaned["expect_events"] = bool(cleaned.get("expect_events", False))
        return cleaned

    def run(self, monitor, *, allow_private=False, user_agent=DEFAULT_USER_AGENT):
        config = {**self.default_config, **(monitor.type_config or {})}
        contract_id = config.get("contract_id")
        if not common.is_contract_id(contract_id):
            return CheckResult(False, None, None, "contract_id is not configured")
        lookback = int(config.get("lookback_ledgers", DEFAULT_LOOKBACK_LEDGERS))
        url = monitor.url
        timeout = monitor.timeout_seconds

        latest, error, latency = _http_json.json_rpc(
            url,
            "getLatestLedger",
            timeout=timeout,
            user_agent=user_agent,
            allow_private=allow_private,
        )
        if error is not None:
            return CheckResult(False, None, None, truncate(error))
        sequence = (latest or {}).get("sequence")
        if not isinstance(sequence, int):
            return CheckResult(False, None, latency, "RPC getLatestLedger returned no sequence")

        start_ledger = max(1, sequence - lookback)
        params = {
            "startLedger": start_ledger,
            "filters": [{"type": "contract", "contractIds": [contract_id]}],
            "pagination": {"limit": 10},
        }
        result, error, latency = _http_json.json_rpc(
            url,
            "getEvents",
            params,
            timeout=timeout,
            user_agent=user_agent,
            allow_private=allow_private,
        )
        if error is not None:
            return CheckResult(False, None, latency, truncate(error))

        events = (result or {}).get("events") if isinstance(result, dict) else None
        events = events if isinstance(events, list) else []
        detail = {
            "network": config.get("network", common.DEFAULT_NETWORK),
            "contract_id": contract_id,
            "start_ledger": start_ledger,
            "latest_ledger": sequence,
            "events_found": len(events),
        }
        if config.get("expect_events", False) and not events:
            return CheckResult(
                False,
                None,
                latency,
                truncate(f"No events for {contract_id} in the last {lookback} ledgers"),
                detail,
            )
        return CheckResult(True, None, latency, detail=detail)
