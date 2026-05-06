def test_endpoint_duplicate_repro(client):
    """
    Simulates endpoint behavior for multiple calls with the same content.
    """
    # Note: conftest.py already resets the DB between tests if configured,
    # so we no longer need content_store._cache.clear()

    email = "dupe@example.com"
    content = "This belongs to a duplicate test."
    payload = {
        "name": "Dupe User",
        "email": email,
        "subject": "Subject A",
        "message": content,
    }

    # 1. First request (Success)
    resp1 = client.post("/api/v1/contact", json=payload)
    assert resp1.status_code == 200

    # 2. Second request with SAME content but different subject (Should be blocked)
    # Deduplication is now based only on email and normalized message
    payload_diff_subject = payload.copy()
    payload_diff_subject["subject"] = "Subject B (Changed)"
    resp2 = client.post("/api/v1/contact", json=payload_diff_subject)

    assert resp2.status_code == 400
    assert resp2.json()["error"]["code"] == "DUPLICATE_CONTENT"


def test_endpoint_rate_limit_manual_repro(client):
    """
    Verifies that manual rate limiting does not block duplicates from counting.
    """
    email = "limit@example.com"
    payload = {"name": "Limit User", "email": email, "message": "Fresh message 1"}

    # 1. Send normally (OK)
    resp1 = client.post("/api/v1/contact", json=payload)
    assert resp1.status_code == 200

    # 2. Send duplicate (Should be 400)
    resp2 = client.post("/api/v1/contact", json=payload)
    assert resp2.status_code == 400
