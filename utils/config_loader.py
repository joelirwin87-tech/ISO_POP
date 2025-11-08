"""Load and validate monitor configuration."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class ConfigError(Exception):
    """Raised when the configuration file is missing required keys."""


REQUIRED_ROOT_KEYS = {"stores", "discord_webhooks", "refresh_interval"}


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Configuration file {path} was not found.")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    missing = REQUIRED_ROOT_KEYS - data.keys()
    if missing:
        raise ConfigError(f"Configuration missing required keys: {', '.join(sorted(missing))}")

    if not isinstance(data["stores"], list) or not data["stores"]:
        raise ConfigError("Configuration must define at least one store entry.")

    if not isinstance(data["discord_webhooks"], list) or not data["discord_webhooks"]:
        raise ConfigError("Provide at least one Discord webhook URL in the configuration.")

    refresh = data.get("refresh_interval", 10)
    if not isinstance(refresh, (int, float)) or refresh <= 0:
        raise ConfigError("refresh_interval must be a positive number of seconds.")

    data.setdefault("keywords", [])
    return data
