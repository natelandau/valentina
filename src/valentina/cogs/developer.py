# mypy: disable-error-code="valid-type"
"""Commands for bot development."""
from datetime import datetime
from pathlib import Path
from random import randrange

import aiofiles
import discord
import inflect
import semver
from discord.commands import Option
from discord.ext import commands
from loguru import logger
from peewee import fn

from valentina.constants import MAX_CHARACTER_COUNT, EmbedColor
from valentina.models.bot import Valentina
from valentina.models.db_tables import Character, CharacterClass, RollProbability, User, VampireClan
from valentina.utils.changelog_parser import ChangelogParser
from valentina.utils.converters import ValidCharacterClass
from valentina.utils.helpers import fetch_random_name
from valentina.utils.options import (
    select_aws_object_from_guild,
    select_changelog_version_1,
    select_changelog_version_2,
    select_char_class,
)
from valentina.views import confirm_action, present_embed

p = inflect.engine()


class Developer(commands.Cog):
    """Valentina developer commands. Beware, these can be destructive."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

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
        ctx: discord.ApplicationContext,
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
        url = self.bot.aws_svc.get_url(key)

        # Confirm the deletion action
        title = f"Delete `{key}` from S3"
        is_confirmed, confirmation_response_msg = await confirm_action(
            ctx, title, image=url, thumbnail=self.bot.user.display_avatar.url
        )
        if not is_confirmed:
            return

        # Delete the object from S3
        self.bot.aws_svc.delete_object(key)
        logger.info(f"Deleted object with key: {key} from S3")

        await confirmation_response_msg

    ### DATABASE COMMANDS ################################################################
    @database.command(name="backup", description="Create a backup of the database")
    @commands.is_owner()
    async def backup_db(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Create a backup of the database."""
        title = "Create backup of the database"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        db_file = await self.bot.db_svc.backup_database(self.bot.config)
        logger.info(f"ADMIN: Database backup created: {db_file}")
        await confirmation_response_msg

    ### GUILD COMMANDS ################################################################

    @guild.command(name="character_xp_to_user", description="Transfer all character XP to users")
    @commands.guild_only()
    @commands.is_owner()
    async def character_xp_to_user(self, ctx: discord.ApplicationContext) -> None:
        """Transfer all character XP to users."""
        title = "Transfer all character XP to users"
        is_confirmed, confirmation_response_msg = await confirm_action(
            ctx, title, description="This can not be undone"
        )
        if not is_confirmed:
            return

        users = self.bot.user_svc.fetch_guild_users(ctx)
        for user in users:
            description = ""
            user_experience = User.get_by_id(user.id).data[str(ctx.guild.id)].get("experience", 0)
            user_lifetime_experience = (
                User.get_by_id(user.id).data[str(ctx.guild.id)].get("experience_total", 0)
            )
            description += f"start experience: {user_experience}\n"
            description += f"start lifetime experience: {user_lifetime_experience}\n"

            for c in self.bot.char_svc.fetch_all_player_characters(ctx, owned_by=user):
                description += f"{c.name}: {c.data['experience']} experience\n"
                user_experience += c.data["experience"]
                user_lifetime_experience += c.data["experience_total"]
                self.bot.char_svc.update_or_add(
                    ctx,
                    character=c,
                    data={
                        "experience": 0,
                        "experience_total": 0,
                    },
                )

            # Update the user's experience
            self.bot.user_svc.update_or_add_user(
                ctx,
                user,
                data={
                    str(ctx.guild.id): {
                        "experience": user_experience,
                        "experience_total": user_lifetime_experience,
                    }
                },
            )
            description += f"end experience: {User.get_by_id(user.id).data[str(ctx.guild.id)].get('experience', 0)}\n end lifetime experience: {User.get_by_id(user.id).data[str(ctx.guild.id)].get('experience_total', 0)}\n"
            await ctx.send(embed=discord.Embed(description=description))

        logger.info(f"DEVELOPER: {ctx.author.display_name} transferring all character XP to users")
        await confirmation_response_msg

    @guild.command()
    @commands.guild_only()
    @commands.is_owner()
    async def create_test_characters(
        self,
        ctx: discord.ApplicationContext,
        number: Option(
            int, description="The number of characters to create (default 1)", default=1
        ),
        char_class: Option(
            ValidCharacterClass,
            name="char_class",
            description="The character's class",
            autocomplete=select_char_class,
            required=False,
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
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        self.bot.user_svc.update_or_add_user(ctx)  # Instantiate the user in the database if needed

        for _ in range(number):
            # Assign a random class unless specified
            if char_class is None:
                char_class = CharacterClass.select().order_by(fn.Random()).limit(1).get()

            # Assign a random vampire clan
            if char_class.name.lower() == "vampire":
                vampire_clan = VampireClan.select().order_by(fn.Random()).limit(1).get()
            else:
                vampire_clan = None

            first_name, last_name = await fetch_random_name()

            # Create the character
            data: dict[str, str | int | bool] = {
                "first_name": first_name,
                "last_name": last_name,
                "nickname": char_class.name,
                "developer_character": True,
                "player_character": True,
            }

            character = self.bot.char_svc.update_or_add(
                ctx,
                char_class=char_class,
                clan=vampire_clan,
                data=data,
            )

            # Fetch all traits and set them
            fetched_traits = self.bot.trait_svc.fetch_all_class_traits(char_class.name)

            for trait in fetched_traits:
                character.set_trait_value(trait, randrange(0, 5))

            await present_embed(
                ctx,
                title="Test Character Created",
                fields=[
                    ("Name", character.name),
                    ("Owner", f"[{ctx.user.id}] {ctx.user.display_name}"),
                ],
                level="success",
                ephemeral=hidden,
            )

        await confirmation_response_msg

    @guild.command()
    @commands.is_owner()
    @commands.guild_only()
    async def delete_developer_characters(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete all developer characters from the database."""
        dev_characters = Character.select().where(
            (Character.data["developer_character"] == True)  # noqa: E712
            & (Character.guild == ctx.guild.id)
        )

        title = f"Delete `{len(dev_characters)}` developer {p.plural_noun('character', len(dev_characters))} characters from `{ctx.guild.name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        for c in dev_characters:
            logger.debug(f"DEVELOPER: Deleting {c}")
            c.delete_instance(recursive=True, delete_nullable=True)

        await confirmation_response_msg

    @guild.command(description="Repost the changelog (run in #changelog)")
    @commands.is_owner()
    @commands.guild_only()
    async def repost_changelog(
        self,
        ctx: discord.ApplicationContext,
        oldest_version: Option(str, autocomplete=select_changelog_version_1, required=True),
        newest_version: Option(str, autocomplete=select_changelog_version_2, required=True),
    ) -> None:
        """Post the changelog."""
        if semver.compare(oldest_version, newest_version) > 0:
            raise commands.BadArgument(
                f"Oldest version `{oldest_version}` is newer than newest version `{newest_version}`"
            )

        changelog_channel = self.bot.guild_svc.fetch_changelog_channel(ctx.guild)
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
        updates = {"changelog_posted_version": newest_version}
        self.bot.guild_svc.update_or_add(guild=ctx.guild, updates=updates)

        # Post the changelog
        embed = changelog.get_embed_personality()
        await changelog_channel.send(embed=embed)

        await ctx.respond(
            embed=discord.Embed(
                description=f"Changelog reposted and settings`[changelog_posted_version]` updated to `{newest_version}`",
                color=EmbedColor.SUCCESS.value,
            ),
            ephemeral=True,
        )

    @guild.command(name="purge_cache", description="Purge this guild's cache")
    @commands.guild_only()
    @commands.is_owner()
    async def purge_guild_cache(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Purge the bot's cache and reload all data from the database."""
        title = "Purge the database caches for `{ctx.guild.name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        logger.info(f"DEVELOPER: Purge all caches for {ctx.guild.name}")
        services = {
            "guild_svc": self.bot.guild_svc,
            "user_svc": self.bot.user_svc,
            "char_svc": self.bot.char_svc,
            "campaign_svc": self.bot.campaign_svc,
            "macro_svc": self.bot.macro_svc,
            "trait_svc": self.bot.trait_svc,
        }

        for service_name, service in services.items():
            if hasattr(service, "purge_cache"):
                service.purge_cache(ctx=ctx)
            else:
                logger.warning(f"SERVER: {service_name} does not have a `purge_cache` method")

        await confirmation_response_msg

    ### BOT COMMANDS ################################################################

    @server.command(
        name="clear_probability_cache", description="Clear probability data from the database"
    )
    @commands.is_owner()
    async def clear_probability_cache(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Clear probability data from the database."""
        cached_results = RollProbability.select()

        title = f"Clear `{len(cached_results)}` probability {p.plural_noun('statistic', len(cached_results))} from the database"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        for result in cached_results:
            result.delete_instance()

        logger.info(f"DEVELOPER: {ctx.author.display_name} cleared probability data from the db")
        await confirmation_response_msg

    @server.command(name="reload", description="Reload all cogs")
    @commands.is_owner()
    async def reload(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the confirmation only visible to you (default True)",
            default=True,
        ),
    ) -> None:
        """Reloads all cogs."""
        title = "Reload all cogs"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        count = 0
        for cog in Path(self.bot.parent_dir / "src" / "valentina" / "cogs").glob("*.py"):
            if cog.stem[0] != "_":
                count += 1
                logger.info(f"COGS: Reloading - {cog.stem}")
                self.bot.reload_extension(f"valentina.cogs.{cog.stem}")

        logger.debug("Admin: Reload the bot's cogs")
        await confirmation_response_msg

    @server.command(name="shutdown", description="Shutdown the bot")
    @commands.is_owner()
    async def shutdown(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the shutdown notification only visible to you (default False)",
            default=False,
        ),
    ) -> None:
        """Shutdown the bot."""
        title = "Shutdown the bot and end all active sessions"
        is_confirmed, confirmation_response_msg = await confirm_action(
            ctx, title, hidden=hidden, footer="This is a destructive action that can not be undone."
        )
        if not is_confirmed:
            return

        await confirmation_response_msg
        logger.warning(f"DEVELOPER: {ctx.author.display_name} has shut down the bot")

        await self.bot.close()

    @server.command(name="purge_cache", description="Purge all the bot's caches")
    @commands.guild_only()
    @commands.is_owner()
    async def purge_all_caches(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Purge the bot's cache and reload all data from the database."""
        title = "Purge all database caches across all guilds"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)
        if not is_confirmed:
            return

        services = {
            "guild_svc": self.bot.guild_svc,
            "user_svc": self.bot.user_svc,
            "char_svc": self.bot.char_svc,
            "campaign_svc": self.bot.campaign_svc,
            "macro_svc": self.bot.macro_svc,
            "trait_svc": self.bot.trait_svc,
        }
        logger.info("DEVELOPER: Purge all caches for all guilds")
        for service_name, service in services.items():
            if hasattr(service, "purge_cache"):
                service.purge_cache()
            else:
                logger.warning(f"SERVER: {service_name} does not have a `purge_cache` method")

        await confirmation_response_msg

    @server.command(name="send_log", description="Send the bot's logs")
    @commands.is_owner()
    async def debug_send_log(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Send the bot's logs to the user."""
        file = discord.File(self.bot.config["VALENTINA_LOG_FILE"])
        await ctx.respond(file=file, ephemeral=hidden)

    @server.command(name="tail_logs", description="View last lines of the Valentina's logs")
    @commands.is_owner()
    async def debug_tail_logs(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the logs only visible to you (default True)",
            default=True,
        ),
    ) -> None:
        """Tail the bot's logs."""
        logger.debug("ADMIN: Tail bot logs")
        max_lines_from_bottom = 20
        log_lines = []

        async with aiofiles.open(self.bot.config["VALENTINA_LOG_FILE"], mode="r") as f:
            async for line in f:
                if "has connected to Gateway" not in line:
                    log_lines.append(line)
                    if len(log_lines) > max_lines_from_bottom:
                        log_lines.pop(0)

        response = "".join(log_lines)
        await ctx.respond("```" + response[-MAX_CHARACTER_COUNT:] + "```", ephemeral=hidden)

    ### STATS COMMANDS ################################################################

    @developer.command(name="status", description="View bot status information")
    @commands.is_owner()
    async def status(
        self,
        ctx: discord.ApplicationContext,
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

        embed = discord.Embed(title="Bot Status", color=EmbedColor.INFO.value)
        embed.set_thumbnail(url=self.bot.user.display_avatar)

        embed.add_field(name="\u200b", value="**SERVER INFO**", inline=False)
        embed.add_field(name="Status", value=str(self.bot.status))
        embed.add_field(name="Uptime", value=f"`{days}d, {hours}h, {minutes}m, {seconds}s`")
        embed.add_field(name="Latency", value=f"`{self.bot.latency!s}`")
        embed.add_field(name="Connected Guilds", value=str(len(self.bot.guilds)))
        embed.add_field(name="Bot Version", value=f"`{self.bot.version}`")
        embed.add_field(name="Pycord Version", value=f"`{discord.__version__}`")
        embed.add_field(
            name="Database Version", value=f"`{self.bot.db_svc.fetch_current_version()}`"
        )

        servers = list(self.bot.guilds)
        embed.add_field(
            name="\u200b",
            value=f"**CONNECT TO {len(servers)} {p.plural_noun('GUILD', len(servers))}**",
            inline=False,
        )
        for n, guild in enumerate(servers):
            player_characters = (
                Character.select()
                .where(
                    Character.guild == guild.id,
                    Character.data["player_character"] == True,  # noqa: E712
                )
                .count()
            )
            value = (
                "```yaml\n",
                f"members: {guild.member_count}\n",
                f"owner  : {guild.owner.display_name}\n",
                f"chars  : {player_characters}\n",
                "```",
            )

            embed.add_field(
                name=f"{n + 1}. {guild.name}",
                value="".join(value),
                inline=True,
            )

        await ctx.respond(embed=embed, ephemeral=hidden)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Developer(bot))
