"""Utilities for serving randomized desktop and mobile user agents."""
from __future__ import annotations

import random
from typing import Optional

from fake_useragent import FakeUserAgent, FakeUserAgentError

_FALLBACK_USER_AGENTS = [
    # Curated list of recent desktop and mobile Chrome/Safari/Firefox user agents.
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.197 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.99 Mobile Safari/537.36",
]

_USER_AGENT_PROVIDER: Optional[FakeUserAgent] = None


def _get_provider() -> Optional[FakeUserAgent]:
    global _USER_AGENT_PROVIDER
    if _USER_AGENT_PROVIDER is None:
        try:
            _USER_AGENT_PROVIDER = FakeUserAgent()
        except FakeUserAgentError:
            _USER_AGENT_PROVIDER = None
    return _USER_AGENT_PROVIDER


def random_user_agent() -> str:
    """Return a random user agent string."""

    provider = _get_provider()
    if provider is not None:
        try:
            return provider.random
        except FakeUserAgentError:
            pass
    return random.choice(_FALLBACK_USER_AGENTS)
