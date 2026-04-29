from urllib.parse import urlparse

MAX_URL_LENGTH = 2048

BLOCKED_DOMAINS = {
    "evil.com",
    "malware.example.com",
    "phishing.example.com",
}


def is_blocked_domain(hostname: str | None) -> bool:
    if hostname is None:
        return True
    return hostname.lower() in BLOCKED_DOMAINS


def validate_url(url: str) -> str:
    """Format check, normalization, and blocklist validation."""
    if len(url) > MAX_URL_LENGTH:
        raise ValueError(f"URL exceeds maximum length of {MAX_URL_LENGTH} characters")

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"URL scheme must be http or https, got '{parsed.scheme}'")

    if is_blocked_domain(parsed.hostname):
        raise ValueError(f"Domain '{parsed.hostname}' is blocked")

    normalized = parsed._replace(
        scheme="https",
        netloc=parsed.netloc.lower(),
    ).geturl()

    normalized = normalized.rstrip("/")

    return normalized
