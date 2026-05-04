import time
import pytest
import httpx
import os

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def api_client():
    try:
        with httpx.Client(base_url=BASE_URL, timeout=2.0) as client:
            client.get("/health")
    except httpx.RequestError:
        pytest.skip(f"Backend not running at {BASE_URL}. Skipping E2E tests.")

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        yield client


@pytest.fixture
def chaos_teardown(api_client):
    """
    Narrative fixture for chaos tests:
    - setup -> apply chaos preset (done in the test itself)
    - test -> validate degraded behavior
    - teardown -> assert recovery to STABLE within SLO
    """
    # reset state before test
    api_client.post("/api/v1/chaos/drain")
    time.sleep(1)

    yield

    # Teardown: Wait and assert recovery to STABLE or NORMAL
    max_wait = 120  # chaos incident lasts up to 120s in system_lifecycle
    start_time = time.time()
    recovered = False

    while time.time() - start_time < max_wait:
        resp = api_client.get("/api/v1/metrics/summary")
        if resp.status_code == 200:
            data = resp.json()
            lifecycle = data.get("system_lifecycle")
            if lifecycle in ("STABLE", "NORMAL"):
                recovered = True
                break
        time.sleep(2)

    assert recovered, f"System did not recover to STABLE within {max_wait}s"
