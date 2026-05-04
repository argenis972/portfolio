def test_chaos_mild(api_client, chaos_teardown):
    """
    Simulate MILD preset (traffic spike).
    Validates that the system degrades acceptably and tracks error rate within a window.
    """
    # 1. Setup: Apply Chaos Preset MILD
    resp = api_client.post("/api/v1/chaos/spike")
    assert resp.status_code == 200
    
    # 2. Test: Validate degraded behavior
    metrics_resp = api_client.get("/api/v1/metrics/summary")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    
    # Assert acceptable degradation (P95 should not exceed a large threshold, and error rate should be low)
    assert 0 <= metrics.get("p95_ms", 0) <= 2000, f"P95 latency {metrics.get('p95_ms')}ms out of acceptable degraded window"
    assert 0.0 <= metrics.get("error_rate", 0.0) <= 0.15, f"Error rate {metrics.get('error_rate')} exceeds MILD threshold"
    
    # 3. Teardown handles the recovery validation
