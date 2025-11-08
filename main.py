"""Entry point for the sneaker monitor service.

This script orchestrates the asynchronous monitors for each supported store. The
implementation intentionally mirrors Amenity.IO's behaviour while adding
extensive inline documentation to help operators understand rate limits,
scalability and extension points.
"""
from __future__ import annotations

import asyncio
import json
import logging
import signal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Type

import aiohttp

from sites.adidas import AdidasMonitor
from sites.footlocker import FootlockerMonitor
from sites.nike import NikeMonitor
from sites.shopify import ShopifyMonitor
from sites.snkrs import SnkrsMonitor
from sites.supreme import SupremeMonitor
from sites.yeezysupply import YeezySupplyMonitor
from sites.base import SiteMonitor
from utils.config_loader import ConfigError, load_config
from utils.logger import setup_logging
from utils.proxy_manager import ProxyManager
from utils.request import RequestClient

# Example Discord embed payload printed at startup so operators know exactly what
# will be sent to their webhook.
EXAMPLE_EMBED = {
    "title": "Nike Dunk Low Retro",
    "url": "https://www.nike.com/t/dunk-low-retro-shoe",
    "description": "New sizes: 8, 9 | Restocks: 10",
    "thumbnail": {"url": "https://static.nike.com/a/images/t_prod/p/nike-dunk.jpg"},
    "fields": [
        {"name": "Price", "value": "$120.00", "inline": True},
        {"name": "Sizes", "value": "7, 8, 9, 10", "inline": False},
        {
            "name": "Direct Cart",
            "value": "https://www.nike.com/t/dunk-low-retro-shoe",
            "inline": False,
        },
    ],
}

SITE_FACTORIES: Dict[str, Type[SiteMonitor]] = {
    "shopify": ShopifyMonitor,
    "nike": NikeMonitor,
    "adidas": AdidasMonitor,
    "footlocker": FootlockerMonitor,
    "supreme": SupremeMonitor,
    "yeezysupply": YeezySupplyMonitor,
    "snkrs": SnkrsMonitor,
}

LOGGER = logging.getLogger(__name__)


async def create_monitor(
    store: Dict[str, Any],
    *,
    session: aiohttp.ClientSession,
    proxy_manager: ProxyManager,
    global_keywords: Iterable[str],
    global_refresh: float,
    global_monitor_mode: str,
    webhooks: Iterable[str],
) -> SiteMonitor:
    """Instantiate a monitor for the provided store configuration.

    Inline guidance:
        * Rate limiting: keep `refresh_interval` above ~5 seconds for Shopify and
          Footlocker to avoid 429s. Supreme should be polled slower (15s+) due to
          aggressive bans, and YeezySupply is safest at 30s+.
        * Adding a new store: drop a module in ``sites/`` that subclasses
          :class:`SiteMonitor`, add it to ``SITE_FACTORIES`` here, and include a
          config entry with ``platform`` matching the key. Provide any
          store-specific endpoints inside the store block.
    """

    platform = store.get("platform", "").lower()
    if platform not in SITE_FACTORIES:
        raise ConfigError(f"Unsupported platform '{platform}' for store {store.get('name')}")

    monitor_cls = SITE_FACTORIES[platform]
    store_refresh = float(store.get("refresh_interval", global_refresh))
    # Use store specific keywords if supplied, otherwise fall back to global list.
    keywords = store.get("keywords") or list(global_keywords)
    # Safe polling intervals are also documented in the README; enforcing a
    # minimum of 3 seconds prevents hammering APIs during misconfiguration.
    store_refresh = max(3.0, store_refresh)

    request_client = RequestClient(
        session=session,
        proxy_manager=proxy_manager,
        max_retries=int(store.get("max_retries", 3)),
        backoff_factor=float(store.get("backoff_factor", 1.5)),
        timeout=int(store.get("timeout", 10)),
    )

    # Ensure monitor mode inherits from the root when omitted.
    store.setdefault(
        "monitor_mode",
        (store.get("monitor_mode") or global_monitor_mode).lower(),
    )

    monitor = monitor_cls(
        name=store.get("name", platform.title()),
        config=store,
        refresh_interval=store_refresh,
        keywords=keywords,
        discord_webhooks=webhooks,
        session=session,
        request_client=request_client,
    )
    return monitor


async def run_monitors(config_path: Path) -> None:
    setup_logging()
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        LOGGER.error("Configuration error: %s", exc)
        raise SystemExit(1) from exc

    LOGGER.info("Loaded configuration from %s", config_path)
    LOGGER.info("Example Discord embed: %s", json.dumps(EXAMPLE_EMBED, indent=2))

    proxy_manager = ProxyManager(config.get("proxies", []))
    if proxy_manager.enabled:
        LOGGER.info("Loaded %s proxies for rotation", len(config.get("proxies", [])))
    else:
        LOGGER.warning("No proxies configured; consider adding them to avoid 429 blocks")

    connector = aiohttp.TCPConnector(limit=100)
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        monitors = [
            await create_monitor(
                store,
                session=session,
                proxy_manager=proxy_manager,
                global_keywords=config.get("keywords", []),
                global_refresh=float(config.get("refresh_interval", 15)),
                global_monitor_mode=str(config.get("monitor_mode", "keywords")),
                webhooks=config.get("discord_webhooks", []),
            )
            for store in config.get("stores", [])
        ]

        if not monitors:
            LOGGER.error("No monitors created; ensure the stores list is populated.")
            return

        tasks = [asyncio.create_task(monitor.start()) for monitor in monitors]

        stop_event = asyncio.Event()

        def _handle_shutdown(*_: int) -> None:
            LOGGER.info("Shutdown signal received; stopping monitors...")
            stop_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _handle_shutdown)
            except NotImplementedError:
                # Windows event loop does not support signal handlers.
                pass

        await stop_event.wait()
        for monitor in monitors:
            await monitor.stop()
        await asyncio.gather(*tasks, return_exceptions=True)


def main() -> None:
    config_path = Path(__file__).parent / "config.json"
    asyncio.run(run_monitors(config_path))


if __name__ == "__main__":
    main()
