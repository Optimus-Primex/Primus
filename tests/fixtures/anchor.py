"""Offline fixtures for the Stellar anchor check."""

from __future__ import annotations

STELLAR_TOML = """
ACCOUNTS = ["GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWHF"]
VERSION = 1
NETWORK_PASSPHRASE = "Public Global Stellar Network ; September 2015"
TRANSFER_SERVER_SEP0024 = "https://anchor.example.com/sep24"
DIRECT_PAYMENT_SERVER = "https://anchor.example.com/sep31"
"""

TOML_SEP24_ONLY = """
VERSION = 1
TRANSFER_SERVER_SEP0024 = "https://anchor.example.com/sep24"
"""

TOML_WITHOUT_SERVERS = """
VERSION = 1
"""

TOML_INVALID = """
TRANSFER_SERVER_SEP0024 = [
"""

SEP24_INFO = {
    "deposit": {
        "USDC": {
            "enabled": True,
            "min_amount": 1,
            "max_amount": 10000,
            "fee_fixed": 0,
        }
    },
    "withdraw": {
        "USDC": {
            "enabled": True,
            "min_amount": 1,
            "max_amount": 10000,
            "fee_fixed": 0,
        }
    },
}

SEP24_DISABLED = {
    "deposit": {"USDC": {"enabled": False, "min_amount": 1, "max_amount": 10000}},
    "withdraw": {"USDC": {"enabled": False, "min_amount": 1, "max_amount": 10000}},
}

SEP31_INFO = {
    "receive": {
        "USDC": {
            "enabled": True,
            "min_amount": 1,
            "max_amount": 10000,
            "fields": {"transaction": {"sender_id": {"description": "id"}}},
        }
    }
}


__all__ = [
    "SEP24_DISABLED",
    "SEP24_INFO",
    "SEP31_INFO",
    "STELLAR_TOML",
    "TOML_INVALID",
    "TOML_SEP24_ONLY",
    "TOML_WITHOUT_SERVERS",
]
