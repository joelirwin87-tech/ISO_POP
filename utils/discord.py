"""Discord webhook helper."""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable

import aiohttp

LOGGER = logging.getLogger(__name__)


async def send_embed(session: aiohttp.ClientSession, webhook_url: str, embed: Dict[str, Any]) -> None:
    payload = {"embeds": [embed]}
    async with session.post(webhook_url, json=payload) as response:
        if response.status >= 400:
            text = await response.text()
            LOGGER.error("Discord webhook error %s: %s", response.status, text)
        else:
            LOGGER.info("Sent Discord notification: %s", embed.get("title", "(no title)"))


async def broadcast_embeds(
    session: aiohttp.ClientSession, webhook_urls: Iterable[str], embed: Dict[str, Any]
) -> None:
    for webhook in webhook_urls:
        try:
            await send_embed(session, webhook, embed)
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
