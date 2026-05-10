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
        yield client


@pytest.fixture
def chaos_teardown(api_client):
    """
    Narrative fixture for chaos tests:
    - setup -> forcibly reset system to NORMAL
    - test -> validate degraded behavior
    - teardown -> forcibly reset system to NORMAL
    """
    # Force system to NORMAL before starting the test
    api_client.post("/api/v1/chaos/reset")

    yield

    # Teardown: Force system back to NORMAL
    api_client.post("/api/v1/chaos/reset")
