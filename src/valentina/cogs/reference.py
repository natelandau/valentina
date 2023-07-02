"""Game information cog for Valentina."""

from textwrap import dedent

import discord
from discord.ext import commands
from loguru import logger

from valentina import Valentina
from valentina.views import present_embed


class Reference(commands.Cog):
    """Reference information for the game. Remind yourself of the rules."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    reference = discord.SlashCommandGroup("reference", "Get information about the game")

    async def cog_command_error(
        self, ctx: discord.ApplicationContext, error: discord.ApplicationCommandError | Exception
    ) -> None:
        """Handle exceptions and errors from the cog."""
        if hasattr(error, "original"):
            error = error.original

        command_name = ""
        if ctx.command.parent.name:
            command_name = f"{ctx.command.parent.name} "
        command_name += ctx.command.name

        await present_embed(
            ctx,
            title=f"Error running `{command_name}` command",
            description=str(error),
            level="error",
            ephemeral=True,
            delete_after=15,
        )

    @reference.command(description="See health levels")
    async def health(self, ctx: discord.ApplicationContext) -> None:
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
        )
        logger.debug(f"INFO: {ctx.author.display_name} requested health levels")

    @reference.command(description="See health levels")
    async def xp(self, ctx: discord.ApplicationContext) -> None:
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
        )

    @reference.command(description="Disciplines")
    async def disciplines(self, ctx: discord.ApplicationContext) -> None:
        """Display discipline information."""
        await present_embed(
            ctx,
            title="Disciplines",
            fields=[
                ("ANIMALISM", " Supernatural affinity with and control of animals"),
                ("AUSPEX", "Extrasensory perception, awareness, and premonitions"),
                ("BLOOD SORCERY", "The ability to cast blood magic"),
                ("CELERITY", "Supernatural speed and reflexes"),
                ("CHIMERSTRY", "Illusions made real or at least tangible"),
                ("DOMINATE", "Supernatural control over the minds of others"),
                ("FORTITUDE", "Supernatural toughness and resistance to damage"),
                ("NECROMANCY", "Control of the dead, both spirit and corpse"),
                ("OBFUSCATE", " Remain obscure and unseen, even in crowds"),
                ("POTENCE", " The Discipline of physical vigor and strength"),
                ("PRESENCE", "Attract, sway, and control emotions"),
                ("PROTEAN", "Shape-changing, from growing claws to melding with the earth"),
                ("QUIETUS", "Art of the silent death"),
                ("SERPENTIS", "Acquire the physicality of serpents"),
                ("THAUMATURGY", "The ability to cast rituals and blood magic"),
                ("VICISSITUDE", "The sculpting of flesh into unnatural forms "),
            ],
            level="info",
            inline_fields=True,
        )

    @reference.command(description="Spheres")
    async def magic(self, ctx: discord.ApplicationContext) -> None:
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
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Reference(bot))
