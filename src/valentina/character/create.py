"""Create a character."""

import re
from types import SimpleNamespace

import discord
from loguru import logger
from peewee import fn

from valentina.character.wizard import Wizard
from valentina.models.database import Character
from valentina.views.errors import present_error


async def create_character(
    ctx: discord.ApplicationContext, char_class: str, first_name: str, last_name: str = None
) -> None:
    """Create a character."""
    try:
        # Remove extraenous spaces from the name
        first_name = re.sub(r"\s+", " ", first_name).strip()
        last_name = re.sub(r"\s+", " ", last_name).strip() if last_name else None

        __validate_name(first_name, last_name)

        parameters = SimpleNamespace(
            char_class=char_class, first_name=first_name, last_name=last_name
        )
        character_wizard = Wizard(ctx, parameters)
        await character_wizard.begin_chargen()

    except ValueError as e:
        await present_error(ctx, str(e))


def __validate_name(first_name: str, last_name: str | None) -> None:
    """Validate the name of the character.

    Args:
        first_name (str): The first name of the character
        last_name (str|None): The last name of the character
    """
    errors = []
    max_len = 30

    if (name_len := len(first_name)) > max_len:
        errors.append(f"`{first_name}` is too long by {name_len - max_len} characters.")

    if not re.match(r"^[a-zA-Z0-9 _-]+$", first_name):
        errors.append(
            "Character first names may only contain letters, spaces, hyphens, and underscores."
        )

    if last_name:
        if (name_len := len(last_name)) > max_len:
            errors.append(f"`{last_name}` is too long by {name_len - max_len} characters.")

        if not re.match(r"^[a-zA-Z0-9 _-]+$", last_name):
            errors.append(
                "Character last names may only contain letters, spaces, hyphens, and underscores."
            )

    if last_name is not None:
        query = (
            fn.LOWER(Character.last_name)
            == last_name.lower() & fn.LOWER(Character.first_name)
            == first_name.lower()
        )
        if len(Character.select().where(query)) > 0:
            errors.append(f"A character with the name `{first_name} {last_name}` already exists.")
    else:
        query = fn.LOWER(Character.first_name) == first_name.lower()
        if len(Character.select().where(query)) > 0:
            errors.append(f"A character with the name `{first_name}` already exists.")

    if errors:
        logger.warning(f"Invalid character name: {first_name} {last_name}")
        err = "\n".join(errors)
        raise ValueError(err)
