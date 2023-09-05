"""Helpers for the bot to use via hooks."""

import random
import re
from pathlib import Path

import discord
from discord.ext import commands
from loguru import logger
from semver import Version

from valentina.constants import EmbedColor
from valentina.models.db_tables import DatabaseVersion, Guild


def changelog_parser(
    changelog: str, last_posted_version: str
) -> dict[str, dict[str, str | list[str]]]:
    """Parse a changelog to extract versions, dates, features, and fixes, stopping at the last posted version.

    The function looks for sections in the changelog that correspond to version numbers,
    feature and fix descriptions. It ignores specified sections like Docs, Refactor, Style, and Test.

    Args:
        changelog (str): The changelog text to parse.
        last_posted_version (str): The last version that was posted, parsing stops when this version is reached.

    Returns:
        Dict[str, dict[str, str | list[str]]]: A dictionary containing the parsed data.
        The key is the version number, and the value is another dictionary with date, features, and fixes.
    """
    # Precompile regex patterns
    version = re.compile(r"## v(\d+\.\d+\.\d+)")
    date = re.compile(r"(\d{4}-\d{2}-\d{2})")
    feature = re.compile(r"### Feat")
    fix = re.compile(r"### Fix")
    ignored_sections = re.compile(r"### Docs|### Refactor|### Style|### Test")

    # Initialize dictionary to store parsed data
    changes: dict[str, dict[str, str | list[str]]] = {}
    in_features = in_fixes = False  # Flags for parsing feature and fix sections

    # Split changelog into lines and iterate
    for line in changelog.split("\n"):
        # Skip empty lines
        if line == "":
            continue

        # Skip lines with ignored section headers
        if ignored_sections.match(line):
            in_features = in_fixes = False
            continue

        # Version section
        if version_match := version.match(line):
            version_number = version_match.group(1)
            if version_number == last_posted_version:
                break  # Stop parsing when last posted version is reached

            changes[version_number] = {
                "date": date.search(line).group(1),
                "features": [],
                "fixes": [],
            }
            continue

        if bool(feature.match(line)):
            in_features = True
            in_fixes = False
            continue

        if bool(fix.match(line)):
            in_features = False
            in_fixes = True
            continue

        line = re.sub(r" \(#\d+\)$", "", line)  # noqa: PLW2901
        line = re.sub(r"(\*\*)", "", line)  # noqa: PLW2901
        if in_features:
            changes[version_number]["features"].append(line)  # type: ignore [union-attr]
        if in_fixes:
            changes[version_number]["fixes"].append(line)  # type: ignore [union-attr]

    return changes


async def welcome_message(bot: commands.Bot, guild: discord.Guild) -> None:
    """Send a welcome message to the guild's system channel when the bot joins.

    The function checks the last posted version for the guild and compares it to the current version.
    If the current version is greater, it fetches and parses the changelog, sending an update to the guild.

    Args:
        bot (commands.Bot): The bot instance.
        guild (discord.Guild): The guild object representing the Discord server.

    Returns:
        None
    """
    # Retrieve the last posted version for the guild
    db_version = DatabaseVersion.select().order_by(DatabaseVersion.id.desc()).get().version
    db_guild = Guild.get_by_id(guild.id)

    guild_last_posted_version = db_guild.data.get("changelog_posted_version", None)

    # Use current version -1 if no previous version is logged in the database
    if not guild_last_posted_version:
        current_version = Version.parse(db_version)
        guild_last_posted_version = Version(
            current_version.major, current_version.minor - 1, current_version.patch
        )

    # If a newer version exists, proceed to parse changelog
    if guild_last_posted_version < Version.parse(db_version):
        db_guild.data["changelog_posted_version"] = db_version
        db_guild.save()

        # Locate changelog and read its content
        changelog_path = Path(__file__).parent / "../../../CHANGELOG.md"
        if not changelog_path.exists():
            logger.error(f"Changelog file not found at {changelog_path}")
            raise FileNotFoundError

        changelog = changelog_path.read_text()
        changes = changelog_parser(changelog, guild_last_posted_version)

        # Create and populate the embed description
        description = "## I'm back with a new version of Valentina!\n"
        description += f"Since I last logged in, I was updated to version {db_version}.\nHere's what you missed.\n\n"

        for version, data in changes.items():
            description += (
                f"**On `{data['date']}` I was updated to version `{version}`.**\n```yaml\n"
            )
            if features := data.get("features"):
                description += "### Features:\n" + "\n".join(features) + "\n\n"
            if fixes := data.get("fixes"):
                description += "### Fixes:\n" + "\n".join(fixes) + "\n"
            description += "```\n"

        # Send the embed message
        embed = discord.Embed(title="", description=description, color=EmbedColor.INFO.value)
        embed.set_thumbnail(url=bot.user.display_avatar)
        await guild.system_channel.send(embed=embed)


