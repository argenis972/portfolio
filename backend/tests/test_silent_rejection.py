from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_silent_rejection_invalid_subject():
    """Verifies that a message with invalid characters in subject returns 200 Success."""
    payload = {
        "name": "Attacker",
        "email": "attacker@spam.com",
        "subject": "!!! NOTIFICACION DE SEGURIDAD !!!",
        "message": "This should be silently dropped but return success.",
    }
    response = client.post("/api/v1/contact", json=payload)
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_silent_rejection_invalid_email():
    """Verifies that a message with invalid email format returns 422.

    Previously this returned 200 (silent drop) because email was typed as `str`.
    With EmailStr, Pydantic enforces RFC 5321 format at schema validation time
    and returns 422 INPUT_VALIDATION_ERROR — this is the correct, secure behavior.
    Email format is a hard contract (not a soft guard heuristic).
    """
    payload = {
        "name": "User",
        "email": "not-an-email",
        "subject": "Hello",
        "message": "Valid message but invalid email.",
    }
    response = client.post("/api/v1/contact", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "INPUT_VALIDATION_ERROR"


def test_silent_rejection_invalid_name():
    """Verifies that a message with invalid characters in name returns 200 Success."""
    payload = {
        "name": "12345",  # Should fail NAME_REGEX
        "email": "test@test.com",
        "subject": "Test",
        "message": "Valid message but invalid name.",
    }
    response = client.post("/api/v1/contact", json=payload)
    assert response.status_code == 200
    assert response.json()["success"] is True
