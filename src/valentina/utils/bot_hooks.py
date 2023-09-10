"""Helpers for the bot to use via hooks."""

import random
from pathlib import Path

import discord
from discord.ext import commands
from loguru import logger
from semver import Version

from valentina.constants import EmbedColor
from valentina.models.db_tables import DatabaseVersion, Guild
from valentina.utils.helpers import changelog_parser

RANDOM_RESPONSE = [
    "bot who helps you play White Wolf's TTRPGs",
    "blood sucking bot who's here to serve you",
    "succubus who will yet have your heart",
    "maid servant here to serve your deepest desires",
    "sweet little thing",
    "sweet little thing who will eat your heart out",
    "doll faced beauty who cries next to you in bed",
    "evil temptress who has you begging for more",
    "harpy who makes you regret your words",
    "harlot who makes you regret your choices",
    "temptress has you wrapped around her fingers",
    "guardian angel who watches over you",
    "Tremere primogen makes you offers you can't refuse",
    "Malkavian who makes you question your sanity",
    "Ventrue who makes you question your loyalties",
    "Nosferatu who makes you scream in terror",
    "Toreador who makes you fall in love",
    "Gangrel who makes you run for your life",
    "Brujah who makes you fight for your freedom",
    "Lasombra who makes you question your faith",
    "Ravnos who makes you question your reality",
    "Sabbat warrior who makes you question your humanity",
]


async def send_changelog(bot: commands.Bot, guild: discord.Guild) -> None:
    """Send a welcome message to the guild's system channel when the bot joins.

    The function checks the last posted version for the guild and compares it to the current version.
    If the current version is greater, it fetches and parses the changelog, sending an update to the guild.

    Args:
        bot (commands.Bot): The bot instance.
        guild (discord.Guild): The guild object representing the Discord server.

    Returns:
        None
    """
    # If the guild does not have a changelog channel, return
    db_guild = Guild.get_by_id(guild.id)
    db_changelog_channel_id = db_guild.data.get("changelog_channel_id", None)
    changelog_channel = discord.utils.get(guild.text_channels, id=db_changelog_channel_id)

    if not db_changelog_channel_id or not changelog_channel:
        return

    # Build variables for changelog comparison
    db_version = DatabaseVersion.select().order_by(DatabaseVersion.id.desc()).get().version
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
        description = f"### Your {random.choice(['favorite','friendly neighborhood','prized', 'treasured', 'number one','esteemed','venerated','revered','feared'])} {random.choice(RANDOM_RESPONSE)} has {random.choice(['been granted new powers', 'leveled up','spent experience points','gained new abilities','been bitten by a radioactive spider', 'spent willpower points', 'been updated','squashed bugs and gained new features',])}!\n"

        for version, data in changes.items():
            description += f"### On `{data['date']}` I was updated to version `{version}`\n"

            if features := data.get("features"):
                description += "### Features:\n"
                description += "\n".join(features)
                description += "\n"
            if fixes := data.get("fixes"):
                description += "### Fixes:\n" + "\n".join(fixes) + "\n"

        # Send the embed message
        embed = discord.Embed(title="", description=description, color=EmbedColor.INFO.value)
        embed.set_author(name=bot.user.display_name, icon_url=bot.user.display_avatar)
        embed.set_footer(text="For more information, type /changelog")
        await changelog_channel.send(embed=embed)


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
    description = [
        "### Hi there!",
        f"**I'm Valentina Noir, a {random.choice(RANDOM_RESPONSE)}.**\n",
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
