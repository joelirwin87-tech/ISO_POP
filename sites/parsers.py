"""Shared HTML parsing helpers for store scrapers."""
from __future__ import annotations

import json
from typing import Any, Iterable, Iterator, List

from bs4 import BeautifulSoup


def iter_json_scripts(
    soup: BeautifulSoup,
    *,
    script_id: str | None = None,
    script_type: str | None = None,
) -> Iterator[Any]:
    """Yield JSON payloads embedded in ``<script>`` tags."""

    scripts = soup.find_all("script", id=script_id, type=script_type)
    if not scripts and script_id is not None:
        tag = soup.find("script", id=script_id)
        scripts = [tag] if tag else []
    if not scripts and script_type is not None:
        scripts = soup.find_all("script", type=script_type)

    for script in scripts:
        text = script.string or script.text or ""
        if not text.strip():
            continue
        try:
            yield json.loads(text)
        except json.JSONDecodeError:
            continue


def flatten_json_payloads(payloads: Iterable[Any]) -> Iterator[Any]:
    """Recursively yield JSON objects from nested payloads."""

    for payload in payloads:
        if isinstance(payload, list):
            yield from flatten_json_payloads(payload)
        elif isinstance(payload, dict):
            yield payload


def extract_ld_products(soup: BeautifulSoup) -> List[dict[str, Any]]:
    """Return product dictionaries from JSON-LD entries."""

    products: List[dict[str, Any]] = []
    for payload in flatten_json_payloads(iter_json_scripts(soup, script_type="application/ld+json")):
        if payload.get("@type") in {"Product", "ListItem"}:
            if payload.get("@type") == "ListItem" and isinstance(payload.get("item"), dict):
                candidate = payload["item"]
            else:
                candidate = payload
            if isinstance(candidate, dict) and candidate.get("@type") == "Product":
                products.append(candidate)
    return products
