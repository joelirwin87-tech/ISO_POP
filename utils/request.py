"""HTTP helpers for direct scraping via aiohttp."""
from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any, Dict, Optional

import aiohttp

from .user_agent import random_user_agent

LOGGER = logging.getLogger(__name__)


def _build_headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    headers = {
        "User-Agent": random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    if extra:
        headers.update(extra)
    return headers


async def fetch_text(
    session: aiohttp.ClientSession,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 15,
    max_retries: int = 3,
    backoff_factor: float = 1.5,
) -> str:
    """Fetch a URL and return the response body as text."""

    attempt = 0
    while True:
        attempt += 1
        request_headers = _build_headers(headers)
        try:
            async with session.get(
                url,
                params=params,
                headers=request_headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status in {403, 429} and attempt < max_retries:
                    LOGGER.warning(
                        "Received %s from %s; retrying with backoff", response.status, url
                    )
                    await asyncio.sleep(_backoff_delay(backoff_factor, attempt))
                    continue
                response.raise_for_status()
                return await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            LOGGER.error("Request failure (%s) on %s: %s", attempt, url, exc)
            if attempt >= max_retries:
                raise
            await asyncio.sleep(_backoff_delay(backoff_factor, attempt))


async def fetch_json(
    session: aiohttp.ClientSession,
    url: str,
    **kwargs: Any,
) -> Any:
    """Fetch a URL returning JSON by parsing the text response."""

    text = await fetch_text(session, url, **kwargs)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        LOGGER.debug("Failed to parse JSON from %s: %s", url, text[:200])
        raise exc


def _backoff_delay(backoff_factor: float, attempt: int) -> float:
    jitter = random.uniform(0.4, 1.2)
    return backoff_factor * attempt + jitter
