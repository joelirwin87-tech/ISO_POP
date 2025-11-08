"""Utility module for configuring structured logging across the monitor."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from colorlog import ColoredFormatter


def setup_logging(log_level: int = logging.INFO, log_path: Optional[Path] = None) -> None:
    """Configure application-wide logging handlers."""

    standard_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_formatter = ColoredFormatter(
        "%(log_color)s%(asctime)s | %(levelname)s | %(name)s | %(message)s",  # type: ignore[arg-type]
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "blue",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if not any(isinstance(handler, logging.StreamHandler) for handler in root_logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3)
        file_handler.setFormatter(standard_formatter)
        root_logger.addHandler(file_handler)
