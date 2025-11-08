"""Shopify monitor implementation."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from .base import SiteMonitor

LOGGER = logging.getLogger(__name__)


class ShopifyMonitor(SiteMonitor):
    async def fetch_products(self) -> List[Dict[str, Any]]:
        endpoint = self.config.get("endpoint")
        base_url = self.config.get("base_url", "").rstrip("/")
        if not endpoint:
            endpoint = f"{base_url}/products.json?limit=250"
        data = await self.request_client.get_json(endpoint)
        products: List[Dict[str, Any]] = []
        for product in data.get("products", []):
            variants = product.get("variants", [])
            sizes = {}
            for variant in variants:
                available = variant.get("available", False)
                stock = 1 if available else 0
                title = variant.get("title", "One Size")
                sizes[title] = stock
            image_url = ""
            if product.get("images"):
                image_url = product["images"][0].get("src", "")
            product_id = str(product.get("id"))
            url = f"{base_url}/products/{product.get('handle')}"
            direct_to_cart = ""
            if variants:
                first_variant_id = variants[0].get("id")
                if first_variant_id:
                    direct_to_cart = f"{base_url}/cart/{first_variant_id}:1"
            products.append(
                {
                    "id": product_id,
                    "name": product.get("title", "Unknown"),
                    "price": product.get("variants", [{}])[0].get("price", "0"),
                    "image": image_url,
                    "url": url,
                    "direct_to_cart": direct_to_cart,
                    "sizes": sizes,
                }
            )
        return products

    def build_embed(self, product: Dict[str, Any], diff: Dict[str, List[str]]) -> Dict[str, Any]:
        description_parts = []
        if diff["new_sizes"]:
            description_parts.append(f"New sizes: {', '.join(diff['new_sizes'])}")
        if diff["restocks"]:
            description_parts.append(f"Restocked: {', '.join(diff['restocks'])}")
        if diff["oos"]:
            description_parts.append(f"Now OOS: {', '.join(diff['oos'])}")
        description = "\n".join(description_parts) or "Inventory change detected"
        return {
            "title": product["name"],
            "url": product["url"],
            "description": description,
            "thumbnail": {"url": product.get("image", "")},
            "fields": [
                {"name": "Price", "value": f"${product.get('price', '0')}", "inline": True},
                {"name": "Sizes", "value": ", ".join(product.get("sizes", {}).keys()) or "N/A", "inline": False},
                {"name": "Direct Cart", "value": product.get("direct_to_cart", "N/A"), "inline": False},
            ],
        }
