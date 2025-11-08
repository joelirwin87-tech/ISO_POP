"""Utility helpers for loading environment variables from a .env file."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict


def load_dotenv(path: Path | str = ".env") -> Dict[str, str]:
    """Load key/value pairs from ``path`` into ``os.environ``.

    This lightweight loader avoids introducing an additional dependency while
    supporting the subset of ``.env`` syntax needed for the monitor. Lines
    beginning with ``#`` or missing an ``=`` separator are ignored. Existing
    environment variables are preserved.
    """

    file_path = Path(path)
    if not file_path.exists():
        return {}

    loaded: Dict[str, str] = {}
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        loaded[key] = value
        os.environ.setdefault(key, value)
    return loaded
