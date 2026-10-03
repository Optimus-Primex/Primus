"""Stellar / Soroban check types.

Registered on package import via :func:`register_stellar_types`.
"""

from __future__ import annotations

from .account import StellarAccountCheck, StellarAssetCheck
from .horizon import StellarHorizonCheck
from .soroban_contract import SorobanContractCheck
from .soroban_rpc import SorobanRpcCheck


def register_stellar_types(register) -> None:
    """Register every built-in Stellar/Soroban check type."""

    register(StellarHorizonCheck())
    register(SorobanRpcCheck())
    register(SorobanContractCheck())
    register(StellarAccountCheck())
    register(StellarAssetCheck())


__all__ = [
    "SorobanContractCheck",
    "SorobanRpcCheck",
    "StellarAccountCheck",
    "StellarAssetCheck",
    "StellarHorizonCheck",
    "register_stellar_types",
]
