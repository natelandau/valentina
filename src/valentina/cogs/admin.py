# mypy: disable-error-code="valid-type"
"""Administration commands for Valentina."""
from datetime import datetime
from io import BytesIO
from pathlib import Path

import aiofiles
import discord
from discord.commands import Option
from discord.ext import commands
from discord.ext.commands import MemberConverter
from loguru import logger

from valentina import (
    CONFIG,
    Valentina,
    __version__,
    char_svc,
    chron_svc,
    db_svc,
    guild_svc,
    user_svc,
)
from valentina.models.constants import MAX_CHARACTER_COUNT
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

    @admin.command(description="Toggle audit log on/off")
    async def audit_log(
        self,
        ctx: discord.ApplicationContext,
        channel_name: Option(
            ValidChannelName, "Audit log channel name", required=False, default=None
        ),
    ) -> None:
        """Toggle audit log on/off."""
        setting = guild_svc.is_audit_logging(ctx)
        if setting:
            fields = [
                ("Current audit log status", "Enabled"),
                ("\u200b", "**Disable logging to audit channel?**"),
            ]
        else:
            fields = [
                ("Current audit log status", "Disabled"),
                ("\u200b", "**Enable logging to audit channel?**"),
            ]

        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title="Manage Audit Log Settings",
            level="info",
            ephemeral=True,
            fields=fields,
            view=view,
        )
        await view.wait()

        if not view.confirmed:
            await msg.edit_original_response(
                embed=discord.Embed(title="Setting change cancelled", color=discord.Color.red())
            )
            return

        if setting:
            await guild_svc.send_log(ctx, "Audit logging disabled")
            guild_svc.set_audit_log(ctx, False)
            return

        if not guild_svc.fetch_log_channel(ctx) and not channel_name:
            await present_embed(
                ctx,
                title="No audit log channel",
                description="Please rerun the command and enter a channel name",
                level="error",
                ephemeral=True,
            )
            return

        if not guild_svc.fetch_log_channel(ctx) and channel_name:
            await guild_svc.create_bot_log_channel(ctx.guild, channel_name)
            guild_svc.set_audit_log(ctx, True)
            message = f"Logging to channel **{channel_name}**"
        else:
            guild_svc.set_audit_log(ctx, True)
            message = "Logging to audit channel enabled"

        await present_embed(ctx, title=message, level="success", ephemeral=True, log=True)

    @admin.command(description="View bot status")
    async def status(self, ctx: discord.ApplicationContext) -> None:
        """Show server status information."""
        logger.debug("ADMIN: Show server status information")

        delta_uptime = datetime.utcnow() - self.bot.start_time
        hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        creation = ((ctx.guild.id >> 22) + 1420070400000) // 1000

        await present_embed(
            ctx,
            title="Connection Information",
            description="",
            fields=[
                ("Status", str(self.bot.status)),
                ("Uptime", f"`{days}d, {hours}h, {minutes}m, {seconds}s`"),
                ("Latency", f"`{self.bot.latency!s}`"),
                ("Connected Guilds", str(len(self.bot.guilds))),
                ("Bot Version", f"`{__version__}`"),
                ("Pycord Version", f"`{discord.__version__}`"),
                ("Database Version", f"`{db_svc.database_version()}`"),
                ("Server Creation", f"<t:{creation}>\n<t:{creation}:R>"),
                (
                    "Server Roles",
                    f"`{len(ctx.guild._roles)}` roles\nHighest:\n{ctx.guild.roles[-1].mention}",
                ),
                (
                    "Server Members",
                    f"Total: `{ctx.guild.member_count}`\nBots: `{sum(m.bot for m in ctx.guild.members)}`",
                ),
            ],
            inline_fields=True,
            level="info",
            ephemeral=True,
        )

    @admin.command(description="Live reload Valentina")
    async def reload(self, ctx: discord.ApplicationContext) -> None:
        """Reloads all cogs."""
        logger.debug("Admin: Reload the bot")
        count = 0
        for cog in Path(self.bot.parent_dir / "src" / "valentina" / "cogs").glob("*.py"):
            if cog.stem[0] != "_":
                count += 1
                logger.info(f"COGS: Reloading - {cog.stem}")
                self.bot.reload_extension(f"valentina.cogs.{cog.stem}")

        await present_embed(
            ctx, "Reload Bot", f"{count} cogs successfully reloaded", level="info", ephemeral=True
        )

    @admin.command(description="View last lines of the Valentina's logs")
    async def tail_logs(self, ctx: discord.ApplicationContext) -> None:
        """Tail the bot's logs."""
        logger.debug("ADMIN: Tail bot logs")
        max_lines_from_bottom = 20
        log_lines = []

        async with aiofiles.open(CONFIG["VALENTINA_LOG_FILE"], mode="r") as f:
            async for line in f:
                if "has connected to Gateway" not in line:
                    log_lines.append(line)
                    if len(log_lines) > max_lines_from_bottom:
                        log_lines.pop(0)

        response = "".join(log_lines)
        await ctx.respond("```" + response[-MAX_CHARACTER_COUNT:] + "```", ephemeral=True)

    @admin.command(description="Purge the bot's cache and reload data from DB")
    @logger.catch
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
            guild_svc.purge_cache(ctx)
            user_svc.purge_cache(ctx)
            char_svc.purge_cache(ctx, with_claims=True)
            chron_svc.purge_cache(ctx)
            logger.info(f"ADMIN: Purge cache for {ctx.guild.name}")

        if all_guilds:
            guild_svc.purge_cache()
            user_svc.purge_cache()
            char_svc.purge_cache(with_claims=True)
            chron_svc.purge_cache()
            logger.info("ADMIN: Purge cache for all guilds")

        await msg.delete_original_response()
        await present_embed(
            ctx,
            title="All caches purged" if all_guilds else "Guild caches purged",
            level="success",
            ephemeral=True,
            log=True,
        )

    @admin.command(description="Shutdown Valentina")
    @commands.is_owner()
    async def shutdown(self, ctx: discord.ApplicationContext) -> None:
        """Shutdown the bot."""
        logger.warning(f"ADMIN: {ctx.author.display_name} has shut down the bot")
        await present_embed(
            ctx, title="Shutting down Valentina...", level="warning", ephemeral=True, log=True
        )
        await self.bot.close()

    @admin.command(description="Create DB Backup")
    @commands.is_owner()
    async def db_backup(self, ctx: discord.ApplicationContext) -> None:
        """Create a backup of the database."""
        logger.info("ADMIN: Manually create database backup")
        await db_svc.backup_database(CONFIG)
        await present_embed(
            ctx, title="Database backup created", level="success", ephemeral=True, log=True
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

        for member in converted_members:
            await ctx.guild.ban(member, reason=f"{ctx.author} ({ctx.author.id}): {reason}")

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
