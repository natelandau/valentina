"""Help Command for Valentina."""
from textwrap import dedent

import discord
from discord.commands import Option
from discord.ext import commands, pages

from valentina import CONFIG, Valentina
from valentina.__version__ import __version__
from valentina.views import present_embed


class Help(commands.Cog):
    """Commands for help."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    async def cog_command_error(
        self, ctx: discord.ApplicationContext, error: discord.ApplicationCommandError | Exception
    ) -> None:
        """Handle exceptions and errors from the cog."""
        if hasattr(error, "original"):
            error = error.original

        command_name = ""
        if ctx.command.parent.name:
            command_name = f"{ctx.command.parent.name} "
        command_name += ctx.command.name

        await present_embed(
            ctx,
            title=f"Error running `{command_name}` command",
            description=str(error),
            level="error",
            ephemeral=True,
            delete_after=15,
        )

    def __build_command_list(self) -> list:
        """Build a list of commands for the help command."""
        unsorted_commands: list = []
        for cog in self.bot.cogs:
            if cog != "Owner":
                for cmd in self.bot.get_cog(cog).get_commands():
                    unsorted_commands.append(cmd)

        for c in self.bot.walk_commands():
            if c.name != "help":
                unsorted_commands.append(c)

        return sorted(unsorted_commands, key=lambda x: x.name)

    help = discord.SlashCommandGroup("help", "Help with Valentina")  # noqa: A003

    @help.command(name="commands", description="Help information for Valentina's commands")
    async def command_help(
        self, ctx: discord.ApplicationContext, command: Option(str, required=False)  # type: ignore
    ) -> None:
        """Provide help information."""
        fields = []

        commands = self.__build_command_list()

        if not command:
            fields.append(("\u200b", "**COMMANDS**"))
            fields.extend([(f"**/{x.name}**", x.description) for x in commands])
            await present_embed(
                ctx,
                title="Valentina Noir Help",
                description="Use Valentina's commands by typing `/<command> <subcommand>`\n\nUse `/help <command>` for detailed help information on each command below.\n\n",
                fields=fields,
                level="info",
                ephemeral=True,
            )
        else:
            found_command = False
            for cmd in commands:
                if cmd.name == command:
                    found_command = True
                    fields.append(("\u200b", "**COMMAND**"))
                    fields.append((f"**/{cmd.name} [subcommand]**", cmd.description))
                    fields.append(("\u200b", "**SUBCOMMANDS**"))
                    for c in sorted(cmd.subcommands, key=lambda x: x.name):
                        if not hasattr(c, "subcommands"):
                            fields.append((f"**{c.name}**", c.description))
                        if hasattr(c, "subcommands"):
                            for x in sorted(c.subcommands, key=lambda x: x.name):
                                fields.append((f"**{c.name} {x.name}**", x.description))
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
                description="Use Valentina's commands by typing `/<command> <subcommand>`\n\nUse `/help <command>` for detailed help information on each command below.\n\n",
                fields=fields,
                level="info",
                ephemeral=True,
            )

    @help.command(name="guide", description="A guide on how to use Valentina Noir")
    async def readme(self, ctx: discord.ApplicationContext) -> None:
        """A walkthrough of Valentina Noir."""
        owners = [
            ctx.guild.get_member(int(x)).display_name
            for x in CONFIG["VALENTINA_OWNER_IDS"].split(",")
        ]

        page1 = dedent(
            """

            **VALENTINA NOIR GUIDE**

            This guide will walk you through how to use Valentina Noir. It is split into the following sections:

            1. Core concepts
            2. Character creation
            3. Character management
            4. Gameplay
            5. Chronicles
            6. Additional information

            For a quick command reference, use `/help commands` to see a list of commands, and `/help commands <command>` to see more information about a specific command.
        """
        )

        page2 = dedent(
            """

            **CORE CONCEPTS**

            Valentina Noir manages characters and their stats and provides easy access to rolling dice during gameplay.

            **__Before Gameplay__**
            Prior to starting gameplay, create a character using `/character create`. This will create a character sheet for you and store it in the database. You can create as many characters as you like.

            **__During Gameplay__**
            Claim a character to your discord user using `/character claim`. This will allow you to roll dice for that character. You can only claim one character at a time.  Most commands require you to have a character claimed.

            Macros can be created using `/macro create`. Macros allow you to create a shortcut for a dice roll. For example, you can create a macro called `pa` (perception/alertness) which would roll your perception and alertness stats. You can then roll this macro using `/roll macro pa`.

            _Note: Macros are tied to users, not characters. You can use the same macro for all of your characters._

            **__After Gameplay__**
            Add or spend experience points using `/xp`. This will allow you to level up your character and increase their stats. You can also use `/character unclaim` to unclaim your character and allow another user to claim it.

            """
        )

        page3 = dedent(
            """

            **CHARACTER CREATION**

            Characters are created using `/character create`. This will create a character sheet for you and store it in the database. You can create as many characters as you like.

            *Note: When creating a character, you can choose to use `Quick Mode` which reduces the number of questions asked during character creation. Quick mode is recommended if you are short on time.*

            **IMPORTANT: Valentina does not currently support rolling for character stats. You will need to roll your stats manually and write them on a character sheet. Have that sheet in front of you when creating your character.**

            Running `/character create` will prompt you for the stats for your character. You can enter the stats manually, or use the `Quick Mode` option to reduce the number of questions asked.

            Traits and abilities not listed in the questions, can be added after the fact with `/character add trait`.

            Additional information not linked to dice rolling can also be added to your character sheet using `/character add custom_section`.

            Lastly, an optional biography can be added to your character sheet using `/character update bio`.

            """
        )

        page4 = dedent(
            """

            **CHARACTER MANAGEMENT**

            **__Claiming a character__**
            Claim a character to your discord user using `/character claim`. This will allow you to roll dice for that character, update stats, add custom traits, etc. You can only claim one character at a time.

            *Note: Most commands require you to have a character claimed.*

            **__Unclaiming a character__**
            Unclaim your character using `/character unclaim`. This will allow another user to claim the character.

            **__Updating character stats__**
            Update a the value of stat using `/character update <stat> <value>`.

            For example, `/character update strength 3` will set your character's strength to 3.

            **IMPORTANT: This is useful for correcting errors in character creation, but should not be used to increase stats. To increase stats, use `/character xp`.**

            **__Adding custom traits__**
            Add a custom trait to your character using `/character add trait`. This will allow you to add a custom trait to your character sheet.

            For example, you can add a custom trait called `Fishing` and set the value to `3`. This will allow you to roll dice against your fishing trait using `/roll traits fishing`.

            **__Adding custom information__**
            Add custom information to your character sheet using `/character add custom_section`.

            For example, you can add a custom section called `Gear` and add a list of items to it. This will allow you to view your gear using when viewing your character sheet using `/character sheet`.

            """
        )

        page5 = dedent(
            """
            **GAMEPLAY**

            **__Rolling dice__**
            All dice rolls are done using `/roll`. You can roll against stats, traits, macros, or simply roll a number of dice.

            When rolling D10s, a difficulty can be added to the roll with a default value of `6`.  Botches, failures, successes, and critical success will be automatically calculated.

            **__Rolling against stats__**
            Roll against stats using `/roll traits <stat1> <stat2>`. This will compute the number of dice to roll from the values of the traits.

            For example, `/roll trait dexterity dodge` will roll a dodge.

            **__Rolling with macros__**
            Roll a macro using `/roll macro <macro_name>`.

            For example, `/roll macro pa` will roll a macro called `pa`. The number of dice are computed based on the skills associated with the macro.

            **__Rolling D10s__**
            Use `/dice throw` to roll a number of D10s with an optional difficulty.

            For example, `/dice throw 5 8` will roll 5 D10s with a difficulty of 8.

            **__Rolling arbitrary dice__**
            To roll dice of any size, use `/dice roll simple <pool> <dice size>`.

            For example, `/dice roll simple 3 6` will roll 3 D6s.

            """
        )

        page6 = dedent(
            """

            **CHRONICLES**
            Chronicles are storylines that have multiple chapters and span multiple gaming sessions.  You can think of a chronicle as a campaign.  Chronicles have chapters, NPCs, and notes associated with them to help you keep track of the story.

            List all chronicles using `/chronicle list`.

            View a chronicle using `/chronicle view`. This will show you all of the chapters, NPCs, and notes associated with the chronicle.

            **__Creating a chronicle__**
            Create a chronicle using `/chronicle create`. This will create a new chronicle.

            **__Set a chronicle as active__**
            Set a chronicle as active using `/chronicle set_active`. This will set the chronicle as active and allow you to add chapters, NPCs, and notes to it.

            **__Chapters__**
            Chapters are created using `/chronicle chapter create`.  Chapters are used to keep track of the story.  You can add notes to chapters using `/chronicle note create [chapter]`.

            List all chapters using `/chronicle chapter list`.

            **__NPCs__**
            NPCs are created using `/chronicle npc create`.  NPCs are used to keep track of non-player characters in the story.  View all NPCs for a chronicle with `/chronicle npc list`.

            **__Notes__**
            Notes are created using `/chronicle note create`.  Notes are used to keep track of important information in the story.  View all notes for a chronicle with `/chronicle note list`.

            You can attach a note to a specific chapter using `/chronicle note create [chapter]`.
            """
        )

        page7 = dedent(
            f"""

        **ADDITIONAL INFORMATION**
        For bug reports, feature requests, or general questions, please add an issue to the [Valentina Noir GitHub repository](https://github.com/natelandau/valentina).  Or reach out to the developer {' ,'.join(owners)}.

        You are running Valentina Noir version `{__version__}`.

        """
        )

        paginator = pages.Paginator(pages=[page1, page2, page3, page4, page5, page6, page7])
        paginator.remove_button("first")
        paginator.remove_button("last")

        # Send the paginator as a dm to the user
        await paginator.respond(ctx.interaction, target=ctx.author)

        # If successful, we post this message in the originating channel
        await ctx.respond(
            "Please check your DMs! The Guide to Valentina Noir has been sent to you.",
            ephemeral=True,
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Help(bot))
