"""Stellar anchor (SEP-24 / SEP-31) check type.

The monitor URL is the anchor's home domain.  The check fetches
``/.well-known/stellar.toml``, resolves the SEP-24 transfer server and/or the
SEP-31 direct payment server, and validates their ``/info`` documents.

Only HTTPS endpoints are accepted, and every URL (including redirect targets)
goes through the shared SSRF guard.
"""

from __future__ import annotations

import re
import tomllib
from urllib.parse import urlparse

from ...validators import ValidationError, assert_public_host
from .. import _http_json
from ..base import DEFAULT_USER_AGENT, CheckResult, CheckType, truncate
from . import common

SEP24_SERVER_KEY = "TRANSFER_SERVER_SEP0024"
SEP31_SERVER_KEY = "DIRECT_PAYMENT_SERVER"
SERVICE_MODES = {"auto", "sep24", "sep31", "both"}
ASSET_CODE_RE = re.compile(r"^[A-Za-z0-9]{1,12}$")
MAX_REQUIRED_FIELDS = 20


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _clean_required_fields(value) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError("required_fields must be a list of field names")
    fields: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if not text:
            continue
        if len(text) > 64:
            raise ValidationError("required_fields entries must be at most 64 characters")
        if text not in fields:
            fields.append(text)
    if len(fields) > MAX_REQUIRED_FIELDS:
        raise ValidationError(f"required_fields supports at most {MAX_REQUIRED_FIELDS} entries")
    return fields


