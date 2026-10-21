"""Offline tests for the on-chain registry publisher.

No test performs a network call: the Soroban RPC client is a small fake and
keys are generated in-process.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from stellar_sdk import Account, Address, Keypair, StrKey, scval
from stellar_sdk.soroban_rpc import SendTransactionStatus

from primus.models import Check, Monitor, utcnow
from primus.services import registry
from primus.services.registry import (
    PublishResult,
    RegistryNotConfigured,
    RegistryPublisher,
    RegistrySettings,
    RegistrySubmissionError,
    RegistryValidationError,
    ReportPayload,
    build_report_payload,
    load_settings,
    monitor_symbol,
    normalise_latency,
    report_arguments,
)

CONTRACT_ID = StrKey.encode_contract(b"\x01" * 32)
TX_HASH = "a" * 64


class FakeClient:
    def __init__(self, public_key, *, simulation_error=None, send_status="PENDING"):
        self.account = Account(public_key, 1)
        self.simulation_error = simulation_error
        self.send_status = send_status
        self.loaded_account_id = None
        self.simulated = None
        self.prepared = None
        self.sent = None
        self.error_result_xdr = None
        self.simulation_exception = None

    def load_account(self, account_id):
        self.loaded_account_id = account_id
        return self.account

    def simulate_transaction(self, transaction_envelope):
        self.simulated = transaction_envelope
        if self.simulation_exception is not None:
            raise self.simulation_exception
        return SimpleNamespace(error=self.simulation_error)

    def prepare_transaction(self, transaction_envelope, response=None):
        self.prepared = transaction_envelope
        return transaction_envelope

    def send_transaction(self, transaction_envelope):
        self.sent = transaction_envelope
        return SimpleNamespace(
            status=self.send_status,
            hash=TX_HASH,
            error_result_xdr=self.error_result_xdr,
        )

    def poll_transaction(self, transaction_hash, **kwargs):
        return SimpleNamespace(status="SUCCESS", ledger=123)


def make_publisher(client, secret=None):
    secret = secret or Keypair.random().secret
    settings = RegistrySettings(
        contract_id=CONTRACT_ID,
        secret_key=secret,
        network="testnet",
    )
    return RegistryPublisher(settings, client=client)


def test_report_arguments_match_contract_signature():
    signer = Keypair.random()
    args = report_arguments(signer.public_key, ReportPayload("monitor_7", True, 42))

    assert scval.from_address(args[0]).address == signer.public_key
    assert scval.from_symbol(args[1]) == "monitor_7"
    assert scval.from_bool(args[2]) is True
    assert scval.from_uint32(args[3]) == 42


def test_build_transaction_invokes_report_on_contract():
    signer = Keypair.random()
    client = FakeClient(signer.public_key)
    publisher = make_publisher(client, signer.secret)

    transaction = publisher.build_transaction(ReportPayload("7", False, 12))
    operation = transaction.transaction.operations[0]
    invocation = operation.host_function.invoke_contract

    assert client.loaded_account_id == signer.public_key
    assert Address.from_xdr_sc_address(invocation.contract_address).address == CONTRACT_ID
    assert invocation.function_name.sc_symbol == b"report"
    assert scval.from_symbol(invocation.args[1]) == "7"
    assert scval.from_bool(invocation.args[2]) is False
    assert scval.from_uint32(invocation.args[3]) == 12


def test_happy_path_signs_and_submits():
    signer = Keypair.random()
    client = FakeClient(signer.public_key)
    publisher = make_publisher(client, signer.secret)

    result = publisher.publish(payload=ReportPayload("7", True, 12))

    assert result == PublishResult(tx_hash=TX_HASH, status="PENDING")
    assert client.simulated is not None
    assert client.prepared is not None
    assert client.sent is not None
    assert len(client.sent.signatures) == 1


def test_wait_polls_for_confirmation():
    signer = Keypair.random()
    client = FakeClient(signer.public_key)
    publisher = make_publisher(client, signer.secret)

    result = publisher.publish(payload=ReportPayload("7", True, 12), wait=True)

    assert result.status == "SUCCESS"
    assert result.ledger == 123


def test_payload_uses_latest_check_and_normalises_latency():
    monitor = SimpleNamespace(
        id=7,
        last_status="up",
        last_latency_ms=10.0,
    )
    check = SimpleNamespace(success=False, latency_ms=-4.6)

    payload = build_report_payload(monitor, check)

    assert payload == ReportPayload(monitor_id="7", up=False, latency_ms=0)


def test_payload_falls_back_to_monitor_fields():
    monitor = SimpleNamespace(id=9, last_status="up", last_latency_ms=5.4)

    assert build_report_payload(monitor) == ReportPayload("9", True, 5)


def test_monitor_symbol_validation_and_latency_bounds():
    assert monitor_symbol(12) == "12"
    assert normalise_latency(None) == 0
    assert normalise_latency(float("nan")) == 0
    assert normalise_latency(2**40) == registry.MAX_LATENCY_MS
    with pytest.raises(RegistryValidationError):
        monitor_symbol("bad-symbol")
    with pytest.raises(RegistryValidationError):
        monitor_symbol("")


def test_unconfigured_publisher_fails_cleanly(monkeypatch):
    for name in (
        "PRIMUS_REGISTRY_CONTRACT_ID",
        "PRIMUS_REGISTRY_SECRET_KEY",
        "PRIMUS_REGISTRY_NETWORK",
        "PRIMUS_REGISTRY_RPC_URL",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = load_settings({})
    with pytest.raises(RegistryNotConfigured) as excinfo:
        RegistryPublisher(settings)

    message = str(excinfo.value)
    assert "PRIMUS_REGISTRY_CONTRACT_ID" in message
    assert "PRIMUS_REGISTRY_SECRET_KEY" in message


def test_invalid_network_is_rejected():
    with pytest.raises(RegistryValidationError):
        load_settings({"PRIMUS_REGISTRY_NETWORK": "regtest"})


def test_invalid_secret_is_rejected_without_leaking_it():
    settings = RegistrySettings(
        contract_id=CONTRACT_ID,
        secret_key="S" + "A" * 55,
        network="testnet",
    )
    with pytest.raises(RegistryValidationError) as excinfo:
        RegistryPublisher(settings, client=FakeClient(Keypair.random().public_key))

    assert settings.secret_key not in str(excinfo.value)
    assert "PRIMUS_REGISTRY_SECRET_KEY" in str(excinfo.value)


def test_simulation_error_is_mapped():
    signer = Keypair.random()
    client = FakeClient(signer.public_key, simulation_error="HostError: trapped")
    publisher = make_publisher(client, signer.secret)

    with pytest.raises(RegistrySubmissionError, match="simulation failed"):
        publisher.publish(payload=ReportPayload("7", True, 1))


def test_send_error_is_mapped():
    signer = Keypair.random()
    client = FakeClient(signer.public_key, send_status=SendTransactionStatus.ERROR)
    client.error_result_xdr = "AAAAAAAA"
    publisher = make_publisher(client, signer.secret)

    with pytest.raises(RegistrySubmissionError, match="submission failed"):
        publisher.publish(payload=ReportPayload("7", True, 1))


def test_transport_failure_redacts_secret():
    signer = Keypair.random()
    client = FakeClient(signer.public_key)
    client.simulation_exception = RuntimeError(f"transport exploded with {signer.secret}")
    publisher = make_publisher(client, signer.secret)

    with pytest.raises(RegistrySubmissionError) as excinfo:
        publisher.publish(payload=ReportPayload("7", True, 1))

    assert signer.secret not in str(excinfo.value)
    assert "***" in str(excinfo.value)


def test_publish_monitor_status_loads_latest_check(app, db, user):
    monitor = Monitor(user_id=user.id, name="registry", url="https://example.com")
    db.session.add(monitor)
    db.session.commit()
    db.session.add(
        Check(
            monitor_id=monitor.id,
            success=True,
            latency_ms=25.0,
            checked_at=utcnow(),
        )
    )
    db.session.commit()

    captured = {}

    class FakePublisher:
        def publish_status(self, monitor, check, wait=False):
            captured["monitor"] = monitor
            captured["check"] = check
            return TX_HASH

    tx_hash = registry.publish_monitor_status(monitor, publisher=FakePublisher())

    assert tx_hash == TX_HASH
    assert captured["check"].success is True
    assert captured["check"].latency_ms == 25.0


def test_cli_publish_status_returns_tx_hash(app, db, user, monkeypatch):
    monitor = Monitor(user_id=user.id, name="registry", url="https://example.com")
    db.session.add(monitor)
    db.session.commit()

    seen = {}

    def fake_publish(monitor_obj, config=None, **kwargs):
        seen["monitor_id"] = monitor_obj.id
        return TX_HASH

    monkeypatch.setattr(registry, "publish_monitor_status", fake_publish)

    result = app.test_cli_runner().invoke(
        args=["primus", "publish-status", "--monitor-id", str(monitor.id)]
    )

    assert result.exit_code == 0
    assert TX_HASH in result.output
    assert seen["monitor_id"] == monitor.id


def test_cli_publish_status_unknown_monitor(app, db):
    result = app.test_cli_runner().invoke(
        args=["primus", "publish-status", "--monitor-id", "99999"]
    )

    assert result.exit_code != 0
    assert "not found" in result.output.lower()
