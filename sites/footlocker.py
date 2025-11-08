"""HTML scraper for Footlocker search results."""
from __future__ import annotations

import logging
from typing import Any, Dict, List
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from utils.request import fetch_text

from .parsers import iter_json_scripts

LOGGER = logging.getLogger(__name__)

SITE_NAME = "Footlocker"


def create_scraper(config: Dict[str, Any]):
    base_url = config.get("base_url", "https://www.footlocker.com")
    search_path = config.get("search_path", "/search")

    async def scrape(session, keyword):
        query = keyword or config.get("fallback_query", "")
        if not query:
            return []
        params = urlencode({"query": query})
        search_url = f"{base_url.rstrip('/')}{search_path}?{params}"
        html = await fetch_text(session, search_url)
        soup = BeautifulSoup(html, "html.parser")
        products: List[Dict[str, Any]] = []

        for payload in iter_json_scripts(soup, script_id="__NEXT_DATA__"):
            try:
                items = payload["props"]["pageProps"]["initialState"]["products"]["listing"]
            except KeyError:
                continue
            for item in items:
                title = item.get("name") or ""
                if keyword and keyword.lower() not in title.lower():
                    continue
                url = item.get("pdpLink") or ""
                if url.startswith("/"):
                    url = f"{base_url.rstrip('/')}{url}"
                price_raw = item.get("price") or item.get("salePrice")
                if isinstance(price_raw, (int, float)):
                    price = f"${price_raw:,.2f}"
                else:
                    price = str(price_raw) if price_raw else "Unknown"
                image = (item.get("images") or {}).get("productImage") or ""
                sizes = {}
                for size in item.get("sizes", []):
                    label = size.get("size") or size.get("displaySize")
                    available = size.get("available", False)
                    if label:
                        sizes[str(label)] = available
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
            LOGGER.debug("Footlocker scraper found no data for %s", search_url)
        return products

    return scrape
