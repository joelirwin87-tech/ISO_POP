"""Generic site monitor built around HTML scrapers."""
from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Sequence

import aiohttp

from utils.cache import ProductCache, ProductSnapshot
from utils.discord import DiscordNotifier

LOGGER = logging.getLogger(__name__)

ScrapeResult = Dict[str, Any]
ScrapeFunc = Callable[[aiohttp.ClientSession, str], Awaitable[List[ScrapeResult]]]


@dataclass(frozen=True)
class MonitorConfig:
    name: str
    site: str
    refresh_interval: float
    jitter_range: Sequence[float]
    keywords: Sequence[str]
    scrape: ScrapeFunc


class SiteMonitor:
    """Polls a scraping function and emits Discord notifications on changes."""

    def __init__(
        self,
        config: MonitorConfig,
        session: aiohttp.ClientSession,
        notifier: DiscordNotifier,
    ) -> None:
        self._config = config
        self._session = session
        self._cache = ProductCache()
        self._running = False
        self._notifier = notifier

    async def start(self) -> None:
        self._running = True
        LOGGER.info("Starting monitor for %s", self._config.name)
        try:
            while self._running:
                await self._poll_once()
                await self._sleep_with_jitter()
        except asyncio.CancelledError:
            LOGGER.info("Monitor %s cancelled", self._config.name)
            raise
        except Exception:  # noqa: BLE001 - catch-all to protect orchestrator
            LOGGER.exception("Monitor %s crashed unexpectedly", self._config.name)
            await self._notifier.send_error(
                f"{self._config.name} monitor crashed",
                "Unexpected exception in monitor loop; see logs for details.",
            )
        finally:
            LOGGER.info("Monitor %s stopped", self._config.name)

    async def stop(self) -> None:
        self._running = False

    async def _poll_once(self) -> None:
        keywords = list(self._config.keywords) or [""]
        aggregated: List[ScrapeResult] = []
        for keyword in keywords:
            try:
                results = await self._config.scrape(self._session, keyword)
            except Exception as exc:  # noqa: BLE001 - surfaces parsing/network failures per keyword
                LOGGER.exception("%s scrape failed for keyword '%s'", self._config.name, keyword)
                notified = await self._notifier.send_error(
                    f"{self._config.name} scrape failed",
                    f"Keyword '{keyword}' failed with error: {exc}",
                )
                if not notified:
                    LOGGER.error(
                        "Failed to notify Discord about scrape error for %s", self._config.name
                    )
                continue
            LOGGER.debug("%s returned %s products for '%s'", self._config.name, len(results), keyword)
            for result in results:
                result.setdefault("site", self._config.site)
                result.setdefault("keyword", keyword)
            aggregated.extend(results)
            await asyncio.sleep(random.uniform(0.4, 1.1))

        if not aggregated:
            LOGGER.debug("%s produced no results on this poll", self._config.name)
            return

        identifiers = [product.get("url", "") for product in aggregated if product.get("url")]
        self._cache.prune(identifiers)

        for product in aggregated:
            url = product.get("url")
            if not url:
                continue
            snapshot = ProductSnapshot(
                title=product.get("title", "Unknown Product"),
                price=str(product.get("price", "N/A")),
                image=product.get("image", ""),
                url=url,
                site=product.get("site", self._config.site),
                sizes={size: bool(available) for size, available in product.get("sizes", {}).items()},
            )
            diff = self._cache.diff(url, snapshot)
            if diff["is_new"] or diff["new_sizes"] or diff["restocks"]:
                embed = self._build_embed(product, diff)
                ok = await self._notifier.send_embed(embed)
                if not ok:
                    LOGGER.error(
                        "Discord notification failed for %s (%s)",
                        self._config.name,
                        product.get("url", "unknown"),
                    )

    async def _sleep_with_jitter(self) -> None:
        base = self._config.refresh_interval
        jitter_low, jitter_high = self._config.jitter_range
        await asyncio.sleep(base + random.uniform(jitter_low, jitter_high))

    def _build_embed(self, product: ScrapeResult, diff: Dict[str, Any]) -> Dict[str, Any]:
        description_parts = []
        if diff.get("is_new"):
            description_parts.append("New product detected")
        if diff.get("new_sizes"):
            description_parts.append(f"New sizes: {', '.join(diff['new_sizes'])}")
        if diff.get("restocks"):
            description_parts.append(f"Restocks: {', '.join(diff['restocks'])}")
        if diff.get("oos"):
            description_parts.append(f"Now OOS: {', '.join(diff['oos'])}")

        description = " | ".join(description_parts) or f"Update detected on {self._config.site}"
        size_display = ", ".join(size for size, available in product.get("sizes", {}).items() if available)

        return {
            "title": product.get("title", "Unknown Product"),
            "url": product.get("url", ""),
            "description": description,
            "thumbnail": {"url": product.get("image", "")},
            "fields": [
                {"name": "Site", "value": product.get("site", self._config.site), "inline": True},
                {"name": "Price", "value": str(product.get("price", "N/A")), "inline": True},
                {"name": "Sizes", "value": size_display or "Unknown", "inline": False},
            ],
        }
