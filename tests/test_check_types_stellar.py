"""Tests for the Stellar / Soroban check types (network calls are mocked)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from primus.services.check_types import available_types, get_check_type
from primus.services.check_types.stellar import common
from primus.services.validators import ValidationError, validate_monitor_payload

REQUEST_JSON = "primus.services.check_types._http_json.request_json"
JSON_RPC = "primus.services.check_types._http_json.json_rpc"

ACCOUNT_ID = "G" + "A" * 55
CONTRACT_ID = "C" + "A" * 55
ISSUER_ID = "G" + "B" * 55


def now_iso(offset_seconds: int = 0) -> str:
    return (datetime.now(UTC) + timedelta(seconds=offset_seconds)).isoformat()


def make_monitor(**overrides):
    values = {
        "type": "stellar-horizon",
        "url": "https://horizon.stellar.org",
        "timeout_seconds": 5,
        "type_config": {},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def fake_request_json(code, data, latency=4.0):
    def _fake(*args, **kwargs):
        return code, data, latency

    return _fake


# -- registry ---------------------------------------------------------------
def test_stellar_types_are_registered():
    slugs = {check_type.slug for check_type in available_types()}
    assert {
        "stellar-horizon",
        "soroban-rpc",
        "soroban-contract",
        "stellar-account",
        "stellar-asset",
    } <= slugs


# -- Horizon ----------------------------------------------------------------
def test_horizon_success(monkeypatch):
    data = {
        "_embedded": {
            "records": [{"sequence": 100, "closed_at": now_iso(), "protocol_version": 20}]
        }
    }
    monkeypatch.setattr(REQUEST_JSON, fake_request_json(200, data))
    result = get_check_type("stellar-horizon").run(make_monitor(), allow_private=True)
    assert result.success
    assert result.detail["latest_ledger"] == 100
    assert result.detail["ledger_lag_seconds"] is not None


def test_horizon_stale_ledger_fails(monkeypatch):
    data = {"_embedded": {"records": [{"sequence": 9, "closed_at": now_iso(-600)}]}}
    monkeypatch.setattr(REQUEST_JSON, fake_request_json(200, data))
    monitor = make_monitor(type_config={"max_ledger_lag_seconds": 30})
    result = get_check_type("stellar-horizon").run(monitor, allow_private=True)
    assert not result.success
    assert "lag" in result.error.lower()


def test_horizon_http_error_fails(monkeypatch):
    monkeypatch.setattr(REQUEST_JSON, fake_request_json(503, None))
    result = get_check_type("stellar-horizon").run(make_monitor(), allow_private=True)
    assert not result.success


def test_horizon_no_ledgers_fails(monkeypatch):
    monkeypatch.setattr(REQUEST_JSON, fake_request_json(200, {"_embedded": {"records": []}}))
    result = get_check_type("stellar-horizon").run(make_monitor(), allow_private=True)
    assert not result.success
    assert "no ledgers" in result.error.lower()


# -- Soroban RPC ------------------------------------------------------------
def _rpc_stub(latest, health=None, network=None):
    def _fake(url, method, params=None, **kwargs):
        if method == "getLatestLedger":
            return latest, None, 5.0
        if method == "getHealth":
            return health, None, 5.0
        if method == "getNetwork":
            return network, None, 5.0
        raise AssertionError(f"unexpected method {method}")

    return _fake


def test_soroban_rpc_success(monkeypatch):
    stub = _rpc_stub(
        {"sequence": 1000, "protocolVersion": 20, "closeTime": now_iso()},
        {"status": "healthy", "latestLedger": 1000},
        {"passphrase": common.NETWORKS["testnet"]["passphrase"]},
    )
    monkeypatch.setattr(JSON_RPC, stub)
    monitor = make_monitor(type="soroban-rpc", type_config={"network": "testnet"})
    result = get_check_type("soroban-rpc").run(monitor, allow_private=True)
    assert result.success
    assert result.detail["latest_ledger"] == 1000


def test_soroban_rpc_unhealthy_fails(monkeypatch):
    stub = _rpc_stub(
        {"sequence": 10, "closeTime": now_iso()},
        {"status": "unhealthy"},
        {"passphrase": common.NETWORKS["mainnet"]["passphrase"]},
    )
    monkeypatch.setattr(JSON_RPC, stub)
    result = get_check_type("soroban-rpc").run(make_monitor(type="soroban-rpc"), allow_private=True)
    assert not result.success


def test_soroban_rpc_passphrase_mismatch_fails(monkeypatch):
    stub = _rpc_stub(
        {"sequence": 10, "closeTime": now_iso()},
        {"status": "healthy"},
        {"passphrase": "some-other-network"},
    )
    monkeypatch.setattr(JSON_RPC, stub)
    result = get_check_type("soroban-rpc").run(make_monitor(type="soroban-rpc"), allow_private=True)
    assert not result.success
    assert "passphrase" in result.error.lower()


def test_soroban_rpc_transport_error_fails(monkeypatch):
    def _fake(url, method, params=None, **kwargs):
        return None, "connection refused", 0.0

    monkeypatch.setattr(JSON_RPC, _fake)
    result = get_check_type("soroban-rpc").run(make_monitor(type="soroban-rpc"), allow_private=True)
    assert not result.success


# -- Soroban contract -------------------------------------------------------
def test_soroban_contract_success(monkeypatch):
    def _fake(url, method, params=None, **kwargs):
        if method == "getLatestLedger":
            return {"sequence": 5000}, None, 5.0
        if method == "getEvents":
            assert params["filters"][0]["contractIds"] == [CONTRACT_ID]
            return {"events": [{"id": "1"}], "latestLedger": 5000}, None, 5.0
        raise AssertionError(method)

    monkeypatch.setattr(JSON_RPC, _fake)
    monitor = make_monitor(type="soroban-contract", type_config={"contract_id": CONTRACT_ID})
    result = get_check_type("soroban-contract").run(monitor, allow_private=True)
    assert result.success
    assert result.detail["events_found"] == 1


def test_soroban_contract_expect_events_fails_when_empty(monkeypatch):
    def _fake(url, method, params=None, **kwargs):
        if method == "getLatestLedger":
            return {"sequence": 5000}, None, 5.0
        return {"events": [], "latestLedger": 5000}, None, 5.0

    monkeypatch.setattr(JSON_RPC, _fake)
    monitor = make_monitor(
        type="soroban-contract",
        type_config={"contract_id": CONTRACT_ID, "expect_events": True},
    )
    result = get_check_type("soroban-contract").run(monitor, allow_private=True)
    assert not result.success
    assert "no events" in result.error.lower()


# -- Account / asset --------------------------------------------------------
def test_account_success(monkeypatch):
    data = {
        "balances": [{"asset_type": "native", "balance": "50.0000000"}],
        "sequence": "12",
        "subentry_count": 0,
    }
    monkeypatch.setattr(REQUEST_JSON, fake_request_json(200, data))
    monitor = make_monitor(type="stellar-account", type_config={"account_id": ACCOUNT_ID})
    result = get_check_type("stellar-account").run(monitor, allow_private=True)
    assert result.success
    assert result.detail["native_balance"] == 50.0


def test_account_below_minimum_fails(monkeypatch):
    data = {"balances": [{"asset_type": "native", "balance": "5.0"}]}
    monkeypatch.setattr(REQUEST_JSON, fake_request_json(200, data))
    monitor = make_monitor(
        type="stellar-account",
        type_config={"account_id": ACCOUNT_ID, "min_xlm_balance": 10},
    )
    result = get_check_type("stellar-account").run(monitor, allow_private=True)
    assert not result.success


def test_account_not_found(monkeypatch):
    monkeypatch.setattr(REQUEST_JSON, fake_request_json(404, None))
    monitor = make_monitor(type="stellar-account", type_config={"account_id": ACCOUNT_ID})
    result = get_check_type("stellar-account").run(monitor, allow_private=True)
    assert not result.success
    assert "not found" in result.error.lower()


def test_asset_success(monkeypatch):
    data = {"_embedded": {"records": [{"amount": "1000.0", "num_accounts": 5}]}}
    monkeypatch.setattr(REQUEST_JSON, fake_request_json(200, data))
    monitor = make_monitor(
        type="stellar-asset",
        type_config={"asset_code": "usdc", "asset_issuer": ISSUER_ID},
    )
    result = get_check_type("stellar-asset").run(monitor, allow_private=True)
    assert result.success
    assert result.detail["asset_code"] == "USDC"


# -- validation -------------------------------------------------------------
def test_validate_horizon_config(app):
    cleaned = validate_monitor_payload(
        {
            "name": "Stellar",
            "url": "https://horizon.stellar.org",
            "type": "stellar-horizon",
            "type_config": {"network": "testnet"},
        },
        app.config,
    )
    assert cleaned["type"] == "stellar-horizon"
    assert cleaned["type_config"]["network"] == "testnet"
    assert cleaned["type_config"]["max_ledger_lag_seconds"] == 30


def test_validate_rejects_bad_network(app):
    with pytest.raises(ValidationError):
        validate_monitor_payload(
            {
                "name": "x",
                "url": "https://h.example.com",
                "type": "stellar-horizon",
                "type_config": {"network": "regtest"},
            },
            app.config,
        )


def test_validate_rejects_bad_contract_id(app):
    with pytest.raises(ValidationError):
        validate_monitor_payload(
            {
                "name": "x",
                "url": "https://rpc.example.com",
                "type": "soroban-contract",
                "type_config": {"contract_id": "nope"},
            },
            app.config,
        )


def test_validate_rejects_bad_account_id(app):
    with pytest.raises(ValidationError):
        validate_monitor_payload(
            {
                "name": "x",
                "url": "https://h.example.com",
                "type": "stellar-account",
                "type_config": {"account_id": "nope"},
            },
            app.config,
        )


def test_api_creates_stellar_monitor(client, api_headers):
    response = client.post(
        "/api/monitors",
        json={
            "name": "Stellar Horizon",
            "url": "https://horizon-testnet.stellar.org",
            "type": "stellar-horizon",
            "type_config": {"network": "testnet"},
            "interval_seconds": 60,
        },
        headers=api_headers,
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["type"] == "stellar-horizon"
    assert body["type_config"]["network"] == "testnet"
