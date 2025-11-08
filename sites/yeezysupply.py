"""YeezySupply monitor implementation."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from utils.request import RequestClient

from .base import SiteMonitor

LOGGER = logging.getLogger(__name__)


class YeezySupplyMonitor(SiteMonitor):
    async def fetch_products(self) -> List[Dict[str, Any]]:
        request_client: RequestClient = self.config["request_client"]
        endpoint = self.config.get("endpoint", "https://www.yeezysupply.com/api/yeezy/releases")
        try:
            data = await request_client.get_json(endpoint)
        except Exception as exc:  # noqa: BLE001 - the endpoint is notoriously unstable.
            LOGGER.warning("Failed to fetch YeezySupply data from %s: %s", endpoint, exc)
            return []
        products: List[Dict[str, Any]] = []
        releases = data.get("releases") or data.get("items") or []
        for release in releases:
            product_id = release.get("id") or release.get("pid") or release.get("product_id")
            name = release.get("name", "Yeezy Product")
            price = release.get("price", {}).get("amount") or release.get("price", 0)
            image = release.get("image", release.get("imageUrl", ""))
            url = release.get("link", "https://www.yeezysupply.com/")
            sizes = {}
            for size in release.get("availability", {}).get("sizes", []):
                size_label = size.get("name") or size.get("size") or "OS"
                sizes[size_label] = 1 if size.get("available", False) else 0
            products.append(
                {
                    "id": product_id,
                    "name": name,
                    "price": f"{float(price):,.2f}" if price else "0",
                    "image": image,
                    "url": url,
                    "direct_to_cart": url,
                    "sizes": sizes,
                }
            )
        return products

    def build_embed(self, product: Dict[str, Any], diff: Dict[str, List[str]]) -> Dict[str, Any]:
        description = " | ".join(
            part
            for part in [
                f"New: {', '.join(diff['new_sizes'])}" if diff["new_sizes"] else "",
                f"Restock: {', '.join(diff['restocks'])}" if diff["restocks"] else "",
                f"Sold out: {', '.join(diff['oos'])}" if diff["oos"] else "",
            ]
            if part
        ) or "YeezySupply update"
        return {
            "title": product.get("name", "YeezySupply Product"),
            "url": product.get("url", "https://www.yeezysupply.com/"),
            "description": description,
            "thumbnail": {"url": product.get("image", "")},
            "fields": [
                {"name": "Price", "value": f"${product.get('price', '0')}", "inline": True},
                {"name": "Sizes", "value": ", ".join(product.get("sizes", {}).keys()) or "N/A", "inline": False},
            ],
        }
