"""Shared logger initialization for CLI scripts.

Usage:
    from utils.logger import get_logger
    log = get_logger(__name__)
    log.info("message")
"""
from __future__ import annotations

import logging
from typing import Optional

try:
    from rich.logging import RichHandler  # type: ignore

    _DEFAULT_HANDLER = RichHandler(rich_tracebacks=True, markup=True)
except ImportError:  # pragma: no cover
    _DEFAULT_HANDLER = logging.StreamHandler()


_FORMAT = "%(message)s"  # rich handler already adds time & level


def configure_logging(level: int = logging.INFO) -> None:
    """Idempotently configure root logger with a nicer handler."""
    root = logging.getLogger()
    if any(isinstance(h, (logging.StreamHandler,)) for h in root.handlers):
        # Assume already configured
        return
    root.setLevel(level)
    _DEFAULT_HANDLER.setLevel(level)
    formatter = logging.Formatter(_FORMAT)
    _DEFAULT_HANDLER.setFormatter(formatter)
    root.addHandler(_DEFAULT_HANDLER)


def get_logger(name: str = __name__, level: Optional[int] = None) -> logging.Logger:
    """Return a module-level logger (configuring root on first call)."""
    configure_logging()
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(level)
    return logger 