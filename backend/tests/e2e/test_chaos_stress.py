import time


def test_chaos_stress(api_client, chaos_teardown):
    """
    Simulate STRESS preset (latency injection).
    Validates that circuit breaker / worker gets delayed.
    """
    # 1. Setup: Apply Chaos Preset STRESS
    resp = api_client.post("/api/v1/chaos/latency")
    assert resp.status_code == 200

    # 2. Test: Validate degraded behavior
    time.sleep(1)
    metrics_resp = api_client.get("/api/v1/metrics/summary")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()

    # STRESS should open the circuit breaker or cause worker delay/fallback
    assert metrics.get("active_path") in (
        "fallback",
        "async",
    ), "Circuit breaker did not open/fallback"

    # 3. Teardown handles the recovery validation
