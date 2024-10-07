# mypy: disable-error-code="valid-type"
"""Commands for bot development."""

import random
from datetime import UTC, datetime

import aiofiles
import discord
import inflect
from beanie import DeleteRules
from discord.commands import Option
from discord.ext import commands
from faker import Faker
from loguru import logger

from valentina.constants import (
    COGS_PATH,
    PREF_MAX_EMBED_CHARACTERS,
    CharClass,
    EmbedColor,
    InventoryItemType,
    LogLevel,
)
from valentina.discord.bot import Valentina, ValentinaContext
from valentina.discord.characters import RNGCharGen
from valentina.discord.models import ChannelManager
from valentina.discord.utils.autocomplete import (
    select_aws_object_from_guild,
    select_changelog_version_1,
    select_changelog_version_2,
    select_char_class,
)
from valentina.discord.utils.converters import ValidCharClass
from valentina.discord.views import confirm_action, present_embed
from valentina.models import (
    AWSService,
    Campaign,
    CampaignBook,
    CampaignBookChapter,
    ChangelogPoster,
    Character,
    CharacterSheetSection,
    GlobalProperty,
    Guild,
    InventoryItem,
    RollProbability,
    User,
    WebDiscordSync,
)
from valentina.utils import ValentinaConfig, instantiate_logger

p = inflect.engine()


class Developer(commands.Cog):
    """Valentina developer commands. Beware, these can be destructive."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot
        self.aws_svc = AWSService()

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
    maintenance = developer.create_subgroup(
        "maintenance",
        "maintenance commands",
        default_member_permissions=discord.Permissions(administrator=True),
    )

    ## MAINTENANCE COMMANDS ################################################################
    @maintenance.command(
        name="clear_sync_cache", description="Clear processed web/discord sync data from the DB"
    )
    @commands.is_owner()
    async def clear_sync_cache(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the interaction only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """Clears processed web/discord sync data from the database."""
        processed_syncs = await WebDiscordSync.find(WebDiscordSync.processed == True).to_list()  # noqa: E712

        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx,
            title=f"Delete {len(processed_syncs)} processed syncs from the database",
            hidden=hidden,
            audit=False,
        )

        if not is_confirmed:
            return

        for sync in processed_syncs:
            await sync.delete()

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

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
            ctx (ValentinaContext): The application context.
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
    @commands.is_owner()
    async def create_dummy_data(self, ctx: ValentinaContext) -> None:  # noqa: C901
        """Create dummy data in the database for the current guild."""
        title = f"Create dummy data on `{ctx.guild.name}`"
        is_confirmed, interaction, confirmation_embed = await confirm_action(ctx, title)
        if not is_confirmed:
            return

        # Campaigns
        created_campaigns = []
        for _ in range(2):
            campaign = await Campaign(
                name=Faker().sentence(nb_words=3).rstrip("."),
                description=Faker().paragraph(nb_sentences=3),
                guild=ctx.guild.id,
            ).insert()

            created_campaigns.append(campaign)

        # Campaign Books
        created_books = []
        for campaign in created_campaigns:
            for n in range(2):
                book = await CampaignBook(
                    name=Faker().sentence(nb_words=3).rstrip("."),
                    campaign=str(campaign.id),
                    number=n + 1,
                    description_short=Faker().paragraph(nb_sentences=3),
                    description_long=Faker().paragraph(nb_sentences=8),
                ).insert()

                campaign.books.append(book)
                await campaign.save()
                created_books.append(book)

        # Campaign Book Chapters
        for book in created_books:
            for n in range(2):
                chapter = await CampaignBookChapter(
                    name=Faker().sentence(nb_words=3).rstrip("."),
                    book=str(book.id),
                    number=n + 1,
                    description_short=Faker().paragraph(nb_sentences=3),
                    description_long=Faker().paragraph(nb_sentences=8),
                ).insert()

                book.chapters.append(chapter)
                await book.save()

        # Characters
        user = await User.get(ctx.author.id)
        chargen = RNGCharGen(ctx, user)
        created_characters = []
        for _ in range(3):
            character = await chargen.generate_full_character(
                developer_character=True,
                player_character=True,
                char_class=random.choice(CharClass.playable_classes()),
                nickname_is_class=True,
            )
            created_characters.append(character)

        # Add inventory & custom sections to characters and associate characters with campaigns
        for character in created_characters:
            for _ in range(3):
                i = InventoryItem(
                    name=Faker().sentence(nb_words=2).rstrip("."),
                    description=Faker().sentence(),
                    character=str(character.id),
                    type=random.choice([x.name for x in InventoryItemType]),
                )
                item = await i.insert()
                character.inventory.append(item)

                section = CharacterSheetSection(
                    title=Faker().sentence(nb_words=3).rstrip("."),
                    content=Faker().paragraph(nb_sentences=3),
                )
                character.sheet_sections.append(section)

            # Add the character to the user's list of characters
            user.characters.append(character)
            await user.save()

            # Associate the character with a campaign
            campaign = random.choice(created_campaigns)
            character.campaign = str(campaign.id)
            await character.save()

        # Create discord channels and add campaigns to the guild
        guild = await Guild.get(ctx.guild.id, fetch_links=True)

        channel_manager = ChannelManager(guild=ctx.guild, user=ctx.author)
        for campaign in created_campaigns:
            await channel_manager.confirm_campaign_channels(campaign)
            guild.campaigns.append(campaign)

        await guild.save()

        logger.info(f"DATABASE: Dummy data created on {ctx.guild.name}")
        await interaction.edit_original_response(embed=confirmation_embed, view=None)

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
        changelog = ChangelogPoster(
            bot=self.bot,
            ctx=ctx,
            oldest_version=oldest_version,
            newest_version=newest_version,
        )

        await changelog.post()

        # Update the last posted version in guild settings
        if changelog.posted:
            # Update the last posted version in guild settings
            guild = await Guild.get(ctx.guild.id)
            guild.changelog_posted_version = newest_version
            await guild.save()

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
        for cog in COGS_PATH.glob("*.py"):
            if cog.stem[0] != "_":
                count += 1
                self.bot.reload_extension(f"valentina.discord.cogs.{cog.stem}")

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
        log_file = ValentinaConfig().log_file
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

        logfile = ValentinaConfig().log_file
        async with aiofiles.open(logfile) as f:
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
        delta_uptime = datetime.now(UTC) - self.bot.start_time
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
