"""Discord webhook helper utilities."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

import aiohttp

LOGGER = logging.getLogger(__name__)

DEFAULT_WEBHOOK_URL = (
    "https://discord.com/api/webhooks/1436670362107514972/"
    "VmfmnFyiEn0NlPStjGNQOy_12yMW1zEjPfNR1cwqxz_HLfTwQwNlE9o2AieRbl5aFEXT"
)
ENV_WEBHOOK_KEY = "DISCORD_WEBHOOK"


def resolve_webhook_url() -> str:
    """Return the webhook URL from the environment or the default constant."""

    value = os.getenv(ENV_WEBHOOK_KEY, DEFAULT_WEBHOOK_URL).strip()
    return value or DEFAULT_WEBHOOK_URL


class DiscordNotifier:
    """Encapsulates Discord webhook delivery logic."""

    def __init__(self, session: aiohttp.ClientSession, webhook_url: str) -> None:
        self._session = session
        self._webhook_url = webhook_url

    @property
    def webhook_url(self) -> str:
        return self._webhook_url

    async def ensure_ready(self, retry_interval: float = 60.0) -> None:
        """Ensure the webhook is reachable, retrying until success."""

        while True:
            try:
                async with self._session.get(self._webhook_url) as response:
                    if response.status == 200:
                        LOGGER.info("Validated Discord webhook: %s", self._webhook_url)
                        return
                    text = await response.text()
                    LOGGER.error(
                        "Discord webhook validation failed (%s): %s", response.status, text
                    )
            except aiohttp.ClientError as exc:
                LOGGER.error("Discord webhook validation error: %s", exc)
            LOGGER.info("Retrying Discord webhook validation in %ss", retry_interval)
            await asyncio.sleep(retry_interval)

    async def send_embed(self, embed: Dict[str, Any]) -> bool:
        """Send an embed payload to the configured webhook."""

        payload = {"embeds": [embed]}
        try:
            async with self._session.post(self._webhook_url, json=payload) as response:
                if response.status >= 400:
                    text = await response.text()
                    LOGGER.error(
                        "Discord webhook error %s when sending embed: %s", response.status, text
                    )
                    return False
                LOGGER.info("Sent Discord embed: %s", embed.get("title", "(no title)"))
                return True
        except aiohttp.ClientError as exc:
            LOGGER.error("Failed to deliver embed to %s: %s", webhook, exc)


async def validate_webhook(session: aiohttp.ClientSession, webhook_url: str) -> bool:
    """Return ``True`` if the webhook URL is reachable and valid."""

    try:
        async with session.get(webhook_url) as response:
            if response.status == 200:
                LOGGER.info("Validated Discord webhook: %s", webhook_url)
                return True
            LOGGER.error(
                "Discord webhook validation failed for %s with status %s",
                webhook_url,
                response.status,
            )
            return False
    except aiohttp.ClientError as exc:
        LOGGER.error("Discord webhook validation error for %s: %s", webhook_url, exc)
        return False
