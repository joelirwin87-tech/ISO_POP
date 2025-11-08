"""Footlocker monitor implementation."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from .base import SiteMonitor

LOGGER = logging.getLogger(__name__)


class FootlockerMonitor(SiteMonitor):
    async def fetch_products(self) -> List[Dict[str, Any]]:
        keyword_query = "+".join(self.keywords) if self.keywords else self.config.get("fallback_query", "jordan")
        endpoint = self.config.get(
            "endpoint",
            f"https://www.footlocker.com/api/products/search?query={keyword_query}&count=20",
        )
        data = await self.request_client.get_json(endpoint)
        products: List[Dict[str, Any]] = []
        for product in data.get("results", []):
            product_id = product.get("id") or product.get("productId")
            sizes = {}
            for sku in product.get("skuInfo", []):
                sizes[sku.get("size", "One Size")] = 1 if sku.get("available", False) else 0
            image = product.get("imageUrl")
            url = f"https://www.footlocker.com/product/~/{product.get('urlKey', product_id)}.html"
            price = product.get("price", {}).get("currentPrice", 0)
            products.append(
                {
                    "id": product_id,
                    "name": product.get("name", "Footlocker Product"),
                    "price": f"{price:,.2f}",
                    "image": image,
                    "url": url,
                    "direct_to_cart": url,
                    "sizes": sizes,
                }
            )
        return products

    def build_embed(self, product: Dict[str, Any], diff: Dict[str, List[str]]) -> Dict[str, Any]:
        parts = []
        if diff["new_sizes"]:
            parts.append(f"New: {', '.join(diff['new_sizes'])}")
        if diff["restocks"]:
            parts.append(f"Restock: {', '.join(diff['restocks'])}")
        if diff["oos"]:
            parts.append(f"OOS: {', '.join(diff['oos'])}")
        description = " | ".join(parts) or "Footlocker change detected"
        return {
            "title": f"{product['name']} (Footlocker)",
            "url": product["url"],
            "description": description,
            "thumbnail": {"url": product.get("image", "")},
            "fields": [
                {"name": "Price", "value": f"${product.get('price', '0')}", "inline": True},
                {"name": "Sizes", "value": ", ".join(product.get("sizes", {}).keys()) or "N/A", "inline": False},
            ],
        }
