"""Logging utilities for Valentina."""
import logging
import sys

from loguru import logger


class InterceptHandler(logging.Handler):
    """Intercepts standard logging and redirects to Loguru."""

    def emit(self, record):  # type: ignore [no-untyped-def]
        """Intercepts standard logging and redirects to Loguru."""
        # Get corresponding Loguru level if it exists.
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
