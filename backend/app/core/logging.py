"""
Sets up logging for the whole app.

"Structured logging" just means: instead of random text messages, every log
line has a consistent format (like a mini table), which makes it much easier
to search and debug later, especially once this runs in production.
"""

import logging
import sys

import structlog


def configure_logging(debug: bool = True) -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if debug else logging.INFO,
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer() if debug else structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    return structlog.get_logger(name)
