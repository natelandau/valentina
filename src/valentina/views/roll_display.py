"""Display and manipulate roll outcomes."""

from dataclasses import dataclass

import discord

from valentina.models.dicerolls import DiceRoll
from valentina.utils.helpers import pluralize


@dataclass
class _Trait:
    """Class to store Trait information.

    Attributes:
        name (str): The name of the trait.
        value (int): The value of the trait.
    """

    name: str | None
    value: int


#############################################################################
class RollDisplay:
    """Display and manipulate roll outcomes.

    This class is responsible for creating an embed message representing a roll.
    """

    def __init__(
        self,
        ctx: discord.ApplicationContext,
        roll: DiceRoll,
        comment: str | None = None,
        trait_one_name: str | None = None,
        trait_one_value: int = 0,
        trait_two_name: str | None = None,
        trait_two_value: int = 0,
    ):
        self.ctx = ctx
        self.roll = roll
        self.comment = comment
        self.trait_one = _Trait(trait_one_name, trait_one_value)
        self.trait_two = _Trait(trait_two_name, trait_two_value)

    def _add_comment_field(self, embed: discord.Embed) -> discord.Embed:
        """Add the comment field to the embed."""
        if self.comment:
            embed.add_field(name="\u200b", value=f"**Comment**\n {self.comment}", inline=False)

        return embed

    def _add_roll_fields(self, embed: discord.Embed) -> discord.Embed:
        """Add the roll fields to the embed."""
        roll_string = " ".join(f"`{die}`" for die in self.roll.roll)

        embed.add_field(
            name="\u200b",
            value=f"{self.ctx.author.display_name} rolled **{self.roll.pool}{self.roll.dice_type.name.lower()}**",
            inline=False,
        )
        embed.add_field(
            name=f"Dice: {roll_string}",
            value="\u200b",
            inline=False,
        )
        if self.roll.dice_type.name == "D10":
            embed.add_field(name="Pool", value=str(self.roll.pool), inline=True)
            embed.add_field(name="Difficulty", value=str(self.roll.difficulty), inline=True)

        return embed

    def _add_trait_fields(self, embed: discord.Embed) -> discord.Embed:
        """Add the trait fields to the embed."""
        if self.trait_one.name:
            embed.add_field(
                name="**Rolled Traits**",
                value=f"{self.trait_one.name}: `{self.trait_one.value} {pluralize(self.trait_one.value, 'die')}`\n{self.trait_two.name}: `{self.trait_two.value} {pluralize(self.trait_two.value, 'die')}`",
                inline=False,
            )

        return embed

    async def get_embed(self) -> discord.Embed:
        """The graphical representation of the roll."""
        title = self.roll.takeaway

        embed = discord.Embed(title=title, colour=self.roll.embed_color)

        # Thumbnail
        embed.set_thumbnail(url=self.roll.thumbnail_url)

        embed = self._add_roll_fields(embed)
        embed = self._add_trait_fields(embed)
        return self._add_comment_field(embed)

    async def display(self) -> None:
        """Display the roll."""
        embed = await self.get_embed()
        await self.ctx.respond(embed=embed)
