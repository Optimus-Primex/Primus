#![no_std]

//! Primus Registry - a minimal Soroban contract that stores the latest uptime
//! status reported for a monitor and emits an event on every update.
//!
//! Primus can use it two ways:
//!   * write: report a check result on-chain after a monitor check, and
//!   * read:  the `soroban-contract` check type verifies the contract's events
//!     / state are live.
//!
//! The contract is intentionally tiny and dependency-free beyond the Soroban
//! SDK so it is cheap to audit and deploy.

use soroban_sdk::{contract, contractevent, contractimpl, contracttype, Address, Env, Symbol};

/// Storage key namespace.
#[contracttype]
pub enum DataKey {
    /// Latest status for a monitor, keyed by the monitor's id.
    Status(Symbol),
}

/// The most recent check result reported for a monitor.
#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Status {
    pub up: bool,
    pub latency_ms: u32,
    pub ledger: u32,
    pub timestamp: u64,
}

/// Emitted whenever a monitor's status is reported.
#[contractevent]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StatusReported {
    #[topic]
    pub monitor_id: Symbol,
    pub up: bool,
    pub latency_ms: u32,
}

#[contract]
pub struct PrimusRegistry;

#[contractimpl]
impl PrimusRegistry {
    /// Record the latest status for `monitor_id`.
    ///
    /// The `reporter` must authorise the call, so the on-chain history is
    /// attributable.
    pub fn report(env: Env, reporter: Address, monitor_id: Symbol, up: bool, latency_ms: u32) {
        reporter.require_auth();

        let status = Status {
            up,
            latency_ms,
            ledger: env.ledger().sequence(),
            timestamp: env.ledger().timestamp(),
        };
        env.storage()
            .persistent()
            .set(&DataKey::Status(monitor_id.clone()), &status);

        StatusReported {
            monitor_id,
            up,
            latency_ms,
        }
        .publish(&env);
    }

    /// Return the latest status for `monitor_id`, if it has ever been reported.
    pub fn get_status(env: Env, monitor_id: Symbol) -> Option<Status> {
        env.storage().persistent().get(&DataKey::Status(monitor_id))
    }

    /// Whether the monitor was up in its most recent report.
    pub fn is_up(env: Env, monitor_id: Symbol) -> bool {
        match env
            .storage()
            .persistent()
            .get::<DataKey, Status>(&DataKey::Status(monitor_id))
        {
            Some(status) => status.up,
            None => false,
        }
    }
}

#[cfg(test)]
mod test;
