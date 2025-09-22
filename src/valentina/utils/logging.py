"""Logging utilities for Valentina."""

import logging
import sys

from loguru import logger

from valentina.constants import LogLevel
from valentina.utils import ValentinaConfig


def instantiate_logger(log_level: LogLevel | None = None) -> None:  # pragma: no cover
    """Instantiate the Loguru logger for Valentina.

    Configure the logger with the specified verbosity level, log file path,
    and whether to log to a file.

    Args:
        log_level (LogLevel): The verbosity level for the logger.

    Returns:
        None
    """
    log_level_name = log_level.value if log_level else ValentinaConfig().log_level

    http_log_level = ValentinaConfig().log_level_http
    aws_log_level = ValentinaConfig().log_level_aws

    # Configure Loguru
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level_name,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>: <level>{message}</level> | <level>{extra}</level>",
        enqueue=True,
    )
    logger.add(
        ValentinaConfig().log_file,
        level=log_level_name,
        rotation="10 MB",
        retention=3,
        compression="zip",
        enqueue=True,
    )

    # Intercept standard discord.py logs and redirect to Loguru
    logging.getLogger("discord.http").setLevel(level=http_log_level.upper())
    logging.getLogger("discord.gateway").setLevel(level=http_log_level.upper())
    logging.getLogger("discord.webhook").setLevel(level=http_log_level.upper())
    logging.getLogger("discord.client").setLevel(level=http_log_level.upper())
    logging.getLogger("pymongo").setLevel(level=ValentinaConfig().log_level_pymongo.upper())
    logging.getLogger("faker").setLevel(level="INFO")
    logging.getLogger("hypercorn").setLevel(level=ValentinaConfig().webui_log_level.upper())
    logging.getLogger("requests_oauthlib").setLevel(level="INFO")
    logging.getLogger("quart.app").setLevel(level=ValentinaConfig().webui_log_level.upper())
    logging.getLogger("quart_wtf").setLevel(level=ValentinaConfig().webui_log_level.upper())
    logging.getLogger("jinjax").setLevel(level="INFO")
    logging.getLogger("asyncio").setLevel(level="ERROR")

    for service in ["urllib3", "boto3", "botocore", "s3transfer"]:
        logging.getLogger(service).setLevel(level=aws_log_level.upper())

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


class InterceptHandler(logging.Handler):
    """Intercepts standard logging and redirects to Loguru.

    This class is a logging handler that intercepts standard logging messages and redirects them to Loguru, a third-party logging library. When a logging message is emitted, this handler determines the corresponding Loguru level for the message and logs it using the Loguru logger.

    Methods:
        emit: Intercepts standard logging and redirects to Loguru.

    Examples:
    To use the InterceptHandler with the Python logging module:
    ```
    import logging
    from logging import StreamHandler

    from loguru import logger

    # Create a new InterceptHandler and add it to the Python logging module.
    intercept_handler = InterceptHandler()
    logging.basicConfig(handlers=[StreamHandler(), intercept_handler], level=logging.INFO)

    # Log a message using the Python logging module.
    logging.info("This message will be intercepted by the InterceptHandler and logged using Loguru.")
    ```
    """

    @staticmethod
    def emit(record: logging.LogRecord) -> None:
        """Intercepts standard logging and redirects to Loguru.

        This method is called by the Python logging module when a logging message is emitted. It intercepts the message and redirects it to Loguru, a third-party logging library. The method determines the corresponding Loguru level for the message and logs it using the Loguru logger.

        Args:
            record: A logging.LogRecord object representing the logging message.
        """
        # Get corresponding Loguru level if it exists.
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno  # type: ignore [assignment]

        # Find caller from where originated the logged message.
        frame, depth = sys._getframe(6), 6  # noqa: SLF001
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
