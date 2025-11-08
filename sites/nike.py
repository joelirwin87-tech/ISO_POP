"""HTML scraper for Nike retail listings."""
from __future__ import annotations

import logging
from typing import Any, Dict, List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from utils.request import fetch_text

from .parsers import iter_json_scripts

LOGGER = logging.getLogger(__name__)

SITE_NAME = "Nike"


def create_scraper(config: Dict[str, Any]):
    base_url = config.get("base_url", "https://www.nike.com")
    search_path = config.get("search_path", "/w?q={query}")

    async def scrape(session, keyword):
        query = keyword or config.get("fallback_query", "")
        if not query:
            return []
        search_url = f"{base_url.rstrip('/')}{search_path.format(query=quote_plus(query))}"
        html = await fetch_text(session, search_url)
        soup = BeautifulSoup(html, "html.parser")
        products: List[Dict[str, Any]] = []

        for payload in iter_json_scripts(soup, script_id="__NEXT_DATA__"):
            data = payload
            try:
                items = (
                    data["props"]["pageProps"]["initialState"]["Wall"]["products"]["products"]
                )
            except KeyError:
                continue
            for item in items:
                title = item.get("title") or item.get("fullTitle") or ""
                if keyword and keyword.lower() not in title.lower():
                    continue
                url = item.get("pdpUrl") or ""
                if url.startswith("/"):
                    url = f"{base_url.rstrip('/')}{url}"
                price_raw = item.get("price", {}).get("currentRetailPrice") or item.get("price", {}).get("msrp")
                if isinstance(price_raw, (int, float)):
                    price = f"${price_raw:,.2f}"
                else:
                    price = str(price_raw) if price_raw else "Unknown"
                image = item.get("imageUrl") or ""
                sizes = {}
                for sku in item.get("skus", []):
                    size = sku.get("nikeSize") or sku.get("sizeDescription")
                    if size:
                        sizes[str(size)] = sku.get("available", False)
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
            LOGGER.debug("Nike scraper found no JSON payloads for %s", search_url)
        return products

    return scrape
