"""HTML scraper for Supreme product listings."""
from __future__ import annotations

import logging
from typing import Any, Dict, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from utils.request import fetch_text

LOGGER = logging.getLogger(__name__)

SITE_NAME = "Supreme"


def create_scraper(config: Dict[str, Any]):
    base_url = config.get("base_url", "https://www.supremenewyork.com")
    catalog_path = config.get("catalog_path", "/shop/all")

    async def scrape(session, keyword):
        html = await fetch_text(session, f"{base_url.rstrip('/')}{catalog_path}")
        soup = BeautifulSoup(html, "html.parser")
        products: List[Dict[str, Any]] = []

        for product in soup.select("ul#shop-scroller li a"):
            title = " ".join(product.stripped_strings)
            if keyword and keyword.lower() not in title.lower():
                continue
            url = urljoin(base_url, product.get("href", ""))
            image_tag = product.find("img")
            image = urljoin(base_url, image_tag["src"]) if image_tag and image_tag.get("src") else ""
            price_tag = product.find("span", class_="price")
            price = price_tag.text.strip() if price_tag else "Unknown"
            products.append(
                {
                    "title": title,
                    "url": url,
                    "image": image,
                    "price": price,
                    "sizes": {},
                    "site": config.get("name", SITE_NAME),
                }
            )

        if not products:
            LOGGER.debug("Supreme scraper found no matches for keyword '%s'", keyword)
        return products

    return scrape
