"""Discord webhook helper."""
from __future__ import annotations

import asyncio
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
    tasks = []
    for webhook in webhook_urls:
        tasks.append(asyncio.create_task(send_embed(session, webhook, embed)))
    if not tasks:
        return
    for task in tasks:
        try:
            await task
        except aiohttp.ClientError as exc:
            LOGGER.error("Failed to deliver embed: %s", exc)
