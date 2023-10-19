# mypy: disable-error-code="valid-type"
"""Administration commands for Valentina."""
from pathlib import Path

import discord
import inflect
from discord.commands import Option
from discord.ext import commands
from discord.ext.commands import MemberConverter

from valentina.constants import VALID_IMAGE_EXTENSIONS, RollResultType
from valentina.models.bot import Valentina
from valentina.utils import errors
from valentina.utils.converters import ValidImageURL
from valentina.utils.discord_utils import assert_permissions
from valentina.utils.helpers import fetch_data_from_url
from valentina.views import (
    SettingsManager,
    ThumbnailReview,
    confirm_action,
    present_embed,
)

p = inflect.engine()


class Admin(commands.Cog):
    """Valentina settings, debugging, and administration."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot

    admin = discord.SlashCommandGroup(
        "admin",
        "Administer Valentina",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    user = admin.create_subgroup(
        "user",
        "Administer users",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    guild = admin.create_subgroup(
        "guild",
        "Administer guild",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    channel = admin.create_subgroup(
        "channel",
        "Administer the current channel",
        default_member_permissions=discord.Permissions(administrator=True),
    )

    ### USER ADMINISTRATION COMMANDS ################################################################

    @user.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def add_role(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Member,
        role: discord.Role,
        reason: Option(str, description="Reason for adding role", default="No reason provided"),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Add user to role."""
        # Confirm the action
        title = f"Add {member.display_name} to {role.name}"
        is_confirmed, confirmation_response_msg = await confirm_action(
            ctx, title, description=reason, hidden=hidden
        )
        if not is_confirmed:
            return

        await member.add_roles(role, reason=reason)

        await confirmation_response_msg

    @user.command()
    @discord.guild_only()
    @commands.has_permissions(administrator=True)
    async def kick(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Member,
        *,
        reason: str = "No reason given",
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Kick a target member, by ID or mention."""
        if member.id == ctx.author.id:
            msg = "You cannot kick yourself."
            raise errors.ValidationError(msg)

        if member.top_role >= ctx.author.top_role:
            msg = "You cannot kick this member."
            raise errors.ValidationError(msg)

        # Confirm the action
        title = f"Kick {member.display_name} from this guild"
        is_confirmed, confirmation_response_msg = await confirm_action(
            ctx, title, description=reason, hidden=hidden
        )
        if not is_confirmed:
            return

        await member.kick(reason=reason)

        await confirmation_response_msg

    @user.command()
    @discord.guild_only()
    @commands.has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: discord.ApplicationContext,
        user: discord.User,
        *,
        reason: str = "No reason given",
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Ban a target member, by ID or mention."""
        await assert_permissions(ctx, ban_members=True)
        if user := discord.utils.get(ctx.guild.members, id=user.id):
            if user.id == ctx.author.id:
                msg = "You cannot ban yourself."
                raise errors.ValidationError(msg)

            if user.top_role >= ctx.author.top_role:
                msg = "You cannot ban this member."
                raise errors.ValidationError(msg)

        # Confirm the action
        title = f"Ban {user.display_name} from this guild"
        is_confirmed, confirmation_response_msg = await confirm_action(
            ctx, title, description=reason, hidden=hidden
        )
        if not is_confirmed:
            return

        await ctx.guild.ban(
            discord.Object(id=user.id), reason=f"{ctx.author} ({ctx.author.id}): {reason}"
        )

        await confirmation_response_msg

    @user.command()
    @discord.guild_only()
    @commands.has_permissions(administrator=True)
    async def unban(
        self,
        ctx: discord.ApplicationContext,
        user: discord.User,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Revoke ban from a banned user."""
        # Confirm the action
        title = f"Unban {user.display_name} from this guild"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        try:
            await ctx.guild.unban(user)
        except discord.HTTPException:
            await present_embed(
                ctx,
                title=f"{user.display_name} ({user.id}) was not banned",
                level="info",
                ephemeral=True,
            )
            return

        await confirmation_response_msg

    @user.command()
    @discord.guild_only()
    @commands.has_permissions(administrator=True)
    async def massban(
        self,
        ctx: discord.ApplicationContext,
        members: Option(
            str, "The mentions, usernames, or IDs of the members to ban. Separated by spaces"
        ),
        *,
        reason: Option(
            str,
            description="The reason for the ban",
            default="No reason provided",
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Ban the supplied members from the guild. Limited to 10 at a time."""
        await assert_permissions(ctx, ban_members=True)
        converter = MemberConverter()
        converted_members = [
            await converter.convert(ctx, member) for member in members.split()  # type: ignore # mismatching context type
        ]
        if (count := len(converted_members)) > 10:  # noqa: PLR2004
            await present_embed(
                ctx,
                title="Too many members",
                description="You can only ban 10 members at a time",
                level="error",
                ephemeral=True,
            )
            return

        # Confirm the action
        title = f"Mass ban {count} {p.plural_noun('member', count)} from this guild"
        is_confirmed, confirmation_response_msg = await confirm_action(
            ctx, title, description=reason, hidden=hidden
        )
        if not is_confirmed:
            return

        for user in converted_members:
            if user := discord.utils.get(ctx.guild.members, id=user.id):
                if user.id == ctx.author.id:
                    msg = "You cannot ban yourself."
                    raise errors.ValidationError(msg)

                if user.top_role >= ctx.author.top_role:
                    msg = "You cannot ban this member."
                    raise errors.ValidationError(msg)

            await ctx.guild.ban(user, reason=f"{ctx.author} ({ctx.author.id}): {reason}")

        await confirmation_response_msg

    ## SETTINGS COMMANDS #############################################################################

    @admin.command(name="settings", description="Manage Guild Settings")
    async def settings_manager(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Manage Guild Settings."""
        manager = SettingsManager(ctx)
        paginator = await manager.display_settings_manager()
        await paginator.respond(ctx.interaction, ephemeral=hidden)
        await paginator.wait()

    ### GUILD ADMINISTRATION COMMANDS ################################################################

    @guild.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def review_result_thumbnails(
        self, ctx: discord.ApplicationContext, roll_type: Option(RollResultType, required=True)
    ) -> None:
        """Review all result thumbnails for this guild."""
        await ThumbnailReview(ctx, roll_type).send(ctx)

    @guild.command(name="emoji_add")
    async def emoji_add(
        self,
        ctx: discord.ApplicationContext,
        name: Option(str, description="The name of the emoji to add"),
        file: Option(
            discord.Attachment,
            description="Location of the image on your local computer",
            required=False,
            default=None,
        ),
        url: Option(ValidImageURL, description="URL of the image", required=False, default=None),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Add a custom emoji to this guild."""
        await assert_permissions(ctx, manage_emojis=True)

        # Validate input
        if (not file and not url) or (file and url):
            await present_embed(ctx, title="Please provide a single image", level="error")
            return

        if file:
            file_extension = Path(file.filename).suffix.lstrip(".").lower()
            if file_extension not in VALID_IMAGE_EXTENSIONS:
                await present_embed(
                    ctx,
                    title=f"Must provide a valid image: {', '.join(VALID_IMAGE_EXTENSIONS)}",
                    level="error",
                )
                return

        # Grab the bytes from the file or url
        data = await file.read() if file else await fetch_data_from_url(url)

        # Confirm the action
        title = f"Add custom emoji :{name}:"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        # Add the emoji
        await ctx.guild.create_custom_emoji(name=name, image=data)

        # Send confirmation
        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    @guild.command(name="emoji_delete")
    @discord.option("name", description="The name of the emoji to delete.")
    async def emoji_delete(
        self,
        ctx: discord.ApplicationContext,
        name: str,
        reason: Option(
            str,
            description="The reason for deleting this emoji",
            default="No reason provided",
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete a custom emoji from this guild."""
        await assert_permissions(ctx, manage_emojis=True)
        for emoji in ctx.guild.emojis:
            if emoji.name == name:
                await emoji.delete(reason=reason)

                await self.bot.guild_svc.send_to_audit_log(
                    ctx, f"Delete emoji from guild: `:{name}:`"
                )

                await present_embed(
                    ctx,
                    title=f"Emoji `:{name}:` deleted",
                    description=reason,
                    level="success",
                    ephemeral=hidden,
                )
                return

        await present_embed(
            ctx,
            title="Emoji Not Found",
            description=f"Could not find a custom emoji name `:{name}:`",
            level="error",
            ephemeral=True,
        )

    ### CHANNEL ADMINISTRATION COMMANDS ################################################################
    @channel.command(name="slowmode", description="Set slowmode for the current channel")
    @discord.guild_only()
    @commands.has_permissions(administrator=True)
    async def slowmode(
        self,
        ctx: discord.ApplicationContext,
        seconds: Option(int, description="The slowmode cooldown in seconds, 0 to disable slowmode"),
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Set slowmode for the current channel."""
        if not isinstance(ctx.channel, discord.TextChannel):
            msg = "Slowmode can only be set in text channels."
            raise commands.BadArgument(msg)

        await assert_permissions(ctx, manage_channels=True)

        if not 21600 >= seconds >= 0:  # noqa: PLR2004
            await present_embed(
                ctx,
                title="Error setting slowmode",
                description="Slowmode should be between `21600` and `0` seconds",
                level="error",
                ephemeral=hidden,
            )
            return

        # Confirm the action
        title = f"Set slowmode to {seconds} seconds"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        await ctx.channel.edit(slowmode_delay=seconds)

        await confirmation_response_msg

    @channel.command()
    @discord.guild_only()
    @commands.has_permissions(administrator=True)
    async def lock(
        self,
        ctx: discord.ApplicationContext,
        *,
        reason: Option(
            str,
            description="The reason for locking this channel",
            default="No reason provided",
        ),
        hidden: Option(
            bool,
            description="Make the response only visible to you (default false).",
            default=False,
        ),
    ) -> None:
        """Disable the `Send Message` permission for the default role."""
        await assert_permissions(ctx, manage_roles=True)

        if not isinstance(ctx.channel, discord.TextChannel):
            msg = "Only text channels can be locked"
            raise commands.BadArgument(msg)

        if ctx.channel.overwrites_for(ctx.guild.default_role).send_messages is False:
            await ctx.respond("This channel is already locked.", ephemeral=True)
            return

        # Confirm the action
        title = "Lock this channel"
        is_confirmed, confirmation_response_msg = await confirm_action(
            ctx, title, description=reason, hidden=hidden
        )
        if not is_confirmed:
            return

        await ctx.channel.edit(
            overwrites={ctx.guild.default_role: discord.PermissionOverwrite(send_messages=False)},
            reason=f"{ctx.author} ({ctx.author.id}): {reason}",
        )

        await confirmation_response_msg

    @channel.command()
    @discord.guild_only()
    @commands.has_permissions(administrator=True)
    async def unlock(
        self,
        ctx: discord.ApplicationContext,
        *,
        reason: Option(
            str,
            description="The reason for unlocking this channel",
            default="No reason provided",
        ),
        hidden: Option(
            bool,
            description="Make the response only visible to you (default false).",
            default=False,
        ),
    ) -> None:
        """Set the `Send Message` permission to the default state for the default role."""
        await assert_permissions(ctx, manage_roles=True)
        if not isinstance(ctx.channel, discord.TextChannel):
            msg = "Only text channels can be locked or unlocked"
            raise commands.BadArgument(msg)

        if ctx.channel.overwrites_for(ctx.guild.default_role).send_messages is not False:
            await ctx.respond("This channel isn't locked.", ephemeral=True)
            return

        # Confirm the action
        title = "Unlock this channel"
        is_confirmed, confirmation_response_msg = await confirm_action(
            ctx, title, description=reason, hidden=hidden
        )
        if not is_confirmed:
            return

        await ctx.channel.edit(
            overwrites={ctx.guild.default_role: discord.PermissionOverwrite(send_messages=None)},
            reason=f"{ctx.author} ({ctx.author.id}): {reason}",
        )
        await confirmation_response_msg

    @channel.command()
    @commands.has_permissions(administrator=True)
    @discord.option(
        "limit",
        description="The amount of messages to delete",
        min_value=1,
        max_value=100,
    )
    async def purge_old_messages(
        self,
        ctx: discord.ApplicationContext,
        limit: int,
        *,
        reason: Option(
            str,
            description="The reason for purging messages.",
            default="No reason provided",
        ),
    ) -> None:
        """Delete messages from this channel."""
        await assert_permissions(ctx, read_message_history=True, manage_messages=True)

        if purge := getattr(ctx.channel, "purge", None):
            count = len(await purge(limit=limit, reason=reason))
            await present_embed(
                ctx,
                title=f"Purged `{count}` {p.plural_noun('message', count)} from this channel",
                level="warning",
                ephemeral=True,
            )
            return

        await ctx.respond("This channel cannot be purged", ephemeral=True)
        return

    @channel.command()
    @commands.has_permissions(administrator=True)
    @discord.option(
        "member",
        description="The member whose messages will be deleted.",
    )
    @discord.option(
        "limit",
        description="The amount of messages to search.",
        min_value=1,
        max_value=100,
    )
    async def purge_by_member(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Member,
        limit: int,
        *,
        reason: Option(
            str,
            description="The reason for purging messages",
            default="No reason provided",
        ),
    ) -> None:
        """Purge a member's messages from this channel."""
        await assert_permissions(ctx, read_message_history=True, manage_messages=True)

        if purge := getattr(ctx.channel, "purge", None):
            count = len(
                await purge(limit=limit, reason=reason, check=lambda m: m.author.id == member.id)
            )
            await present_embed(
                ctx,
                title=f"Purged `{count}` {p.plural_noun('message', count)} from `{member.display_name}` in this channel",
                level="warning",
                ephemeral=True,
            )
            return

        await ctx.respond("This channel cannot be purged", ephemeral=True)
        return

    @channel.command()
    @commands.has_permissions(administrator=True)
    @discord.option(
        "limit",
        description="The amount of messages to search.",
        min_value=1,
        max_value=100,
    )
    async def purge_bot_messages(
        self,
        ctx: discord.ApplicationContext,
        limit: int,
        *,
        reason: Option(
            str,
            description="The reason for purging messages",
            default="No reason provided",
        ),
    ) -> None:
        """Purge bot messages from this channel."""
        await assert_permissions(ctx, read_message_history=True, manage_messages=True)

        if purge := getattr(ctx.channel, "purge", None):
            count = len(await purge(limit=limit, reason=reason, check=lambda m: m.author.bot))
            await present_embed(
                ctx,
                title=f"Purged `{count}` bot {p.plural_noun('message', count)} in this channel",
                level="warning",
                ephemeral=True,
            )
            return

        await ctx.respond("This channel cannot be purged", ephemeral=True)
        return

    @channel.command()
    @commands.has_permissions(administrator=True)
    @discord.option(
        "phrase",
        description="The phrase to delete messages containing it.",
    )
    @discord.option(
        "limit",
        description="The amount of messages to search.",
        min_value=1,
        max_value=100,
    )
    async def purge_containing(
        self,
        ctx: discord.ApplicationContext,
        phrase: str,
        limit: int,
        *,
        reason: Option(
            str,
            description="The reason for purging messages",
            default="No reason provided",
        ),
    ) -> None:
        """Purge messages containing a specific phrase from this channel."""
        await assert_permissions(ctx, read_message_history=True, manage_messages=True)

        if purge := getattr(ctx.channel, "purge", None):
            count = len(
                await purge(limit=limit, reason=reason, check=lambda m: phrase in m.content)
            )
            await present_embed(
                ctx,
                title=f"Purged `{count}` {p.plural_noun('message', count)} containing `{phrase}` in this channel",
                level="warning",
                ephemeral=True,
            )
            return

        await ctx.respond("This channel cannot be purged", ephemeral=True)
        return


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Admin(bot))
