# mypy: disable-error-code="valid-type"
"""Experience commands."""

import discord
import inflect
from discord.commands import Option
from discord.ext import commands

from valentina.constants import TraitCategory, XPMultiplier
from valentina.models import User
from valentina.models.bot import Valentina, ValentinaContext
from valentina.utils.autocomplete import select_character_from_user, select_trait_from_char_option
from valentina.utils.converters import (
    ValidCharacterObject,
    ValidCharTrait,
)
from valentina.utils.helpers import get_trait_multiplier, get_trait_new_value
from valentina.views import confirm_action, present_embed

p = inflect.engine()


class Experience(commands.Cog):
    """Experience commands."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot

    xp = discord.SlashCommandGroup("xp", "Add, spend, or view experience points")

    @xp.command(name="add", description="Add experience to a user")
    async def xp_add(
        self,
        ctx: ValentinaContext,
        amount: Option(int, description="The amount of experience to add", required=True),
        user: Option(
            discord.User,
            description="The user to grant experience to",
            required=False,
            default=None,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default false).",
            default=False,
        ),
    ) -> None:
        """Add experience to a user."""
        if not user:
            user = await User.get(ctx.author.id)
        else:
            user = await User.get(user.id)

        if not await ctx.can_grant_xp(user):
            await present_embed(
                ctx,
                title="You do not have permission to add experience to this user",
                description="Contact an admin for assistance",
                level="error",
                ephemeral=True,
            )
            return

        active_campaign = await ctx.fetch_active_campaign()

        title = f"Add `{amount}` xp to `{user.name}`"
        description = "View experience with `/user_info`"
        is_confirmed, msg, confirmation_embed = await confirm_action(
            ctx, title, description=description, hidden=hidden
        )
        if not is_confirmed:
            return

        # Make the database updates
        await user.add_campaign_xp(active_campaign, amount)

        # Send the confirmation message
        await ctx.post_to_audit_log(title)
        await msg.edit_original_response(embed=confirmation_embed, view=None)

    @xp.command(name="add_cool_point", description="Add a cool point to a user")
    async def cp_add(
        self,
        ctx: ValentinaContext,
        amount: Option(int, description="The amount of experience to add (default 1)", default=1),
        user: Option(
            discord.User,
            description="The user to grant experience to",
            required=False,
            default=None,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default false).",
            default=False,
        ),
    ) -> None:
        """Add cool points to a user."""
        if not user:
            user = await User.get(ctx.author.id)
        else:
            user = await User.get(user.id)

        if not await ctx.can_grant_xp(user):
            await present_embed(
                ctx,
                title="You do not have permission to add experience to this user",
                description="Contact an admin for assistance",
                level="error",
                ephemeral=True,
            )
            return

        active_campaign = await ctx.fetch_active_campaign()

        title = f"Add `{amount}` cool {p.plural_noun('point', amount)} to `{user.name}`"
        description = "View cool points with `/user_info`"
        is_confirmed, msg, confirmation_embed = await confirm_action(
            ctx, title, description=description, hidden=hidden
        )
        if not is_confirmed:
            return

        # Make the database updates
        await user.add_campaign_cool_points(active_campaign, amount)

        # Send the confirmation message
        await ctx.post_to_audit_log(title)
        await msg.edit_original_response(embed=confirmation_embed, view=None)

    @xp.command(name="spend", description="Spend experience points")
    async def xp_spend(
        self,
        ctx: ValentinaContext,
        character: Option(
            ValidCharacterObject,
            description="The character to view",
            autocomplete=select_character_from_user,
            required=True,
        ),
        trait: Option(
            ValidCharTrait,
            description="Trait to raise with xp",
            required=True,
            autocomplete=select_trait_from_char_option,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default false).",
            default=False,
        ),
    ) -> None:
        """Spend experience points."""
        # Guard statement: fail if the trait is already at max value
        if trait.value >= trait.max_value:
            await present_embed(
                ctx,
                title=f"Error: {trait.name} at max value",
                description=f"**{trait.name}** is already at max value of `{trait.value}`",
                level="error",
                ephemeral=True,
            )
            return

        # Find the multiplier for the trait
        if (
            trait.category == TraitCategory.DISCIPLINES
            and character.clan
            and trait.name in character.clan.value.disciplines
        ):
            # Clan disciplines are cheaper
            multiplier = XPMultiplier.CLAN_DISCIPLINE.value
        else:
            multiplier = get_trait_multiplier(trait.name, trait.category.name)

        # Compute the cost of the upgrade
        if trait.value == 0:
            # First dots sometimes have a different cost
            upgrade_cost = get_trait_new_value(trait.name, trait.category.name)
        else:
            upgrade_cost = (trait.value + 1) * multiplier

        new_trait_value = trait.value + 1

        title = f"Upgrade `{trait.name}` from `{trait.value}` {p.plural_noun('dot', trait.value)} to `{trait.value + 1}` {p.plural_noun('dot', trait.value + 1)} for `{upgrade_cost}` xp"
        is_confirmed, msg, confirmation_embed = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        # Make the updates
        user = await User.get(ctx.author.id)
        active_campaign = await ctx.fetch_active_campaign()

        await user.spend_campaign_xp(active_campaign, upgrade_cost)
        trait.value = new_trait_value
        await trait.save()

        # Send the confirmation message
        await ctx.post_to_audit_log(title)
        await msg.edit_original_response(embed=confirmation_embed, view=None)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Experience(bot))
