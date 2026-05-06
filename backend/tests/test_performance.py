from app.main import app


def test_etag_and_304_not_modified(client):
    """
    Tests if backend generates ETags and responds with 304 when content hasn't changed.
    """
    # 1. First request to obtain ETag
    resp1 = client.get("/api/v1/about")
    assert resp1.status_code == 200
    etag = resp1.headers.get("ETag")
    assert etag is not None
    assert resp1.headers.get("Cache-Control") is not None

    # 2. Second request sending If-None-Match
    resp2 = client.get("/api/v1/about", headers={"If-None-Match": etag})

    # Should return 304 Not Modified
    assert resp2.status_code == 304
    # 304 MUST NOT have a body
    assert resp2.text == ""
    # Must maintain cache headers
    assert resp2.headers.get("ETag") == etag
    assert "public" in resp2.headers.get("Cache-Control")


def test_etag_changes_when_content_changes(client):
    """
    Verifies if ETag changes when the payload is different.
    """
    # Mocking different data to force ETag change
    from unittest.mock import AsyncMock

    from app.use_cases import GetAboutUseCase

    mock_uc = AsyncMock(spec=GetAboutUseCase)
    mock_uc.execute.return_value = {
        "name": "Argenis",
        "title": "Dev",
        "location": "Curitiba, PR",
        "email": "argenis@test.com",
        "phone": "123456789",
        "github": "https://github.com/argenis",
        "linkedin": "https://linkedin.com/in/argenis",
        "description": {"pt": "Desc", "en": "Desc", "es": "Desc"},
        "availability": {"pt": "Sim", "en": "Yes", "es": "Sí"},
    }

    from app.controllers.dependencies import dep_about

    app.dependency_overrides[dep_about] = lambda: mock_uc

    try:
        resp1 = client.get("/api/v1/about")
        etag1 = resp1.headers.get("ETag")

        # Change returned data
        mock_uc.execute.return_value = {
            "name": "Argenis Lopez",
            "title": "Senior Dev",
            "location": "Curitiba, PR",
            "email": "argenis@test.com",
            "phone": "123456789",
            "github": "https://github.com/argenis",
            "linkedin": "https://linkedin.com/in/argenis",
            "description": {"pt": "Desc", "en": "Desc", "es": "Desc"},
            "availability": {"pt": "Sim", "en": "Yes", "es": "Sí"},
        }
        resp2 = client.get("/api/v1/about")
        etag2 = resp2.headers.get("ETag")

        assert etag1 != etag2
    finally:
        app.dependency_overrides.pop(dep_about, None)
