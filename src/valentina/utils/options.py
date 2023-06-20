"""Reusable options for cogs and commands."""

import discord
from discord.commands import OptionChoice

from valentina import char_svc

_max_options = 25  # Maximum options discord allows for a select menu


async def select_character(ctx: discord.ApplicationContext) -> list[OptionChoice]:
    """Generate a list of the user's available characters.

    Note: ctx is passed in by by py-cord when the option is used.
    """
    if (guild := ctx.interaction.guild) is None:
        return []

    # TODO: Check for chars associated with a user
    characters = char_svc.fetch_all_characters(guild.id)
    chars = []
    for character in characters:
        char_id = character.id
        name = f"{character.name}"
        chars.append((name, char_id))

    name_search = ctx.value.casefold()

    found_chars = [
        OptionChoice(name, ident)
        for name, ident in sorted(chars)
        if name.casefold().startswith(name_search or "")
    ]

    if len(found_chars) > _max_options:
        instructions = "Keep typing ..." if ctx.value else "Start typing a name."
        return [OptionChoice(f"Too many characters to display. {instructions}", "")]

    return found_chars
