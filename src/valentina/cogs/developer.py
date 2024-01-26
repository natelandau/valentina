# mypy: disable-error-code="valid-type"
"""Commands for bot development."""

from datetime import datetime
from pathlib import Path

import aiofiles
import discord
import inflect
import semver
from beanie import DeleteRules
from discord.commands import Option
from discord.ext import commands

from valentina.characters import RNGCharGen
from valentina.constants import PREF_MAX_EMBED_CHARACTERS, EmbedColor, LogLevel
from valentina.models import AWSService, Character, GlobalProperty, Guild, RollProbability, User
from valentina.models.bot import Valentina, ValentinaContext
from valentina.utils import instantiate_logger
from valentina.utils.autocomplete import (
    select_aws_object_from_guild,
    select_changelog_version_1,
    select_changelog_version_2,
    select_char_class,
)
from valentina.utils.changelog_parser import ChangelogParser
from valentina.utils.converters import ValidCharClass
from valentina.utils.helpers import get_config_value
from valentina.views import confirm_action, present_embed

p = inflect.engine()


class Developer(commands.Cog):
    """Valentina developer commands. Beware, these can be destructive."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot
        self.aws_svc = AWSService()

    ### BOT ADMINISTRATION COMMANDS ################################################################

    developer = discord.SlashCommandGroup(
        "developer",
        "Valentina developer commands. Beware, these can be destructive.",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    s3 = developer.create_subgroup(
        "aws",
        "Work with data stored in Amazon S3",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    database = developer.create_subgroup(
        "database",
        "Work with the database",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    guild = developer.create_subgroup(
        "guild",
        "Work with the current guild",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    server = developer.create_subgroup(
        "server",
        "Work with the bot globally",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    stats = developer.create_subgroup(
        "stats",
        "View bot statistics",
        default_member_permissions=discord.Permissions(administrator=True),
    )

    ### S3 COMMANDS ################################################################
    @s3.command(
        name="delete", description="Delete an image from the Amazon S3 bucket for the active guild"
    )
    @commands.is_owner()
    async def delete_from_s3_guild(
        self,
        ctx: ValentinaContext,
        key: discord.Option(
            str, "Name of file", required=True, autocomplete=select_aws_object_from_guild
        ),
    ) -> None:
        """Delete an image from the Amazon S3 bucket for the active guild.

        This function fetches the URL of the image to be deleted, confirms the action with the user,
        deletes the object from S3, and then sends a message to the audit log.

        Args:
            ctx (ApplicationContext): The application context.
            key (str): The key of the file to be deleted from S3.

        Returns:
            None
        """
        # Fetch the URL of the image to be deleted
        url = self.aws_svc.get_url(key)

        # Confirm the deletion action
        title = f"Delete `{key}` from S3"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, image=url, thumbnail=self.bot.user.display_avatar.url
        )

        if not is_confirmed:
            return

        # Delete the object from S3
        # TODO: Search for the url in character data and delete it there too so we don't have dead links
        self.aws_svc.delete_object(key)

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    ### GUILD COMMANDS ################################################################

    @guild.command()
    @commands.guild_only()
    @commands.is_owner()
    async def create_test_characters(
        self,
        ctx: ValentinaContext,
        number: Option(
            int, description="The number of characters to create (default 1)", default=1
        ),
        character_class: Option(
            ValidCharClass,
            name="char_class",
            description="The character's class",
            autocomplete=select_char_class,
            required=False,
            default=None,
        ),
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Create test characters in the database for the current guild."""
        title = (
            f"Create `{number}` of test {p.plural_noun('character', number)} on `{ctx.guild.name}`"
        )
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden
        )
        if not is_confirmed:
            return

        user = await User.get(ctx.author.id)

        chargen = RNGCharGen(ctx, user)
        for _ in range(number):
            character = await chargen.generate_full_character(
                developer_character=True,
                player_character=True,
                char_class=character_class,
                nickname_is_class=True,
            )

            await present_embed(
                ctx,
                title="Test Character Created",
                fields=[
                    ("Name", character.name),
                    ("Owner", f"[{ctx.author.id}] {ctx.author.display_name}"),
                ],
                level="success",
                ephemeral=hidden,
            )

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @guild.command()
    @commands.is_owner()
    @commands.guild_only()
    async def delete_developer_characters(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete all developer characters from the database."""
        dev_characters = await Character.find(
            Character.type_developer == True,  # noqa: E712
            fetch_links=True,
        ).to_list()

        title = f"Delete `{len(dev_characters)}` developer {p.plural_noun('character', len(dev_characters))} characters from `{ctx.guild.name}`"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden
        )
        if not is_confirmed:
            return

        for c in dev_characters:
            ctx.log_command(f"Delete dev character {c.name}")
            await c.delete(link_rule=DeleteRules.DELETE_LINKS)

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @guild.command(description="Repost the changelog (run in #changelog)")
    @commands.is_owner()
    @commands.guild_only()
    async def repost_changelog(
        self,
        ctx: ValentinaContext,
        oldest_version: Option(str, autocomplete=select_changelog_version_1, required=True),
        newest_version: Option(str, autocomplete=select_changelog_version_2, required=True),
    ) -> None:
        """Post the changelog."""
        if semver.compare(oldest_version, newest_version) > 0:
            msg = (
                f"Oldest version `{oldest_version}` is newer than newest version `{newest_version}`"
            )
            raise commands.BadArgument(msg)

        guild = await Guild.get(ctx.guild.id)
        changelog_channel = guild.fetch_changelog_channel(ctx.guild)
        if not changelog_channel:
            await ctx.respond(
                embed=discord.Embed(
                    title="Can not post changelog",
                    description="No changelog channel set",
                    color=EmbedColor.ERROR.value,
                )
            )
            return

        # Grab the changelog
        changelog = ChangelogParser(
            self.bot,
            oldest_version,
            newest_version,
            exclude_categories=[
                "docs",
                "refactor",
                "style",
                "test",
                "chore",
                "perf",
                "ci",
                "build",
            ],
        )
        if not changelog.has_updates():
            await ctx.respond(
                embed=discord.Embed(
                    title="Can not post changelog",
                    description="No updates found which pass the exclude list",
                    color=EmbedColor.ERROR.value,
                )
            )
            return

        # Update the last posted version in guild settings
        guild.changelog_posted_version = newest_version
        await guild.save()

        # Post the changelog
        embed = changelog.get_embed_personality()
        await changelog_channel.send(embed=embed)

        await ctx.respond(
            embed=discord.Embed(
                description=f"Changelog reposted and `guild.changelog_posted_version` updated to `{newest_version}`",
                color=EmbedColor.SUCCESS.value,
            ),
            ephemeral=True,
        )

    ### BOT COMMANDS ################################################################

    @server.command(
        name="clear_probability_cache", description="Clear probability data from the database"
    )
    @commands.is_owner()
    async def clear_probability_cache(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Clear probability data from the database."""
        results = await RollProbability.find_all().to_list()

        title = f"Clear `{len(results)}` probability {p.plural_noun('statistic', len(results))} from the database"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden
        )
        if not is_confirmed:
            return

        for result in results:
            await result.delete()

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @server.command(name="reload", description="Reload all cogs")
    @commands.is_owner()
    async def reload(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the confirmation only visible to you (default True)",
            default=True,
        ),
    ) -> None:
        """Reloads all cogs."""
        title = "Reload all cogs"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden
        )
        if not is_confirmed:
            return

        count = 0
        for cog in Path(self.bot.parent_dir / "src" / "valentina" / "cogs").glob("*.py"):
            if cog.stem[0] != "_":
                count += 1
                self.bot.reload_extension(f"valentina.cogs.{cog.stem}")

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @server.command(name="shutdown", description="Shutdown the bot")
    @commands.is_owner()
    async def shutdown(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the shutdown notification only visible to you (default False)",
            default=False,
        ),
    ) -> None:
        """Shutdown the bot."""
        title = "Shutdown the bot and end all active sessions"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden, footer="This is a destructive action that can not be undone."
        )
        if not is_confirmed:
            return

        await interaction.edit_original_response(embed=confirmation_embed, view=None)
        ctx.log_command("Shutdown the bot", LogLevel.WARNING)

        await self.bot.close()

    @server.command(name="send_log", description="Send the bot's logs")
    @commands.is_owner()
    async def debug_send_log(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Send the bot's logs to the user."""
        ctx.log_command("Send the bot's logs", LogLevel.DEBUG)
        log_file = get_config_value("VALENTINA_LOG_FILE")
        file = discord.File(log_file)
        await ctx.respond(file=file, ephemeral=hidden)

    @server.command(name="tail_logs", description="View last lines of the Valentina's logs")
    @commands.is_owner()
    async def debug_tail_logs(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the logs only visible to you (default True)",
            default=True,
        ),
    ) -> None:
        """Tail the bot's logs."""
        ctx.log_command("Tail the bot's logs", LogLevel.DEBUG)
        max_lines_from_bottom = 20
        log_lines = []

        logfile = get_config_value("VALENTINA_LOG_FILE")
        async with aiofiles.open(logfile, mode="r") as f:
            async for line in f:
                if "has connected to Gateway" not in line:
                    log_lines.append(line)
                    if len(log_lines) > max_lines_from_bottom:
                        log_lines.pop(0)

        response = "".join(log_lines)
        await ctx.respond("```" + response[-PREF_MAX_EMBED_CHARACTERS:] + "```", ephemeral=hidden)

    ### STATS COMMANDS ################################################################

    @developer.command(name="status", description="View bot status information")
    @commands.is_owner()
    async def status(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the server status only visible to you (default True)",
            default=True,
        ),
    ) -> None:
        """Show server status information."""
        delta_uptime = datetime.utcnow() - self.bot.start_time
        hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        db_properties = await GlobalProperty.find_one()

        embed = discord.Embed(title="Bot Status", color=EmbedColor.INFO.value)
        embed.set_thumbnail(url=self.bot.user.display_avatar)

        embed.add_field(name="\u200b", value="**SERVER INFO**", inline=False)
        embed.add_field(name="Status", value=str(self.bot.status))
        embed.add_field(name="Uptime", value=f"`{days}d, {hours}h, {minutes}m, {seconds}s`")
        embed.add_field(name="Latency", value=f"`{self.bot.latency!s}`")
        embed.add_field(name="Connected Guilds", value=str(len(self.bot.guilds)))
        embed.add_field(name="Bot Version", value=f"`{self.bot.version}`")
        embed.add_field(name="Pycord Version", value=f"`{discord.__version__}`")
        embed.add_field(name="Database Version", value=f"`{db_properties.most_recent_version}`")

        servers = list(self.bot.guilds)
        embed.add_field(
            name="\u200b",
            value=f"**CONNECT TO {len(servers)} {p.plural_noun('GUILD', len(servers))}**",
            inline=False,
        )
        for n, guild in enumerate(servers):
            player_characters = await Character.find(
                Character.guild == guild.id,
                Character.type_player == True,  # noqa: E712
            ).count()
            storyteller_characters = await Character.find(
                Character.guild == guild.id,
                Character.type_storyteller == True,  # noqa: E712
            ).count()
            value = (
                "```yaml\n",
                f"members            : {guild.member_count}\n",
                f"owner              : {guild.owner.display_name}\n",
                f"player chars       : {player_characters}\n",
                f"storyteller chars  : {storyteller_characters}\n",
                "```",
            )

            embed.add_field(
                name=f"{n + 1}. {guild.name}",
                value="".join(value),
                inline=True,
            )

        await ctx.respond(embed=embed, ephemeral=hidden)

    ### LOGGING COMMANDS ################################################################

    @developer.command(name="logging", description="Change log level")
    @commands.is_owner()
    async def logging(
        self,
        ctx: ValentinaContext,
        log_level: Option(LogLevel),
        hidden: Option(
            bool,
            description="Make the confirmation only visible to you (default True)",
            default=True,
        ),
    ) -> None:
        """Change log level."""
        title = f"Set log level to: `{log_level.value}`"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden
        )
        if not is_confirmed:
            return

        instantiate_logger(log_level)
        await interaction.edit_original_response(embed=confirmation_embed, view=None)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Developer(bot))
