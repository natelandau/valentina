"""Utilities to allow the webui to interact with Discord."""

import inspect
from datetime import UTC, datetime
from typing import Literal

from flask_discord.models import User as FlaskDiscordUser
from loguru import logger

from valentina.constants import EmbedColor
from valentina.models import User
from valentina.webui import discord_oauth

from .helpers import fetch_guild, fetch_user


def log_to_logfile(msg: str, level: str = "INFO", user: User = None) -> None:  # pragma: no cover
    """Log a message to the console and log file with contextual information.

    Determine the appropriate logging context (module and function name) based
    on the call stack, then log the provided message with the given log level.
    If a user is provided, append the username to the log entry.

    Args:
        msg (str): The message to be logged.
        level (str, optional): The log level (e.g., "INFO", "ERROR"). Defaults to "INFO".
        user (User, optional): The user associated with the log entry. Defaults to None.

    Returns:
        None
    """
    username = f"@{user.name}" if user else ""

    if inspect.stack()[1].function == "log_message" and inspect.stack()[2].function in {
        "post_to_audit_log",
        "post_to_error_log",
    }:
        name1 = inspect.stack()[3].filename.split("/")[-3].split(".")[0]
        name2 = inspect.stack()[3].filename.split("/")[-2].split(".")[0]
        name3 = inspect.stack()[3].filename.split("/")[-1].split(".")[0]
        new_name = f"{name1}.{name2}.{name3}"
    elif inspect.stack()[1].function == "log_message":
        name1 = inspect.stack()[2].filename.split("/")[-3].split(".")[0]
        name2 = inspect.stack()[2].filename.split("/")[-2].split(".")[0]
        name3 = inspect.stack()[2].filename.split("/")[-1].split(".")[0]
        new_name = f"{name1}.{name2}.{name3}"
    else:
        name1 = inspect.stack()[1].filename.split("/")[-3].split(".")[0]
        name2 = inspect.stack()[1].filename.split("/")[-2].split(".")[0]
        name3 = inspect.stack()[1].filename.split("/")[-1].split(".")[0]
        new_name = f"{name1}.{name2}.{name3}"

    logger.patch(lambda r: r.update(name=new_name)).log(  # type: ignore [call-arg]
        level.upper(), f"{msg} [{username}]"
    )


async def log_message(
    log_type: Literal["audit", "error"],
    msg: str,
    level: str = "INFO",
    view: str = "",
) -> None:
    """Log a message to the console, log file, and Discord.

    Fetch the current user and log the message with the specified level.
    Then, send the log message to a designated Discord channel based on the
    log type (either "audit" or "error"). If a user or view is provided,
    include this information in the log entry's footer.

    Args:
        log_type (Literal["audit", "error"]): The type of log, determining the
        Discord channel (audit or error log).
        msg (str): The message to be logged.
        level (str, optional): The log level (e.g., "INFO", "ERROR"). Defaults to "INFO".
        view (str, optional): The name of the view or context in which the log is generated.
        Defaults to an empty string.

    Returns:
        None
    """
    user = await fetch_user()
    log_to_logfile(msg, level, user)

    guild = await fetch_guild()
    if not guild:
        return None

    channel = guild.channels.error_log if log_type == "error" else guild.channels.audit_log
    if not channel:
        return None

    footer = ""
    footer += f"User: @{user.name}" if user and user.name else ""
    footer += " | " if user and user.name and view else ""
    footer += f"WebUI: {view}" if view else ""

    return discord_oauth.bot_request(
        f"/channels/{channel}/messages",
        "POST",
        json={
            "embeds": [
                {
                    "color": EmbedColor[level.upper()].value,
                    "title": msg,
                    "description": "",
                    "footer": {"text": f"{footer}"},
                    "timestamp": str(datetime.now(UTC)),
                }
            ],
        },
    )


async def post_to_audit_log(msg: str, level: str = "INFO", view: str = "") -> None:
    """Send a message to the audit log channel for a guild.

    Log the provided message with the specified level and view context to the
    audit log channel.

    Args:
        msg (str): The message to be logged.
        level (str, optional): The log level (e.g., "INFO", "ERROR"). Defaults to "INFO".
        view (str, optional): The name of the view or context in which the log is generated.
        Defaults to an empty string.

    Returns:
        None
    """
    await log_message("audit", msg, level, view)


async def post_to_error_log(msg: str, level: str = "ERROR", view: str = "") -> None:
    """Send a message to the error log channel for a guild.

    Log the provided message with the specified level and view context to the
    error log channel.

    Args:
        msg (str): The message to be logged.
        level (str, optional): The log level (e.g., "ERROR", "WARNING"). Defaults to "ERROR".
        view (str, optional): The name of the view or context in which the log is generated.
        Defaults to an empty string.

    Returns:
        None
    """
    await log_message("error", msg, level, view)


async def send_user_dm(user: FlaskDiscordUser, message: str) -> dict | str:
    """Send a private message to a user on Discord.

    Create a direct message channel with the specified user and send the
    provided message to that channel.

    Args:
        user (FlaskDiscordUser): The user to whom the message will be sent.
        message (str): The content of the message to send.

    Returns:
        dict | str: The response from the Discord API, either as a dictionary
        or a string indicating the result of the message send operation.
    """
    dm_channel = discord_oauth.bot_request(
        "/users/@me/channels", "POST", json={"recipient_id": user.id}
    )
    return discord_oauth.bot_request(
        f"/channels/{dm_channel['id']}/messages",
        "POST",
        json={"content": message},
    )
