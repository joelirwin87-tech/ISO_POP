"""Entry point for the sneaker monitor service."""
from __future__ import annotations

import asyncio
import logging
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable

import aiohttp

from sites import adidas, footlocker, nike, shopify, snkrs, supreme, yeezysupply
from sites.base import MonitorConfig, SiteMonitor
from utils.config_loader import ConfigError, load_config
from utils.discord import DiscordNotifier, resolve_webhook_url
from utils.logger import setup_logging
from utils.request import fetch_text
from utils.env import load_dotenv

LOGGER = logging.getLogger(__name__)

SCRAPER_FACTORIES = {
    "shopify": shopify.create_scraper,
    "nike": nike.create_scraper,
    "adidas": adidas.create_scraper,
    "footlocker": footlocker.create_scraper,
    "supreme": supreme.create_scraper,
    "yeezysupply": yeezysupply.create_scraper,
    "snkrs": snkrs.create_scraper,
}


async def create_monitor(
    store: Dict[str, Any],
    *,
    session: aiohttp.ClientSession,
    notifier: DiscordNotifier,
    global_keywords: Iterable[str],
    global_refresh: float,
) -> SiteMonitor:
    platform = store.get("platform", "").lower()
    if platform not in SCRAPER_FACTORIES:
        raise ConfigError(f"Unsupported platform '{platform}' for store {store.get('name')}")

    scraper_factory = SCRAPER_FACTORIES[platform]
    scrape_func = scraper_factory(store)

    store_refresh = max(5.0, float(store.get("refresh_interval", global_refresh)))
    keywords = store.get("keywords") or list(global_keywords)
    jitter_low = float(store.get("jitter_min", 0.5))
    jitter_high = float(store.get("jitter_max", 1.5))
    if jitter_low > jitter_high:
        jitter_low, jitter_high = jitter_high, jitter_low

    monitor_config = MonitorConfig(
        name=store.get("name", platform.title()),
        site=store.get("site", store.get("name", platform.title())),
        refresh_interval=store_refresh,
        jitter_range=(jitter_low, jitter_high),
        keywords=tuple(keywords),
        scrape=scrape_func,
    )
    return SiteMonitor(monitor_config, session, notifier)


async def perform_startup_checks(
    session: aiohttp.ClientSession, notifier: DiscordNotifier
) -> None:
    LOGGER.info("Performing startup connectivity checks")
    try:
        await fetch_text(
            session,
            "https://www.google.com/generate_204",
            timeout=5,
            max_retries=2,
            backoff_factor=1.0,
        )
    except Exception as exc:  # noqa: BLE001 - fail fast on connectivity issues
        LOGGER.error("Network connectivity check failed: %s", exc)
        raise SystemExit(1) from exc

    await notifier.ensure_ready()


async def run_monitors(config_path: Path) -> None:
    setup_logging()
    load_dotenv()
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        LOGGER.error("Configuration error: %s", exc)
        raise SystemExit(1) from exc

    LOGGER.info("Loaded configuration from %s", config_path)

    connector = aiohttp.TCPConnector(limit=20)
    timeout = aiohttp.ClientTimeout(total=25)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        notifier = DiscordNotifier(session, resolve_webhook_url())
        redacted = (
            f"{notifier.webhook_url[:40]}..." if len(notifier.webhook_url) > 43 else notifier.webhook_url
        )
        LOGGER.info("Using Discord webhook: %s", redacted)
        await perform_startup_checks(session, notifier)

        store_names = [
            store.get("name")
            or store.get("site")
            or store.get("platform", "Unknown Store").title()
            for store in config.get("stores", [])
        ]
        refresh_interval = float(config.get("refresh_interval", 15))
        timestamp = datetime.now(timezone.utc).isoformat()
        startup_embed = {
            "title": "Sneaker Monitor Active",
            "color": 0x00FFAA,
            "description": "Monitor service connected to Discord.",
            "fields": [
                {
                    "name": "Stores",
                    "value": "\n".join(store_names) if store_names else "None configured",
                    "inline": False,
                },
                {
                    "name": "Refresh Interval",
                    "value": f"{refresh_interval:.1f}s",
                    "inline": True,
                },
                {
                    "name": "Started",
                    "value": timestamp,
                    "inline": True,
                },
            ],
        }
        if not await notifier.send_embed(startup_embed):
            LOGGER.error("Failed to deliver startup embed to Discord")

        monitors = [
            await create_monitor(
                store,
                session=session,
                notifier=notifier,
                global_keywords=config.get("keywords", []),
                global_refresh=float(config.get("refresh_interval", 15)),
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
