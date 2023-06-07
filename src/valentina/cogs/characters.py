# mypy: disable-error-code="valid-type"
"""Gameplay cog for Valentina."""

import discord
from discord.commands import Option
from discord.ext import commands

from valentina import Valentina
from valentina.character.create import create_character
from valentina.models.constants import CharClass

possible_classes = [char_class.value for char_class in CharClass]


class Characters(commands.Cog, name="Character Management"):
    """Commands for characters."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    chars = discord.SlashCommandGroup("character", "Work with characters")

    @chars.command(name="create", description="Create a new character.")
    async def create_character(
        self,
        ctx: discord.ApplicationContext,
        char_class: Option(
            str,
            name="class",
            description="The character's class",
            choices=[char_class.value for char_class in CharClass],
        ),
        first_name: Option(str, "The character's name"),
        last_name: Option(str, "The character's last name", required=False, default=None),
    ) -> None:
        """Create a new character.

        Args:
            char_class (CharClass): The character's class
            ctx (discord.ApplicationContext): The context of the command
            first_name (str): The character's first name
            last_name (str, optional): The character's last name. Defaults to None.
        """
        await create_character(ctx, char_class, first_name, last_name)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Characters(bot))
