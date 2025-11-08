"""Supreme monitor implementation using the public mobile_stock endpoint."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from .base import SiteMonitor

LOGGER = logging.getLogger(__name__)


class SupremeMonitor(SiteMonitor):
    async def fetch_products(self) -> List[Dict[str, Any]]:
        endpoint = self.config.get("endpoint", "https://www.supremenewyork.com/mobile_stock.json")
        data = await self.request_client.get_json(endpoint)
        products: List[Dict[str, Any]] = []
        for category_items in data.get("products_and_categories", {}).values():
            for item in category_items:
                product_id = str(item.get("id"))
                name = item.get("name", "Supreme Product")
                url = f"https://www.supremenewyork.com/shop/{product_id}"
                # Supreme requires a second call for style-specific stock.
                try:
                    detail_endpoint = f"https://www.supremenewyork.com/shop/{product_id}.json"
                    detail = await self.request_client.get_json(detail_endpoint)
                except Exception as exc:  # noqa: BLE001 - Supreme often rate limits.
                    LOGGER.debug("Failed to load detail for %s: %s", product_id, exc)
                    continue
                styles = detail.get("styles", [])
                for style in styles:
                    style_id = style.get("id")
                    image_url = style.get("image_url", "")
                    sizes = {}
                    for size in style.get("sizes", []):
                        sizes[size.get("name", "OS")] = 1 if size.get("stock_level", 0) > 0 else 0
                    products.append(
                        {
                            "id": f"{product_id}-{style_id}",
                            "name": f"{name} - {style.get('name', 'Default')}",
                            "price": f"{detail.get('price', 0) / 100:,.2f}",
                            "image": f"https:{image_url}",
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
        ) or "Supreme stock change"
        return {
            "title": product["name"],
            "url": product["url"],
            "description": description,
            "thumbnail": {"url": product.get("image", "")},
            "fields": [
                {"name": "Price", "value": f"${product.get('price', '0')}", "inline": True},
                {"name": "Sizes", "value": ", ".join(product.get("sizes", {}).keys()) or "N/A", "inline": False},
            ],
        }
