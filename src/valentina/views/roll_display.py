"""Display and manipulate roll outcomes."""

import discord
import inflect

from valentina.constants import Emoji
from valentina.models import CharacterTrait, DiceRoll
from valentina.models.bot import ValentinaContext

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
        roll_string = " ".join(f"{die}" for die in self.roll.roll)
        if self.desperation_pool > 0:
            desperation_roll_string = " ".join(f"{die}" for die in self.roll.desperation_roll)

        description = f"""\
### {self.ctx.author.display_name} rolled `{self.desperation_pool + self.roll.pool}{self.roll.dice_type.name.lower()}`
## {self.roll.embed_title}
{self.roll.embed_description}
"""

        description += f"""\
### Rolled Dice:
```scala
Roll        : {roll_string}
{"Desperation : " + desperation_roll_string if self.desperation_pool > 0 else ""}
```
"""

        if self.desperation_pool > 0 and self.roll.desperation_botches > 0:
            description += f"""\
### {Emoji.FACEPALM.value} `{self.roll.desperation_botches}` Desperation {p.plural_noun('botch', self.roll.desperation_botches)}
> You must pick either:
> - {Emoji.DESPAIR.value} **Despair** (Fail your roll)
> - {Emoji.OVERREACH.value} **Overreach** (Succeed but raise the danger level by 1)
"""

        description += f"""\
### Roll Details:
```scala
Difficulty       : {self.roll.difficulty}
Pool             : {self.roll.pool}{self.roll.dice_type.name.lower()}
"""

        if self.desperation_pool > 0:
            description += f"""\
Desperation Pool : {self.desperation_pool}{self.roll.dice_type.name.lower()}
Total Dice Rolled: {self.desperation_pool + self.roll.pool}{self.roll.dice_type.name.lower()}
"""

        if self.trait_one:
            description += f"{self.trait_one.name:<17}: {self.trait_one.value} {p.plural_noun('die', self.trait_one.value)}\n"
        if self.trait_two:
            description += f"{self.trait_two.name:<17}: {self.trait_two.value} {p.plural_noun('die', self.trait_two.value)}\n"

        description += "```"

        embed = discord.Embed(
            title=None,
            description=description,
            color=self.roll.embed_color,
        )

        # Thumbnail
        embed.set_thumbnail(url=await self.roll.thumbnail_url())

        return self._add_comment_field(embed)

    async def display(self) -> None:
        """Display the roll."""
        embed = await self.get_embed()
        await self.ctx.respond(embed=embed)
