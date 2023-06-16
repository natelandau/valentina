"""Help Command for Valentina."""
import discord
from discord.commands import Option
from discord.ext import commands

from valentina import CONFIG, Valentina
from valentina.__version__ import __version__
from valentina.views.embeds import present_embed


class Help(commands.Cog):
    """Commands for help."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    @commands.slash_command(name="help", description="See help information.")
    async def get_help(
        self, ctx: discord.ApplicationContext, command: Option(str, required=False)  # type: ignore
    ) -> None:
        """Provide help information."""
        ephemeral = True
        level = "info"
        fields = []
        if not command or command.lower() == "help":
            # Start to build the description
            title = "Valentina Noir Help"
            description = "Use Valentina's commands by typing `/<command> <subcommand>`\n\nUse `/help <command>` for detailed help information on each command below.\n\n"
            fields.append(("\u200b", "**COMMANDS**"))

            # iterate trough cogs, gathering descriptions
            for cog in self.bot.cogs:
                fields.append((f"{cog}", self.bot.cogs[cog].__doc__ or "No description"))

            # iterate through uncategorized commands
            for command in self.bot.walk_commands():
                # if command not in a cog
                # listing command if cog name is None and command isn't hidden
                if not command.cog_name and not command.hidden and command.name != "help":
                    fields.append((f"{command.name}", command.description))

            # Add owner information
            owners = [ctx.guild.get_member(int(x)).mention for x in CONFIG["OWNER_IDS"].split(",")]

            fields.append(
                (
                    "\u200b",
                    f"***About Valentina Noir:***\n Version: `v{__version__}`\n Developed by {' ,'.join(owners)}\n[View source on Github](https://github.com/natelandau/valentina)",
                )
            )
        # trying to find matching cog and it's commands
        else:
            for cog in self.bot.cogs:
                c = cog.lower()
                if c == command.lower():
                    title = f"Help for\u0020\u0020`/{c}`"
                    description = (
                        f"{self.bot.cogs[cog].__doc__}\n\nUsage:\u0020\u0020`/{c} <subcommand>`"
                    )
                    fields.append(("\u200b", "**SUBCOMMANDS**"))
                    # getting commands from cog
                    for command in self.bot.get_cog(cog).walk_commands():
                        if (
                            isinstance(command, discord.commands.core.SlashCommand)
                            and command.parent.name.lower() != c
                        ):
                            fields.append(
                                (
                                    f"`{command.parent.name} {command.name}`",
                                    command.description,
                                )
                            )
                        elif isinstance(command, discord.commands.core.SlashCommand):
                            fields.append(
                                (
                                    f"`{command.name}`",
                                    command.description if command.description else "",
                                )
                            )

                    # found cog - breaking loop
                    break
            # if input not found
            # yes, for-loops have an else statement, it's called when no 'break' was issued
            else:
                title = "What's that?!"
                description = f"I've never heard of a command named `{command}` before :scream:"
                level = "error"

        await present_embed(
            ctx=ctx,
            title=title,
            description=description,
            fields=fields,
            level=level,
            ephemeral=ephemeral,
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Help(bot))
