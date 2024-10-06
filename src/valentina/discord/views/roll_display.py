"""Display and manipulate roll outcomes."""

import discord
import inflect

from valentina.constants import Emoji
from valentina.discord.bot import ValentinaContext
from valentina.models import CharacterTrait, DiceRoll
from valentina.utils.helpers import convert_int_to_emoji

p = inflect.engine()


class RollDisplay:
    """Display and manipulate roll outcomes.

    This class is responsible for creating an embed message representing a roll.
    """

    def __init__(
        self,
        ctx: ValentinaContext,
        roll: DiceRoll,
        comment: str | None = None,
        trait_one: CharacterTrait | None = None,
        trait_two: CharacterTrait | None = None,
        desperation_pool: int = 0,
    ):
        self.ctx = ctx
        self.roll = roll
        self.comment = comment
        self.trait_one = trait_one
        self.trait_two = trait_two
        self.desperation_pool = desperation_pool

    def _add_comment_field(self, embed: discord.Embed) -> discord.Embed:
        """Add the comment field to the embed."""
        if self.comment:
            embed.add_field(name="\u200b", value=f"**Comment**\n {self.comment}", inline=False)

        return embed

    async def get_embed(self) -> discord.Embed:
        """The graphical representation of the roll."""
        roll_string = " ".join(
            f"{convert_int_to_emoji(die, markdown=True)}" for die in self.roll.roll
        )

        if self.desperation_pool > 0:
            desperation_roll_string = " ".join(
                f"{convert_int_to_emoji(die, markdown=True)}" for die in self.roll.desperation_roll
            )

        description = f"""\
### {self.ctx.author.mention} rolled `{self.desperation_pool + self.roll.pool}{self.roll.dice_type.name.lower()}`
## {self.roll.roll_result_humanized.upper()}
**{self.roll.num_successes_humanized}**
"""

        embed = discord.Embed(
            title=None,
            description=description,
            color=self.roll.embed_color,
        )

        # Rolled dice
        value = f"{roll_string}"
        if self.desperation_pool > 0:
            value += f" + {desperation_roll_string}"

        embed.add_field(name="Rolled Dice", value=f"{value}", inline=False)

        if self.desperation_pool > 0 and self.roll.desperation_botches > 0:
            embed.add_field(name="\u200b", value="\u200b", inline=False)  # spacer
            value = f"""\
> You must pick either:
> - {Emoji.DESPAIR.value} **Despair** (Fail your roll)
> - {Emoji.OVERREACH.value} **Overreach** (Succeed but raise the danger level by 1)
"""
            embed.add_field(
                name=f"**{Emoji.FACEPALM.value} {self.roll.desperation_botches} Desperation {p.plural_noun('botch', self.roll.desperation_botches)}**",
                value=f"{value}",
                inline=False,
            )

        embed.add_field(name="Difficulty", value=f"`{self.roll.difficulty}`", inline=True)
        embed.add_field(
            name="Dice Pool",
            value=f"`{self.roll.pool}{self.roll.dice_type.name.lower()}`",
            inline=True,
        )

        if self.desperation_pool > 0:
            embed.add_field(
                name="Desperation Pool",
                value=f"`{self.desperation_pool}{self.roll.dice_type.name.lower()}`",
                inline=True,
            )

        if self.trait_one:
            embed.add_field(name="\u200b", value="**TRAITS**", inline=False)
            embed.add_field(
                name=f"{self.trait_one.name}",
                value=f"`{self.trait_one.value} {p.plural_noun('die', self.trait_one.value)}`",
                inline=True,
            )
        if self.trait_two:
            embed.add_field(
                name=f"{self.trait_two.name}",
                value=f"`{self.trait_two.value} {p.plural_noun('die', self.trait_two.value)}`",
                inline=True,
            )

        embed.set_thumbnail(url=await self.roll.thumbnail_url())

        return self._add_comment_field(embed)

    async def display(self) -> None:
        """Display the roll."""
        embed = await self.get_embed()
        await self.ctx.respond(embed=embed)
