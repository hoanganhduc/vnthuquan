"""Mirror definitions and helpers."""

from __future__ import annotations

from urllib.parse import urlparse

KNOWN_MIRRORS = (
    "http://vietnamthuquan.eu",
    "http://vnthuquan.net",
)

DEFAULT_MIRROR = KNOWN_MIRRORS[0]


def normalize_mirror(url: str | None) -> str:
    """Normalize a mirror URL and reject unsupported schemes."""

    if not url:
        return DEFAULT_MIRROR
    normalized = url.strip().rstrip("/")
    parsed = urlparse(normalized)
    if not parsed.scheme:
        normalized = f"http://{normalized}"
        parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid mirror URL: {url}")
    return normalized.rstrip("/")


def list_mirrors() -> list[str]:
    """Return known legacy mirrors."""

    return list(KNOWN_MIRRORS)
