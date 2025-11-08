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

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(The monitor only requires ``aiohttp``; feel free to install it manually if
you prefer not to create a requirements file.)*
2. Update ``config.json`` with real webhook URLs, stores, and optional proxies.
3. Run the monitor:
   ```bash
   python main.py
   ```

The service prints an example Discord embed payload at startup so you can verify
the message structure before enabling alerts.

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
fallback ``refresh_interval``.

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

- Respect each site's terms of service and rate limits.
- Always route traffic through proxies you control.
- Monitor log output for 403/429 responses and adjust intervals accordingly.
