# Stellar & Soroban monitoring

Primus ships protocol-specific **check types** for the Stellar ecosystem. Each
check type is a small, stateless plugin registered in
`primus/services/check_types/`; the scheduler, API and incident state machine
are protocol-agnostic.

## Check types

| `type` | What it checks | Key `type_config` fields |
| --- | --- | --- |
| `stellar-horizon` | Horizon reachable and the latest ledger's close lag is within bounds | `network`, `max_ledger_lag_seconds` |
| `soroban-rpc` | Soroban RPC node health, latest ledger and network passphrase | `network`, `max_ledger_lag_seconds`, `verify_passphrase` |
| `soroban-contract` | A deployed contract's event stream via `getEvents` | `network`, `contract_id`, `lookback_ledgers`, `expect_events` |
| `stellar-account` | An account exists and its XLM balance meets a minimum | `network`, `account_id`, `min_xlm_balance` |
| `stellar-asset` | An issued asset exists on Horizon | `network`, `asset_code`, `asset_issuer` |

All Stellar types are Horizon REST or Soroban JSON-RPC calls, so no extra
Python dependency is required. `network` is one of `mainnet`, `testnet`,
`futurenet`.

## Known networks

| Network | Horizon | Soroban RPC |
| --- | --- | --- |
| `mainnet` | `https://horizon.stellar.org` | `https://mainnet.sorobanrpc.com` |
| `testnet` | `https://horizon-testnet.stellar.org` | `https://soroban-testnet.stellar.org` |
| `futurenet` | `https://horizon-futurenet.stellar.org` | `https://rpc-futurenet.stellar.org` |

## Examples

Monitor a Horizon endpoint for ledger lag:

```bash
curl -X POST http://localhost:5000/api/monitors \
  -H "Authorization: Bearer $PRIMUS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "Stellar Horizon (mainnet)",
        "url": "https://horizon.stellar.org",
        "type": "stellar-horizon",
        "type_config": {"network": "mainnet", "max_ledger_lag_seconds": 30},
        "interval_seconds": 60
      }'
```

Watch a Soroban contract's events:

```json
{
  "name": "My Soroban contract",
  "url": "https://soroban-testnet.stellar.org",
  "type": "soroban-contract",
  "type_config": {
    "network": "testnet",
    "contract_id": "CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABSC4",
    "lookback_ledgers": 1000,
    "expect_events": true
  }
}
```

Check an account's XLM balance:

```json
{
  "name": "Treasury account",
  "url": "https://horizon.stellar.org",
  "type": "stellar-account",
  "type_config": {
    "account_id": "GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWHF",
    "min_xlm_balance": 100
  }
}
```

## The on-chain registry

`contracts/primus-registry` is a Soroban contract that stores the latest status
reported for a monitor and emits a `StatusReported` event. Use it to publish an
auditable uptime record on-chain; the `soroban-contract` check type can then
watch it. See [`contracts/primus-registry/README.md`](../contracts/primus-registry/README.md).

## Adding a new check type

Subclass `CheckType` (see `primus/services/check_types/base.py`), implement
`run()` (and optionally `validate_config()`), then register it. Types are
resolved from `Monitor.type`, so nothing else in the codebase needs to change.
