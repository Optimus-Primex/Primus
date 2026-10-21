"""Publish monitor status to the on-chain Primus registry.

The Soroban contract in ``contracts/primus-registry`` exposes::

    report(reporter: Address, monitor_id: Symbol, up: bool, latency_ms: u32)

This module builds the matching ``invokeHostFunction`` transaction, simulates
it through Soroban RPC, signs it with the configured signer and submits it.

The signer secret is read from configuration and never logged.  Failures are
mapped to :class:`RegistryError` subclasses with redacted messages, and the
Soroban RPC client is injectable so the publisher can be tested without any
network access.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..models import STATUS_UP, Check, Monitor
from .check_types.stellar import common

BASE_FEE = 100
DEFAULT_NETWORK = "testnet"
DEFAULT_TIMEOUT_SECONDS = 60
MAX_LATENCY_MS = 2**32 - 1
MONITOR_SYMBOL_PATTERN = r"^[A-Za-z0-9_]{1,32}$"

_NETWORKS = {"testnet", "mainnet"}
_REDACTION = "***"


class RegistryError(RuntimeError):
    """Base class for registry publishing failures."""


class RegistryNotConfigured(RegistryError):
    """The publisher is missing required configuration."""


class RegistryValidationError(RegistryError):
    """A configured value or monitor payload is invalid."""


class RegistrySubmissionError(RegistryError):
    """Simulation, signing or submission failed."""


class SorobanClient(Protocol):
    """The subset of :class:`stellar_sdk.SorobanServer` used by the publisher."""

    def load_account(self, account_id: str) -> Any: ...

    def simulate_transaction(self, transaction_envelope: Any) -> Any: ...

    def prepare_transaction(
        self, transaction_envelope: Any, response: Any | None = None
    ) -> Any: ...

    def send_transaction(self, transaction_envelope: Any) -> Any: ...

    def poll_transaction(self, transaction_hash: str, **kwargs: Any) -> Any: ...


@dataclass(frozen=True)
class RegistrySettings:
    """Resolved registry configuration.

    ``secret_key`` is excluded from ``repr`` so accidental logging of the
    settings object cannot leak the signer key.
    """

    contract_id: str = ""
    secret_key: str = field(default="", repr=False)
    network: str = DEFAULT_NETWORK
    rpc_url: str = ""

    def missing(self) -> list[str]:
        missing = []
        if not self.contract_id:
            missing.append("PRIMUS_REGISTRY_CONTRACT_ID")
        if not self.secret_key:
            missing.append("PRIMUS_REGISTRY_SECRET_KEY")
        return missing

    @property
    def network_passphrase(self) -> str:
        return common.NETWORKS[self.network]["passphrase"]

    def __repr__(self) -> str:
        return (
            f"RegistrySettings(contract_id={self.contract_id!r}, "
            f"network={self.network!r}, rpc_url={self.rpc_url!r})"
        )


@dataclass(frozen=True)
class ReportPayload:
    """The values passed to the registry's ``report`` function."""

    monitor_id: str
    up: bool
    latency_ms: int


@dataclass(frozen=True)
class PublishResult:
    """Outcome of a submitted registry transaction."""

    tx_hash: str
    status: str = "PENDING"
    ledger: int | None = None


