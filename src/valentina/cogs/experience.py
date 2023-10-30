# mypy: disable-error-code="valid-type"
"""Experience commands."""
import discord
import inflect
from discord.commands import Option
from discord.ext import commands

from valentina.constants import COOL_POINT_VALUE, CharClass, VampireClan, XPMultiplier
from valentina.models.bot import Valentina
from valentina.utils.converters import (
    ValidCharacterObject,
    ValidCharTrait,
)
from valentina.utils.helpers import (
    get_max_trait_value,
    get_trait_multiplier,
    get_trait_new_value,
)
from valentina.utils.options import select_player_character, select_trait_from_char_option
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
        ctx: discord.ApplicationContext,
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
            user = await self.bot.user_svc.fetch_user(ctx)
        else:
            user = await self.bot.user_svc.fetch_user(ctx, user=user)

        if not await self.bot.user_svc.can_update_xp(ctx, user):
            await present_embed(
                ctx,
                title="You do not have permission to add experience to this user",
                description="Contact an admin for assistance",
                level="error",
                ephemeral=True,
            )
            return

        campaign = self.bot.campaign_svc.fetch_active(ctx)

        title = f"Add `{amount}` xp to `{user.data['display_name']}`"
        description = "View experience with `/user_info`"
        is_confirmed, confirmation_response_msg = await confirm_action(
            ctx, title, description=description, hidden=hidden
        )
        if not is_confirmed:
            return

        # Make the database updates
        user.add_experience(campaign.id, amount)
        self.bot.user_svc.purge_cache(ctx)

        # Send the confirmation message
        await self.bot.guild_svc.post_to_audit_log(title)
        await confirmation_response_msg

    @xp.command(name="add_cool_point", description="Add a cool point to a user")
    async def cp_add(
        self,
        ctx: discord.ApplicationContext,
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
            user = await self.bot.user_svc.fetch_user(ctx)
        else:
            user = await self.bot.user_svc.fetch_user(ctx, user=user)

        if not await self.bot.user_svc.can_update_xp(ctx, user):
            await present_embed(
                ctx,
                title="You do not have permission to add experience to this user",
                description="Contact an admin for assistance",
                level="error",
                ephemeral=True,
            )
            return

        campaign = self.bot.campaign_svc.fetch_active(ctx)

        title = (
            f"Add `{amount}` cool {p.plural_noun('point', amount)} to `{user.data['display_name']}`"
        )
        description = "View cool points with `/user_info`"
        is_confirmed, confirmation_response_msg = await confirm_action(
            ctx, title, description=description, hidden=hidden
        )
        if not is_confirmed:
            return

        # Make the database updates
        user.add_cool_points(campaign.id, amount)
        user.add_experience(campaign.id, amount * COOL_POINT_VALUE)
        self.bot.user_svc.purge_cache(ctx)

        # Send the confirmation message
        await self.bot.guild_svc.post_to_audit_log(title)
        await confirmation_response_msg

    @xp.command(name="spend", description="Spend experience points")
    async def xp_spend(
        self,
        ctx: discord.ApplicationContext,
        character: Option(
            ValidCharacterObject,
            description="The character to view",
            autocomplete=select_player_character,
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
        campaign = self.bot.campaign_svc.fetch_active(ctx)
        old_trait_value = character.get_trait_value(trait)
        category = trait.category.name

        char_class = CharClass[character.char_class.name]
        try:
            clan = VampireClan[character.clan.name] if character.clan else None
        except KeyError:
            clan = None

        # Compute the cost of the upgrade
        if char_class == char_class.VAMPIRE and trait.name in clan.value["disciplines"]:
            multiplier = XPMultiplier.CLAN_DISCIPLINE.value
        else:
            multiplier = get_trait_multiplier(trait.name, category)

        if old_trait_value > 0:
            upgrade_cost = (old_trait_value + 1) * multiplier

        if old_trait_value == 0:
            upgrade_cost = get_trait_new_value(trait.name, category)

        if old_trait_value >= get_max_trait_value(trait.name, category):
            await present_embed(
                ctx,
                title=f"Error: {trait.name} at max value",
                description=f"**{trait.name}** is already at max value of `{old_trait_value}`",
                level="error",
                ephemeral=True,
            )
            return

        new_trait_value = old_trait_value + 1

        title = f"Upgrade `{trait.name}` from `{old_trait_value}` {p.plural_noun('dot', old_trait_value)} to `{new_trait_value}` {p.plural_noun('dot', new_trait_value)} for `{upgrade_cost}` xp"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        # Make the database updates
        user = character.owned_by
        user.spend_experience(campaign.id, upgrade_cost)
        character.set_trait_value(trait, new_trait_value)
        self.bot.user_svc.purge_cache(ctx)

        # Send the confirmation message
        await self.bot.guild_svc.post_to_audit_log(title)
        await confirmation_response_msg


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Experience(bot))
