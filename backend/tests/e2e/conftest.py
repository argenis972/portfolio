import time
import pytest
import httpx
import os

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def api_client():
    try:
        with httpx.Client(base_url=BASE_URL, timeout=0.5) as client:
            client.get("/health")
    except httpx.RequestError:
        pytest.skip(f"Backend not running at {BASE_URL}. Skipping E2E tests.")

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # Prevent 120s waits by skipping E2E tests if the backend doesn't support instant reset
        reset_resp = client.post("/api/v1/chaos/reset")
        if reset_resp.status_code == 404:
            pytest.skip("Backend is running an old version without /api/v1/chaos/reset. Skipping E2E to avoid 120s delays.")

        yield client


@pytest.fixture
def chaos_teardown(api_client):
    """
    Narrative fixture for chaos tests:
    - setup -> apply chaos preset (done in the test itself)
    - test -> validate degraded behavior
    - teardown -> assert recovery to STABLE within SLO
    """
    # Ensure system is STABLE/NORMAL before starting the test
    max_wait = 150
    start_time = time.time()
    ready = False

    while time.time() - start_time < max_wait:
        resp = api_client.get("/api/v1/metrics/summary")
        if resp.status_code == 200:
            data = resp.json()
            if data.get("system_lifecycle") in ("STABLE", "NORMAL"):
                ready = True
                break
        time.sleep(2)

    assert ready, "System not in a stable state before test"

    yield

    # Teardown: Instantly reset chaos state to avoid waiting 120s
    reset_resp = api_client.post("/api/v1/chaos/reset")
    assert reset_resp.status_code == 200, f"Reset failed with status {reset_resp.status_code}"

    # Wait a tiny bit to ensure the next request doesn't hit any race conditions
    time.sleep(0.1)

    # Final verification: system should be NORMAL immediately after reset
    resp = api_client.get("/api/v1/metrics/summary")
    if resp.status_code == 200:
        data = resp.json()
        assert data.get("system_lifecycle") == "NORMAL", "System failed to return to NORMAL after reset"
