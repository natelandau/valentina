"""Utilities to allow the webui to interact with Discord."""

import inspect
from datetime import UTC, datetime
from typing import Literal

from loguru import logger

from valentina.constants import EmbedColor
from valentina.models import User
from valentina.webui import discord_oauth

from .helpers import fetch_guild, fetch_user


def log_to_logfile(msg: str, level: str = "INFO", user: User = None) -> None:  # pragma: no cover
    """Log the command to the console and log file."""
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
    """Log the message to the console, log file, and Discord."""
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
    """Send a message to the audit log channel for a guild."""
    await log_message("audit", msg, level, view)


async def post_to_error_log(msg: str, level: str = "ERROR", view: str = "") -> None:
    """Send a message to the error log channel for a guild."""
    await log_message("error", msg, level, view)
