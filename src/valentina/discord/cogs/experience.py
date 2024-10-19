# mypy: disable-error-code="valid-type"
"""Experience commands."""

import discord
import inflect
from discord.commands import Option
from discord.ext import commands

from valentina.controllers import PermissionManager, TraitModifier
from valentina.discord.bot import Valentina, ValentinaContext
from valentina.discord.utils.autocomplete import select_char_trait
from valentina.discord.utils.converters import ValidTraitFromID
from valentina.discord.utils.discord_utils import fetch_channel_object
from valentina.discord.views import confirm_action, present_embed
from valentina.models import User

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

        permission_mngr = PermissionManager(ctx.guild.id)
        if not await permission_mngr.can_grant_xp(author_id=ctx.author.id, target_id=user.id):
            await present_embed(
                ctx,
                title="You do not have permission to add experience to this user",
                description="Contact an admin for assistance",
                level="error",
                ephemeral=True,
            )
            return

        channel_objects = await fetch_channel_object(ctx, need_campaign=True)
        campaign = channel_objects.campaign

        title = f"Add `{amount}` xp to `{user.name}` in `{campaign.name}`"
        description = "View experience with `/user_info`"
        is_confirmed, msg, confirmation_embed = await confirm_action(
            ctx, title, description=description, hidden=hidden, audit=True
        )
        if not is_confirmed:
            return

        # Make the database updates
        await user.add_campaign_xp(campaign, amount)

        # Send the confirmation message
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

        permission_mngr = PermissionManager(ctx.guild.id)
        if not await permission_mngr.can_grant_xp(author_id=ctx.author.id, target_id=user.id):
            await present_embed(
                ctx,
                title="You do not have permission to add experience to this user",
                description="Contact an admin for assistance",
                level="error",
                ephemeral=True,
            )
            return

        channel_objects = await fetch_channel_object(ctx, need_campaign=True)
        campaign = channel_objects.campaign

        title = f"Add `{amount}` cool {p.plural_noun('point', amount)} to `{user.name}` in `{campaign.name}`"
        description = "View cool points with `/user_info`"
        is_confirmed, msg, confirmation_embed = await confirm_action(
            ctx, title, description=description, hidden=hidden, audit=True
        )
        if not is_confirmed:
            return

        # Make the database updates
        await user.add_campaign_cool_points(campaign, amount)

        # Send the confirmation message
        await msg.edit_original_response(embed=confirmation_embed, view=None)

    @xp.command(name="spend", description="Spend experience points")
    async def xp_spend(
        self,
        ctx: ValentinaContext,
        trait: Option(
            ValidTraitFromID,
            name="trait_one",
            description="First trait to roll",
            required=True,
            autocomplete=select_char_trait,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default false).",
            default=False,
        ),
    ) -> None:
        """Spend experience points."""
        channel_objects = await fetch_channel_object(ctx, need_campaign=True, need_character=True)
        campaign = channel_objects.campaign
        character = channel_objects.character

        trait_controller = TraitModifier(character, await User.get(ctx.author.id))

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

        cost_to_upgrade = trait_controller.cost_to_upgrade(trait)

        title = f"Upgrade `{trait.name}` from `{trait.value}` {p.plural_noun('dot', trait.value)} to `{trait.value + 1}` {p.plural_noun('dot', trait.value + 1)} for `{cost_to_upgrade}` xp"
        is_confirmed, msg, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden, audit=True
        )
        if not is_confirmed:
            return

        await trait_controller.upgrade_with_xp(trait, campaign)

        # Send the confirmation message
        await msg.edit_original_response(embed=confirmation_embed, view=None)


def setup(bot: Valentina) -> None:  # pragma: no cover
    """Add the cog to the bot."""
    bot.add_cog(Experience(bot))
