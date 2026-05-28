"""URL allowlist enforcement for the egress output filter (P10 — task 1.2.5).

Only docs.secureclaim.example and status.secureclaim.example (and their
subdomains) are permitted in customer-visible output.  Every other URL is
replaced inline and audited.

Only http/https URLs are scanned — javascript: / data: URI injection is the
sanitiser's concern (task 1.2.6).  Pure module, no I/O.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

_URL_RE = re.compile(r"https?://[^\s\"'<>\]]+", re.IGNORECASE)

ALLOWED_HOSTS: frozenset[str] = frozenset(
    {
        "docs.secureclaim.example",
        "status.secureclaim.example",
    }
)

_PLACEHOLDER = "[external link removed]"


def _is_allowed(url: str) -> bool:
    try:
        hostname: str | None = urlparse(url).hostname  # already lowercased
    except ValueError:
        hostname = None
    if not hostname:
        # Unparseable or no host — treat as violation so it gets stripped+audited
        return False
    for host in ALLOWED_HOSTS:
        if hostname == host or hostname.endswith(f".{host}"):
            return True
    return False


def strip_urls(text: str) -> tuple[str, list[str]]:
    """Replace non-allowlisted URLs with a placeholder.

    Returns (modified_text, list_of_stripped_urls).  The list is empty when
    every URL in the text is on the allowlist.
    """
    stripped: list[str] = []

    def _replace(m: re.Match[str]) -> str:
        url = m.group()
        if _is_allowed(url):
            return url
        stripped.append(url)
        return _PLACEHOLDER

    return _URL_RE.sub(_replace, text), stripped
