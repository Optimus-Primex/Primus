"""Stellar account and asset check types (Horizon REST)."""

from __future__ import annotations

from urllib.parse import quote

from ...validators import ValidationError
from .. import _http_json
from ..base import DEFAULT_USER_AGENT, CheckResult, CheckType, truncate
from . import common


class StellarAccountCheck(CheckType):
    slug = "stellar-account"
    label = "Stellar Account"
    description = "Check a Stellar account exists and its XLM balance."
    requires_url = True
    default_config = {
        "network": common.DEFAULT_NETWORK,
        "account_id": "",
        "min_xlm_balance": 0,
    }

    def validate_config(self, config=None, app_config=None) -> dict:
        cleaned = dict(self.default_config)
        cleaned.update(config or {})
        cleaned["network"] = common.normalise_network(cleaned.get("network"))
        account_id = str(cleaned.get("account_id") or "").strip()
        if not common.is_account_id(account_id):
            raise ValidationError("account_id must be a Stellar account id (G...)")
        cleaned["account_id"] = account_id
        try:
            cleaned["min_xlm_balance"] = float(cleaned.get("min_xlm_balance", 0) or 0)
        except (TypeError, ValueError):
            raise ValidationError("min_xlm_balance must be a number") from None
        return cleaned

    def run(self, monitor, *, allow_private=False, user_agent=DEFAULT_USER_AGENT):
        config = {**self.default_config, **(monitor.type_config or {})}
        account_id = config.get("account_id")
        if not common.is_account_id(account_id):
            return CheckResult(False, None, None, "account_id is not configured")
        min_balance = float(config.get("min_xlm_balance", 0) or 0)

        target = f"{(monitor.url or '').rstrip('/')}/accounts/{quote(account_id)}"
        try:
            code, data, latency = _http_json.request_json(
                target,
                timeout=monitor.timeout_seconds,
                user_agent=user_agent,
                allow_private=allow_private,
            )
        except _http_json.HttpJsonError as exc:
            return CheckResult(False, None, None, truncate(str(exc)))

        if code == 404:
            return CheckResult(False, code, latency, f"Account {account_id} not found")
        if code != 200 or not isinstance(data, dict):
            return CheckResult(False, code, latency, truncate(f"Horizon returned HTTP {code}"))

        native = _native_balance(data)
        detail = {
            "network": config.get("network", common.DEFAULT_NETWORK),
            "account_id": account_id,
            "native_balance": native,
            "sequence": data.get("sequence"),
            "subentry_count": data.get("subentry_count"),
        }
        if native is None:
            return CheckResult(False, code, latency, "Account has no native balance", detail)
        if native < min_balance:
            return CheckResult(
                False,
                code,
                latency,
                truncate(f"XLM balance {native} below minimum {min_balance}"),
                detail,
            )
        return CheckResult(True, code, latency, detail=detail)


class StellarAssetCheck(CheckType):
    slug = "stellar-asset"
    label = "Stellar Asset"
    description = "Check a Stellar asset exists and is issued."
    requires_url = True
    default_config = {
        "network": common.DEFAULT_NETWORK,
        "asset_code": "",
        "asset_issuer": "",
    }

    def validate_config(self, config=None, app_config=None) -> dict:
        cleaned = dict(self.default_config)
        cleaned.update(config or {})
        cleaned["network"] = common.normalise_network(cleaned.get("network"))
        code = str(cleaned.get("asset_code") or "").strip().upper()
        if not 1 <= len(code) <= 12:
            raise ValidationError("asset_code must be 1-12 characters")
        cleaned["asset_code"] = code
        issuer = str(cleaned.get("asset_issuer") or "").strip()
        if not common.is_account_id(issuer):
            raise ValidationError("asset_issuer must be a Stellar account id (G...)")
        cleaned["asset_issuer"] = issuer
        return cleaned

    def run(self, monitor, *, allow_private=False, user_agent=DEFAULT_USER_AGENT):
        config = {**self.default_config, **(monitor.type_config or {})}
        asset_code = str(config.get("asset_code") or "").strip().upper()
        asset_issuer = config.get("asset_issuer")
        if not asset_code or not common.is_account_id(asset_issuer):
            return CheckResult(False, None, None, "asset_code/asset_issuer are not configured")

        target = (
            f"{(monitor.url or '').rstrip('/')}/assets"
            f"?asset_code={quote(asset_code)}&asset_issuer={quote(asset_issuer)}&limit=1"
        )
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
        detail = {
            "network": config.get("network", common.DEFAULT_NETWORK),
            "asset_code": asset_code,
            "asset_issuer": asset_issuer,
            "assets_found": len(records),
        }
        if not records:
            return CheckResult(
                False, code, latency, truncate(f"Asset {asset_code} not found"), detail
            )
        detail["amount"] = records[0].get("amount")
        detail["num_accounts"] = records[0].get("num_accounts")
        return CheckResult(True, code, latency, detail=detail)


def _native_balance(account: dict) -> float | None:
    for balance in account.get("balances", []) or []:
        if balance.get("asset_type") == "native":
            try:
                return float(balance.get("balance"))
            except (TypeError, ValueError):
                return None
    return None
