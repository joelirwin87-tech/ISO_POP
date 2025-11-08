"""HTML scraper for Nike SNKRS launches."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from utils.request import fetch_text

from .parsers import iter_json_scripts

LOGGER = logging.getLogger(__name__)

SITE_NAME = "SNKRS"


def create_scraper(config: Dict[str, Any]):
    base_url = config.get("base_url", "https://www.nike.com/launch")

    async def scrape(session, keyword):
        html = await fetch_text(session, base_url)
        soup = BeautifulSoup(html, "html.parser")
        products: List[Dict[str, Any]] = []

        for payload in iter_json_scripts(soup, script_id="__NEXT_DATA__"):
            try:
                items = payload["props"]["pageProps"]["initialState"]["threads"]["objects"]
            except KeyError:
                continue
            for item in items:
                product = item.get("productInfo", [{}])[0]
                merch = product.get("merchProduct", {})
                title = merch.get("label") or item.get("title") or ""
                if keyword and keyword.lower() not in title.lower():
                    continue
                url = product.get("launchView", {}).get("productUrl") or item.get("url") or base_url
                if url.startswith("/"):
                    url = f"https://www.nike.com{url}"
                image = product.get("imageUrls", {}).get("productImageUrl") or ""
                price_raw = merch.get("price", {}).get("currentRetailPrice") or merch.get("price", {}).get("msrp")
                if isinstance(price_raw, (int, float)):
                    price = f"${price_raw:,.2f}"
                else:
                    price = str(price_raw) if price_raw else "Unknown"
                sizes = {}
                for sku in product.get("skus", []):
                    size = sku.get("nikeSize") or sku.get("localizedSize")
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
            LOGGER.debug("SNKRS scraper found no structured payloads")
        return products

    return scrape
