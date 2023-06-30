"""Display and manipulate roll outcomes."""

import discord

from valentina.models.dicerolls import DiceRoll


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
        embed.set_thumbnail(
            url=self.roll.thumbnail_url,
        )
        embed.description = f"\u200b\n**{self.ctx.author.display_name} rolled {self.roll.pool}{self.roll.dice_type.name.lower()}**"

        roll_string = ""
        for die in self.roll.roll:
            roll_string += f"`{die}` "

        # Fields
        embed.add_field(name="\u200b", value="**ROLL DETAILS**", inline=False)
        embed.add_field(name="Roll", value=roll_string, inline=False)
        if self.roll.dice_type.name == "D10":
            embed.add_field(name="Pool", value=str(self.roll.pool), inline=True)
            embed.add_field(name="Difficulty", value=str(self.roll.difficulty), inline=True)

        if self.trait_one_name:
            embed.add_field(name="\u200b", value="**Rolled Traits**", inline=False)
            embed.add_field(name=self.trait_one_name, value=str(self.trait_one_value), inline=True)

        if self.trait_two_name:
            embed.add_field(name=self.trait_two_name, value=str(self.trait_two_value), inline=True)

        if self.comment:
            embed.add_field(name="\u200b", value=f"**Comment**\n {self.comment}", inline=False)

        return embed

    async def display(self) -> None:
        """Display the roll."""
        embed = await self.get_embed()
        await self.ctx.respond(embed=embed)
