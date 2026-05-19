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


@pytest.mark.parametrize(
    "honeypot_field,value",
    [
        ("website", "http://evilbot.com"),
        ("fax", "123456"),
        ("company", "Spam Corp"),
        ("middle_name", "Danger"),
    ],
)
def test_honeypot_triggered(mock_use_case, honeypot_field, value):
    """Verifies if the honeypot blocks the send but returns fake success."""
    payload = {
        "name": "Bot",
        "email": "bot@spam.com",
        "subject": "Spam bot",
        "message": "I am a bot filling all fields.",
        honeypot_field: value,
    }

    response = client.post("/api/v1/contact", json=payload)

    assert response.status_code == 200
    assert response.json()["success"] is True
    # The Use Case MUST NOT have been called
    mock_use_case.execute.assert_not_called()


def test_spam_score_high_silent_drop(mock_use_case):
    """Verifies if a very high score (>70) causes a silent drop."""
    payload = {
        "name": "Spammer",
        "email": "spammer@temp-mail.org",  # +40 pts
        "subject": "Cheap Bitcoin",
        "message": "Buy bitcoin now! http://spam1.com http://spam2.com http://spam3.com official winner prize",  # +25 pts (links) + 30 pts (keywords)
    }

    response = client.post("/api/v1/contact", json=payload)

    assert response.status_code == 200
    assert response.json()["success"] is True
    # The Use Case MUST NOT have been called
    mock_use_case.execute.assert_not_called()


def test_spam_score_medium_suspect(mock_use_case):
    """Verifies if a medium score (>30) marks it as [SUSPECT]."""
    payload = {
        "name": "Suspicious User",
        "email": "user@gmail.com",
        "subject": "Inquiry",
        "message": "Official marketing offer for your project: http://mysite.com",
    }

    response = client.post("/api/v1/contact", json=payload)

    assert response.status_code == 200
    # The Use Case should have been called with is_suspicious=True
    mock_use_case.execute.assert_called_once()
    args, kwargs = mock_use_case.execute.call_args
    assert kwargs["is_suspicious"] is True
    assert kwargs["spam_score"] > 30


def test_normal_message_not_suspect(mock_use_case):
    """Verifies if a normal message passes without marking."""
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
    """Verifies False return when data has no spam fields."""
    assert is_honeypot_triggered({"name": "John", "email": "j@mock.com"}) is False


def test_honeypot_is_triggered_with_spam_fields():
    """Verifies True return when feeding arrays containing fields like website, fax, company, middle_name."""
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
    P1 regression: adjacent URLs separated by a comma should be counted
    as two distinct links, not a single merged one.
    """
    from app.core.spam_check import calculate_spam_score

    # https://a.com,https://b.com -> 2 links, 2 unique domains
    # Should not apply the same domain penalty (+15).
    # But it should count as 2 links for the rule of >=3 links.
    msg = "Check https://a.com,https://b.com,www.c.com"
    score = calculate_spam_score(msg, "valid@email.com")

    # Detalle esperado:
    # all_links = 3
    # unique_domains = 3
    # Rule 2 (all_links >= 3) -> +45
    # Rule 2 (multiple links same domain) -> NO (+0)
    assert score == 45
