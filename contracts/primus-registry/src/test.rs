use super::*;
use soroban_sdk::{symbol_short, testutils::Address as _, Env};

#[test]
fn unknown_monitor_is_down() {
    let env = Env::default();
    let contract_id = env.register(PrimusRegistry, ());
    let client = PrimusRegistryClient::new(&env, &contract_id);

    assert!(!client.is_up(&symbol_short!("api")));
    assert!(client.get_status(&symbol_short!("api")).is_none());
}

#[test]
fn report_then_read_back() {
    let env = Env::default();
    env.mock_all_auths();
    let contract_id = env.register(PrimusRegistry, ());
    let client = PrimusRegistryClient::new(&env, &contract_id);

    let reporter = Address::generate(&env);
    let monitor = symbol_short!("api");

    client.report(&reporter, &monitor, &true, &42);

    assert!(client.is_up(&monitor));
    let status = client.get_status(&monitor).unwrap();
    assert!(status.up);
    assert_eq!(status.latency_ms, 42);
}

#[test]
fn latest_report_wins() {
    let env = Env::default();
    env.mock_all_auths();
    let contract_id = env.register(PrimusRegistry, ());
    let client = PrimusRegistryClient::new(&env, &contract_id);

    let reporter = Address::generate(&env);
    let monitor = symbol_short!("api");

    client.report(&reporter, &monitor, &true, &10);
    client.report(&reporter, &monitor, &false, &0);

    assert!(!client.is_up(&monitor));
    assert_eq!(client.get_status(&monitor).unwrap().latency_ms, 0);
}
