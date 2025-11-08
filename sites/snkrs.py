"""SNKRS monitor piggybacking on Nike product feed."""
from __future__ import annotations

from typing import Any, Dict, List

from .nike import NikeMonitor


class SnkrsMonitor(NikeMonitor):
    async def fetch_products(self) -> List[Dict[str, Any]]:
        # Override endpoint to specifically pull SNKRS launches by default.
        self.config.setdefault(
            "endpoint",
            "https://api.nike.com/product_feed/threads/v2/?filter=marketplace(US)&filter=language(en-US)&filter=channelId(snkrs_web_app)&count=40&filter=upcoming(true)",
        )
        return await super().fetch_products()

    def build_embed(self, product: Dict[str, Any], diff: Dict[str, List[str]]) -> Dict[str, Any]:
        embed = super().build_embed(product, diff)
        embed["title"] = f"{product['name']} (SNKRS)"
        return embed
