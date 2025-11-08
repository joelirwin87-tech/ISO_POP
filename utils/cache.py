"""In-memory cache for product states."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List


@dataclass
class ProductSnapshot:
    title: str
    price: str
    image: str
    url: str
    site: str
    sizes: Dict[str, bool]


@dataclass
class ProductCache:
    _products: Dict[str, ProductSnapshot] = field(default_factory=dict)

    def diff(self, product_id: str, new_snapshot: ProductSnapshot) -> Dict[str, List[str] | bool]:
        """Compare snapshots and return a diff dict describing changes."""
        previous = self._products.get(product_id)
        changes: Dict[str, List[str] | bool] = {
            "new_sizes": [],
            "restocks": [],
            "oos": [],
            "is_new": False,
        }
        if previous is None:
            self._products[product_id] = new_snapshot
            changes["new_sizes"] = [size for size, available in new_snapshot.sizes.items() if available]
            changes["is_new"] = True
            return changes

        for size, stock in new_snapshot.sizes.items():
            previous_stock = previous.sizes.get(size, 0)
            if not previous_stock and stock:
                changes["restocks"].append(size)

        for size, stock in previous.sizes.items():
            if stock and not new_snapshot.sizes.get(size, False):
                changes["oos"].append(size)

        self._products[product_id] = new_snapshot
        return changes

    def prune(self, valid_ids: Iterable[str]) -> None:
        valid_set = set(valid_ids)
        for product_id in list(self._products.keys()):
            if product_id not in valid_set:
                self._products.pop(product_id, None)
