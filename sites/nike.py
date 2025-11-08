"""Nike SNKRS monitor implementation."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from .base import SiteMonitor

LOGGER = logging.getLogger(__name__)


class NikeMonitor(SiteMonitor):
    async def fetch_products(self) -> List[Dict[str, Any]]:
        endpoint = self.config.get(
            "endpoint",
            "https://api.nike.com/product_feed/threads/v2/?filter=marketplace(US)&filter=language(en-US)&filter=channelId(snkrs_web_app)&count=20",
        )
        data = await self.request_client.get_json(endpoint)
        products: List[Dict[str, Any]] = []
        for thread in data.get("objects", []):
            product = thread.get("productInfo", [{}])[0]
            merch_product = product.get("merchProduct", {})
            sku_data = product.get("skus", [])
            sizes = {}
            for sku in sku_data:
                sizes[sku.get("countrySpecifications", [{}])[0].get("localizedSize", sku.get("nikeSize", "Unknown"))] = (
                    1 if sku.get("available", False) else 0
                )
            image_url = ""
            images = product.get("imageUrls", {})
            if images.get("productImageUrl"):
                image_url = images["productImageUrl"]
            url = product.get("launchView", {}).get("productUrl") or thread.get("publishedContent", {}).get("nodes", [{}])[0].get("url")
            if url and url.startswith("/"):
                url = f"https://www.nike.com{url}"
            price_obj = merch_product.get("price", {})
            price = price_obj.get("currentRetailPrice") or price_obj.get("msrp", 0)
            products.append(
                {
                    "id": merch_product.get("styleColor", thread.get("id")),
                    "name": merch_product.get("label", thread.get("title")),
                    "price": f"{price:,.2f}",
                    "image": image_url,
                    "url": url or "https://www.nike.com/launch",
                    "direct_to_cart": url or "https://www.nike.com/cart",
                    "sizes": sizes,
                }
            )
        return products

    def build_embed(self, product: Dict[str, Any], diff: Dict[str, List[str]]) -> Dict[str, Any]:
        description = " | ".join(
            part
            for part in [
                f"New sizes: {', '.join(diff['new_sizes'])}" if diff["new_sizes"] else "",
                f"Restocks: {', '.join(diff['restocks'])}" if diff["restocks"] else "",
                f"OOS: {', '.join(diff['oos'])}" if diff["oos"] else "",
            ]
            if part
        ) or "Nike stock change detected"
        return {
            "title": f"{product['name']} (Nike)",
            "url": product["url"],
            "description": description,
            "thumbnail": {"url": product.get("image", "")},
            "fields": [
                {"name": "Price", "value": f"${product.get('price', '0')}", "inline": True},
                {"name": "Sizes", "value": ", ".join(product.get("sizes", {}).keys()) or "N/A", "inline": False},
                {"name": "Direct", "value": product.get("direct_to_cart", "https://www.nike.com/cart"), "inline": False},
            ],
        }
