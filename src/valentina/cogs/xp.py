# mypy: disable-error-code="valid-type"
"""A cog for handling XP and leveling up."""
import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina.models.bot import Valentina
from valentina.models.constants import COOL_POINT_VALUE, EmbedColor, XPMultiplier
from valentina.utils.converters import ValidCharTrait
from valentina.utils.helpers import (
    fetch_clan_disciplines,
    get_max_trait_value,
    get_trait_multiplier,
    get_trait_new_value,
)
from valentina.utils.options import select_char_trait
from valentina.views import ConfirmCancelButtons, present_embed


class Xp(commands.Cog, name="XP"):
    """Add or spend experience points."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    xp = discord.SlashCommandGroup("xp", "Add or spend xp")

    @xp.command(name="spend", description="Spend experience points to upgrade a trait")
    async def spend_xp(
        self,
        ctx: discord.ApplicationContext,
        trait: Option(
            ValidCharTrait,
            description="Trait to raise with xp",
            required=True,
            autocomplete=select_char_trait,
        ),
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Spend experience points."""
        character = self.bot.char_svc.fetch_claim(ctx)
        old_value = character.get_trait_value(trait)
        category = trait.category.name

        if character.char_class.name == "Vampire" and trait.name in fetch_clan_disciplines(
            character.clan_name
        ):
            multiplier = XPMultiplier.CLAN_DISCIPLINE.value
        else:
            multiplier = get_trait_multiplier(trait.name, category)

        if old_value > 0:
            upgrade_cost = (old_value + 1) * multiplier

        if old_value == 0:
            upgrade_cost = get_trait_new_value(trait.name, category)

        remaining_xp = character.data["experience"] - upgrade_cost
        if remaining_xp < 0:
            await present_embed(
                ctx,
                title="Error: Not enough XP",
                description=f"**{trait.name}** upgrade cost is **{upgrade_cost} XP**. You have **{character.data['experience']} XP**.",
                level="error",
                ephemeral=hidden,
            )
            return

        if old_value >= get_max_trait_value(trait.name, category):
            await present_embed(
                ctx,
                title=f"Error: {trait.name} at max value",
                description=f"**{trait.name}** is already at max value of {old_value}.",
                level="error",
                ephemeral=hidden,
            )
            return

        view = ConfirmCancelButtons(ctx.author)

        msg = await present_embed(
            ctx,
            title=f"Upgrade {trait.name}?",
            description=f"Upgrading **{trait.name}** from **{old_value}** to **{old_value + 1}** dots will cost **{upgrade_cost} XP**",
            fields=[
                ("Current XP", character.data["experience"]),
                ("XP Cost", str(upgrade_cost)),
                ("Remaining XP", character.data["experience"] - upgrade_cost),
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

        new_value = old_value + 1
        new_experience = character.data["experience"] - upgrade_cost

        character.set_trait_value(trait, new_value)

        self.bot.char_svc.update_or_add(
            ctx,
            character=character,
            data={"experience": new_experience},
        )

        logger.debug(f"XP: {character.name} {trait.name} upgraded by {ctx.author.name}")

        await msg.delete_original_response()
        await present_embed(
            ctx=ctx,
            title=f"{character.name} upgraded",
            level="success",
            fields=[
                ("Trait", trait.name),
                ("Original Value", str(old_value)),
                ("New Value", str(new_value)),
                ("XP Cost", str(upgrade_cost)),
                ("Remaining XP", str(new_experience)),
            ],
            inline_fields=True,
            log=True,
            ephemeral=hidden,
        )

    @xp.command(name="add", description="Add experience to a character")
    async def add_xp(
        self,
        ctx: discord.ApplicationContext,
        exp: Option(int, description="The amount of experience to add", required=True),
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Add experience to a character."""
        character = self.bot.char_svc.fetch_claim(ctx)

        if not self.bot.user_svc.has_xp_permissions(ctx, character):
            await present_embed(
                ctx,
                title="Permission error",
                description="You do not have permissions to add experience on this character\nSpeak to an administrator",
                level="error",
                ephemeral=True,
                delete_after=30,
            )
            return

        exp = int(exp)
        new_exp = character.data["experience"] + exp if character.data.get("experience") else exp
        new_total = (
            character.data["experience_total"] + exp if character.data.get("experience") else exp
        )

        self.bot.char_svc.update_or_add(
            ctx,
            character=character,
            data={
                "experience": new_exp,
                "experience_total": new_total,
            },
        )
        logger.info(f"XP: {character} xp updated by {ctx.author.name}")
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
            ephemeral=hidden,
        )

    @xp.command(name="add_cp", description="Add cool points to a character")
    async def add_cool_points(
        self,
        ctx: discord.ApplicationContext,
        cp: Option(int, description="The number of cool points to add", required=True),
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Add cool points to a character."""
        character = self.bot.char_svc.fetch_claim(ctx)

        if not self.bot.user_svc.has_xp_permissions(ctx, character):
            await present_embed(
                ctx,
                title="Permission error",
                description="You do not have permissions to add experience on this character\nSpeak to an administrator",
                level="error",
                ephemeral=True,
                delete_after=30,
            )
            return

        cp = int(cp)
        new_total = (
            character.data["cool_points_total"] + cp
            if character.data.get("cool_points_total")
            else cp
        )

        new_xp = (
            character.data["experience"] + (cp * COOL_POINT_VALUE)
            if character.data.get("experience")
            else cp * COOL_POINT_VALUE
        )
        new_xp_total = (
            character.data["experience_total"] + new_xp
            if character.data.get("experience_total")
            else new_xp
        )

        self.bot.char_svc.update_or_add(
            ctx,
            character=character,
            data={
                "cool_points_total": new_total,
                "experience": new_xp_total,
                "experience_total": new_xp_total,
            },
        )
        logger.info(f"CP: {character} cool points updated by {ctx.author.name}")
        await present_embed(
            ctx=ctx,
            title=f"{character.name} gained cool points",
            fields=[
                ("Cool Points Added", str(cp)),
                ("All time Cool Points", f"{new_total}"),
                ("Experience Added", str(new_xp)),
                ("Current XP", f"{new_xp_total}"),
            ],
            level="success",
            log=True,
            ephemeral=hidden,
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Xp(bot))
