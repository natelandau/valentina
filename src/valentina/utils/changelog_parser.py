"""Helper class for parsing changelogs."""
import random
import re

import discord
from discord.ext import commands
from loguru import logger
from semver import Version

from valentina.constants import BOT_DESCRIPTIONS, CHANGELOG_PATH, EmbedColor


class ChangelogParser:
    """Helper class for parsing changelogs."""

    def __init__(
        self,
        bot: commands.Bot,
        oldest_version: str | None = None,
        newest_version: str | None = None,
        exclude_categories: list[str] = [],
    ):
        self.path = CHANGELOG_PATH
        self.bot = bot
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

    def __check_version_schema(self, version: str) -> bool:
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
        full_category_list = [
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
        categories = [
            category for category in full_category_list if category not in self.exclude_categories
        ]
        category_re = re.compile(rf"### ({'|'.join(categories)})", re.I)

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

                if (Version.parse(version_being_parsed) >= Version.parse(self.oldest_version)) and (
                    Version.parse(version_being_parsed) <= Version.parse(self.newest_version)
                ):
                    changelog_dict[version_being_parsed] = {"date": date_re.search(line).group(1)}
                    parse_version = True
                    continue

                # Stop parsing if we are below the to_version
                if Version.parse(version_being_parsed) < Version.parse(self.oldest_version):
                    break

                # Do not parse if we are above the from_version
                if Version.parse(version_being_parsed) > Version.parse(self.newest_version):
                    parse_version = False
                    continue

            # Check for category line
            if category_match := category_re.match(line):
                current_category = category_match.group(1).lower()
                continue

            # If we are within a version and a category, append line to that category
            if parse_version and current_category:
                cleaned_line = re.sub(r" \(#\d+\)$", "", line)  # Clean up PR references

                if current_category not in changelog_dict[version_being_parsed]:
                    changelog_dict[version_being_parsed][current_category] = [cleaned_line]
                else:
                    changelog_dict[version_being_parsed][current_category].append(cleaned_line)  # type: ignore [union-attr]

        return changelog_dict

    def has_updates(self) -> bool:
        """Check if there are any meaningful updates in the changelog other than the date.

        This function modifies `self.changelog_dict` to remove any versions that have only one item (i.e., only a date and no other changes).

        Returns:
            bool: True if there are meaningful updates, False otherwise.
        """
        # List to store keys for removal
        keys_to_remove = [key for key, version in self.changelog_dict.items() if len(version) <= 1]

        # Remove the identified keys
        for key in keys_to_remove:
            self.changelog_dict.pop(key)

        # Return False if the dictionary is empty; True otherwise
        return bool(self.changelog_dict)

    def list_of_versions(self) -> list[str]:
        """Get a list of all versions in the changelog.

        Returns:
            list[str]: A list of all versions in the changelog.
        """
        return list(self.changelog_dict.keys())

    def get_embed_basic(self) -> discord.Embed:
        """Generate an embed for the changelog.

        Returns:
            discord.Embed: The changelog embed.
        """
        description = ""

        # Loop through each version in the changelog
        for version, data in self.changelog_dict.items():
            # Add the version header
            description += f"### v{version} ({data['date']})\n"

            # Add each category
            for category, entries in data.items():
                # Skip the version and date
                if category in ["date"]:
                    continue

                # Add the category header
                description += f"\n**{category.capitalize()}**\n"

                # Add each entry
                for entry in entries:
                    description += f"{entry}\n"

        embed = discord.Embed(
            title="Valentina Changelog", description=description, color=EmbedColor.INFO.value
        )
        embed.set_footer(text="For more information, type /changelog")
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        return embed

    def get_embed_personality(self) -> discord.Embed:
        """Generate an embed for the changelog.

        Returns:
            discord.Embed: The changelog embed.
        """
        print("alive")
        # Create and populate the embed description
        description = f"Valentina, your {random.choice(['honored','admired','distinguished','celebrated','hallowed','prestigious','acclaimed','favorite','friendly neighborhood','prized', 'treasured', 'number one','esteemed','venerated','revered','feared'])} {random.choice(BOT_DESCRIPTIONS)} has {random.choice(['been granted new powers', 'leveled up','spent experience points','gained new abilities','been bitten by a radioactive spider', 'spent willpower points', 'been updated','squashed bugs and gained new features',])}!\n\n"

        # Loop through each version in the changelog
        for version, data in self.changelog_dict.items():
            # Add the version header
            description += f"**On {data['date']} I was updated to `v{version}`**\n"

            # Add each category
            for category, entries in data.items():
                # Skip the version and date
                if category in ["date"]:
                    continue

                # Add the category header
                description += f"\n**{category.capitalize()}**\n"

                # Add each entry
                for entry in entries:
                    description += f"{entry}\n"

        embed = discord.Embed(description=description, color=EmbedColor.INFO.value)
        embed.set_footer(text="For more information, type /changelog")
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        return embed
