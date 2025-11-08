"""Simple round-robin proxy manager with opt-in sticky sessions."""
from __future__ import annotations

import asyncio
import itertools
import random
from typing import Iterable, List, Optional


class ProxyManager:
    """Maintain a pool of proxies and provide rotation helpers."""

    def __init__(self, proxies: Iterable[str] | None = None) -> None:
        self._proxies = [proxy.strip() for proxy in proxies or [] if proxy.strip()]
        self._lock = asyncio.Lock()
        self._cycle = itertools.cycle(self._proxies) if self._proxies else None

    @property
    def proxies(self) -> List[str]:
        return list(self._proxies)

    @property
    def enabled(self) -> bool:
        return bool(self._proxies)

    async def next_proxy(self) -> Optional[str]:
        """Return the next proxy from the rotation.

        The rotation is protected by an asyncio lock to ensure we do not hand out
        the same proxy to concurrent tasks when the list is short.
        """
        if not self._cycle:
            return None
        async with self._lock:
            return next(self._cycle)

    def random_proxy(self) -> Optional[str]:
        """Return a random proxy without affecting the main rotation."""
        if not self._proxies:
            return None
        return random.choice(self._proxies)
