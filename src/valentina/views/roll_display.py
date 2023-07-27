"""Display and manipulate roll outcomes."""

import discord

from valentina.models.dicerolls import DiceRoll
from valentina.utils.helpers import pluralize


class RollDisplay:
    """Display and manipulate roll outcomes."""

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
        self.trait_one_name = trait_one_name
        self.trait_one_value = trait_one_value
        self.trait_two_name = trait_two_name
        self.trait_two_value = trait_two_value

    async def get_embed(self) -> discord.Embed:
        """The graphical representation of the roll."""
        title = self.roll.takeaway

        embed = discord.Embed(title=title, colour=self.roll.embed_color)

        # Thumbnail
        embed.set_thumbnail(url=self.roll.thumbnail_url)

        roll_string = ""
        for die in self.roll.roll:
            roll_string += f"`{die}` "

        # Fields
        embed.add_field(
            name="",
            value=f"{self.ctx.author.display_name} rolled **{self.roll.pool}{self.roll.dice_type.name.lower()}**",
            inline=False,
        )
        embed.add_field(
            name=f"Dice: {roll_string}",
            value="",
            inline=False,
        )
        if self.roll.dice_type.name == "D10":
            embed.add_field(name="Pool", value=str(self.roll.pool), inline=True)
            embed.add_field(name="Difficulty", value=str(self.roll.difficulty), inline=True)

        if self.trait_one_name:
            embed.add_field(
                name="**Rolled Traits**",
                value=f"{self.trait_one_name}: `{self.trait_one_value} {pluralize(self.trait_one_value, 'die')}`\n{self.trait_two_name}: `{self.trait_two_value} {pluralize(self.trait_two_value, 'die')}`",
                inline=False,
            )

        if self.comment:
            embed.add_field(name="\u200b", value=f"**Comment**\n {self.comment}", inline=False)

        return embed

    async def display(self) -> None:
        """Display the roll."""
        embed = await self.get_embed()
        await self.ctx.respond(embed=embed)
