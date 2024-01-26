"""Logging utilities for Valentina."""

import logging
import sys

from loguru import logger

from valentina.constants import LogLevel
from valentina.utils.helpers import get_config_value


def instantiate_logger(log_level: LogLevel | None = None) -> None:  # pragma: no cover
    """Instantiate the Loguru logger for Valentina.

    Configure the logger with the specified verbosity level, log file path,
    and whether to log to a file.

    Args:
        log_level (LogLevel): The verbosity level for the logger.

    Returns:
        None
    """
    if log_level:
        log_level_name = log_level.value
    else:
        log_level_name = LogLevel(get_config_value("VALENTINA_LOG_LEVEL", "INFO").upper())

    http_log_level = get_config_value("VALENTINA_LOG_LEVEL_HTTP", "INFO")
    aws_log_level = get_config_value("VALENTINA_LOG_LEVEL_AWS", "INFO")

    # Configure Loguru
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level_name,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>: <level>{message}</level>",
        enqueue=True,
    )
    logger.add(
        get_config_value("VALENTINA_LOG_FILE", "valentina.log"),
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
    logging.getLogger("faker").setLevel(level="INFO")
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
    def emit(record):  # type: ignore [no-untyped-def]
        """Intercepts standard logging and redirects to Loguru.

        This method is called by the Python logging module when a logging message is emitted. It intercepts the message and redirects it to Loguru, a third-party logging library. The method determines the corresponding Loguru level for the message and logs it using the Loguru logger.

        Args:
            record: A logging.LogRecord object representing the logging message.

        """
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
