# mypy: disable-error-code="valid-type"
"""Administration commands for Valentina."""

from io import BytesIO

import discord
from discord import OptionChoice
from discord.commands import Option
from discord.ext import commands
from discord.ext.commands import MemberConverter
from loguru import logger

from valentina.models.bot import Valentina
from valentina.models.constants import TraitPermissions, XPPermissions
from valentina.utils import Context
from valentina.utils.converters import ValidChannelName
from valentina.utils.helpers import pluralize
from valentina.views import ConfirmCancelButtons, present_embed


class Admin(commands.Cog):
    """Valentina settings, debugging, and administration."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    async def cog_command_error(
        self, ctx: discord.ApplicationContext, error: discord.ApplicationCommandError | Exception
    ) -> None:
        """Handle exceptions and errors from the cog."""
        if hasattr(error, "original"):
            error = error.original

        logger.exception(error)

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

    ### BOT ADMINISTRATION COMMANDS ################################################################

    admin = discord.SlashCommandGroup(
        "admin",
        "Administer Valentina",
        default_member_permissions=discord.Permissions(administrator=True),
    )

    @admin.command(description="Purge the bot's cache and reload data from DB")
    @commands.guild_only()
    async def puge_cache(
        self,
        ctx: discord.ApplicationContext,
        all_guilds: Option(bool, choices=[True, False], default=False, required=False),
    ) -> None:
        """Purge the bot's cache and reload all data from DB."""
        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title="Purge all caches?" if all_guilds else "Purge this guild's cache?",
            description="This will purge all caches and reload all data from the database"
            if all_guilds
            else "This will purge this guild's cache and reload all data from the database",
            level="info",
            ephemeral=True,
            view=view,
        )
        await view.wait()

        if not view.confirmed:
            await msg.edit_original_response(
                embed=discord.Embed(
                    title="Cache Purge Cancelled",
                    color=discord.Color.red(),
                )
            )
            return

        if not all_guilds:
            self.bot.guild_svc.purge_cache(ctx)
            self.bot.user_svc.purge_cache(ctx)
            self.bot.char_svc.purge_cache(ctx, with_claims=True)
            self.bot.chron_svc.purge_cache(ctx)
            logger.info(f"ADMIN: Purge cache for {ctx.guild.name}")

        if all_guilds:
            self.bot.guild_svc.purge_cache()
            self.bot.user_svc.purge_cache()
            self.bot.char_svc.purge_cache(with_claims=True)
            self.bot.chron_svc.purge_cache()
            logger.info("ADMIN: Purge cache for all guilds")

        await msg.delete_original_response()
        await present_embed(
            ctx,
            title="All caches purged" if all_guilds else "Guild caches purged",
            level="success",
            ephemeral=True,
            log=True,
        )

    @admin.command(description="Manage settings")
    @commands.guild_only()
    async def settings(
        self,
        ctx: discord.ApplicationContext,
        xp_permissions: Option(
            str,
            "Whether users should be allowed to edit their XP totals.",
            choices=[
                OptionChoice(x.name.title().replace("_", " "), str(x.value)) for x in XPPermissions
            ],
            required=False,
        ),
        use_audit_log: Option(
            bool,
            "Send audit logs to channel",
            choices=[OptionChoice("Enable", True), OptionChoice("Disable", False)],
            required=False,
            default=None,
        ),
        audit_log_channel: Option(
            ValidChannelName,
            "Log to this channel",
            required=False,
            default=None,
        ),
        trait_permissions: Option(
            str,
            "Whether users should be allowed to edit their traits.",
            choices=[
                OptionChoice(x.name.title().replace("_", " "), str(x.value))
                for x in TraitPermissions
            ],
            required=False,
        ),
    ) -> None:
        """Manage settings."""
        fields = []
        if xp_permissions is not None:
            logger.debug(
                f"SETTINGS: ([{ctx.guild.id}] {ctx.guild.name}) XP Permissions: {XPPermissions(int(xp_permissions)).name.title()}"
            )
            fields.append(("XP Permissions", XPPermissions(int(xp_permissions)).name.title()))
            self.bot.guild_svc.update_or_add(ctx=ctx, xp_permissions=int(xp_permissions))

        if trait_permissions is not None:
            logger.debug(
                f"SETTINGS: ([{ctx.guild.id}] {ctx.guild.name}) Trait Permissions: {TraitPermissions(int(trait_permissions)).name.title()}"
            )
            fields.append(
                ("Trait Permissions", TraitPermissions(int(trait_permissions)).name.title())
            )
            self.bot.guild_svc.update_or_add(ctx=ctx, trait_permissions=int(trait_permissions))

        if use_audit_log is not None:
            guild_settings = self.bot.guild_svc.fetch_guild_settings(ctx)

            if use_audit_log and not guild_settings["log_channel_id"] and not audit_log_channel:
                await present_embed(
                    ctx,
                    title="No audit log channel",
                    description="Please rerun the command and enter a channel name for audit logging",
                    level="error",
                    ephemeral=True,
                )
                return

            logger.debug(
                f"SETTINGS: ([{ctx.guild.id}] {ctx.guild.name}) Log to channel: {use_audit_log}"
            )
            fields.append(("Audit Logging", "Enabled" if use_audit_log else "Disabled"))
            self.bot.guild_svc.update_or_add(ctx=ctx, use_audit_log=use_audit_log)

        if audit_log_channel is not None:
            channel = await self.bot.guild_svc.create_bot_log_channel(ctx, audit_log_channel)
            logger.debug(
                f"SETTINGS: ([{ctx.guild.id}] {ctx.guild.name}) Log channel: {channel.name}"
            )
            fields.append(("Audit Log Channel", channel.mention))

        if len(fields) > 0:
            await present_embed(
                ctx,
                title="Settings Updated",
                fields=fields,
                level="success",
                log=True,
                ephemeral=True,
            )
        else:
            await present_embed(ctx, title="No settings updated", level="info", ephemeral=True)

    @admin.command(description="Show server settings")
    @commands.guild_only()
    async def show_settings(self, ctx: discord.ApplicationContext) -> None:
        """Show server settings."""
        settings = self.bot.guild_svc.fetch_guild_settings(ctx)

        fields = [
            ("XP Permissions", XPPermissions(settings["xp_permissions"]).name.title()),
            ("Trait Permissions", TraitPermissions(settings["trait_permissions"]).name.title()),
            ("Audit Logging", "Enabled" if settings["use_audit_log"] else "Disabled"),
            (
                "Audit Log Channel",
                discord.utils.get(ctx.guild.text_channels, id=settings["log_channel_id"]).mention
                if settings["log_channel_id"]
                else "Not set",
            ),
        ]
        await present_embed(
            ctx,
            title="Server Settings",
            fields=fields,
            inline_fields=True,
            level="info",
            ephemeral=True,
        )

    ### MODERATION COMMANDS ################################################################

    moderate = discord.SlashCommandGroup(
        "mod",
        "Moderation commands",
        default_member_permissions=discord.Permissions(administrator=True),
    )

    @moderate.command()
    @discord.guild_only()
    async def userinfo(
        self,
        ctx: discord.ApplicationContext,
        user: Option(discord.User, description="The user to view information for", default=None),
    ) -> None:
        """View information about a user."""
        target = user or ctx.author
        creation = ((target.id >> 22) + 1420070400000) // 1000

        fields = [("Account Created", f"<t:{creation}:R> on <t:{creation}:D>")]
        if isinstance(target, discord.Member):
            fields.append(
                (
                    "Joined Server",
                    f"<t:{int(target.joined_at.timestamp())}:R> on <t:{int(target.joined_at.timestamp())}:D>",
                )
            )
            fields.append(
                (
                    f"Roles ({len(target._roles)})",
                    ", ".join(r.mention for r in target.roles[::-1][:-1])
                    or "_Member has no roles_",
                )
            )
            if boost := target.premium_since:
                fields.append(
                    (
                        "Boosting Since",
                        f"<t:{int(boost.timestamp())}:R> on <t:{int(boost.timestamp())}:D>",
                    )
                )
            else:
                fields.append(("Boosting Server?", "No"))

        await present_embed(
            ctx,
            title=f"{target.display_name}",
            fields=fields,
            inline_fields=False,
            thumbnail=target.display_avatar.url,
            author=str(target),
            author_avatar=target.display_avatar.url,
            footer=f"Requested by {ctx.author}",
            ephemeral=True,
            level="info",
        )

    @moderate.command()
    @discord.guild_only()
    async def kick(
        self, ctx: Context, member: discord.Member, *, reason: str = "No reason given"
    ) -> None:
        """Kick a target member, by ID or mention."""
        if member.id == ctx.author.id:
            raise ValueError("You cannot kick yourself.")

        if member.top_role >= ctx.author.top_role:
            raise ValueError("You cannot kick this member.")

        await member.kick(reason=reason)

        await present_embed(
            ctx,
            title="Kick Successful",
            description=f"Kicked {member.mention} ({member})",
            fields=[("Reason", reason)] if reason else [],
            level="success",
            ephemeral=True,
            log=True,
        )

    @moderate.command()
    @discord.guild_only()
    @commands.has_permissions(ban_members=True)
    async def ban(
        self, ctx: Context, user: discord.User, *, reason: str = "No reason given"
    ) -> None:
        """Ban a target member, by ID or mention."""
        if user := discord.utils.get(ctx.guild.members, id=user.id):
            if user.id == ctx.author.id:
                raise ValueError("You cannot ban yourself.")

            if user.top_role >= ctx.author.top_role:
                raise ValueError("You cannot ban this member.")

        await ctx.guild.ban(
            discord.Object(id=user.id), reason=f"{ctx.author} ({ctx.author.id}): {reason}"
        )

        await present_embed(
            ctx,
            title="Ban Successful",
            description=f"Banned {user.mention} ({user})",
            fields=[("Reason", reason)] if reason else [],
            level="success",
            ephemeral=True,
            log=True,
        )

    @moderate.command()
    @discord.guild_only()
    async def unban(self, ctx: Context, user: discord.User) -> None:
        """Revoke ban from a banned user."""
        try:
            await ctx.guild.unban(user)
        except discord.HTTPException as e:
            raise Exception("This user has not been banned.") from e

        await present_embed(
            ctx,
            title="Unban Successful",
            description=f"Unbanned `{user} ({user.id})`.",
            level="success",
            ephemeral=True,
            log=True,
        )

    @moderate.command()
    @discord.guild_only()
    async def massban(
        self,
        ctx: Context,
        members: Option(
            str, "The mentions, usernames, or IDs of the members to ban. Seperated by spaces"
        ),
        *,
        reason: Option(
            str,
            description="The reason for the ban",
            default="No reason provided",
        ),
    ) -> None:
        """Ban the supplied members from the guild. Limited to 10 at a time."""
        await ctx.assert_permissions(ban_members=True)
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

        for user in converted_members:
            if user := discord.utils.get(ctx.guild.members, id=user.id):
                if user.id == ctx.author.id:
                    raise ValueError("You cannot ban yourself.")

                if user.top_role >= ctx.author.top_role:
                    raise ValueError("You cannot ban this member.")
            await ctx.guild.ban(user, reason=f"{ctx.author} ({ctx.author.id}): {reason}")

        await present_embed(
            ctx,
            title="Mass Ban Successful",
            description=f"Banned **{count}** {pluralize(count, 'member')}",
            level="success",
            ephemeral=True,
            log=True,
        )

    @moderate.command()
    @discord.guild_only()
    async def slowmode(
        self,
        ctx: Context,
        seconds: Option(int, description="The slowmode cooldown in seconds, 0 to disable slowmode"),
    ) -> None:
        """Set slowmode for the current channel."""
        if not isinstance(ctx.channel, discord.TextChannel):
            raise commands.BadArgument("Slowmode can only be set in text channels.")

        await ctx.assert_permissions(manage_channels=True)
        if not 21600 >= seconds >= 0:  # noqa: PLR2004
            await present_embed(
                ctx,
                title="Error setting slowmode",
                description="Slowmode should be between `21600` and `0` seconds",
                level="error",
                ephemeral=True,
            )
            return

        await ctx.channel.edit(slowmode_delay=seconds)
        await present_embed(
            ctx,
            title="Slowmode set",
            description=f"The slowmode cooldown is now `{seconds}` {pluralize(seconds, 'second')}"
            if seconds > 0
            else "Slowmode is now disabled",
            level="success",
        )

        return

    @moderate.command()
    @discord.guild_only()
    async def lock(
        self,
        ctx: Context,
        *,
        reason: Option(
            str,
            description="The reason for locking this channel",
            default="No reason provided",
        ),
    ) -> None:
        """Disable the Send Messages permission for the default role."""
        await ctx.assert_permissions(manage_roles=True)

        if not isinstance(ctx.channel, discord.TextChannel):
            raise commands.BadArgument("Only text channels can be locked")

        if ctx.channel.overwrites_for(ctx.guild.default_role).send_messages is False:
            await ctx.respond("This channel is already locked.", ephemeral=True)
            return

        await ctx.channel.edit(
            overwrites={ctx.guild.default_role: discord.PermissionOverwrite(send_messages=False)},
            reason=f"{ctx.author} ({ctx.author.id}): {reason}",
        )
        await present_embed(
            ctx,
            title="Channel Locked",
            description=f"{ctx.author.display_name} locked this channel",
            fields=[("Reason", reason)],
            level="warning",
        )

        return

    @moderate.command()
    @discord.guild_only()
    async def unlock(
        self,
        ctx: Context,
        *,
        reason: Option(
            str,
            description="The reason for unlocking this channel",
            default="No reason provided",
        ),
    ) -> None:
        """Set the Send Messages permission to the default state for the default role."""
        await ctx.assert_permissions(manage_roles=True)
        if not isinstance(ctx.channel, discord.TextChannel):
            raise commands.BadArgument("Only text channels can be locked or unlocked")

        if ctx.channel.overwrites_for(ctx.guild.default_role).send_messages is not False:
            await ctx.respond("This channel isn't locked.", ephemeral=True)
            return

        await ctx.channel.edit(
            overwrites={ctx.guild.default_role: discord.PermissionOverwrite(send_messages=None)},
            reason=f"{ctx.author} ({ctx.author.id}): {reason}",
        )
        await present_embed(
            ctx,
            title="Channel Unlocked",
            description=f"{ctx.author.display_name} unlocked this channel",
            fields=[("Reason", reason)],
            level="info",
        )

    @moderate.command()
    @discord.option(
        "limit",
        description="The amount of messages to delete",
        min_value=1,
        max_value=100,
    )
    async def purge_old_messages(
        self,
        ctx: Context,
        limit: int,
        *,
        reason: Option(
            str,
            description="The reason for purging messages.",
            default="No reason provided",
        ),
    ) -> None:
        """Delete messages from this channel."""
        await ctx.assert_permissions(read_message_history=True, manage_messages=True)

        if purge := getattr(ctx.channel, "purge", None):
            count = len(await purge(limit=limit, reason=reason))
            await present_embed(
                ctx,
                title="Channel Purged",
                description=f"Purged **{count}** {pluralize(count, 'message')} from this channel",
                level="success",
                ephemeral=True,
            )
            return

        await ctx.respond("This channel cannot be purged", ephemeral=True)
        return

    @moderate.command()
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
        ctx: Context,
        member: discord.Member,
        limit: int,
        *,
        reason: Option(
            str,
            description="The reason for purging messsages",
            default="No reason provided",
        ),
    ) -> None:
        """Purge a member's messages from this channel."""
        await ctx.assert_permissions(read_message_history=True, manage_messages=True)

        if purge := getattr(ctx.channel, "purge", None):
            count = len(
                await purge(limit=limit, reason=reason, check=lambda m: m.author.id == member.id)
            )
            await present_embed(
                ctx,
                title="Channel Purged",
                description=f"Purged **{count}** {pluralize(count, 'message')} from **{member.display_name}** in this channel",
                level="success",
                ephemeral=True,
            )
            return

        await ctx.respond("This channel cannot be purged", ephemeral=True)
        return

    @moderate.command()
    @discord.option(
        "limit",
        description="The amount of messages to search.",
        min_value=1,
        max_value=100,
    )
    async def purge_bot_messages(
        self,
        ctx: Context,
        limit: int,
        *,
        reason: Option(
            str,
            description="The reason for purging messages",
            default="No reason provided",
        ),
    ) -> None:
        """Purge bot messages from this channel."""
        await ctx.assert_permissions(read_message_history=True, manage_messages=True)

        if purge := getattr(ctx.channel, "purge", None):
            count = len(await purge(limit=limit, reason=reason, check=lambda m: m.author.bot))
            await present_embed(
                ctx,
                title="Channel Purged",
                description=f"Purged **{count}** {pluralize(count, 'message')} from bots in this channel",
                level="success",
                ephemeral=True,
            )
            return

        await ctx.respond("This channel cannot be purged", ephemeral=True)
        return

    @moderate.command()
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
        ctx: Context,
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
        await ctx.assert_permissions(read_message_history=True, manage_messages=True)

        if purge := getattr(ctx.channel, "purge", None):
            count = len(
                await purge(limit=limit, reason=reason, check=lambda m: phrase in m.content)
            )
            await present_embed(
                ctx,
                title="Channel Purged",
                description=f"Purged **{count}** {pluralize(count, 'message')} containing `{phrase}` in this channel",
                level="success",
                ephemeral=True,
            )
            return

        await ctx.respond("This channel cannot be purged", ephemeral=True)
        return

    ### EMOJI COMMANDS ################################################################

    emoji = discord.SlashCommandGroup(
        "emoji",
        "Add/remove custom emojis to this guild",
        default_member_permissions=discord.Permissions(manage_emojis=True),
    )

    @emoji.command(name="add")
    @discord.option("name", description="The name of the emoji.")
    @discord.option("url", description="The image url of the emoji.")
    async def emoji_add(self, ctx: Context, name: str, url: str) -> None:
        """Add a custom emoji to this guild."""
        await ctx.assert_permissions(manage_emojis=True)
        async with self.bot.http_session.get(url) as res:
            if 300 > res.status >= 200:  # noqa: PLR2004
                await ctx.guild.create_custom_emoji(
                    name=name, image=BytesIO(await res.read()).getvalue()
                )

                await present_embed(
                    ctx,
                    title="Emoji Created",
                    description=f"Custom emoji `:{name}:` added",
                    image=url,
                    log=True,
                    level="success",
                    ephemeral=True,
                )

            else:
                await present_embed(
                    ctx,
                    title="Emoji Creation Failed",
                    description=f"An HTTP error ocurred while fetching the image: {res.status} {res.reason}",
                    log=True,
                    level="error",
                    ephemeral=True,
                )

    @emoji.command(name="delete")
    @discord.option("name", description="The name of the emoji to delete.")
    async def emoji_delete(
        self,
        ctx: Context,
        name: str,
        reason: Option(
            str,
            description="The reason for deleting this emoji",
            default="No reason provided",
        ),
    ) -> None:
        """Delete a custom emoji from this guild."""
        await ctx.assert_permissions(manage_emojis=True)
        for emoji in ctx.guild.emojis:
            if emoji.name == name:
                await emoji.delete(reason=reason)

                await present_embed(
                    ctx,
                    title="Emoji Deleted",
                    description=f"`:{name}:` deleted",
                    fields=[("Reason", reason)] if reason else [],
                    log=True,
                    level="success",
                    ephemeral=True,
                )
                return

        await present_embed(
            ctx,
            title="Emoji Not Found",
            description=f"Could not find a custom emoji name `:{name}:`",
            level="error",
            ephemeral=True,
        )

    ##################################################


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Admin(bot))
