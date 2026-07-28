import logging
import sys

import structlog
from structlog.types import Processor

from kalshi_bot.config import Settings


def configure_logging(settings: Settings) -> None:
    renderer: Processor

    if settings.environment == "development":
        renderer = structlog.dev.ConsoleRenderer(
            colors=sys.stdout.isatty(),
        )
    else:
        renderer = structlog.processors.JSONRenderer()

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.log_level,
        force=True,
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(
                fmt="iso",
                utc=True,
            ),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
