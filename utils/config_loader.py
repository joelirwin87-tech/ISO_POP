"""Load and validate monitor configuration."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List


class ConfigError(Exception):
    """Raised when the configuration file is missing required keys."""


REQUIRED_ROOT_KEYS = {"stores", "discord_webhooks", "refresh_interval"}
PLACEHOLDER_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)(?::-(.*?))?\}")


def _resolve_placeholders(value: Any) -> Any:
    """Resolve ``${VAR}`` placeholders recursively using environment variables."""

    if isinstance(value, dict):
        return {key: _resolve_placeholders(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_resolve_placeholders(item) for item in value]
    if isinstance(value, str):
        def _replace(match: re.Match[str]) -> str:
            env_key = match.group(1)
            default = match.group(2)
            env_value = os.getenv(env_key)
            if env_value is None:
                if default is not None:
                    return default
                raise ConfigError(
                    f"Environment variable '{env_key}' is required but not set for placeholder '{match.group(0)}'."
                )
            return env_value

        return PLACEHOLDER_PATTERN.sub(_replace, value)
    return value


def _ensure_list(value: Any, *, allow_empty: bool, field_name: str) -> List[str]:
    if isinstance(value, list):
        entries = [str(item).strip() for item in value if str(item).strip()]
    elif isinstance(value, str):
        split_values = re.split(r"[\n,]", value)
        entries = [item.strip() for item in split_values if item.strip()]
    else:
        raise ConfigError(f"Field '{field_name}' must be a list or comma separated string.")

    if not entries and not allow_empty:
        raise ConfigError(f"Field '{field_name}' must contain at least one entry.")
    return entries


def _validate_stores(stores: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    validated: List[Dict[str, Any]] = []
    for raw_store in stores:
        if not isinstance(raw_store, dict):
            raise ConfigError("Store entries must be objects.")
        platform = raw_store.get("platform")
        if not platform:
            raise ConfigError("Each store entry requires a 'platform' key.")
        refresh_raw = raw_store.get("refresh_interval")
        refresh = float(refresh_raw or 0)
        if isinstance(refresh_raw, str):
            try:
                refresh = float(refresh_raw)
            except ValueError as exc:
                raise ConfigError(
                    f"Store '{raw_store.get('name', platform)}' has invalid refresh_interval."
                ) from exc
        if refresh and refresh < 3:
            raise ConfigError(
                f"Store '{raw_store.get('name', platform)}' has refresh_interval below 3 seconds."
            )
        if refresh:
            raw_store["refresh_interval"] = float(refresh)
        validated.append(raw_store)
    if not validated:
        raise ConfigError("Configuration must define at least one store entry.")
    return validated


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Configuration file {path} was not found.")

    with path.open("r", encoding="utf-8") as handle:
        raw_data = json.load(handle)

    missing = REQUIRED_ROOT_KEYS - raw_data.keys()
    if missing:
        raise ConfigError(f"Configuration missing required keys: {', '.join(sorted(missing))}")

    data = _resolve_placeholders(raw_data)

    data["discord_webhooks"] = _ensure_list(
        data.get("discord_webhooks"), allow_empty=False, field_name="discord_webhooks"
    )

    data.setdefault("proxies", [])
    data["proxies"] = _ensure_list(data.get("proxies", []), allow_empty=True, field_name="proxies")

    data.setdefault("keywords", [])
    if isinstance(data["keywords"], str):
        data["keywords"] = _ensure_list(data["keywords"], allow_empty=True, field_name="keywords")

    refresh = data.get("refresh_interval", 10)
    if isinstance(refresh, str) and refresh.strip():
        try:
            refresh = float(refresh)
        except ValueError as exc:
            raise ConfigError("refresh_interval must be numeric") from exc
    if not isinstance(refresh, (int, float)) or float(refresh) <= 0:
        raise ConfigError("refresh_interval must be a positive number of seconds.")
    data["refresh_interval"] = float(refresh)

    data["stores"] = _validate_stores(data.get("stores", []))
    data.setdefault("monitor_mode", "keywords")

    return data
