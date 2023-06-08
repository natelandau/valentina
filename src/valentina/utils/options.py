"""Reusable options for cogs and commands."""

import discord
from discord.commands import Option, OptionChoice

from valentina import char_svc

_max_options = 25  # Maximum options discord allows for a select menu


def character_select(description="The character to use", required=False) -> Option:  # type: ignore [no-untyped-def]
    """Return an Option that generates a list of player characters. When used, the user will be prompted to select a character from a list of available characters. When selected, the character's database id will be passed to the command."""
    return Option(str, description, autocomplete=_available_characters, required=required)


async def _available_characters(ctx: discord.ApplicationContext) -> list[OptionChoice]:
    """Generate a list of the user's available characters.

    Note: ctx is passed in by by pycord when the option is used.

    """
    if (guild := ctx.interaction.guild) is None:
        return []

    # TODO: Check for chars associated with a user
    characters = char_svc.fetch_all(guild.id)
    chars = []
    for character in characters:
        char_id = character.id
        name = f"{character.first_name}"
        name += f" {character.last_name}" if character.last_name else ""
        name += f" ({character.nickname})" if character.nickname else ""
        chars.append((name, str(char_id)))

    name_search = ctx.value.casefold()

    found_chars = [
        OptionChoice(name, ident)
        for name, ident in chars
        if name.casefold().startswith(name_search or "")
    ]

    if len(found_chars) > _max_options:
        instructions = "Keep typing ..." if ctx.value else "Start typing a name."
        return [OptionChoice(f"Too many characters to display. {instructions}", "")]

    return found_chars
