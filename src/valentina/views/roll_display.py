"""Display and manipulate roll outcomes."""
import discord

from valentina.models.dicerolls import Roll


class RollDisplay:
    """Display and manipulate roll outcomes."""

    def __init__(self, ctx: discord.ApplicationContext, roll: Roll, comment: str = None):
        self.ctx = ctx
        self.roll = roll
        self.comment = comment

    async def get_embed(self) -> discord.Embed:
        """The graphical representation of the roll."""
        title = self.roll.takeaway

        embed = discord.Embed(title=title, colour=self.roll.embed_color)
        embed.set_author(
            name=self.ctx.author.display_name, icon_url=self.ctx.author.display_avatar.url
        )

        # Thumbnail
        embed.set_thumbnail(
            url=self.roll.thumbnail_url,
        )

        roll_string = ""
        for die in self.roll.roll:
            roll_string += f"`{die}` "

        # Fields
        embed.add_field(name="Roll", value=roll_string, inline=False)
        embed.add_field(name="Pool", value=str(self.roll.pool), inline=True)
        embed.add_field(name="Difficulty", value=str(self.roll.difficulty), inline=True)
        embed.add_field(name="Dice Type", value=str(self.roll.dice_type.name), inline=True)

        # Footer
        if self.comment is not None:
            embed.set_footer(text=self.comment)

        return embed

    async def display(self) -> None:
        """Display the roll."""
        embed = await self.get_embed()
        await self.ctx.respond(embed=embed)
