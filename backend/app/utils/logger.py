import logging
import sys

import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
)


def get_logger(name: str) -> structlog.BoundLogger:
    """Return a bound structlog logger for the given module name.

    Usage:
        logger = get_logger(__name__)
        logger.info("event_name", key="value")
    """
    return structlog.get_logger(name)
