"""HTML scraper for Shopify stores."""
from __future__ import annotations

import logging
from typing import Any, Dict, List
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from utils.request import fetch_text

from .parsers import extract_ld_products

LOGGER = logging.getLogger(__name__)

SITE_NAME = "Shopify"


def create_scraper(config: Dict[str, Any]):
    base_url = config.get("base_url", "").rstrip("/")
    if not base_url:
        raise ValueError("Shopify scraper requires 'base_url' in the config")

    search_path = config.get("search_path", "/search?q={query}&type=product")
    async def scrape(session, keyword):
        query = keyword or config.get("fallback_query", "")
        if not query:
            return []

        search_url = urljoin(base_url, search_path.format(query=quote_plus(query)))
        html = await fetch_text(session, search_url)
        soup = BeautifulSoup(html, "html.parser")
        products: List[Dict[str, Any]] = []

        for product in extract_ld_products(soup):
            title = product.get("name", "").strip()
            if not title:
                continue
            if keyword and keyword.lower() not in title.lower():
                continue
            url = product.get("url") or ""
            if url.startswith("/"):
                url = urljoin(base_url, url)
            images = product.get("image", [])
            image = ""
            if isinstance(images, list) and images:
                image = images[0]
            elif isinstance(images, str):
                image = images
            offers = product.get("offers", {})
            price = "Unknown"
            sizes: Dict[str, bool] = {}
            if isinstance(offers, dict):
                price = offers.get("price") or offers.get("highPrice") or price
                sku = offers.get("sku")
                if sku:
                    sizes[sku] = True
            elif isinstance(offers, list):
                for offer in offers:
                    if isinstance(offer, dict):
                        price = offer.get("price") or price
                        sku = offer.get("sku") or offer.get("name")
                        if sku:
                            sizes[sku] = True

            # Fallback to product card markup if JSON-LD is sparse
            if not price:
                price = _extract_price_from_markup(soup, url)

            products.append(
                {
                    "title": title,
                    "url": url,
                    "image": image,
                    "price": price,
                    "sizes": sizes or {"OS": True},
                    "site": config.get("name", SITE_NAME),
                }
            )

        return products

    return scrape


def _extract_price_from_markup(soup: BeautifulSoup, url: str) -> str:
    anchor = soup.find("a", href=lambda href: isinstance(href, str) and href in {url, url.replace("https://", "http://")})
    if not anchor:
        return "Unknown"
    price_tag = anchor.find_next("span", class_=lambda c: c and "price" in c.lower())
    if price_tag and price_tag.text:
        return price_tag.text.strip()
    return "Unknown"
