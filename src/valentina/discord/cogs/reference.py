# mypy: disable-error-code="valid-type"
"""Game information cog for Valentina."""

from textwrap import dedent

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina.discord.bot import Valentina, ValentinaContext
from valentina.discord.views import present_embed


class Reference(commands.Cog):
    """Reference information for the game. Remind yourself of the rules."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot

    reference = discord.SlashCommandGroup("reference", "Get information about the game")

    @reference.command(description="See health levels")
    async def health(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Display health levels."""
        description = dedent(
            """
        ```
        Bruised       :
        Hurt          : -1
        Injured       : -1
        Wounded       : -2
        Mauled        : -2
        Crippled      : -5
        Incapacitated :
        ```
        """
        )

        await present_embed(
            ctx,
            title="Health Levels",
            description=description,
            level="info",
            ephemeral=hidden,
        )
        logger.debug(f"INFO: {ctx.author.display_name} requested health levels")

    @reference.command(description="See health levels")
    async def xp(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Display experience costs."""
        description = dedent(
            """
            Multiply the new dot rating by the multiplier to get the cost to raise a trait.
            ```
            Abilities.............: x3
            Arete.................: x10
            Attributes............: x5
            Backgrounds...........: x2
            Disciplines (Clan)....: x5
            Flaws.................: x2
            Gifts.................: x3
            Gnosis................: x2
            Humanity..............: x1
            Merits................: x2
            Disciplines (Other)...: x7
            Rage..................: x1
            Spheres...............: x7
            Virtues...............: x2
            Willpower.............: x1
            ```
            """
        )
        await present_embed(
            ctx,
            title="Experience Costs",
            description=description,
            level="info",
            ephemeral=hidden,
        )

    @reference.command(description="Disciplines")
    async def disciplines(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Display discipline information."""
        await present_embed(
            ctx,
            title="Disciplines",
            fields=[
                (
                    "ANIMALISM",
                    " Supernatural affinity with and control of animals.\n[more](https://whitewolf.fandom.com/wiki/Animalism_(VTM))",
                ),
                (
                    "AUSPEX",
                    "Extrasensory perception, awareness, and premonitions.\n[more](https://whitewolf.fandom.com/wiki/Auspex_(VTM))",
                ),
                (
                    "BLOOD SORCERY",
                    "The ability to cast blood magic.\n[more](https://whitewolf.fandom.com/wiki/Blood_Sorcery_(VTM))",
                ),
                (
                    "CELERITY",
                    "Supernatural speed and reflexes.\n[more](https://whitewolf.fandom.com/wiki/Celerity_(VTM))",
                ),
                (
                    "CHIMERSTRY",
                    "Illusions made real or at least tangible.\n[more](https://whitewolf.fandom.com/wiki/Chimerstry)",
                ),
                (
                    "DOMINATE",
                    "Supernatural control over the minds of others.\n[more](https://whitewolf.fandom.com/wiki/Dominate_(VTM))",
                ),
                (
                    "FORTITUDE",
                    "Supernatural toughness and resistance to damage.\n[more](https://whitewolf.fandom.com/wiki/Fortitude)",
                ),
                (
                    "NECROMANCY",
                    "Control of the dead, both spirit and corpse.\n[more](https://whitewolf.fandom.com/wiki/Necromancy_(VTM))",
                ),
                (
                    "OBFUSCATE",
                    " Remain obscure and unseen, even in crowds.\n[more](https://whitewolf.fandom.com/wiki/Obfuscate_(VTM))",
                ),
                (
                    "POTENCE",
                    " The Discipline of physical vigor and strength.\n[more](https://whitewolf.fandom.com/wiki/Potence)",
                ),
                (
                    "PRESENCE",
                    "Attract, sway, and control emotions.\n[more](https://whitewolf.fandom.com/wiki/Presence_(VTM))",
                ),
                (
                    "PROTEAN",
                    "Shape-changing, from growing claws to melding with the earth.\n[more](https://whitewolf.fandom.com/wiki/Protean_(VTM))",
                ),
                (
                    "QUIETUS",
                    "Art of the silent death.\n[more](https://whitewolf.fandom.com/wiki/Quietus)",
                ),
                (
                    "SERPENTIS",
                    "Acquire the physicality of serpents.\n[more](https://whitewolf.fandom.com/wiki/Serpentis)",
                ),
                (
                    "THAUMATURGY",
                    "The ability to cast rituals and blood magic.\n[more](https://whitewolf.fandom.com/wiki/Thaumaturgy_(VTM))",
                ),
                (
                    "VICISSITUDE",
                    "The sculpting of flesh into unnatural forms.\n[more](https://whitewolf.fandom.com/wiki/Vicissitude)",
                ),
            ],
            level="info",
            inline_fields=True,
            ephemeral=hidden,
        )

    @reference.command(description="Spheres")
    async def magic(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Magic reference information."""
        await present_embed(
            ctx,
            title="Magic Reference",
            fields=[
                ("Mage: The Ascension", "https://whitewolf.fandom.com/wiki/Mage:_The_Ascension"),
                ("Spheres", "https://whitewolf.fandom.com/wiki/Sphere"),
                ("Arete", "https://whitewolf.fandom.com/wiki/Arete_(MTAs)"),
                ("Quintessence", "https://whitewolf.fandom.com/wiki/Quintessence_(MTAs)"),
                ("Paradox", "https://whitewolf.fandom.com/wiki/Mage:_The_Ascension#Paradox"),
                ("Foci", "https://whitewolf.fandom.com/wiki/Focus"),
                ("Essence", "https://whitewolf.fandom.com/wiki/Essence_(MTAs)"),
                ("Resonance", "https://whitewolf.fandom.com/wiki/Resonance_(MTAs)"),
            ],
            level="info",
            inline_fields=True,
            ephemeral=hidden,
        )

    @reference.command(name="thaumaturgy", description="Thaumaturgy")
    async def thaumaturgy(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Reference information for Thaumaturgy Paths."""
        page1 = dedent(
            """
            Created by exhaustive research and extensive experimentation, Thaumaturgy utilizes the principles of Hermetic magic used by House Tremere when it was still a cabal of mages, adapted to be fueled by the inherent magical power of Vitae rather than Quintessence. While it is certainly powerful and versatile, it is organized very differently to the [Spheres](https://whitewolf.fandom.com/wiki/Sphere); Thaumaturgy is largely unknown to mages, and universally distrusted and reviled by those who have encountered it.

            Thaumaturgy uses a system of paths and rituals to focus the thaumaturge's will. Paths are learned expressions of thaumaturgical principles developed into reliable, repeatable effects. Unlike the "natural" powers of Disciplines, however, thaumaturges must concentrate their will, forcing the power of their blood to unnatural ends. If their concentration is not complete, if they falter, then the magic will fail, and in extreme cases such failure can have a lasting effect on the thaumaturge, draining their mental resources.

            [Rituals](https://whitewolf.fandom.com/wiki/Ritual_(VTM)), by contrast, are elaborate, sophisticated and codified instructions for producing set magical effects. Rituals vary in complexity, and require varying levels of thaumaturgical knowledge to complete successfully. They often require the trappings of Hermetic magic - circles drawn in chalk, locks of the victim's hair, meditation, chanting ancient words of power, and the like. Rituals can take hours, days or even months to perform, but - if successfully completed - will always produce the same result. They can be incredibly powerful, particularly when senior thaumaturges join forces; it was a thaumaturgical ritual that cursed the entire Assamite clan.

            - [Paths Info](https://whitewolf.fandom.com/wiki/Thaumaturgy_(VTM))
            - [Rituals Info](https://whitewolf.fandom.com/wiki/List_of_Thaumaturgy_Rituals)

            """
        )

        await present_embed(
            ctx, title="Thaumaturgy", description=page1, level="info", ephemeral=hidden
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Reference(bot))
