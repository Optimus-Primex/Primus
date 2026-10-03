# Primus Registry (Soroban)

A minimal [Soroban](https://developers.stellar.org/docs/smart-contracts) smart
contract that stores the latest uptime status reported for a monitor and emits
an event on every update. It gives Primus an on-chain, auditable record of
monitor health and backs the `soroban-contract` check type.

## Interface

| Function | Description |
| --- | --- |
| `report(reporter, monitor_id, up, latency_ms)` | Record the latest status. `reporter` must authorise the call. Emits a `StatusReported` event. |
| `get_status(monitor_id)` | Return the stored `Status` (or `None`). |
| `is_up(monitor_id)` | Whether the last report was up. |

```rust
pub struct Status {
    pub up: bool,
    pub latency_ms: u32,
    pub ledger: u32,
    pub timestamp: u64,
}
```

## Build & test

```bash
cd contracts/primus-registry

cargo test              # unit tests (soroban-sdk testutils)

stellar contract build  # deployable wasm (requires stellar-cli v25.2.0+)
```

`stellar contract build` writes `target/wasm32v1-none/release/primus_registry.wasm`.
A plain `cargo build --release --target wasm32v1-none` also works as a compile
check when you set `SOROBAN_SDK_BUILD_SYSTEM_SUPPORTS_SPEC_SHAKING_V2=1`
(soroban-sdk rejects `wasm32-unknown-unknown` on Rust 1.84+ and requires
stellar-cli to do spec shaking).

On Windows, `cargo test` needs the MSVC toolchain (or build the tests with
`crate-type = ["rlib"]` under the GNU toolchain to work around a known mingw
cdylib export limit). CI runs on Linux.

## Deploy (Stellar testnet)

```bash
stellar contract build
stellar contract deploy \
  --wasm target/wasm32v1-none/release/primus_registry.wasm \
  --network testnet \
  --source <your-identity>
```

Copy the resulting contract id (`C...`) into a Primus `soroban-contract`
monitor's `type_config.contract_id` to watch it.
