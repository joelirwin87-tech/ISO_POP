"""HTTP helpers built on aiohttp with retry and proxy support."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp

from .proxy_manager import ProxyManager
from .user_agent import random_user_agent

LOGGER = logging.getLogger(__name__)


class RequestClient:
    """Wrapper around :class:`aiohttp.ClientSession` that injects resiliency."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        proxy_manager: ProxyManager,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        timeout: int = 10,
    ) -> None:
        self._session = session
        self._proxy_manager = proxy_manager
        self._max_retries = max(1, max_retries)
        self._backoff_factor = max(0.1, backoff_factor)
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    async def _request(self, method: str, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        headers = kwargs.pop("headers", {})
        headers.setdefault("User-Agent", random_user_agent())
        headers.setdefault("Accept", "application/json, text/plain, */*")
        headers.setdefault("Accept-Language", "en-US,en;q=0.9")

        proxy = kwargs.pop("proxy", None)
        if proxy:
            LOGGER.debug("Using provided proxy %s", proxy)

        attempt = 0
        while True:
            attempt += 1
            chosen_proxy = proxy
            if chosen_proxy is None:
                chosen_proxy = await self._proxy_manager.next_proxy()
            try:
                response = await self._session.request(
                    method,
                    url,
                    headers=headers,
                    proxy=chosen_proxy,
                    timeout=self._timeout,
                    **kwargs,
                )
                if response.status in {403, 429}:
                    LOGGER.warning("Received %s from %s, rotating proxy", response.status, url)
                    await response.release()
                    if attempt >= self._max_retries:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=f"Failed after {attempt} attempts",
                            headers=response.headers,
                        )
                    await asyncio.sleep(self._backoff(attempt))
                    continue
                response.raise_for_status()
                return response
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                LOGGER.error("Request error on %s attempt %s: %s", url, attempt, exc)
                if attempt >= self._max_retries:
                    raise
                await asyncio.sleep(self._backoff(attempt))

    def _backoff(self, attempt: int) -> float:
        return self._backoff_factor * attempt

    async def get_json(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        async with await self._request("GET", url, **kwargs) as response:
            try:
                return await response.json()
            except aiohttp.ContentTypeError:
                text = await response.text()
                LOGGER.debug("Non-JSON response from %s: %s", url, text[:200])
                raise

    async def get_text(self, url: str, **kwargs: Any) -> str:
        async with await self._request("GET", url, **kwargs) as response:
            return await response.text()
