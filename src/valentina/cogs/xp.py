# mypy: disable-error-code="valid-type"

"""A cog for handling XP and leveling up."""
import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina.models.bot import Valentina
from valentina.models.constants import EmbedColor, XPMultiplier
from valentina.utils.helpers import (
    fetch_clan_disciplines,
    get_max_trait_value,
    get_trait_multiplier,
    get_trait_new_value,
)
from valentina.utils.options import select_trait
from valentina.views import ConfirmCancelButtons, present_embed


class Xp(commands.Cog, name="XP"):
    """Add or spend experience points."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

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

    xp = discord.SlashCommandGroup("xp", "Add or spend xp")

    @xp.command(name="spend", description="Spend experience points to upgrade a trait")
    async def spend_xp(
        self,
        ctx: discord.ApplicationContext,
        trait: Option(
            str,
            description="Trait to raise with xp",
            required=True,
            autocomplete=select_trait,
        ),
    ) -> None:
        """Spend experience points."""
        character = self.bot.char_svc.fetch_claim(ctx)

        old_value = self.bot.char_svc.fetch_trait_value(ctx, character, trait)
        category = self.bot.char_svc.fetch_trait_category(ctx, character, trait)

        if character.char_class.name == "Vampire" and trait in fetch_clan_disciplines(
            character.clan_name
        ):
            multiplier = XPMultiplier.CLAN_DISCIPLINE.value
        else:
            multiplier = get_trait_multiplier(trait, category)

        if old_value > 0:
            upgrade_cost = (old_value + 1) * multiplier

        if old_value == 0:
            upgrade_cost = get_trait_new_value(trait, category)

        remaining_xp = character.experience - upgrade_cost
        if remaining_xp < 0:
            await present_embed(
                ctx,
                title="Error: Not enough XP",
                description=f"**{trait}** upgrade cost is **{upgrade_cost} XP**. You have **{character.experience} XP**.",
                level="error",
                ephemeral=True,
            )
            return

        if old_value >= get_max_trait_value(trait):
            await present_embed(
                ctx,
                title=f"Error: {trait} at max value",
                description=f"**{trait}** is already at max value of {old_value}.",
                level="error",
            )
            return

        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title=f"Upgrade {trait}?",
            description=f"Upgrading **{trait}** from **{old_value}** to **{old_value + 1}** dots will cost **{upgrade_cost} XP**",
            fields=[
                ("Current XP", character.experience),
                ("XP Cost", str(upgrade_cost)),
                ("Remaining XP", character.experience - upgrade_cost),
            ],
            inline_fields=True,
            ephemeral=True,
            level="info",
            view=view,
        )
        await view.wait()
        if not view.confirmed:
            embed = discord.Embed(title="Upgrade cancelled", color=EmbedColor.INFO.value)
            await msg.edit_original_response(embed=embed, view=None)
            return

        if view.confirmed:
            new_value = old_value + 1
            new_experience = character.experience - upgrade_cost
            self.bot.char_svc.update_trait_value_by_name(ctx, character, trait, new_value)
            self.bot.char_svc.update_character(
                ctx,
                character.id,
                **{"experience": new_experience},
            )

            logger.info(f"XP: {character.name} {trait} upgraded by {ctx.author.name}")
            await msg.delete_original_response()
            await present_embed(
                ctx=ctx,
                title=f"{character.name} upgraded",
                level="success",
                fields=[
                    ("Trait", trait),
                    ("Original Value", str(old_value)),
                    ("New Value", str(new_value)),
                    ("XP Cost", str(upgrade_cost)),
                    ("Remaining XP", str(new_experience)),
                ],
                inline_fields=True,
                log=True,
            )

    @xp.command(name="add", description="Add experience to a character")
    async def add_xp(
        self,
        ctx: discord.ApplicationContext,
        exp: Option(int, description="The amount of experience to add", required=True),
    ) -> None:
        """Add experience to a character."""
        character = self.bot.char_svc.fetch_claim(ctx)

        exp = int(exp)
        new_exp = character.experience + exp
        new_total = character.experience_total + exp

        self.bot.char_svc.update_character(
            ctx,
            character.id,
            experience=new_exp,
            experience_total=new_total,
        )
        logger.info(f"EXP: {character.name} exp updated by {ctx.author.name}")
        await present_embed(
            ctx=ctx,
            title=f"{character.name} gained experience",
            fields=[
                ("Points Added", str(exp)),
                ("Current XP", new_exp),
                ("All time XP", f"{new_total}"),
            ],
            inline_fields=True,
            level="success",
            log=True,
        )

    @xp.command(name="cp", description="Add cool points to a character")
    async def add_cool_points(
        self,
        ctx: discord.ApplicationContext,
        cp: Option(int, description="The number of cool points to add", required=True),
    ) -> None:
        """Add cool points to a character."""
        character = self.bot.char_svc.fetch_claim(ctx)

        cp = int(cp)
        new_cp = character.cool_points + cp
        new_total = character.cool_points_total + cp

        self.bot.char_svc.update_character(
            ctx,
            character.id,
            cool_points=new_cp,
            cool_points_total=new_total,
        )
        logger.info(f"CP: {character.name} cool points updated by {ctx.author.name}")
        await present_embed(
            ctx=ctx,
            title=f"{character.name} gained cool points",
            fields=[
                ("Cool Points Added", str(cp)),
                ("Current Cool Points", new_cp),
                ("All time Cool Points", f"{new_total}"),
            ],
            level="success",
            log=True,
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Xp(bot))
