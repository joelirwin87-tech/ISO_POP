"""Utility module for configuring structured logging across the monitor."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

try:
    from colorlog import ColoredFormatter
except ImportError:  # pragma: no cover - colorlog is optional at runtime.
    ColoredFormatter = None  # type: ignore[assignment]


def setup_logging(log_level: int = logging.INFO, log_path: Optional[Path] = None) -> None:
    """Configure application-wide logging handlers.

    Args:
        log_level: Minimum level for log messages.
        log_path: Optional file path for storing rolling log files.
    """
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    color_formatter: Optional[logging.Formatter] = None
    if ColoredFormatter is not None:
        color_formatter = ColoredFormatter(
            "%(log_color)s%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Ensure we do not attach duplicate handlers when re-running in notebooks or hot reloads.
    if not any(isinstance(handler, logging.StreamHandler) for handler in root_logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(color_formatter or formatter)
        root_logger.addHandler(console_handler)

    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