def _validate_target(url: str, allow_private: bool, label: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        scheme = parsed.scheme or "no scheme"
        return f"{label} must use HTTPS (got {scheme!r})"
    if not parsed.hostname:
        return f"{label} must include a hostname"
    try:
        assert_public_host(parsed.hostname, allow_private)
    except ValidationError as exc:
        return str(exc)
    return None


def _normalise_assets(service: str, data: dict) -> dict[str, dict]:
    """Return ``{code: entry}`` for a SEP-24 or SEP-31 /info document."""

    if service == "sep31":
        receive = data.get("receive")
        if not isinstance(receive, dict):
            return {}
        return {
            str(code).upper(): entry for code, entry in receive.items() if isinstance(entry, dict)
        }

    deposit = data.get("deposit")
    withdraw = data.get("withdraw")
    deposit = deposit if isinstance(deposit, dict) else {}
    withdraw = withdraw if isinstance(withdraw, dict) else {}
    assets: dict[str, dict] = {}
    for code in set(deposit) | set(withdraw):
        assets[str(code).upper()] = {
            "deposit": deposit.get(code),
            "withdraw": withdraw.get(code),
        }
    return assets


def _asset_enabled(service: str, entry: dict, side: str) -> bool:
    if service == "sep31":
        return bool(entry.get("enabled"))
    section = entry.get(side)
    return isinstance(section, dict) and bool(section.get("enabled"))


def _asset_summary(service: str, entry: dict) -> dict:
    if service == "sep31":
        return {"receive": _asset_enabled(service, entry, "receive")}
    return {
        "deposit": _asset_enabled(service, entry, "deposit"),
        "withdraw": _asset_enabled(service, entry, "withdraw"),
    }


def _field_sides(
    service: str, entry: dict, require_deposit: bool, require_withdraw: bool
) -> list[tuple[str, dict]]:
    if service == "sep31":
        return [("receive", entry)]

    sides: list[tuple[str, dict]] = []
    if require_deposit:
        side = entry.get("deposit")
        sides.append(("deposit", side if isinstance(side, dict) else {}))
    if require_withdraw:
        side = entry.get("withdraw")
        sides.append(("withdraw", side if isinstance(side, dict) else {}))
    if not sides:
        for name in ("deposit", "withdraw"):
            side = entry.get(name)
            if isinstance(side, dict):
                sides.append((name, side))
    return sides


def _validate_requirements(
    service: str,
    assets: dict[str, dict],
    *,
    asset_code: str,
    require_deposit: bool,
    require_withdraw: bool,
    required_fields: list[str],
) -> str | None:
    label = service.upper()

    if asset_code:
        if asset_code not in assets:
            return f"Asset {asset_code} is not offered by {label}"
        candidates = {asset_code: assets[asset_code]}
    else:
        candidates = assets

    if asset_code and not require_deposit and not require_withdraw:
        entry = candidates[asset_code]
        if not any(_asset_enabled(service, entry, side) for side in ("deposit", "withdraw")):
            return f"Asset {asset_code} is disabled on {label}"

    if require_deposit:
        enabled = [
            code for code, entry in candidates.items() if _asset_enabled(service, entry, "deposit")
        ]
        if not enabled:
            if asset_code:
                return f"Asset {asset_code} has deposit disabled on {label}"
            return f"No deposit-enabled asset is offered by {label}"

    if require_withdraw:
        enabled = [
            code for code, entry in candidates.items() if _asset_enabled(service, entry, "withdraw")
        ]
        if not enabled:
            if asset_code:
                return f"Asset {asset_code} has withdrawal disabled on {label}"
            return f"No withdrawal-enabled asset is offered by {label}"

    if required_fields:
        if asset_code:
            for side_name, side in _field_sides(
                service, candidates[asset_code], require_deposit, require_withdraw
            ):
                missing = [field for field in required_fields if field not in side]
                if missing:
                    return (
                        f"Asset {asset_code} {side_name} info on {label} is missing "
                        f"fields: {', '.join(missing)}"
                    )
        else:
            satisfied = False
            for entry in candidates.values():
                sides = _field_sides(service, entry, require_deposit, require_withdraw)
                if sides and all(
                    all(field in side for field in required_fields) for _, side in sides
                ):
                    satisfied = True
                    break
            if not satisfied:
                return (
                    f"No asset on {label} exposes all required fields: {', '.join(required_fields)}"
                )

    return None


class StellarAnchorCheck(CheckType):
    slug = "stellar-anchor"
    label = "Stellar Anchor (SEP-24/SEP-31)"
    description = "Check an anchor's stellar.toml and SEP-24/SEP-31 info endpoints."
    requires_url = True
    help_text = (
        "URL is the anchor home domain (HTTPS only). Options: services "
        "(auto|sep24|sep31|both), asset_code, require_deposit, "
        "require_withdraw (SEP-24 only), and required_fields (list of /info "
        "field names that must be present)."
    )
    default_config = {
        "network": common.DEFAULT_NETWORK,
        "services": "auto",
        "asset_code": "",
        "require_deposit": False,
        "require_withdraw": False,
        "required_fields": [],
    }

    def validate_config(self, config=None, app_config=None) -> dict:
        cleaned = dict(self.default_config)
        cleaned.update(config or {})
        cleaned["network"] = common.normalise_network(cleaned.get("network"))

        services = str(cleaned.get("services") or "auto").strip().lower()
        if services not in SERVICE_MODES:
            allowed = ", ".join(sorted(SERVICE_MODES))
            raise ValidationError(f"services must be one of: {allowed}")
        cleaned["services"] = services

        asset_code = str(cleaned.get("asset_code") or "").strip().upper()
        if asset_code and not ASSET_CODE_RE.match(asset_code):
            raise ValidationError("asset_code must be 1-12 letters or digits")
        cleaned["asset_code"] = asset_code

        cleaned["require_deposit"] = _truthy(cleaned.get("require_deposit"))
        cleaned["require_withdraw"] = _truthy(cleaned.get("require_withdraw"))
        if cleaned["require_withdraw"] and services == "sep31":
            raise ValidationError("require_withdraw requires a SEP-24 service")
        cleaned["required_fields"] = _clean_required_fields(cleaned.get("required_fields"))
        return cleaned

    def run(self, monitor, *, allow_private=False, user_agent=DEFAULT_USER_AGENT):
        config = {**self.default_config, **(monitor.type_config or {})}
        services = str(config.get("services") or "auto").strip().lower()
        if services not in SERVICE_MODES:
            services = "auto"
        asset_code = str(config.get("asset_code") or "").strip().upper()
        require_deposit = _truthy(config.get("require_deposit"))
        require_withdraw = _truthy(config.get("require_withdraw"))
        try:
            required_fields = _clean_required_fields(config.get("required_fields"))
        except ValidationError as exc:
            return CheckResult(False, None, None, truncate(str(exc)))

        timeout = monitor.timeout_seconds
        base = (monitor.url or "").rstrip("/")
        error = _validate_target(base, allow_private, "Anchor home domain")
        if error:
            return CheckResult(False, None, None, truncate(error))

        toml_url = f"{base}/.well-known/stellar.toml"
        try:
            code, text, latency = _http_json.request_text(
                toml_url,
                timeout=timeout,
                user_agent=user_agent,
                allow_private=allow_private,
                require_https=True,
            )
        except _http_json.HttpJsonError as exc:
            return CheckResult(False, None, None, truncate(str(exc)))

        if code != 200:
            return CheckResult(False, code, latency, truncate(f"stellar.toml returned HTTP {code}"))
        try:
            document = tomllib.loads(text or "")
        except tomllib.TOMLDecodeError as exc:
            return CheckResult(False, code, latency, truncate(f"invalid stellar.toml: {exc}"))

        sep24_server = document.get(SEP24_SERVER_KEY)
        sep31_server = document.get(SEP31_SERVER_KEY)
        sep24_server = sep24_server.strip() if isinstance(sep24_server, str) else ""
        sep31_server = sep31_server.strip() if isinstance(sep31_server, str) else ""

        selected: dict[str, str] = {}
        if services in ("auto", "sep24", "both"):
            if sep24_server:
                selected["sep24"] = sep24_server
            elif services != "auto":
                return CheckResult(
                    False,
                    code,
                    latency,
                    truncate(f"stellar.toml is missing {SEP24_SERVER_KEY}"),
                )
        if services in ("auto", "sep31", "both"):
            if sep31_server:
                selected["sep31"] = sep31_server
            elif services != "auto":
                return CheckResult(
                    False,
                    code,
                    latency,
                    truncate(f"stellar.toml is missing {SEP31_SERVER_KEY}"),
                )

        if not selected:
            return CheckResult(
                False,
                code,
                latency,
                truncate("stellar.toml has no TRANSFER_SERVER_SEP0024 or DIRECT_PAYMENT_SERVER"),
            )
        if require_withdraw and "sep24" not in selected:
            return CheckResult(
                False,
                code,
                latency,
                truncate("require_withdraw needs a SEP-24 transfer server"),
            )

        for service, server in selected.items():
            error = _validate_target(server, allow_private, f"{service.upper()} server")
            if error:
                return CheckResult(False, code, latency, truncate(error))

        detail = {
            "network": config.get("network", common.DEFAULT_NETWORK),
            "home_domain": base,
            "services": {},
            "assets": {},
        }
        total_latency = latency or 0.0

        for service, server in selected.items():
            label = service.upper()
            info_url = f"{server.rstrip('/')}/{service}/info"
            try:
                code, data, info_latency = _http_json.request_json(
                    info_url,
                    timeout=timeout,
                    user_agent=user_agent,
                    allow_private=allow_private,
                    require_https=True,
                )
            except _http_json.HttpJsonError as exc:
                return CheckResult(False, None, total_latency, truncate(f"{label} info: {exc}"))
            total_latency = round(total_latency + (info_latency or 0.0), 2)

            if code != 200:
                return CheckResult(
                    False,
                    code,
                    total_latency,
                    truncate(f"{label} info returned HTTP {code}"),
                    detail,
                )
            if not isinstance(data, dict):
                return CheckResult(
                    False,
                    code,
                    total_latency,
                    truncate(f"{label} info did not return a JSON object"),
                    detail,
                )

            assets = _normalise_assets(service, data)
            if not assets:
                return CheckResult(
                    False,
                    code,
                    total_latency,
                    truncate(f"{label} info exposed no assets"),
                    detail,
                )

            error = _validate_requirements(
                service,
                assets,
                asset_code=asset_code,
                require_deposit=require_deposit,
                require_withdraw=require_withdraw,
                required_fields=required_fields,
            )
            if error:
                return CheckResult(False, code, total_latency, truncate(error), detail)

            detail["services"][service] = {
                "url": server,
                "assets": sorted(assets),
            }
            detail["assets"][service] = {
                asset: _asset_summary(service, entry) for asset, entry in sorted(assets.items())
            }

        return CheckResult(True, code, total_latency, detail=detail)
