"""Common base class for store monitors."""
from __future__ import annotations

import abc
import asyncio
import logging
from typing import Any, Dict, Iterable, List

import aiohttp

from utils.cache import ProductCache, ProductSnapshot
from utils.discord import broadcast_embeds
from utils.request import RequestClient

LOGGER = logging.getLogger(__name__)


class SiteMonitor(abc.ABC):
    """Abstract base class implementing common polling logic."""

    def __init__(
        self,
        name: str,
        config: Dict[str, Any],
        refresh_interval: float,
        keywords: Iterable[str],
        discord_webhooks: Iterable[str],
        session: aiohttp.ClientSession,
        request_client: RequestClient,
    ) -> None:
        self.name = name
        self.config = config
        self.refresh_interval = refresh_interval
        self.keywords = [kw.lower() for kw in keywords]
        self.webhooks = list(discord_webhooks)
        self.session = session
        self.request_client = request_client
        self.cache = ProductCache()
        self.monitor_mode = config.get("monitor_mode", "keywords")
        self._running = True

    async def start(self) -> None:
        """Continuously poll the site until cancelled."""
        LOGGER.info("Starting monitor for %s", self.name)
        while self._running:
            try:
                await self._poll_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - we want to catch everything here.
                LOGGER.exception("Monitor %s encountered an error: %s", self.name, exc)
            await asyncio.sleep(self.refresh_interval)

    async def stop(self) -> None:
        self._running = False

    async def _poll_once(self) -> None:
        products = await self.fetch_products()
        filtered = self.filter_products(products)
        await self._handle_products(filtered)

    def filter_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self.monitor_mode == "keywords" and self.keywords:
            filtered = []
            for product in products:
                name = product.get("name", "").lower()
                if any(keyword in name for keyword in self.keywords):
                    filtered.append(product)
            return filtered
        if self.monitor_mode == "url":
            allowed_ids = {entry.lower() for entry in self.config.get("product_ids", [])}
            allowed_urls = {entry.lower() for entry in self.config.get("product_urls", [])}
            if not (allowed_ids or allowed_urls):
                return products
            filtered: List[Dict[str, Any]] = []
            for product in products:
                product_id = product.get("id", "").lower()
                product_url = product.get("url", "").lower()
                if (allowed_ids and product_id in allowed_ids) or (
                    allowed_urls and product_url in allowed_urls
                ):
                    filtered.append(product)
            return filtered
        return products

    async def _handle_products(self, products: List[Dict[str, Any]]) -> None:
        valid_ids = [product["id"] for product in products if "id" in product]
        self.cache.prune(valid_ids)
        for product in products:
            product_id = product.get("id")
            if not product_id:
                continue
            snapshot = ProductSnapshot(
                name=product.get("name", "Unknown Product"),
                sizes=product.get("sizes", {}),
                price=product.get("price", "N/A"),
                image=product.get("image", ""),
                url=product.get("url", ""),
                direct_to_cart=product.get("direct_to_cart", ""),
            )
            diff = self.cache.diff(product_id, snapshot)
            if diff["new_sizes"] or diff["restocks"]:
                embed = self.build_embed(product, diff)
                await broadcast_embeds(self.session, self.webhooks, embed)

    @abc.abstractmethod
    async def fetch_products(self) -> List[Dict[str, Any]]:
        """Return a list of normalized product dictionaries."""

    @abc.abstractmethod
    def build_embed(self, product: Dict[str, Any], diff: Dict[str, List[str]]) -> Dict[str, Any]:
        """Construct a Discord embed payload for notifications."""
