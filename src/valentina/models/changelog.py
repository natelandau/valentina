"""Classes and functions to manage posting changelogs to Discord channels."""

import random
import re

import discord
import semver
from discord.ext import commands
from loguru import logger

from valentina.constants import (
    BOT_DESCRIPTIONS,
    CHANGELOG_EXCLUDE_CATEGORIES,
    CHANGELOG_PATH,
    EmbedColor,
)
from valentina.utils import errors

from .guild import Guild


class ChangelogPoster:
    """Helper class for posting changelogs to the changelog channel specified in guild settings."""

    def __init__(
        self,
        bot: commands.Bot | None = None,
        ctx: discord.ApplicationContext | None = None,
        channel: discord.TextChannel | None = None,
        exclud_cagegories: list[str] = CHANGELOG_EXCLUDE_CATEGORIES,
        oldest_version: str | None = None,
        newest_version: str | None = None,
        with_personality: bool = False,
    ):
        self.exclude_categories = exclud_cagegories
        self.bot = bot
        self.ctx = ctx
        self.channel = channel

        self.changelog = ChangelogParser(
            bot=self.bot if self.bot else self.ctx.bot,
            exclude_categories=self.exclude_categories,
            oldest_version=oldest_version,
            newest_version=newest_version,
        )

        self.oldest_version, self.newest_version = self._validate_versions(
            oldest_version, newest_version
        )

        self.with_personality = with_personality

        self.posted = False  # Flag to indicate if the changelog has been posted

    async def _get_channel_from_ctx(self) -> discord.TextChannel | None:
        """Get the changelog channel from the guild settings.

        Returns:
            discord.TextChannel | None: The changelog channel if it exists, None otherwise.
        """
        if self.ctx:
            guild = await Guild.get(self.ctx.guild.id)
            return guild.fetch_changelog_channel(self.ctx.guild)

        return None

    async def _validate_channel(self) -> bool:
        """Validate that the channel exists.

        Returns:
            bool: True if the channel exists, False otherwise.
        """
        if not self.channel:
            self.channel = await self._get_channel_from_ctx()

        if not self.channel and not self.ctx:
            logger.error("CHANGELOG: No changelog channel")
            return False

        if not self.channel and self.ctx:
            await self.ctx.respond(
                embed=discord.Embed(
                    title="Can not post changelog",
                    description="No changelog channel set",
                    color=EmbedColor.ERROR.value,
                ),
                ephemeral=True,
            )
            return False

        return True

    def _validate_versions(self, oldest_version: str, newest_version: str) -> tuple[str, str]:
        """Validate the input to the ChangelogPoster."""
        if oldest_version and newest_version and semver.compare(oldest_version, newest_version) > 0:
            msg = (
                f"Oldest version `{oldest_version}` is newer than newest version `{newest_version}`"
            )
            raise commands.BadArgument(msg)

        if (
            oldest_version not in self.changelog.list_of_versions()
            and newest_version not in self.changelog.list_of_versions()
        ):
            msg = f"Oldest version `{oldest_version}` not found in changelog"
            raise errors.VersionNotFoundError(msg)

        return oldest_version, newest_version

    def has_updates(self) -> bool:
        """Check if there are any meaningful updates in the changelog other than the date.

        Returns:
            bool: True if there are meaningful updates, False otherwise.
        """
        return self.changelog.has_updates()

    async def post(self) -> None:
        """Post the changelog to the specified channel."""
        if not await self._validate_channel():
            return

        if not self.has_updates() and not self.ctx:
            logger.info("CHANGELOG: No updates found")
            return

        if not self.has_updates() and self.ctx:
            await self.ctx.respond(
                embed=discord.Embed(
                    title="Can not post changelog",
                    description="No updates found",
                    color=EmbedColor.ERROR.value,
                ),
                ephemeral=True,
            )
            return

        embed = (
            self.changelog.get_embed()
            if not self.with_personality
            else self.changelog.get_embed_personality()
        )

        await self.channel.send(embed=embed)
        logger.info(f"Post changelog: {self.oldest_version} -> {self.newest_version}")
        self.posted = True


