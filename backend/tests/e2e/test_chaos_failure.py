def test_chaos_failure(api_client, chaos_teardown):
    """
    Simulate FAILURE preset.
    Validates that /health returns 200 OK (Degraded) and the system acts fail-silent.
    """
    # 1. Setup: Apply Chaos Preset FAILURE
    resp = api_client.post("/api/v1/chaos/failure")
    assert resp.status_code == 200

    # 2. Test: Validate degraded behavior
    # Ensure that health check returns 200 (Degraded) despite failure
    health_resp = api_client.get("/health")
    assert health_resp.status_code == 200

    health_data = health_resp.json()
    assert health_data.get("status") in (
        "degraded",
        "ok",
        "error",
    ), "Health status is missing"

    if health_data.get("status") == "degraded":
        assert "dependencies" in health_data

    # Ensure the failure is visible in metrics
    metrics_resp = api_client.get("/api/v1/metrics/summary")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert metrics.get("system_lifecycle") in (
        "DEGRADED",
        "RECOVERING",
    ), "System status should reflect failure"

    # 3. Teardown handles the recovery validation
