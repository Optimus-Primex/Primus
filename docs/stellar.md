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
| `stellar-anchor` | An anchor's `stellar.toml` and SEP-24/SEP-31 info endpoints | `network`, `services`, `asset_code`, `require_deposit`, `require_withdraw`, `required_fields` |

All Stellar types are Horizon REST or Soroban JSON-RPC calls, so no extra
Python dependency is required. `network` is one of `mainnet`, `testnet`,
`futurenet`.

`stellar-anchor` reads the anchor home domain from `url` (it must be HTTPS),
fetches `/.well-known/stellar.toml`, and calls the SEP-24 `/sep24/info` and/or
SEP-31 `/sep31/info` endpoint advertised there. Every URL, including redirect
targets, goes through the same SSRF guard as the HTTP check type. Plain-HTTP
home domains, transfer servers, and redirects are rejected.

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

Check a SEP-24/SEP-31 anchor (the URL is the anchor's home domain, not the
transfer server):

```json
{
  "name": "Anchor USDC",
  "url": "https://anchor.example.com",
  "type": "stellar-anchor",
  "type_config": {
    "network": "mainnet",
    "services": "both",
    "asset_code": "USDC",
    "require_deposit": true,
    "require_withdraw": true,
    "required_fields": ["min_amount", "max_amount"]
  }
}
```

- `services`: `auto` (default; use whichever servers the TOML advertises),
  `sep24`, `sep31`, or `both`.
- `asset_code`: optional; when set it must appear in the selected info
  document(s).
- `require_deposit` / `require_withdraw`: require an enabled deposit or
  withdrawal asset. `require_withdraw` applies to SEP-24 only.
- `required_fields`: optional list of field names that must be present on the
  asset's `/info` entry (for example `min_amount`, `max_amount`, `fee_fixed`).

## The on-chain registry

`contracts/primus-registry` is a Soroban contract that stores the latest status
reported for a monitor and emits a `StatusReported` event. Use it to publish an
auditable uptime record on-chain; the `soroban-contract` check type can then
watch it. See [`contracts/primus-registry/README.md`](../contracts/primus-registry/README.md).

### Contract interface

The publisher calls exactly the contract's `report` function:

```rust
report(reporter: Address, monitor_id: Symbol, up: bool, latency_ms: u32)
```

- `reporter` is the configured signer's public key and authorises the call.
- `monitor_id` is the Primus monitor's numeric id encoded as a Soroban `Symbol`
  (for example, monitor `7` is published as `Symbol("7")`).
- `up` comes from the latest stored check (falling back to `Monitor.last_status`).
- `latency_ms` is the latest check latency, rounded and clamped to a `u32`.

### Build and deploy the contract

Building requires [stellar-cli](https://developers.stellar.org/docs/tools/cli)
v25.2.0+ and a Rust toolchain:

```bash
cd contracts/primus-registry
stellar contract build
stellar contract deploy \
  --wasm target/wasm32v1-none/release/primus_registry.wasm \
  --network testnet \
  --source <funded-identity>
```

On testnet you can create a throwaway identity and fund it with Friendbot:

```bash
stellar keys generate --network testnet primus-publisher
stellar keys fund primus-publisher --network testnet
stellar keys address primus-publisher
```

Copy the deployed contract id (`C...`) into `PRIMUS_REGISTRY_CONTRACT_ID`. Do
not commit the signer secret; provide it only through the environment.

### Deployed registry (testnet)

A demo instance is live on testnet and was used for the smoke report below:

```
PRIMUS_REGISTRY_CONTRACT_ID=CDEPU2EKEOCC6EKHHQZVTOVH67VLO2DEYK5VG3CYNWQYY3OUDEMGNDQI
https://stellar.expert/explorer/testnet/contract/CDEPU2EKEOCC6EKHHQZVTOVH67VLO2DEYK5VG3CYNWQYY3OUDEMGNDQI
```

- wasm sha256: `0385b9fb46aad6d9899814eabf3332a96130eba4d9a5831909f073bc1f3e6dc0`
- wasm upload tx: `57417cb5f40244edd309003499ac1ef4499045d4cbb2e49a463324c29457b586`
- contract deploy tx: `7c9dbf0a4d221a926a1ef797589aae411d10d8794fbaed4e2d8b140af053ca8b`
- report tx: `593c90095cc5dde11133e7fc63b136f747f04f5454f42156667b9ac1b6b43b32`
  (success, ledger `5308464`)
- read back `get_status("proof_1")`:
  `{"up": true, "latency_ms": 42, "ledger": 5308464, "timestamp": 1792565907}`

The instance is a public testnet registry; reports are authorized by the
reporter's key, not by a contract admin.

### Publish from Python

The publisher uses the official [`stellar-sdk`](https://pypi.org/project/stellar-sdk/)
package (pinned in `requirements.txt`, also available as the `stellar` optional
extra). It loads the signer account, builds an `invokeHostFunction` transaction,
simulates it via Soroban RPC, prepares/signs it and submits it. The signer secret
is never included in logs or error messages.

```bash
# .env (never commit real values)
PRIMUS_REGISTRY_CONTRACT_ID=C...
PRIMUS_REGISTRY_SECRET_KEY=S...
PRIMUS_REGISTRY_NETWORK=testnet
# Optional; defaults to the public RPC endpoint for the selected network:
PRIMUS_REGISTRY_RPC_URL=https://soroban-testnet.stellar.org
```

Then publish the monitor's latest check:

```bash
flask primus publish-status --monitor-id 7
# Published monitor 7 status to the registry. Tx hash: ...
```

To publish automatically after every scheduled check, set
`PRIMUS_REGISTRY_PUBLISH_ON_CHECK=1`. The hook is **disabled by default**; a
failed publish is logged but never fails the check or incident state machine.

The command is **stateless**: it returns/prints the transaction hash but does
not add a database column or outbox table. If you need a durable audit trail,
run it from cron and capture stdout, or query the contract's `StatusReported`
events. `soroban-contract` monitors can watch those events directly.

The signer account must exist and hold enough XLM to pay the Soroban resource
fees. Publishing fails cleanly with a nonzero exit code when configuration is
missing, the contract id/secret is invalid, simulation rejects the call, or the
network refuses the transaction.


## Adding a new check type

Subclass `CheckType` (see `primus/services/check_types/base.py`), implement
`run()` (and optionally `validate_config()`), then register it. Types are
resolved from `Monitor.type`, so nothing else in the codebase needs to change.
