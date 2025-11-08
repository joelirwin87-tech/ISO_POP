"""Health check utilities executed during service startup."""
from __future__ import annotations

import asyncio
import logging
from typing import Iterable
from urllib.parse import urlparse

import requests

from .discord import broadcast_embeds
from .proxy_manager import ProxyManager

LOGGER = logging.getLogger(__name__)


def validate_webhook_urls(webhooks: Iterable[str]) -> None:
    """Ensure webhook URLs resemble Discord endpoints."""

    for webhook in webhooks:
        parsed = urlparse(webhook)
        if parsed.scheme not in {"https", "http"}:
            raise ValueError(f"Webhook '{webhook}' must be http(s).")
        if "discord" not in parsed.netloc and "127.0.0.1" not in parsed.netloc and "localhost" not in parsed.netloc:
            raise ValueError(
                f"Webhook '{webhook}' does not look like a Discord endpoint; set DISABLE_WEBHOOK_VALIDATION to override."
            )
        if "/api/webhooks" not in parsed.path:
            LOGGER.warning("Webhook %s does not include '/api/webhooks'; double-check the URL.", webhook)


async def verify_proxy_connectivity(proxy_manager: ProxyManager, test_url: str = "https://www.google.com/generate_204") -> None:
    """Validate that outbound connectivity works (optionally via proxies)."""

    def _request(proxy: str | None) -> bool:
        proxies = {"http": proxy, "https": proxy} if proxy else None
        try:
            response = requests.get(test_url, proxies=proxies, timeout=5)
            response.raise_for_status()
            return True
        except requests.RequestException as exc:  # pragma: no cover - network errors depend on environment
            LOGGER.warning("Connectivity check failed via %s: %s", proxy or "direct", exc)
            return False

    if proxy_manager.enabled:
        for proxy in proxy_manager.proxies:
            if await asyncio.to_thread(_request, proxy):
                LOGGER.info("Connectivity check succeeded through proxy %s", proxy)
                return
        raise ConnectionError("All configured proxies failed the connectivity test.")

    if not await asyncio.to_thread(_request, None):
        raise ConnectionError("Direct internet connectivity test failed.")
    LOGGER.info("Connectivity check succeeded without proxies.")


async def send_startup_embed(session, webhooks, embed):
    """Send a health-check embed to confirm Discord delivery."""

    if not webhooks:
        return
    await broadcast_embeds(session, webhooks, embed)
