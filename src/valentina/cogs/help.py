# mypy: disable-error-code="valid-type"
"""Help Command for Valentina."""

from pathlib import Path

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina.models.bot import Valentina, ValentinaContext
from valentina.utils.helpers import get_config_value
from valentina.views import auto_paginate, present_embed


class Help(commands.Cog):
    """Commands for help."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot

    def __build_command_list(self, ctx: ValentinaContext) -> list:
        """Build a list of commands for the help command."""
        unsorted_commands: list = []

        # build user specific list of commands to hide
        hidden_commands = ["Owner"]  # Always hide the "Owner" cog

        owner_ids = get_config_value("VALENTINA_OWNER_IDS", pass_none=True)
        if owner_ids:
            owners = [int(x) for x in owner_ids.split(",")]
            if ctx.author.id not in owners:
                hidden_commands.append("Developer")

            if ctx.author.guild_permissions.administrator is False:
                hidden_commands.append("Admin")

        for cog in self.bot.cogs:
            if cog not in hidden_commands:
                for cmd in self.bot.get_cog(cog).get_commands():
                    unsorted_commands.append(cmd)  # noqa: PERF402

        """
        # NOTE: Uncomment this to show all unsorted commands
        for c in self.bot.walk_commands():
            if c.name != "help":
                unsorted_commands.append(c)
        """

        return sorted(unsorted_commands, key=lambda x: x.name)

    def __build_help_text(self, cmd: commands.Command) -> str:
        """Build the help text for a command."""
        description = (
            f"## `/{cmd.name} [subcommand]`\n"
            if hasattr(cmd, "subcommands")
            else f"## `/{cmd.name}`\n"
        )
        description += f"{cmd.description}\n"
        if not hasattr(cmd, "subcommands"):
            return description

        description += "### Subcommands\n"

        for c in sorted(cmd.subcommands, key=lambda x: x.name):
            if hasattr(c, "subcommands"):
                description += f"**{c.name} `[subcommand]`**\n"
            else:
                description += f"**{c.name}**\n"
            description += f"└ {c.description}\n\n"

        return description

    help = discord.SlashCommandGroup("help", "Help with Valentina")  # noqa: A003

    @help.command(name="commands", description="Help information for Valentina's commands")
    async def command_help(
        self,
        ctx: ValentinaContext,
        command: Option(str, required=False),  # type: ignore
    ) -> None:
        """Provide help information."""
        commands = self.__build_command_list(ctx)

        if not command:
            description = "**Usage:** Type `/<command> <subcommand>`\n"

            description += "### All Commands\n"
            for cmd in commands:
                description += f"**{cmd.name}**\n"
                description += f"└ {cmd.description}\n\n"
            description += "\u23AF" * 33 + "\n"
            description += (
                "> Use `/help <command>` for detailed help information on each command.\n"
            )

            await present_embed(
                ctx,
                title="Valentina Noir Help",
                description=description,
                level="info",
                ephemeral=True,
            )
        else:
            found_command = False
            arg_command = command.split(" ")

            for cmd in commands:
                if cmd.name == arg_command[0] and not arg_command[1:]:
                    found_command = True
                    description = self.__build_help_text(cmd)
                    description += "\u23AF" * 33 + "\n"
                    description += "> Use `/help <command> <command>` for information on subcommands with subcommands.\n"

                    break

                if cmd.name == arg_command[0] and hasattr(cmd, "subcommands") and arg_command[1:]:
                    for c in cmd.subcommands:
                        if c.name == arg_command[1]:
                            found_command = True
                            description = description = self.__build_help_text(c)

                            break

            if not found_command:
                await present_embed(
                    ctx,
                    title="Command not found",
                    description=f"Command `{command}` not found. :scream:",
                    level="error",
                    ephemeral=True,
                    delete_after=15,
                )
                return

            await present_embed(
                ctx,
                title="Valentina Noir Help",
                description=description,
                level="info",
                ephemeral=True,
            )

    @help.command(name="user_guide", description="A guide on how to use Valentina Noir")
    async def user_guide(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the user guide only visible to you (default true).",
            default=True,
        ),
    ) -> None:
        """A walkthrough of Valentina Noir."""
        path = Path(__file__).parent / "../../../user_guide.md"
        if not path.exists():
            logger.error(f"User Guide file not found at {path}")
            raise FileNotFoundError

        user_guide = path.read_text()
        await auto_paginate(
            ctx,
            title="Valentina User Guide",
            text=user_guide,
            url="https://github.com/natelandau/valentina/blob/main/user_guide.md",
            hidden=hidden,
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Help(bot))
