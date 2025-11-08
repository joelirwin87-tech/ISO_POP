"""Adidas monitor implementation."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from .base import SiteMonitor

LOGGER = logging.getLogger(__name__)


class AdidasMonitor(SiteMonitor):
    async def fetch_products(self) -> List[Dict[str, Any]]:
        keyword_query = "+".join(self.keywords) if self.keywords else self.config.get("fallback_query", "yeezy")
        endpoint = self.config.get(
            "endpoint",
            f"https://www.adidas.com/api/plp/content-engine?sitePath=us&query={keyword_query}&start=0&count=48",
        )
        data = await self.request_client.get_json(endpoint)
        grid = data.get("grid", {})
        products: List[Dict[str, Any]] = []
        for item in grid.get("items", []):
            availability = item.get("availability", {})
            variation_list = availability.get("variation_list", [])
            sizes = {}
            for variant in variation_list:
                size_label = variant.get("size") or variant.get("sku") or "OS"
                sizes[size_label] = 1 if variant.get("availability") == "IN_STOCK" else 0
            product_id = item.get("id") or item.get("model_number")
            url = "https://www.adidas.com" + item.get("link", "")
            image = item.get("image", {}).get("src")
            price = item.get("price", {}).get("current_price", 0)
            products.append(
                {
                    "id": product_id,
                    "name": item.get("name", "Adidas Product"),
                    "price": f"{price:,.2f}",
                    "image": image,
                    "url": url,
                    "direct_to_cart": url,
                    "sizes": sizes,
                }
            )
        return products

    def build_embed(self, product: Dict[str, Any], diff: Dict[str, List[str]]) -> Dict[str, Any]:
        description = "\n".join(
            part
            for part in [
                f"New: {', '.join(diff['new_sizes'])}" if diff["new_sizes"] else "",
                f"Restocked: {', '.join(diff['restocks'])}" if diff["restocks"] else "",
                f"Sold out: {', '.join(diff['oos'])}" if diff["oos"] else "",
            ]
            if part
        ) or "Adidas inventory change"
        return {
            "title": f"{product['name']} (Adidas)",
            "url": product["url"],
            "description": description,
            "thumbnail": {"url": product.get("image", "")},
            "fields": [
                {"name": "Price", "value": f"${product.get('price', '0')}", "inline": True},
                {"name": "Sizes", "value": ", ".join(product.get("sizes", {}).keys()) or "N/A", "inline": False},
            ],
        }
