"""HTML scraper for YeezySupply (mirrors Adidas infrastructure)."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from utils.request import fetch_text

from .parsers import iter_json_scripts

LOGGER = logging.getLogger(__name__)

SITE_NAME = "YeezySupply"


def create_scraper(config: Dict[str, Any]):
    base_url = config.get("base_url", "https://www.yeezysupply.com")

    async def scrape(session, keyword):
        html = await fetch_text(session, base_url)
        soup = BeautifulSoup(html, "html.parser")
        products: List[Dict[str, Any]] = []

        for payload in iter_json_scripts(soup, script_id="__NEXT_DATA__"):
            try:
                items = payload["props"]["pageProps"]["initialData"]["products"]
            except KeyError:
                continue
            for item in items:
                title = item.get("name") or ""
                if keyword and keyword.lower() not in title.lower():
                    continue
                url = item.get("pdpLink") or base_url
                price_raw = item.get("price")
                if isinstance(price_raw, (int, float)):
                    price = f"${price_raw:,.2f}"
                else:
                    price = str(price_raw) if price_raw else "Unknown"
                image = item.get("image") or ""
                sizes = {}
                for size in item.get("availability", {}).get("sizes", []):
                    if isinstance(size, dict):
                        label = size.get("size") or size.get("displaySize")
                        if label:
                            sizes[str(label)] = size.get("available", False)
                products.append(
                    {
                        "title": title,
                        "url": url,
                        "image": image,
                        "price": price,
                        "sizes": sizes,
                        "site": config.get("name", SITE_NAME),
                    }
                )

        if not products:
            LOGGER.debug("YeezySupply scraper found no structured payloads")
        return products

    return scrape