async def create_storyteller_role(guild: discord.Guild) -> discord.Role:
    """Create a storyteller role for the guild."""
    storyteller = discord.utils.get(guild.roles, name="Storyteller")

    if storyteller is None:
        storyteller = await guild.create_role(
            name="Storyteller",
            color=discord.Color.dark_teal(),
            mentionable=True,
            hoist=True,
        )

    perms = discord.Permissions()
    perms.update(
        add_reactions=True,
        attach_files=True,
        can_create_instant_invite=True,
        change_nickname=True,
        connect=True,
        create_private_threads=True,
        create_public_threads=True,
        embed_links=True,
        external_emojis=True,
        external_stickers=True,
        manage_messages=True,
        manage_threads=True,
        mention_everyone=True,
        read_message_history=True,
        read_messages=True,
        send_messages_in_threads=True,
        send_messages=True,
        send_tts_messages=True,
        speak=True,
        stream=True,
        use_application_commands=True,
        use_external_emojis=True,
        use_external_stickers=True,
        use_slash_commands=True,
        use_voice_activation=True,
        view_channel=True,
    )
    await storyteller.edit(reason=None, permissions=perms)
    logger.debug(f"CONNECT: {storyteller.name} role created")

    return storyteller


async def create_player_role(guild: discord.Guild) -> discord.Role:
    """Create player role for the guild."""
    player = discord.utils.get(guild.roles, name="Player", mentionable=True, hoist=True)

    if player is None:
        player = await guild.create_role(
            name="Player",
            color=discord.Color.dark_blue(),
            mentionable=True,
            hoist=True,
        )

    perms = discord.Permissions()
    perms.update(
        add_reactions=True,
        attach_files=True,
        can_create_instant_invite=True,
        change_nickname=True,
        connect=True,
        create_private_threads=True,
        create_public_threads=True,
        embed_links=True,
        external_emojis=True,
        external_stickers=True,
        mention_everyone=True,
        read_message_history=True,
        read_messages=True,
        send_messages_in_threads=True,
        send_messages=True,
        send_tts_messages=True,
        speak=True,
        stream=True,
        use_application_commands=True,
        use_external_emojis=True,
        use_external_stickers=True,
        use_slash_commands=True,
        use_voice_activation=True,
        view_channel=True,
    )
    await player.edit(reason=None, permissions=perms)
    logger.debug(f"CONNECT: {player.name} role created")

    return player


async def respond_to_mentions(bot: commands.Bot, message: discord.Message) -> None:
    """Respond to @mentions of the bot."""
    random_response = [
        "a bot to help you play White Wolf's TTRPGs",
        "a blood sucking bot who is here to serve you",
        "a succubus who will steal your heart",
        "a maid servant here to serve your deepest desires",
        "a sweet little thing who will make you scream",
        "an evil temptress who have you begging for more",
        "a harpy who will make you regret your words",
        "a harlot who will make you regret your choices",
        "a temptress who will wrap you around her finger",
        "a Tremere primogen who will make you an offer you can't refuse",
        "a Malkavian who will make you question your sanity",
        "a Ventrue who will make you question your loyalties",
        "a Nosferatu who will make you scream in terror",
        "a Toreador who will make you fall in love",
        "a Gangrel who will make you run for your life",
        "a Brujah who will make you fight for your freedom",
        "a Lasombra who will make you question your faith",
        "a Ravnos who will make you question your reality",
        "a Sabbat warrior who will make you question your humanity",
    ]

    description = [
        "### Hi there!",
        f"**I'm Valentina Noir, {random.choice(random_response)}.**\n",
        "I'm still in development, so please be patient with me.\n",
        "There are a few ways to get help using me. (_You do want to use me, right?_)\n",
        "- Type `/help` to get a list of commands",
        "- Type `/help <command>` to get help for a specific command",
        "- Type `/help user_guide` to read about my capabilities",
        "- Type `/changelog` to read about my most recent updates\n",
        " If none of those answered your questions, please contact an admin.",
    ]

    embed = discord.Embed(title="", description="\n".join(description), color=EmbedColor.INFO.value)
    embed.set_thumbnail(url=bot.user.display_avatar)
    await message.channel.send(embed=embed)
