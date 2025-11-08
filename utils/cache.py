"""In-memory cache for product states."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List


@dataclass
class ProductSnapshot:
    name: str
    sizes: Dict[str, int]
    price: str
    image: str
    url: str
    direct_to_cart: str


@dataclass
class ProductCache:
    _products: Dict[str, ProductSnapshot] = field(default_factory=dict)

    def diff(self, product_id: str, new_snapshot: ProductSnapshot) -> Dict[str, List[str]]:
        """Compare snapshots and return a diff dict describing changes."""
        previous = self._products.get(product_id)
        changes: Dict[str, List[str]] = {"new_sizes": [], "restocks": [], "oos": []}
        if previous is None:
            self._products[product_id] = new_snapshot
            changes["new_sizes"] = list(new_snapshot.sizes.keys())
            return changes

        for size, stock in new_snapshot.sizes.items():
            previous_stock = previous.sizes.get(size, 0)
            if previous_stock == 0 and stock > 0:
                changes["restocks"].append(size)

        for size, stock in previous.sizes.items():
            if stock > 0 and new_snapshot.sizes.get(size, 0) == 0:
                changes["oos"].append(size)

        self._products[product_id] = new_snapshot
        return changes

    def prune(self, valid_ids: Iterable[str]) -> None:
        valid_set = set(valid_ids)
        for product_id in list(self._products.keys()):
            if product_id not in valid_set:
                self._products.pop(product_id, None)
