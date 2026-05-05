"""
Tests for Honeypot and Spam Scoring defense layers.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.controllers.dependencies import get_send_contact_use_case
from app.core.honeypot import is_honeypot_triggered
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_use_case():
    uc = AsyncMock()
    uc.execute.return_value = True
    app.dependency_overrides[get_send_contact_use_case] = lambda: uc
    try:
        yield uc
    finally:
        app.dependency_overrides.pop(get_send_contact_use_case, None)


def test_honeypot_triggered(mock_use_case):
    """Verifica se o honeypot bloqueia o envio mas retorna sucesso falso."""
    payload = {
        "name": "Bot",
        "email": "bot@spam.com",
        "subject": "Spam bot",
        "message": "I am a bot filling all fields.",
        "website": "http://evilbot.com",  # Honeypot field
    }

    response = client.post("/api/v1/contact", json=payload)

    assert response.status_code == 200
    assert response.json()["success"] is True
    # O Caso de Uso NÃO deve ter sido chamado
    mock_use_case.execute.assert_not_called()


def test_spam_score_high_silent_drop(mock_use_case):
    """Verifica se score muito alto (>70) causa drop silencioso."""
    payload = {
        "name": "Spammer",
        "email": "spammer@temp-mail.org",  # +40 pts
        "subject": "Cheap Bitcoin",
        "message": "Buy bitcoin now! http://spam1.com http://spam2.com http://spam3.com official winner prize",  # +25 pts (links) + 30 pts (keywords)
    }

    response = client.post("/api/v1/contact", json=payload)

    assert response.status_code == 200
    assert response.json()["success"] is True
    # O Caso de Uso NÃO deve ter sido chamado
    mock_use_case.execute.assert_not_called()


def test_spam_score_medium_suspect(mock_use_case):
    """Verifica se score médio (>30) marca como [SUSPECT]."""
    payload = {
        "name": "Suspicious User",
        "email": "user@gmail.com",
        "subject": "Inquiry",
        "message": "Official marketing offer for your project: http://mysite.com",
    }

    response = client.post("/api/v1/contact", json=payload)

    assert response.status_code == 200
    # O Caso de Uso deve ter sido chamado com is_suspicious=True
    mock_use_case.execute.assert_called_once()
    args, kwargs = mock_use_case.execute.call_args
    assert kwargs["is_suspicious"] is True
    assert kwargs["spam_score"] > 30


def test_normal_message_not_suspect(mock_use_case):
    """Verifica se message normal passa sem marcação."""
    payload = {
        "name": "Argenis",
        "email": "argenis@example.com",
        "subject": "Job Opportunity",
        "message": "Hello, I would like to talk about a backend role.",
    }

    response = client.post("/api/v1/contact", json=payload)

    assert response.status_code == 200
    mock_use_case.execute.assert_called_once()
    args, kwargs = mock_use_case.execute.call_args
    assert kwargs["is_suspicious"] is False


def test_honeypot_is_triggered_with_empty_data():
    """Verifica retorno False cuando los datos no tienen spam fields."""
    assert is_honeypot_triggered({"name": "John", "email": "j@mock.com"}) is False


def test_honeypot_is_triggered_with_spam_fields():
    """Verifica retorno True al alimentar arrays conteniendo campos como website, fax, company, middle_name."""
    assert is_honeypot_triggered({"website": "http://spam.com"}) is True
    assert is_honeypot_triggered({"fax": "12345"}) is True
    assert is_honeypot_triggered({"company": "Spam Corp"}) is True
    assert is_honeypot_triggered({"middle_name": "Danger"}) is True


# ── P2 Regression Tests ────────────────────────────────────────────────────


def test_spam_score_www_and_https_different_domains_no_false_penalty():
    """
    P2 regression: https://foo.com + www.bar.com are DIFFERENT domains.
    Must NOT trigger the 'repeated same domain' penalty (+15 pts).

    Before the fix, all_links counted protocol prefixes (len=2) while
    unique_domains only extracted from https:// URLs (len=1), incorrectly
    satisfying the same-domain condition.

    Expected: score <= 30 (15 pts for 2 links, no same-domain penalty, no keywords).
    """
    from app.core.spam_check import calculate_spam_score

    score = calculate_spam_score(
        message="Check https://foo.com and also www.bar.com for details.",
        email="user@example.com",
    )
    assert score <= 30, f"Expected score <= 30 for different domains, got {score}"


def test_spam_score_www_and_https_same_domain_triggers_penalty():
    """
    P2 regression: www.foo.com and https://foo.com are the SAME domain.
    Must correctly trigger the 'repeated same domain' penalty (+15 pts).

    Expected: score >= 30 (15 pts for 2 links + 15 pts same-domain penalty).
    """
    from app.core.spam_check import calculate_spam_score

    score = calculate_spam_score(
        message="See https://foo.com/page1 and www.foo.com/page2 for more info.",
        email="user@example.com",
    )
    assert score >= 30, f"Expected same-domain penalty applied, got {score}"


def test_spam_score_url_with_trailing_punctuation_no_false_penalty():
    """
    Edge case: URLs ending a sentence carry trailing punctuation (e.g., 'www.foo.com.').
    The trailing dot must be stripped before domain comparison so that
    'www.beta.com.' and 'https://alpha.com' are not counted as one unique domain.

    Expected: score <= 30 (2 different domains, no same-domain penalty).
    """
    from app.core.spam_check import calculate_spam_score

    score = calculate_spam_score(
        message="Visit https://alpha.com or www.beta.com.",
        email="user@example.com",
    )
    assert score <= 30, (
        f"Expected score <= 30 for different domains with trailing punct, got {score}"
    )


def test_spam_score_adjacent_urls_with_comma_are_separated():
    """
    Regressión para P1: URLs adyacentes separadas por coma deben contarse
    como dos enlaces distintos, no uno solo fusionado.
    """
    from app.core.spam_check import calculate_spam_score

    # https://a.com,https://b.com -> 2 links, 2 unique domains
    # No debería aplicar la penalización de mismo dominio (+15).
    # Pero sí debería contar como 2 links para la regla de >=3 links.
    msg = "Check https://a.com,https://b.com,www.c.com"
    score = calculate_spam_score(msg, "valid@email.com")

    # Detalle esperado:
    # all_links = 3
    # unique_domains = 3
    # Rule 2 (all_links >= 3) -> +45
    # Rule 2 (multiple links same domain) -> NO (+0)
    assert score == 45
