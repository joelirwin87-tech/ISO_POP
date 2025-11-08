# Sneaker Monitor

An asynchronous sneaker monitor that scrapes retailer HTML directly without any
private APIs or proxy infrastructure. The monitor targets Shopify, Nike, SNKRS,
Adidas, Footlocker, Supreme, and YeezySupply stores and publishes Discord
notifications whenever new inventory appears or sizes restock.

## Key Features

- Pure HTML scraping using `aiohttp` + `beautifulsoup4`; no API keys or proxies
  required.
- Randomised user-agents and headers on every request plus jittered polling
  intervals to mimic organic browsing patterns.
- Site-specific scrapers that parse JSON-LD, Next.js payloads, and semantic
  markup to normalise `{title, url, image, price, sizes, site}` records.
- Resilient retry logic with exponential backoff to gracefully handle transient
  rate limiting and throttling responses.
- Discord embeds with product imagery, pricing, and size availability.
- Graceful shutdown handling and colourised structured logging.

## How it Avoids Detection Without Proxies

1. **Header Randomisation** – every request receives a fresh desktop or mobile
   user-agent string alongside realistic Accept and language headers.
2. **Jittered Polling** – monitors sleep for the configured refresh interval plus
   a random delay, preventing predictable scraping intervals that trigger rate
   limiters.
3. **Keyword Fan-out Throttling** – keywords are processed sequentially with
   per-keyword delays, reducing burst load on retailer infrastructure.
4. **Backoff on Bans** – HTTP 403/429 responses trigger exponential backoff with
   jitter before retrying, allowing load balancers to recover.
5. **Minimal Concurrency** – a conservative aiohttp connector limit ensures the
   monitor never floods a single host with parallel sockets.

These techniques spread load across time so requests blend into regular customer
traffic even when running without proxies.

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Update `config.json` with your Discord webhook(s), keywords, and store
   definitions.
3. Run the monitor:
   ```bash
   python main.py
   ```

At startup the monitor verifies outbound network connectivity, checks that each
Discord webhook is valid, and prints an example embed payload. When products are
found or sizes restock an embed is dispatched to every configured webhook.

## Configuration Overview

`config.json` contains global defaults plus a list of store objects. Each store
supports:

- `name`: Friendly label used in logs.
- `platform`: One of `shopify`, `nike`, `snkrs`, `adidas`, `footlocker`,
  `supreme`, or `yeezysupply`.
- `keywords`: Optional override for global keywords.
- `refresh_interval`: Polling interval in seconds (minimum 5s is enforced).
- `jitter_min` / `jitter_max`: Optional jitter applied after each poll.
- Platform-specific knobs such as `base_url`, `search_path`, or
  `catalog_path`.

Global keys include `keywords`, `refresh_interval`, and `discord_webhooks`.

## Adding New Stores

1. Create a module in `sites/` that exposes `create_scraper(config)` and returns
   an async `scrape(session, keyword)` coroutine.
2. Parse the target site's HTML (JSON-LD, embedded scripts, or markup) and
   return normalised product dictionaries with `{title, url, image, price, sizes,
   site}`.
3. Register the factory in `main.py`'s `SCRAPER_FACTORIES` mapping and add an
   entry to `config.json`.

Each scraper automatically inherits caching, Discord notifications, and polling
behaviour from the shared `SiteMonitor` base.

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

- Respect each retailer's terms of service and rate limits.
- Provide accurate keywords to keep requests scoped to relevant inventory.
- Monitor logs for repeated 403/429 responses and increase refresh intervals if
  required.
