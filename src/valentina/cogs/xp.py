# mypy: disable-error-code="valid-type"
"""A cog for handling XP and leveling up."""
import discord
import inflect
from discord.commands import Option
from discord.ext import commands

from valentina.constants import COOL_POINT_VALUE, EmbedColor, XPMultiplier
from valentina.models.bot import Valentina
from valentina.utils.cogs import confirm_action
from valentina.utils.converters import ValidCharTrait
from valentina.utils.helpers import (
    fetch_clan_disciplines,
    get_max_trait_value,
    get_trait_multiplier,
    get_trait_new_value,
)
from valentina.utils.options import select_char_trait
from valentina.views import present_embed

p = inflect.engine()


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
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Spend experience points."""
        character = self.bot.char_svc.fetch_claim(ctx)
        old_value = character.get_trait_value(trait)
        category = trait.category.name

        # Compute the cost of the upgrade
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

        if old_value >= get_max_trait_value(trait.name, category):
            await present_embed(
                ctx,
                title=f"Error: {trait.name} at max value",
                description=f"**{trait.name}** is already at max value of `{old_value}`",
                level="error",
                ephemeral=True,
            )
            return

        # Compute if the character has enough xp to upgrade
        current_xp = character.data.get("experience", 0)
        remaining_xp = current_xp - upgrade_cost
        new_value = old_value + 1
        new_experience = character.data["experience"] - upgrade_cost

        if remaining_xp < 0:
            await present_embed(
                ctx,
                title="Error: Not enough XP",
                description=f"**{trait.name}** upgrade cost is `{upgrade_cost}` xp.  You only have `{current_xp}` xp.",
                level="error",
                ephemeral=True,
            )
            return

        title = f"Upgrade `{trait.name}` from `{old_value}` {p.plural_noun('dot', old_value)} to `{new_value}` {p.plural_noun('dot', new_value)} for `{upgrade_cost}` xp"
        confirmed, msg = await confirm_action(ctx, title, hidden=hidden)

        if not confirmed:
            return

        character.set_trait_value(trait, new_value)
        self.bot.char_svc.update_or_add(
            ctx,
            character=character,
            data={"experience": new_experience},
        )

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await msg.edit_original_response(
            embed=discord.Embed(title=title, color=EmbedColor.SUCCESS.value), view=None
        )

    @xp.command(name="add", description="Add experience to a character")
    async def add_xp(
        self,
        ctx: discord.ApplicationContext,
        xp: Option(int, description="The amount of experience to add", required=True),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
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

        current_xp = character.data.get("experience", 0)
        current_total = character.data.get("experience_total", 0)
        new_xp = current_xp + xp
        new_total = current_total + xp

        title = f"Add `{xp}` xp to `{character.name}`"
        confirmed, msg = await confirm_action(ctx, title, hidden=hidden)

        if not confirmed:
            return

        self.bot.char_svc.update_or_add(
            ctx,
            character=character,
            data={
                "experience": new_xp,
                "experience_total": new_total,
            },
        )

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await msg.edit_original_response(
            embed=discord.Embed(title=title, color=EmbedColor.SUCCESS.value), view=None
        )

    @xp.command(name="add_cp", description="Add cool points to a character")
    async def add_cool_points(
        self,
        ctx: discord.ApplicationContext,
        cp: Option(int, description="The number of cool points to add", required=True),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Add cool points to a character."""
        character = self.bot.char_svc.fetch_claim(ctx)

        if not self.bot.user_svc.has_xp_permissions(ctx, character):
            await present_embed(
                ctx,
                title="Permission error",
                description="You do not have permissions to add cool points on this character\nSpeak to an administrator",
                level="error",
                ephemeral=True,
                delete_after=30,
            )
            return

        current_cp = character.data.get("cool_points_total", 0)
        current_xp = character.data.get("experience", 0)
        current_xp_total = character.data.get("experience_total", 0)

        xp_amount = cp * COOL_POINT_VALUE

        new_xp = current_xp + xp_amount
        new_xp_total = current_xp_total + xp_amount
        new_cp_total = current_cp + cp

        title = (
            f"Add `{cp}` cool {p.plural_noun('point', cp)} ({xp_amount} xp) to `{character.name}`"
        )
        confirmed, msg = await confirm_action(ctx, title, hidden=hidden)

        if not confirmed:
            return

        self.bot.char_svc.update_or_add(
            ctx,
            character=character,
            data={
                "cool_points_total": new_cp_total,
                "experience": new_xp,
                "experience_total": new_xp_total,
            },
        )

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await msg.edit_original_response(
            embed=discord.Embed(title=title, color=EmbedColor.SUCCESS.value), view=None
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Xp(bot))
