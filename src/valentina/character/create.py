"""Create a character."""

import re

import discord
from loguru import logger
from peewee import fn

from valentina.character.views import CharGenModal, SelectClan
from valentina.character.wizard import Wizard
from valentina.models.database import Character, Guild
from valentina.views import present_embed


async def create_character(
    ctx: discord.ApplicationContext,
    quick_char: bool,
    char_class: str,
    first_name: str,
    last_name: str,
    nickname: str | None = None,
) -> None:
    """Create a character.

    Args:
        char_class (str): The character's class
        ctx (discord.ApplicationContext): The context of the command
        first_name (str): The character's first name
        last_name (str, optional): The character's last name. Defaults to None.
        nickname (str, optional): The character's nickname. Defaults to None.
        quick_char (bool, optional): Create a character with only essential traits?.
    """
    try:
        # Instantiate the property dictionary
        properties: dict[str, str | int] = {}

        # Remove extraenous spaces from the name
        first_name = re.sub(r"\s+", " ", first_name).strip()
        last_name = re.sub(r"\s+", " ", last_name).strip() if last_name else None

        # Validate the name to ensure uniqueness and correct values
        for n in first_name, last_name, nickname:
            if n:
                __validate_name(n)
        __unique_name(ctx, first_name, last_name, nickname)

        properties["first_name"] = first_name.title()
        properties["last_name"] = last_name.title() if last_name else None
        properties["nickname"] = nickname.title() if nickname else None
        properties["char_class"] = char_class

        # Gather universal trait information from the CharGenModal. This modal is used b/c these traits have a value that can be higher than 5 which is the maximum number of buttons presented in the wizard
        modal = CharGenModal(title="Additional character information", char_class=char_class)
        await ctx.send_modal(modal)
        await modal.wait()
        properties["humanity"] = int(modal.humanity) if modal.humanity else 0
        properties["willpower"] = int(modal.willpower) if modal.willpower else 0
        properties["arete"] = int(modal.arete) if modal.arete else 0
        properties["quintessence"] = int(modal.quintessence) if modal.quintessence else 0
        properties["rage"] = int(modal.rage) if modal.rage else 0
        properties["gnosis"] = int(modal.gnosis) if modal.gnosis else 0
        properties["blood_pool"] = int(modal.blood_pool) if modal.blood_pool else 0
        properties["conviction"] = int(modal.conviction) if modal.conviction else 0
        properties["faith"] = int(modal.faith) if modal.faith else 0

        ## VAMPIRE SPECIFIC #####################################################
        # If the character is a vampire, get the clan
        vampire_clan: str | None = None
        if char_class.lower() == "vampire":
            view = SelectClan(ctx.author)

            await ctx.send("Select a clan", view=view)
            await view.wait()
            vampire_clan = view.value

        properties["vampire_clan"] = vampire_clan

        ## START THE CHARGEN WIZARD #####################################################
        character_wizard = Wizard(ctx, quick_char=quick_char, properties=properties)
        await character_wizard.begin_chargen()

    except ValueError as e:
        logger.debug(f"CHARGEN: User input did not validate: {e}")
        await present_embed(
            ctx, title="Error in Character Generation", description=str(e), level="ERROR"
        )


def __validate_name(name: str) -> None:
    """Validates names (first, last, and nicknames).

    Args:
        name (str): The name to validate
    """
    errors = []
    max_len = 30

    if (name_len := len(name)) > max_len:
        errors.append(f"`{name}` is too long by {name_len - max_len} characters.")

    if not re.match(r"^[a-zA-Z0-9 _-]+$", name):
        errors.append("`{name}` may only contain letters, spaces, hyphens, and underscores.")


def __unique_name(
    ctx: discord.ApplicationContext, first_name: str, last_name: str | None, nickname: str | None
) -> None:
    """Ensure that the name of the character is unique in the database."""
    errors = []
    first_name = first_name.lower() if first_name else None
    last_name = last_name.lower() if last_name else None
    nickname = nickname.lower() if nickname else None

    if last_name is not None:
        search = (
            fn.LOWER(Character.first_name)
            == first_name & fn.LOWER(Character.last_name)
            == last_name
        )
    else:
        search = fn.LOWER(Character.first_name) == first_name

    query = Character.select().where(search).join(Guild).where(Guild.id == ctx.guild.id)
    if len(query) > 0:
        if last_name is not None:
            errors.append(f"A character with the name `{first_name} {last_name}` already exists.")
        else:
            errors.append(f"A character with the name `{first_name}` already exists.")

    if nickname is not None:
        query = (
            Character.select()
            .where(fn.LOWER(Character.nickname) == nickname)
            .join(Guild)
            .where(Guild.id == ctx.guild.id)
        )
        if len(query) > 0:
            errors.append(f"A character with the nickname `{nickname}` already exists.")

    if errors:
        err = "\n".join(errors)
        raise ValueError(err)
