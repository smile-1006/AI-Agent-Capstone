"""Logging configuration.

Uses structlog to produce structured JSON logs suitable for production.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from app.settings import settings


def configure_logging() -> None:
    """Configure global logging.

    The project uses plain stdlib logging to keep runtime dependencies minimal.
    """

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )


def get_logger(**kwargs: Any) -> logging.Logger:
    """Get a logger.

    kwargs are accepted to preserve the call pattern; they are currently not
    injected into log records.
    """

    return logging.getLogger("ai-agent-capstone")


