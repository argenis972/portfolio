"""
Spam scoring and classification logic.
"""

import re

# List of suspicious keywords common in spam (with word boundaries to avoid false positives)
SPAM_KEYWORDS = [
    r"\bcrypto\b",
    r"\bbitcoin\b",
    r"\bbtc\b",
    r"\binvestment\b",
    r"\bseo\b",
    r"\bmarketing\b",
    r"\bcasino\b",
    r"\bbetting\b",
    r"\blottery\b",
    r"\bwinner\b",
    r"\bprize\b",
    r"\bdiscount\b",
    r"\burgent\b",
    r"\bofficial\b",
    r"\bagency\b",
    r"\bapp development\b",
    r"\bwebsite design\b",
    r"\bproposal\b",
    r"\bleads\b",
    r"\blead generation\b",
    r"\bfreelance\b",
    r"\boutsourcing\b",
    r"\btelegram\b",
    r"\bwhatsapp\b",
    # Spanish/Portuguese keywords
    r"\binvertir\b",
    r"\binversión\b",
    r"\binversion\b",
    r"\bganar\b",
    r"\bganador\b",
    r"\bnegocio\b",
    r"\bgratis\b",
    r"\bpromoción\b",
    r"\bpromocion\b",
    r"\bpromoção\b",
    r"\bgana\b",
    r"\bganhe\b",
    r"\bdinero\b",
    r"\boferta\b",
    r"\binvestimento\b",
]

# Domains often used for temporary/burner emails
TEMP_EMAIL_DOMAINS = [
    "temp-mail.org",
    "10minutemail.com",
    "guerrillamail.com",
    "mailinator.com",
    "sharklasers.com",
    "yopmail.com",
]


# Regexes previously in the schema, now used for scoring
NAME_REGEX = re.compile(r"^[^\d\W_](?:[^\d\W_]|[ .,'-]){1,79}$")
SUBJECT_REGEX = re.compile(r"^(?:[^\d\W_]|[0-9]|[ .\[\],:;!?()/#&+@'\-]){0,120}$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def calculate_spam_score(
    message: str, email: str, name: str = "", subject: str = ""
) -> int:
    """
    Calculates a spam score based on message content, email, name and subject.
    0-30: Normal (deliver)
    31-69: Suspect (deliver with flag)
    >=70: Silent Spam (silent drop)

    Invalid formats now return 100 to ensure silent drop (no 422 error to user).
    """
    score = 0
    message_lower = message.lower()

    # Rule 0: Strict format validation
    if not EMAIL_REGEX.match(email):
        return 100

    if name and not NAME_REGEX.fullmatch(name):
        return 100

    if name:
        for char in name:
            if char.isnumeric():
                return 100

    if subject and not SUBJECT_REGEX.fullmatch(subject):
        return 100

    # Rule 1: Message too short
    if len(message.strip()) < 10:
        score += 10

    # Rule 2: Excessive links
    # Capture full URL tokens for both https:// and bare www. formats.
    # We exclude common delimiters like , ; ( ) [ ] to prevent merging adjacent URLs.
    all_links_raw = re.findall(
        r"https?://[^\s,;()\[\]]+|www\.[^\s,;()\[\]]+", message_lower
    )

    def _extract_domain(url: str) -> str:
        """Normalize https://www.foo.com/path and www.foo.com → foo.com.

        Also strips trailing prose punctuation (. , ; !) that may appear when
        a URL ends a sentence, e.g. "visit www.foo.com." → "foo.com".
        """
        url = re.sub(r"^https?://", "", url)
        url = re.sub(r"^www\.", "", url)
        hostname = url.split("/")[0].split("?")[0]
        return hostname.rstrip(".,;!")

    all_links = all_links_raw
    unique_domains = set(_extract_domain(u) for u in all_links_raw)

    if len(all_links) >= 3:
        score += 45
    elif len(all_links) >= 1:
        score += 15

    # Extra suspicious: multiple links to same domain in a short message
    if len(all_links) >= 2 and len(unique_domains) == 1 and len(message) < 500:
        score += 15

    # Rule 3: Spam keywords
    keyword_matches = 0
    for kw in SPAM_KEYWORDS:
        if re.search(kw, message_lower, re.UNICODE | re.IGNORECASE):
            keyword_matches += 1

    if keyword_matches >= 3:
        score += 70
    elif keyword_matches == 2:
        score += 40
    elif keyword_matches == 1:
        score += 25

    # Rule 4: Temporary email domains
    email_domain = email.split("@")[-1].lower() if "@" in email else ""
    if email_domain in TEMP_EMAIL_DOMAINS:
        score += 50

    # Rule 5: No spaces in long message
    if len(message) > 50 and " " not in message:
        score += 30

    # Rule 6: Excessive symbols ($%@! etc)
    symbols = len(re.findall(r"[$%@!*#]", message))
    if symbols > 10:
        score += 25
    elif symbols > 5:
        score += 10

    # Rule 7: Excessive capitalization
    if len(message) > 20:
        caps_ratio = sum(1 for c in message if c.isupper()) / len(message)
        if caps_ratio > 0.4:
            score += 20

    # Rule 8: Suspicious subject patterns
    if subject:
        subject_lower = subject.lower()
        if (
            "spam" in subject_lower
            or "advertencia" in subject_lower
            or "security" in subject_lower
        ):
            score += 30

    return min(score, 100)