class ChangelogParser:
    """Helper class for parsing changelogs."""

    def __init__(
        self,
        bot: commands.Bot | discord.bot.Bot | None = None,
        oldest_version: str | None = None,
        newest_version: str | None = None,
        exclude_categories: list[str] = [],
    ):
        self.path = CHANGELOG_PATH
        self.bot = bot
        self.all_categories = [
            "feat",
            "fix",
            "docs",
            "refactor",
            "style",
            "test",
            "chore",
            "perf",
            "ci",
            "build",
        ]
        self.exclude_categories = exclude_categories
        self.oldest_version = (
            (oldest_version if self.__check_version_schema(oldest_version) else None)
            if oldest_version
            else "0.0.1"
        )
        self.newest_version = (
            (newest_version if self.__check_version_schema(newest_version) else None)
            if newest_version
            else "999.999.999"
        )
        self.full_changelog = self.__get_changelog()
        self.changelog_dict = self.__parse_changelog()
        # Clean changelog_dict of excluded categories and empty versions
        self.__clean_changelog()

    @staticmethod
    def __check_version_schema(version: str) -> bool:
        """Check if the version string is in the correct format."""
        return bool(re.match(r"^(\d+\.\d+\.\d+)$", version))

    def __get_changelog(self) -> str:
        """Get the changelog from the file."""
        if not self.path.exists():
            logger.error(f"Changelog file not found at {self.path}")
            raise FileNotFoundError

        return self.path.read_text()

    def __parse_changelog(self) -> dict[str, dict[str, str | list[str]]]:
        """Parse the changelog into a dictionary.

        Loop through each line in the changelog, identifying the version and category of each entry.
        Store these in a nested dictionary, keyed first by the version and then by the category.

        Returns:
            Dict[str, Dict[str, List[str]]]: A nested dictionary containing all changelog information.
        """
        # Prepare compiled regular expressions
        version_re = re.compile(r"## v(\d+\.\d+\.\d+)")
        date_re = re.compile(r"\((\d{4}-\d{2}-\d{2})\)")
        category_re = re.compile(rf"### ({'|'.join(self.all_categories)})", re.IGNORECASE)

        # Initialize the changelog dictionary
        changelog_dict: dict[str, dict[str, str | list[str]]] = {}
        current_category = ""

        # Parse changelog line by line
        for line in self.full_changelog.split("\n"):
            # Skip empty lines
            if not line:
                continue

            # Check for version line
            if version_match := version_re.match(line):
                version_being_parsed = version_match.group(1)

                if (
                    semver.Version.parse(version_being_parsed)
                    >= semver.Version.parse(self.oldest_version)
                ) and (
                    semver.Version.parse(version_being_parsed)
                    <= semver.Version.parse(self.newest_version)
                ):
                    changelog_dict[version_being_parsed] = {"date": date_re.search(line).group(1)}
                    parse_version = True
                    continue

                # Stop parsing if we are below the to_version
                if semver.Version.parse(version_being_parsed) < semver.Version.parse(
                    self.oldest_version
                ):
                    break

                # Do not parse if we are above the from_version
                if semver.Version.parse(version_being_parsed) > semver.Version.parse(
                    self.newest_version
                ):
                    parse_version = False
                    continue

            # Check for category line
            if category_match := category_re.match(line):
                current_category = category_match.group(1).lower()
                continue

            # If we are within a version and a category, append line to that category
            if parse_version and current_category:  # type: ignore [unreachable] # TODO
                cleaned_line = re.sub(r" \(#\d+\)$", "", line)  # Clean up PR references

                if current_category not in changelog_dict[version_being_parsed]:
                    changelog_dict[version_being_parsed][current_category] = [cleaned_line]
                else:
                    changelog_dict[version_being_parsed][current_category].append(cleaned_line)

        return changelog_dict

    def __clean_changelog(self) -> None:
        """Clean up the changelog dictionary by removing excluded categories and empty versions.

        This function modifies `self.changelog_dict` to remove any versions that have only one item
        (i.e., only a date and no other changes). It also removes categories that are in the exclusion list.

        Returns:
        None
        """
        # Remove excluded categories
        categories_to_remove: dict[str, list[str]] = {
            key: [category for category in value if category in self.exclude_categories]
            for key, value in self.changelog_dict.items()
        }

        for key, categories in categories_to_remove.items():
            for category in categories:
                self.changelog_dict[key].pop(category)

        # Identify keys for removal
        keys_to_remove = [key for key, version in self.changelog_dict.items() if len(version) <= 1]

        # Remove the identified keys
        for key in keys_to_remove:
            self.changelog_dict.pop(key)

    def has_updates(self) -> bool:
        """Check if there are any meaningful updates in the changelog other than the date.

        This function modifies `self.changelog_dict` to remove any versions that have only one item (i.e., only a date and no other changes).

        Returns:
            bool: True if there are meaningful updates, False otherwise.
        """
        # Return False if the dictionary is empty; True otherwise
        return bool(self.changelog_dict)

    def list_of_versions(self) -> list[str]:
        """Get a list of all versions in the changelog.

        Returns:
            list[str]: A list of all versions in the changelog.
        """
        return list(self.changelog_dict.keys())

    def get_text(self) -> str:
        """Generate a text version of the changelog."""
        description = ""

        # Loop through each version in the changelog
        for version, data in self.changelog_dict.items():
            # Add the version header
            description += f"### v{version} ({data['date']})\n"

            # Add each category
            for category, entries in data.items():
                # Skip the version and date
                if category == "date":
                    continue

                # Add the category header
                description += f"\n**{category.capitalize()}**\n"

                # Add each entry
                for entry in entries:
                    description += f"{entry}\n"

        description += "\n\n----\n"
        description += "View the [full changelog on Github](https://github.com/natelandau/valentina/releases)\n"

        return description

    def get_embed(self) -> discord.Embed:
        """Generate an embed for the changelog.

        Returns:
            discord.Embed: The changelog embed.
        """
        description = ""

        description = "## Valentina Noir Changelog\n"
        description += self.get_text()

        embed = discord.Embed(
            description=description,
            color=EmbedColor.INFO.value,
        )
        if self.bot:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        return embed

    def get_embed_personality(self) -> discord.Embed:  # pragma: no cover
        """Generate an embed for the changelog.

        Returns:
            discord.Embed: The changelog embed.
        """
        # Create and populate the embed description
        description = f"Valentina, your {random.choice(['honored', 'admired', 'distinguished', 'celebrated', 'hallowed', 'prestigious', 'acclaimed', 'favorite', 'friendly neighborhood', 'prized', 'treasured', 'number one', 'esteemed', 'venerated', 'revered', 'feared'])} {random.choice(BOT_DESCRIPTIONS)}, has {random.choice(['been granted new powers', 'leveled up', 'spent experience points', 'gained new abilities', 'been bitten by a radioactive spider', 'spent willpower points', 'been updated', 'squashed bugs and gained new features',])}!\n"

        description += self.get_text()
        description += "- Run `/changelog` to view specific versions\n"

        embed = discord.Embed(description=description, color=EmbedColor.INFO.value)
        if self.bot:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        return embed