def _clean(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def load_settings(config: Any = None) -> RegistrySettings:
    """Load settings from Flask config, falling back to environment variables."""

    mapping = config if config is not None else os.environ

    def get(flask_key: str, env_key: str, default: str = "") -> str:
        value = mapping.get(flask_key) if hasattr(mapping, "get") else None
        if value is None:
            value = os.environ.get(env_key, default)
        return _clean(value)

    network = get("PRIMUS_REGISTRY_NETWORK", "PRIMUS_REGISTRY_NETWORK", DEFAULT_NETWORK).lower()
    if network not in _NETWORKS:
        allowed = ", ".join(sorted(_NETWORKS))
        raise RegistryValidationError(f"PRIMUS_REGISTRY_NETWORK must be one of: {allowed}")

    contract_id = get("PRIMUS_REGISTRY_CONTRACT_ID", "PRIMUS_REGISTRY_CONTRACT_ID")
    rpc_url = get("PRIMUS_REGISTRY_RPC_URL", "PRIMUS_REGISTRY_RPC_URL")
    if not rpc_url:
        rpc_url = common.NETWORKS[network]["rpc"]

    return RegistrySettings(
        contract_id=contract_id,
        secret_key=get("PRIMUS_REGISTRY_SECRET_KEY", "PRIMUS_REGISTRY_SECRET_KEY"),
        network=network,
        rpc_url=rpc_url,
    )


def monitor_symbol(monitor_id: Any) -> str:
    """Convert a monitor id to a valid Soroban ``Symbol`` value."""

    symbol = _clean(monitor_id)
    if not symbol:
        raise RegistryValidationError("monitor id must not be empty")
    if not re.match(MONITOR_SYMBOL_PATTERN, symbol):
        raise RegistryValidationError(
            "monitor id must be 1-32 characters of letters, digits or underscores"
        )
    return symbol


def normalise_latency(value: Any) -> int:
    """Round a latency to a non-negative ``u32``, treating bad input as zero."""

    try:
        latency = int(round(float(value)))
    except (TypeError, ValueError, OverflowError):
        latency = 0
    return max(0, min(latency, MAX_LATENCY_MS))


def build_report_payload(monitor: Monitor, check: Check | None = None) -> ReportPayload:
    """Build the on-chain payload from a monitor and its latest check.

    ``check`` is the latest stored result.  When it is omitted the monitor's
    denormalised ``last_status`` / ``last_latency_ms`` fields are used.
    """

    if check is not None:
        up = bool(check.success)
        latency = check.latency_ms if check.latency_ms is not None else monitor.last_latency_ms
    else:
        up = getattr(monitor, "last_status", None) == STATUS_UP
        latency = getattr(monitor, "last_latency_ms", None)
    return ReportPayload(
        monitor_id=monitor_symbol(getattr(monitor, "id", "")),
        up=up,
        latency_ms=normalise_latency(latency),
    )


def report_arguments(reporter: str, payload: ReportPayload) -> list[Any]:
    """Return the SCVal arguments for the contract's ``report`` function."""

    from stellar_sdk import Address, scval

    return [
        Address(reporter).to_xdr_sc_val(),
        scval.to_symbol(payload.monitor_id),
        scval.to_bool(payload.up),
        scval.to_uint32(payload.latency_ms),
    ]


def _redact(message: Any, secret: str) -> str:
    text = str(message)
    if secret:
        text = text.replace(secret, _REDACTION)
    return text


class RegistryPublisher:
    """Build, simulate, sign and submit registry status updates."""

    def __init__(
        self,
        settings: RegistrySettings,
        *,
        client: SorobanClient | None = None,
        keypair: Any | None = None,
    ):
        missing = settings.missing()
        if missing:
            raise RegistryNotConfigured(
                "registry publisher is not configured; set " + ", ".join(missing)
            )
        if not common.is_contract_id(settings.contract_id):
            raise RegistryValidationError(
                "PRIMUS_REGISTRY_CONTRACT_ID must be a Soroban contract id (C...)"
            )

        from stellar_sdk import Keypair, SorobanServer

        self.settings = settings
        try:
            self._keypair = keypair or Keypair.from_secret(settings.secret_key)
        except Exception:  # noqa: BLE001 - SDK raises several types
            raise RegistryValidationError(
                "PRIMUS_REGISTRY_SECRET_KEY is not a valid Stellar secret key"
            ) from None
        self._client = client or SorobanServer(settings.rpc_url)

    @classmethod
    def from_config(
        cls,
        config: Any = None,
        *,
        client: SorobanClient | None = None,
        keypair: Any | None = None,
    ) -> RegistryPublisher:
        return cls(load_settings(config), client=client, keypair=keypair)

    @property
    def reporter(self) -> str:
        return self._keypair.public_key

    @property
    def client(self) -> SorobanClient:
        return self._client

    def build_transaction(self, payload: ReportPayload) -> Any:
        """Build the unsigned Soroban transaction for ``payload``."""

        from stellar_sdk import TransactionBuilder

        account = self._client.load_account(self.reporter)
        builder = TransactionBuilder(
            source_account=account,
            network_passphrase=self.settings.network_passphrase,
            base_fee=BASE_FEE,
        )
        builder.append_invoke_contract_function_op(
            contract_id=self.settings.contract_id,
            function_name="report",
            parameters=report_arguments(self.reporter, payload),
        )
        builder.set_timeout(DEFAULT_TIMEOUT_SECONDS)
        return builder.build()

    def publish(
        self,
        monitor: Monitor | None = None,
        check: Check | None = None,
        *,
        payload: ReportPayload | None = None,
        wait: bool = False,
    ) -> PublishResult:
        """Publish a monitor status and return the submitted transaction hash."""

        if payload is None:
            if monitor is None:
                raise RegistryValidationError("monitor or payload is required")
            payload = build_report_payload(monitor, check)

        from stellar_sdk.soroban_rpc import SendTransactionStatus

        secret = self.settings.secret_key
        try:
            transaction = self.build_transaction(payload)
            simulation = self._client.simulate_transaction(transaction)
            simulation_error = getattr(simulation, "error", None)
            if simulation_error:
                raise RegistrySubmissionError(
                    f"simulation failed: {_redact(simulation_error, secret)}"
                )

            prepared = self._client.prepare_transaction(transaction, simulation)
            prepared.sign(self._keypair)
            response = self._client.send_transaction(prepared)
        except RegistryError:
            raise
        except Exception as exc:  # noqa: BLE001 - sanitise SDK/transport failures
            raise RegistrySubmissionError(
                f"registry submission failed: {_redact(exc, secret)}"
            ) from None

        status = getattr(response, "status", "")
        status_text = getattr(status, "value", str(status))
        tx_hash = str(getattr(response, "hash", "") or "")
        if status_text == SendTransactionStatus.ERROR.value:
            detail = getattr(response, "error_result_xdr", None) or "transaction rejected"
            raise RegistrySubmissionError(f"registry submission failed: {_redact(detail, secret)}")
        if status_text == SendTransactionStatus.TRY_AGAIN_LATER.value:
            raise RegistrySubmissionError("registry submission was not accepted; try again later")
        if not tx_hash:
            raise RegistrySubmissionError("registry submission returned no transaction hash")

        result = PublishResult(tx_hash=tx_hash, status=status_text or "PENDING")
        if not wait:
            return result

        try:
            final = self._client.poll_transaction(tx_hash)
        except Exception as exc:  # noqa: BLE001 - submission already succeeded
            raise RegistrySubmissionError(
                f"registry transaction submitted but confirmation failed: {_redact(exc, secret)}"
            ) from None
        final_status = getattr(final, "status", "")
        final_text = getattr(final_status, "value", str(final_status))
        ledger = getattr(final, "ledger", None)
        if final_text == "FAILED":
            raise RegistrySubmissionError(f"registry transaction {tx_hash} failed on-chain")
        return PublishResult(tx_hash=tx_hash, status=final_text or result.status, ledger=ledger)

    def publish_status(
        self,
        monitor: Monitor | None = None,
        check: Check | None = None,
        *,
        payload: ReportPayload | None = None,
        wait: bool = False,
    ) -> str:
        """Convenience wrapper returning only the transaction hash."""

        return self.publish(monitor, check, payload=payload, wait=wait).tx_hash


def publish_monitor_status(
    monitor: Monitor,
    *,
    config: Any = None,
    publisher: RegistryPublisher | None = None,
    check: Check | None = None,
    wait: bool = False,
) -> str:
    """Publish ``monitor``'s latest stored status and return the transaction hash."""

    if check is None:
        check = (
            Check.query.filter_by(monitor_id=monitor.id)
            .order_by(Check.checked_at.desc(), Check.id.desc())
            .first()
        )
    publisher = publisher or RegistryPublisher.from_config(config)
    return publisher.publish_status(monitor, check, wait=wait)
