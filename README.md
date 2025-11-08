# Sneaker Monitor

This project is a fully asynchronous sneaker monitor inspired by Amenity.IO. It
supports Shopify, Nike, SNKRS, Adidas, Footlocker, Supreme, and YeezySupply
stores with keyword or URL based filtering, proxy rotation, and Discord webhook
alerts.

## Features

- Concurrent async polling (``aiohttp`` + ``asyncio``) for rapid store coverage.
- Modular architecture with site-specific scrapers in ``sites/`` and reusable
  helpers in ``utils/``.
- Rotating user agents and proxy pool support to mitigate bans.
- Intelligent retry logic with exponential backoff for HTTP failures.
- Discord embed notifications with product name, price, sizes, imagery, and
direct-to-cart links.
- Configurable via ``config.json`` (keywords, stores, refresh interval, webhooks,
  proxies, and monitor mode).

## Quick Start

1. Copy ``.env.example`` to ``.env`` and populate required secrets:
   ```bash
   cp .env.example .env
   ```
   At minimum set ``DISCORD_WEBHOOK_URLS``; ``PROXY_LIST`` accepts comma or newline separated proxy URLs.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Update ``config.json`` if you need to tweak stores, keywords, or monitor defaults. Secrets should stay in ``.env``.
4. Run the monitor:
   ```bash
   python main.py
   ```

Startup writes ``data/example_embed.json`` and posts a health-check embed (unless ``DISABLE_STARTUP_PING`` is ``true``) so you can verify Discord delivery immediately.

### Docker

```bash
docker compose up --build
```

The compose stack mounts ``config.json`` read-only, loads environment variables from ``.env``, and restarts the container automatically on failure.

## Configuration

``config.json`` contains global defaults and a list of stores. Each store entry
accepts:

- ``name``: Friendly name for logging.
- ``platform``: ``shopify``, ``nike``, ``snkrs``, ``adidas``, ``footlocker``,
  ``supreme``, or ``yeezysupply``.
- ``monitor_mode``: ``keywords`` or ``url``. URL mode expects ``product_ids``.
- ``refresh_interval``: Optional override per store (seconds). See inline
  comments in ``main.py`` for safe values to avoid rate limits.
- ``endpoint`` / ``base_url`` / ``fallback_query``: Optional knobs for
  fine-tuning API endpoints.

Global keys include ``keywords``, ``discord_webhooks``, ``proxies``, and the
fallback ``refresh_interval``. Environment placeholders such as ``${DISCORD_WEBHOOK_URLS}`` are resolved at runtime so secrets stay out of version control.

## Adding New Stores

1. Create a module under ``sites/`` that subclasses ``SiteMonitor``.
2. Implement ``fetch_products`` to normalize product data and
   ``build_embed`` for Discord payloads.
3. Register the new platform in ``SITE_FACTORIES`` inside ``main.py`` and add a
   store block to ``config.json``.

Inline comments throughout the code outline rate-limiting considerations and
extension tips.

## Example Discord Embed

```json
{
  "title": "Nike Dunk Low Retro",
  "url": "https://www.nike.com/t/dunk-low-retro-shoe",
  "description": "New sizes: 8, 9 | Restocks: 10",
  "thumbnail": {"url": "https://static.nike.com/a/images/t_prod/p/nike-dunk.jpg"},
  "fields": [
    {"name": "Price", "value": "$120.00", "inline": true},
    {"name": "Sizes", "value": "7, 8, 9, 10", "inline": false},
    {"name": "Direct Cart", "value": "https://www.nike.com/t/dunk-low-retro-shoe", "inline": false}
  ]
}
```

## Safety Notes

- Respect each site's terms of service and rate limits. Safe polling intervals are enforced at three seconds minimum per store to mitigate bans.
- Always route traffic through proxies you control.
- Monitor log output for 403/429 responses and adjust intervals accordingly.
- Log files write to ``logs/monitor.log`` and runtime artifacts are stored in ``cache/`` and ``data/``.
