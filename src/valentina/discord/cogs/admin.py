# mypy: disable-error-code="valid-type"
"""Administration commands for Valentina."""

from pathlib import Path

import discord
import inflect
from discord.commands import Option
from discord.ext import commands
from discord.ext.commands import MemberConverter

from valentina.constants import VALID_IMAGE_EXTENSIONS, RollResultType
from valentina.controllers import ChannelManager, delete_character
from valentina.discord.bot import Valentina, ValentinaContext
from valentina.discord.utils import assert_permissions
from valentina.discord.utils.autocomplete import select_any_character, select_campaign
from valentina.discord.utils.converters import ValidCampaign, ValidCharacterObject, ValidImageURL
from valentina.discord.views import (
    SettingsManager,
    ThumbnailReview,
    confirm_action,
    present_embed,
)
from valentina.models import Guild as DBGuild
from valentina.utils import errors
from valentina.utils.helpers import fetch_data_from_url

p = inflect.engine()


class AdminCog(commands.Cog):
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

    ### VALENTINA ADMINISTRATION COMMANDS ###########################################################
    @admin.command(name="rebuild_campaign_channels", description="Rebuild Campaign Channels")
    @discord.guild_only()
    @commands.has_permissions(administrator=True)
    async def rebuild_campaign_channels(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Manage Guild Settings."""
        title = "Rebuild all campaign channels?"
        is_confirmed, msg, confirmation_embed = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        db_guild = await DBGuild.get(ctx.guild.id, fetch_links=True)

        channel_manager = ChannelManager(guild=ctx.guild)
        for campaign in db_guild.campaigns:
            await channel_manager.delete_campaign_channels(campaign)
            await channel_manager.confirm_campaign_channels(campaign)

        await msg.edit_original_response(embed=confirmation_embed, view=None)

    @discord.guild_only()
    @commands.has_permissions(administrator=True)
    @admin.command(name="character_to_campaign", description="Associate character with a campaign")
    async def associate_campaign(
        self,
        ctx: ValentinaContext,
        character: Option(
            ValidCharacterObject,
            description="The character to transfer",
            autocomplete=select_any_character,
            required=True,
        ),
        campaign: Option(
            ValidCampaign,
            description="The campaign to associate with",
            autocomplete=select_campaign,
            required=True,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Associate a character with a campaign."""
        if character.campaign == str(campaign.id):
            await present_embed(
                ctx,
                title=f"`{character.name}` already in `{campaign.name}`",
                description="The character is already associated with this campaign",
                level="warning",
                ephemeral=True,
            )
            return

        title = f"Associate `{character.name}` with `{campaign.name}`"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx,
            title,
            hidden=hidden,
            audit=True,
        )
        if not is_confirmed:
            return

        character.campaign = str(campaign.id)
        await character.save()

        channel_manager = ChannelManager(guild=ctx.guild)
        await channel_manager.delete_character_channel(character)
        await channel_manager.confirm_character_channel(character=character, campaign=campaign)
        await channel_manager.sort_campaign_channels(campaign)

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @discord.guild_only()
    @commands.has_permissions(administrator=True)
    @admin.command(
        name="delete_champaign_channels",
        description="Associate character with a campaign",
    )
    async def delete_champaign_channels(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete all campaign channels from Discord."""
        db_guild = await DBGuild.get(ctx.guild.id, fetch_links=True)

        title = f"Delete all campaign channels from `{ctx.guild.name}`"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx,
            title,
            hidden=hidden,
        )
        if not is_confirmed:
            return

        channel_manager = ChannelManager(guild=ctx.guild)
        for campaign in db_guild.campaigns:
            await channel_manager.delete_campaign_channels(campaign)

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @discord.guild_only()
    @commands.has_permissions(administrator=True)
    @admin.command(name="character_delete", description="Delete a character from database")
    async def character_delete(
        self,
        ctx: ValentinaContext,
        character: Option(
            ValidCharacterObject,
            description="The character to kill",
            autocomplete=select_any_character,
            required=True,
        ),
        hidden: Option(
            bool,
            description="Make the interaction only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete a character from the database."""
        title = f"Delete `{character.name}` from the database"
        description = "This action is irreversible."
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx,
            title,
            description=description,
            hidden=hidden,
            audit=True,
        )
        if not is_confirmed:
            return

        await delete_character(character)

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    ### USER ADMINISTRATION COMMANDS ###############################################################
    @user.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def role_add(
        self,
        ctx: ValentinaContext,
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
        is_confirmed, msg, confirmation_embed = await confirm_action(
            ctx,
            title,
            description=reason,
            hidden=hidden,
        )
        if not is_confirmed:
            return

        await member.add_roles(role, reason=reason)

        await msg.edit_original_response(embed=confirmation_embed, view=None)

    @user.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def role_remove(
        self,
        ctx: ValentinaContext,
        member: discord.Member,
        role: discord.Role,
        reason: Option(str, description="Reason for removing role", default="No reason provided"),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Add user to role."""
        # Confirm the action
        title = f"Remove {role.name} from {member.display_name}"
        is_confirmed, msg, confirmation_embed = await confirm_action(
            ctx,
            title,
            description=reason,
            hidden=hidden,
        )
        if not is_confirmed:
            return

        await member.remove_roles(role, reason=reason)

        await msg.edit_original_response(embed=confirmation_embed, view=None)

    @user.command()
    @discord.guild_only()
    @commands.has_permissions(administrator=True)
    async def kick(
        self,
        ctx: ValentinaContext,
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

        if isinstance(ctx.author, discord.Member) and member.top_role >= ctx.author.top_role:
            msg = "You cannot kick this member."
            raise errors.ValidationError(msg)

        # Confirm the action
        title = f"Kick {member.display_name} from this guild"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx,
            title,
            description=reason,
            hidden=hidden,
        )
        if not is_confirmed:
            return

        await member.kick(reason=reason)

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @user.command()
    @discord.guild_only()
    @commands.has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: ValentinaContext,
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

            if isinstance(ctx.author, discord.Member) and user.top_role >= ctx.author.top_role:
                msg = "You cannot ban this member."
                raise errors.ValidationError(msg)

        # Confirm the action
        title = f"Ban {user.display_name} from this guild"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx,
            title,
            description=reason,
            hidden=hidden,
        )
        if not is_confirmed:
            return

        await ctx.guild.ban(
            discord.Object(id=user.id),
            reason=f"{ctx.author} ({ctx.author.id}): {reason}",
        )

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @user.command()
    @discord.guild_only()
    @commands.has_permissions(administrator=True)
    async def unban(
        self,
        ctx: ValentinaContext,
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
        is_confirmed, msg, confirmation_embed = await confirm_action(ctx, title, hidden=hidden)
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

        await msg.edit_original_response(embed=confirmation_embed, view=None)

    @user.command()
    @discord.guild_only()
    @commands.has_permissions(administrator=True)
    async def massban(
        self,
        ctx: ValentinaContext,
        members: Option(
            str,
            "The mentions, usernames, or IDs of the members to ban. Separated by spaces",
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
            await converter.convert(ctx, member)  # type: ignore [arg-type]
            for member in members.split()
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
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx,
            title,
            description=reason,
            hidden=hidden,
        )
        if not is_confirmed:
            return

        for user in converted_members:
            if user := discord.utils.get(ctx.guild.members, id=user.id):
                if user.id == ctx.author.id:
                    msg = "You cannot ban yourself."
                    raise errors.ValidationError(msg)

                if isinstance(ctx.author, discord.Member) and user.top_role >= ctx.author.top_role:
                    msg = "You cannot ban this member."
                    raise errors.ValidationError(msg)

            await ctx.guild.ban(user, reason=f"{ctx.author} ({ctx.author.id}): {reason}")

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    ## SETTINGS COMMANDS #############################################################################

    @admin.command(name="settings", description="Manage Guild Settings")
    async def settings_manager(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Manage Guild Settings."""
        db_guild = await DBGuild.get(ctx.guild.id, fetch_links=True)
        manager = SettingsManager(ctx, db_guild=db_guild)
        paginator = await manager.display_settings_manager()
        await paginator.respond(ctx.interaction, ephemeral=hidden)
        await paginator.wait()

    ### GUILD ADMINISTRATION COMMANDS ################################################################

    @guild.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def review_result_thumbnails(
        self,
        ctx: ValentinaContext,
        roll_type: Option(RollResultType, required=True),
    ) -> None:
        """Review all result thumbnails for this guild."""
        db_guild = await DBGuild.get(ctx.guild.id, fetch_links=True)
        await ThumbnailReview(ctx, db_guild=db_guild, roll_type=roll_type).send(ctx)

    @guild.command(name="emoji_add")
    async def emoji_add(
        self,
        ctx: ValentinaContext,
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
        is_confirmed, msg, confirmation_embed = await confirm_action(
            ctx,
            title,
            hidden=hidden,
            audit=True,
        )
        if not is_confirmed:
            return

        # Add the emoji
        await ctx.guild.create_custom_emoji(name=name, image=data)

        # Send confirmation
        await msg.edit_original_response(embed=confirmation_embed, view=None)

    @guild.command(name="emoji_delete")
    @discord.option("name", description="The name of the emoji to delete.")
    async def emoji_delete(
        self,
        ctx: ValentinaContext,
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

                await ctx.post_to_audit_log(f"Delete emoji from guild: `:{name}:`")

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
        ctx: ValentinaContext,
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
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx,
            title,
            hidden=hidden,
        )
        if not is_confirmed:
            return

        await ctx.channel.edit(slowmode_delay=seconds)

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @channel.command()
    @discord.guild_only()
    @commands.has_permissions(administrator=True)
    async def lock(
        self,
        ctx: ValentinaContext,
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
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx,
            title,
            description=reason,
            hidden=hidden,
        )
        if not is_confirmed:
            return

        await ctx.channel.edit(
            overwrites={ctx.guild.default_role: discord.PermissionOverwrite(send_messages=False)},
            reason=f"{ctx.author} ({ctx.author.id}): {reason}",
        )

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @channel.command()
    @discord.guild_only()
    @commands.has_permissions(administrator=True)
    async def unlock(
        self,
        ctx: ValentinaContext,
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
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx,
            title,
            description=reason,
            hidden=hidden,
        )
        if not is_confirmed:
            return

        await ctx.channel.edit(
            overwrites={ctx.guild.default_role: discord.PermissionOverwrite(send_messages=None)},
            reason=f"{ctx.author} ({ctx.author.id}): {reason}",
        )
        await interaction.edit_original_response(embed=confirmation_embed, view=None)

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
        ctx: ValentinaContext,
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
        ctx: ValentinaContext,
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
                await purge(limit=limit, reason=reason, check=lambda m: m.author.id == member.id),
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
        ctx: ValentinaContext,
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
        ctx: ValentinaContext,
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
                await purge(limit=limit, reason=reason, check=lambda m: phrase in m.content),
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
    bot.add_cog(AdminCog(bot))
