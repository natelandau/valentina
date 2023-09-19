"""Respond to events that occur in the Discord server."""

import random

import discord
from discord.ext import commands
from loguru import logger

from valentina.constants import BAD_WORD_PATTERN, BOT_DESCRIPTIONS, EmbedColor
from valentina.models.bot import Valentina
from valentina.models.db_tables import Guild
from valentina.models.errors import reporter


class Events(commands.Cog, name="Events"):
    """Respond to events that occur in the Discord server."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """on_message event handling."""
        # Do not reply to bot's own messages
        if message.author.bot:
            return

        # Do not reply to messages that start with the prefix
        if message.content.startswith(self.bot.command_prefix):
            logger.info(f"BOT: Ignoring command message: {message.content}")
            return

        # Respond to @mentions of the  bot
        if self.bot.user.mentioned_in(message) and message.mention_everyone is False:
            description = [
                "### Hi there!",
                f"**I'm Valentina Noir, a {random.choice(BOT_DESCRIPTIONS)}.**\n",
                "I'm still in development, so please be patient with me.\n",
                "There are a few ways to get help using me. (_You do want to use me, right?_)\n",
                "- Type `/help` to get a list of commands",
                "- Type `/help <command>` to get help for a specific command",
                "- Type `/help user_guide` to read about my capabilities",
                "- Type `/changelog` to read about my most recent updates\n",
                " If none of those answered your questions, please contact an admin.",
            ]

            embed = discord.Embed(
                title="", description="\n".join(description), color=EmbedColor.INFO.value
            )
            embed.set_thumbnail(url=self.bot.user.display_avatar)
            await message.channel.send(embed=embed)

        if BAD_WORD_PATTERN.search(message.content):
            responses = [
                # Existing responses
                "You kiss your mother with that mouth?",
                "Watch your language!",
                "🤬",
                "🤐",
                "What did you just say?",
                "I'm telling your mother!",
                "Whoa, easy there!",
                "Mind your manners!",
                "Is that how you talk at the dinner table?",
                "Do you speak to everyone like that?",
                "I'd wash my mouth out if I were you.",
                "Hey, let's keep it family-friendly.",
                "Wow, someone's got a potty mouth.",
                "That's not appropriate.",
                "Could you rephrase that?",
                "Let's be civil, okay?",
                "Oh, someone's got a sailor mouth!",
                "You must be fun at parties.",
                "Feeling brave, aren't we?",
                "Did you eat a bowl of alphabet soup and choke on the bad words?",
                "Someone needs a timeout!",
                "You're one keyboard away from soap in the mouth.",
                "Well, aren't you a little ray of pitch black.",
                "If you can't say something nice, you're probably at the right place.",
                "Aw, someone needs a hug... from a distance.",
                "You're just a keyboard warrior, aren't you?",
                "You must be the life of the party... or not.",
                "Careful, you'll hurt my circuits with that language.",
                "Trying to sound tough, huh?",
                "Don't make me mute you.",
                "Wow, you really went to college for that vocabulary, didn't you?",
                "Someone's keyboard is on fire today!",
                "Did you learn those words from a cereal box?",
                "Someone's been reading the dictionary's 'Do Not Use' section.",
                "Is that the best you can do?",
                "Ah, the language of Shakespeare, I presume?",
                "Someone's been skipping their etiquette classes.",
                "Is that how you make friends?",
                "Naughty words? You must be a handful.",
                "Whoa, easy tiger!",
            ]
            await message.channel.send(f"{random.choice(responses)}")
            return

    @commands.Cog.listener()
    async def on_application_command_error(
        self, ctx: discord.ApplicationContext, error: discord.DiscordException
    ) -> None:
        """Use centralized reporter to handle errors in slash commands."""
        await reporter.report_error(ctx, error)

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: discord.ApplicationContext, error: discord.DiscordException
    ) -> None:
        """Use centralized reporter to handle errors in prefix commands."""
        await reporter.report_error(ctx, error)

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild) -> None:
        """Log guild name changes and update the database."""
        if before.name != after.name:
            logger.info(f"BOT: Rename guild `{before.name}` => `{after.name}`")
            Guild.update(name=after.name).where(Guild.id == before.id).execute()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Called when a member joins the server."""
        logger.info(f"EVENT: {member.display_name} has joined the server")

        # Add user to the database
        self.bot.user_svc.update_or_add_user(ctx=None, user=member)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Called when the bot joins a guild."""
        logger.info(f"EVENT: Joined {guild.name} ({guild.id})")

        await self.bot.guild_svc.prepare_guild(guild=guild)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Events(bot))
