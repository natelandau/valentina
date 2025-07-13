"""Classes and functions to manage posting changelogs to Discord channels."""

import random
import re
from typing import TYPE_CHECKING, Optional

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

if TYPE_CHECKING:
    from valentina.discord.bot import ValentinaContext


class ChangelogPoster:  # pragma: no cover
    """Helper class for posting changelogs to the changelog channel specified in guild settings."""

    def __init__(  # noqa: PLR0913
        self,
        bot: commands.Bot | None = None,
        ctx: Optional["ValentinaContext"] = None,
        channel: discord.TextChannel | None = None,
        exclude_cagegories: list[str] = CHANGELOG_EXCLUDE_CATEGORIES,
        oldest_version: str | None = None,
        newest_version: str | None = None,
        with_personality: bool = False,
        exclude_oldest_version: bool = False,
    ):
        self.exclude_categories = exclude_cagegories
        self.bot = bot
        self.ctx = ctx
        self.channel = channel

        self.changelog = ChangelogParser(
            bot=self.bot or self.ctx.bot,
            exclude_categories=self.exclude_categories,
            oldest_version=oldest_version,
            newest_version=newest_version,
            exclude_oldest_version=exclude_oldest_version,
        )

        self.oldest_version, self.newest_version = self._validate_versions(
            oldest_version,
            newest_version,
        )

        self.with_personality = with_personality

        self.posted = False  # Flag to indicate if the changelog has been posted

    async def _get_channel_from_ctx(self) -> discord.TextChannel | None:
        """Retrieve the changelog channel from the guild settings.

        Fetch the guild object using the context's guild ID and use it to obtain the designated changelog channel. This method relies on the existence of a valid context (self.ctx) to function properly.

        Returns:
            discord.TextChannel | None: The designated changelog channel if it exists
                and can be fetched, None otherwise.

        Note:
            This method assumes that the Guild model has a method called
            'fetch_changelog_channel' which returns the appropriate channel object.
        """
        if self.ctx:
            guild = await Guild.get(self.ctx.guild.id)
            return guild.fetch_changelog_channel(self.ctx.guild)

        return None

    async def _validate_channel(self) -> bool:
        """Validate the existence of the changelog channel.

        Verify that a valid channel for posting the changelog exists. If no channel is set, attempt to retrieve it from the guild settings using the context.

        Returns:
            bool: True if a valid changelog channel exists, False otherwise.

        Note:
            This method may update the `self.channel` attribute if it's not already set.
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
        """Validate the version inputs for the ChangelogPoster.

        Compare the oldest and newest version strings to ensure they are in the correct order. Check if the provided versions exist in the changelog.

        Args:
            oldest_version (str): The oldest version to include in the changelog.
            newest_version (str): The newest version to include in the changelog.

        Returns:
            tuple[str, str]: A tuple containing the validated oldest and newest versions.

        Raises:
            commands.BadArgument: If the oldest version is newer than the newest version.
            errors.VersionNotFoundError: If neither version is found in the changelog.
        """
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
        """Post the changelog to the specified Discord channel.

        Validate the channel, check for updates, and send the changelog as an embed. If no updates are found, log the information or respond to the context with an error message. Use personality in the embed if specified.

        Raises:
            discord.errors.Forbidden: If the bot lacks permissions to send messages.
            discord.errors.HTTPException: If sending the message fails.

        Note:
            This method sets the 'posted' attribute to True upon successful posting.
        """
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
    """Parse and process changelog files.

    Provide methods to read, interpret, and manipulate changelog entries. Handle version comparisons, category filtering, and data extraction from structured changelog files. Support various output formats for changelog information, including Discord embeds.
    """

    def __init__(
        self,
        bot: commands.Bot | discord.bot.Bot | None = None,
        oldest_version: str | None = None,
        newest_version: str | None = None,
        exclude_categories: list[str] = [],
        exclude_oldest_version: bool = False,
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
        self.exclude_oldest_version = exclude_oldest_version

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
        """Check if the version string follows the correct format.

        Validate that the given version string adheres to the semantic versioning format (MAJOR.MINOR.PATCH). Use a regular expression to ensure the string contains three groups of digits separated by periods.

        Args:
            version (str): The version string to be checked.

        Returns:
            bool: True if the version string is valid, False otherwise.
        """
        return bool(re.match(r"^(\d+\.\d+\.\d+)$", version))

    def __get_changelog(self) -> str:
        """Read and return the contents of the changelog file.

        Attempt to read the changelog file from the specified path. If the file
        exists, return its contents as a string. If the file is not found, log
        an error and raise a FileNotFoundError.

        Returns:
            str: The contents of the changelog file.

        Raises:
            FileNotFoundError: If the changelog file does not exist at the specified path.
        """
        if not self.path.exists():
            logger.error(f"Changelog file not found at {self.path}")
            raise FileNotFoundError

        return self.path.read_text()

    def __parse_changelog(self) -> dict[str, dict[str, str | list[str]]]:  # noqa: C901
        """Parse the changelog into a structured dictionary.

        Iterate through each line of the changelog, identifying version numbers, dates, and categories.
        Construct a nested dictionary where:
        - The outer key is the version number
        - The inner keys are 'date' and category names
        - The values are either the release date (string) or lists of changelog entries

        Respect version boundaries set by oldest_version and newest_version attributes.
        Skip parsing for versions outside these boundaries or when exclude_oldest_version is True.

        Returns:
            dict[str, dict[str, str | list[str]]]: A nested dictionary containing structured changelog information.
                Format: {version: {'date': date_string, category1: [entries], category2: [entries], ...}}
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

                # When requested, do not parse the oldest version
                # This is used when automatically posting the changelog on bot connect
                if self.exclude_oldest_version and semver.Version.parse(
                    version_being_parsed,
                ) == semver.Version.parse(self.oldest_version):
                    parse_version = False
                    continue

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
                    self.oldest_version,
                ):
                    break

                # Do not parse if we are above the from_version
                if semver.Version.parse(version_being_parsed) > semver.Version.parse(
                    self.newest_version,
                ):
                    parse_version = False
                    continue

            # Check for category line
            if category_match := category_re.match(line):
                current_category = category_match.group(1).lower()
                continue

            # If we are within a version and a category, append line to that category
            if parse_version and current_category:  # type: ignore [unreachable] # TODO: Fix unreachable code
                cleaned_line = re.sub(r" \(#\d+\)$", "", line)  # Clean up PR references

                if current_category not in changelog_dict[version_being_parsed]:
                    changelog_dict[version_being_parsed][current_category] = [cleaned_line]
                else:
                    changelog_dict[version_being_parsed][current_category].append(cleaned_line)

        return changelog_dict

    def __clean_changelog(self) -> None:
        """Clean up the changelog dictionary by removing excluded categories and empty versions.

        Remove categories listed in the exclusion list from all versions in the changelog. Delete any versions that contain only a date entry and no other changes. Modify the `self.changelog_dict` in-place to reflect these changes.

        This method ensures that the changelog contains only relevant and non-empty entries.
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
        """Check for meaningful updates in the changelog.

        Determine if the changelog contains any significant updates beyond just date changes.
        Remove versions from `self.changelog_dict` that only contain a date entry and no other changes.
        This modification ensures that only versions with actual content are considered.

        Returns:
            bool: True if meaningful updates exist, False if the changelog is empty or contains only date changes.

        Note:
            This method modifies the `self.changelog_dict` in-place by removing versions without substantial changes.
        """
        # Return False if the dictionary is empty; True otherwise
        return bool(self.changelog_dict)

    def list_of_versions(self) -> list[str]:
        """Return a sorted list of all versions in the changelog.

        This method retrieves all version keys from the changelog dictionary,
        sorts them using semantic versioning rules, and returns them in
        descending order (latest version first).

        Returns:
            list[str]: A sorted list of all version strings in the changelog,
                       ordered from newest to oldest.

        Note:
            The sorting is performed using the semver.Version.parse method,
            ensuring proper semantic versioning order.
        """
        return sorted(self.changelog_dict.keys(), key=semver.Version.parse, reverse=True)

    def get_text(self) -> str:
        """Generate a text version of the changelog.

        Create a formatted string representation of the changelog, including version numbers,
        dates, categories, and individual entries. Organize the content hierarchically with
        version headers, category subheaders, and bulleted entries. Append a link to the full
        changelog on GitHub at the end of the text.

        Returns:
            str: A formatted string containing the entire changelog text.

        Note:
            This method iterates through the `self.changelog_dict` to construct the text,
            skipping the 'date' key when processing categories.
        """
        description = ""

        # Loop through each version in the changelog
        for version, data in self.changelog_dict.items():
            # Add the version header
            description += f"\n### v{version} ({data['date']})\n"

            # Add each category
            for category, entries in data.items():
                # Skip the version and date
                if category == "date":
                    continue

                # Add the category header
                description += f"\n**{category.capitalize()}**\n\n"

                # Add each entry
                for entry in entries:
                    description += f"{entry}\n"

        description += "\n\n----\n"
        description += "View the [full changelog on Github](https://github.com/natelandau/valentina/releases)\n"

        return description

    def get_embed(self) -> discord.Embed:
        """Generate a Discord embed containing the changelog information.

        Create a Discord embed object that includes the full changelog text.
        Set the embed's description to include a header and the formatted
        changelog content. If a bot instance is available, set the embed's
        thumbnail to the bot's avatar.

        Returns:
            discord.Embed: An embed object containing the formatted changelog
                           information, ready to be sent in a Discord message.
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
        """Generate a Discord embed for the changelog with a personalized touch.

        Create a Discord embed that presents the changelog information in a
        more engaging and character-specific manner. This method adds a
        randomized, personality-driven introduction to the changelog content.

        The embed includes:
        - A randomized introductory sentence describing Valentina's update.
        - The full changelog text.
        - A note about viewing specific versions.
        - The bot's avatar as the thumbnail (if available).

        Returns:
            discord.Embed: A Discord embed object containing the personalized
                           changelog information, ready to be sent as a message.
        """
        # Create and populate the embed description
        description = f"Valentina, your {random.choice(['honored', 'admired', 'distinguished', 'celebrated', 'hallowed', 'prestigious', 'acclaimed', 'favorite', 'friendly neighborhood', 'prized', 'treasured', 'number one', 'esteemed', 'venerated', 'revered', 'feared'])} {random.choice(BOT_DESCRIPTIONS)}, has {random.choice(['been granted new powers', 'leveled up', 'spent experience points', 'gained new abilities', 'been bitten by a radioactive spider', 'spent willpower points', 'been updated', 'squashed bugs and gained new features'])}!\n"

        description += self.get_text()
        description += "- Run `/changelog` to view specific versions\n"

        embed = discord.Embed(description=description, color=EmbedColor.INFO.value)
        if self.bot:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        return embed
