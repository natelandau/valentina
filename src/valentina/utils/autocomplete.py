"""Reusable autocomplete options for cogs and commands."""

from typing import cast

import discord
from beanie.operators import And
from discord.commands import OptionChoice

from valentina.constants import (
    MAX_OPTION_LIST_SIZE,
    CharacterConcept,
    CharClass,
    Emoji,
    RNGCharLevel,
    TraitCategory,
    VampireClan,
)
from valentina.models import Campaign, Character, Guild, User
from valentina.models.aws import AWSService
from valentina.models.bot import Valentina
from valentina.utils.changelog_parser import ChangelogParser
from valentina.utils.helpers import truncate_string

MAX_OPTION_LENGTH = 99


async def select_changelog_version_1(ctx: discord.AutocompleteContext) -> list[str]:
    """Populate the autocomplete for the version option. This is for the first of two options."""
    bot = cast(Valentina, ctx.bot)
    possible_versions = ChangelogParser(bot).list_of_versions()

    return [version for version in possible_versions if version.startswith(ctx.value)][
        :MAX_OPTION_LIST_SIZE
    ]


async def select_changelog_version_2(ctx: discord.AutocompleteContext) -> list[str]:
    """Populate the autocomplete for the version option. This is for the second of two options."""
    bot = cast(Valentina, ctx.bot)
    possible_versions = ChangelogParser(bot).list_of_versions()

    return [version for version in possible_versions if version.startswith(ctx.value)][
        :MAX_OPTION_LIST_SIZE
    ]


async def select_chapter(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Populate the autocomplete for the chapter option.

    This function fetches the active campaign from the bot's campaign service,
    fetches all chapters of that campaign, sorts them by chapter number,
    and filters them based on the starting string of the chapter name.
    If the number of chapters reaches a maximum size, it stops appending more chapters.
    If there is no active campaign, it returns a list with a single string "No active campaign".

    Args:
        ctx (discord.AutocompleteContext): The context in which the function is called.

    Returns:
        list[str]: A list of strings representing the chapters.
    """
    # Fetch the active campaign
    guild = await Guild.get(ctx.interaction.guild.id, fetch_links=True)
    active_campaign = await guild.fetch_active_campaign()

    if not active_campaign:
        return [OptionChoice("No active campaign", 1000)]

    choices = [
        OptionChoice(f"{chapter.number}. {chapter.name}", index)
        for index, chapter in enumerate(active_campaign.chapters)
        if chapter.name.lower().startswith(ctx.options["chapter"].lower())
    ][:MAX_OPTION_LIST_SIZE]

    return choices if choices else [OptionChoice("No chapers", 1000)]


async def select_char_class(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of available character classes.

    This function fetches the available character classes, sorts them by name,
    and filters them based on the starting string of the class name.
    If the number of classes reaches a maximum size, it stops appending more classes.

    Args:
        ctx (discord.AutocompleteContext): The context in which the function is called.

    Returns:
        list[OptionChoice]: A list of available character class names.
    """
    # Filter and return character class names
    return [
        OptionChoice(c.value.name, c.name)
        for c in CharClass.playable_classes()
        if c.value.name and c.value.name.lower().startswith(ctx.options["char_class"].lower())
    ][:MAX_OPTION_LIST_SIZE]


async def select_char_concept(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of available character concepts.

    This function fetches the available character concepts, sorts them by name,
    and filters them based on the starting string of the argument.
    If the number of concepts reaches a maximum size, it stops appending more classes.

    Args:
        ctx (discord.AutocompleteContext): The context in which the function is called.

    Returns:
        list[OptionChoice]: A list of available character concepts.
    """
    # Filter and return character class names
    return [
        OptionChoice(c.name.title(), c.name)
        for c in CharacterConcept
        if c.name and c.name.lower().startswith(ctx.options["concept"].lower())
    ][:MAX_OPTION_LIST_SIZE]


async def select_char_level(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of available character levels.

    This function fetches the available character levels, sorts them by name,
    and filters them based on the starting string of the argument.

    Args:
        ctx (discord.AutocompleteContext): The context in which the function is called.

    Returns:
        list[OptionChoice]: A list of available character levels.
    """
    # Filter and return character class levels
    return [
        OptionChoice(c.name.title(), c.name)
        for c in RNGCharLevel
        if c.name.lower().startswith(ctx.options["level"].lower())
    ][:MAX_OPTION_LIST_SIZE]


async def select_char_trait(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of traits and their index for a character.

    This function fetches the active character from the bot's user service,
    retrieves the argument (either "trait" or "trait_one") from the context options,
    and filters the character's traits based on the starting string of the trait name.
    If the number of traits reaches a maximum size, it stops appending more traits.
    If there is no active character, it returns a list with a single string "No active character".

    Args:
        ctx (discord.AutocompleteContext): The context in which the function is called.

    Returns:
        list[OptionChoice]: A list of available names and their index in character.traits.
    """
    # Fetch the active character
    user_object = await User.get(ctx.interaction.user.id, fetch_links=True)
    if not (
        active_character := await user_object.active_character(
            ctx.interaction.guild, raise_error=False
        )
    ):
        return [OptionChoice("No active character", 0)]

    # Determine the option to retrieve the argument
    argument = ctx.options.get("trait") or ctx.options.get("trait_one") or ""

    # Filter and return the character's traits
    return [
        OptionChoice(t.name, i)
        for i, t in enumerate(active_character.traits)
        if t.name.lower().startswith(argument.lower())
    ][:MAX_OPTION_LIST_SIZE]


async def select_char_trait_two(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of available common and custom traits for a character.

    This function fetches the active character from the bot's user service,
    retrieves the argument ("trait_two") from the context options,
    and filters the character's traits based on the starting string of the trait name.
    If the number of traits reaches a maximum size, it stops appending more traits.
    If there is no active character, it returns a list with a single string "No active character".

    Args:
        ctx (discord.AutocompleteContext): The context in which the function is called.

    Returns:
        list[OptionChoice]: A list of available trait names and their index in character.traits.
    """
    user_object = await User.get(ctx.interaction.user.id, fetch_links=True)
    if not (
        active_character := await user_object.active_character(
            ctx.interaction.guild, raise_error=False
        )
    ):
        return [OptionChoice("No active character", 0)]

    # Filter and return the character's traits
    return [
        OptionChoice(t.name, i)
        for i, t in enumerate(active_character.traits)
        if t.name.lower().startswith(ctx.options["trait_two"].lower())
    ][:MAX_OPTION_LIST_SIZE]


async def select_campaign(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of available campaigns for the guilds.

    Args:
        ctx (discord.AutocompleteContext): The context in which the function is called.

    Returns:
        list[OptionChoice]: A list of available campaign names and db ids.
    """
    return [
        OptionChoice(c.name, str(c.id))
        for c in await Campaign.find(Campaign.guild == ctx.interaction.guild.id).to_list()
        if c.name.lower().startswith(ctx.options["campaign"].lower())
    ][:MAX_OPTION_LIST_SIZE]


async def select_custom_section(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Fetches and provides a list of the active character's custom sections.

    This function attempts to retrieve an active character for the user, filtering on
    the characters custom sections and displaying a title and id combination. If there
    are too many sections, appropriate instructions are displayed instead.

    Args:
        ctx (discord.AutocompleteContext): The autocomplete context provided by discord.

    Returns:
        list[OptionChoice]: A list of option choices for discord selection
                            containing title and index pairs.
    """
    # Fetch the active character
    user_object = await User.get(ctx.interaction.user.id, fetch_links=True)
    active_character = await user_object.active_character(ctx.interaction.guild, raise_error=False)

    if not active_character:
        return [OptionChoice("No active character", "")]

    # Create a list of tuples containing display title and list index for each custom section
    options = [
        OptionChoice(truncate_string(section.title, MAX_OPTION_LENGTH), str(index))
        for index, section in enumerate(active_character.sheet_sections)
        if section.title.lower().startswith(ctx.value.lower())
    ]
    if len(options) > MAX_OPTION_LIST_SIZE:
        instructions = "Keep typing ..." if ctx.value else "Start typing..."
        return [OptionChoice(f"Too many sections to display. {instructions}", "")]

    return options


async def select_country(ctx: discord.AutocompleteContext) -> list[OptionChoice]:  # noqa: ARG001
    """Generate a list of available countries for autocomplete.

    This function creates a predefined list of countries and their corresponding codes,
    and returns a list of OptionChoice objects to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects for the autocomplete list.
    """
    return [
        OptionChoice("English", "us,gb"),
        OptionChoice("German", "de"),
        OptionChoice("Spanish", "es,mx"),
        OptionChoice("French", "fr"),
        OptionChoice("Indian", "in"),
        OptionChoice("Scandinavian", "dk,no"),
        OptionChoice("Portuguese", "br"),
        OptionChoice("Slavic", "rs,ua"),
    ]


async def select_aws_object_from_guild(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Populate the autocomplete list for the aws_object option based on the user's input."""
    aws_svc = AWSService()

    guild_prefix = f"{ctx.interaction.guild.id}/"

    return [OptionChoice(x.strip(guild_prefix), x) for x in aws_svc.list_objects(guild_prefix)][
        :MAX_OPTION_LIST_SIZE
    ]


async def select_macro(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Populate a select list with a user's macros based on the input.

    This function fetches the macros for a given user and guild, filters them based on the user's input,
    and returns a list of OptionChoice objects to populate a select list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects to populate the select list.
    """
    user_object = await User.get(ctx.interaction.user.id)

    macros = [(macro, index) for index, macro in enumerate(user_object.macros)]

    # Create OptionChoice objects
    options = [
        OptionChoice(f"{macro.abbreviation} ({macro.name})", index)
        for macro, index in macros
        if macro.abbreviation.lower().startswith(ctx.options["macro"].lower())
    ]

    # Check if the number of options exceeds the maximum allowed
    if len(options) >= MAX_OPTION_LIST_SIZE:
        instructions = "Keep typing ..." if ctx.value else "Start typing a name."
        return [OptionChoice(f"Too many macros to display. {instructions}", "")]

    return options


async def select_note(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Populate the autocomplete list for the note option based on the user's input.

    This function fetches all notes for the active campaign, filters them based on the user's input,
    and returns a list of note IDs and names to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[OptionChoice]: A list of note IDs and names for the autocomplete list.
    """
    # Fetch the active campaign
    guild = await Guild.get(ctx.interaction.guild.id, fetch_links=True)
    active_campaign = await guild.fetch_active_campaign()

    if not active_campaign:
        return [OptionChoice("No active campaign", 1000)]

    choices = [
        OptionChoice(note.name, index)
        for index, note in enumerate(active_campaign.notes)
        if note.name.lower().startswith(ctx.options["note"].lower())
    ][:MAX_OPTION_LIST_SIZE]

    return choices if choices else [OptionChoice("No notes", 1000)]


async def select_npc(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Populate the autocomplete list for the NPC option based on the user's input.

    This function fetches all NPCs for the active campaign, filters them based on the user's input,
    and returns a list of NPC names to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[OptionChoice]: A list of NPC names and associated ids for the autocomplete list.
    """
    # Fetch the active campaign
    guild = await Guild.get(ctx.interaction.guild.id, fetch_links=True)
    active_campaign = await guild.fetch_active_campaign()

    if not active_campaign:
        return [OptionChoice("No active campaign", 1000)]

    npc_choices = [
        OptionChoice(npc.name, index)
        for index, npc in enumerate(active_campaign.npcs)
        if npc.name.lower().startswith(ctx.options["npc"].lower())
    ][:MAX_OPTION_LIST_SIZE]

    return npc_choices if npc_choices else [OptionChoice("No npcs", 1000)]


async def select_player_character(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of the user's available characters for autocomplete.

    This function fetches all alive player characters for the user, filters them based on the user's input, and returns a list of OptionChoice objects to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects for the autocomplete list.
    """
    user_object = await User.get(ctx.interaction.user.id, fetch_links=True)

    # Prepare character data
    all_chars = [
        (
            f"{character.name}" if character.is_alive else f"{Emoji.DEAD.value} {character.name}",
            character.id,
        )
        for character in user_object.all_characters(ctx.interaction.guild)
        if character.type_player
    ]

    # Generate options
    options = [
        OptionChoice(name, str(char_id))
        for name, char_id in sorted(all_chars)
        if name.lower().startswith(ctx.value.lower())
    ][:MAX_OPTION_LIST_SIZE]

    return options if options else [OptionChoice("No characters available", "")]


async def select_storyteller_character(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of available storyteller characters for autocomplete.

    This function fetches all storyteller characters, filters them based on the user's input, and returns a list of OptionChoice objects to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects for the autocomplete list.
    """
    # Prepare character data
    all_chars = [
        (
            f"{character.name}" if character.is_alive else f"{Emoji.DEAD.value} {character.name}",
            character.id,
        )
        async for character in Character.find_many(
            Character.guild == ctx.interaction.guild.id,
            Character.type_storyteller == True,  # noqa: E712
        )
    ]

    # Generate options
    options = [
        OptionChoice(name, str(char_id))
        for name, char_id in sorted(all_chars)
        if name.lower().startswith(ctx.value.lower())
    ][:MAX_OPTION_LIST_SIZE]

    return options if options else [OptionChoice("No characters available", "")]


async def select_any_player_character(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of all type_player characters in the guild for autocomplete.

    This function fetches all player characters for the guild, filters them based on the user's input,
    and returns a list of OptionChoice objects to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects for the autocomplete list.
    """
    # Fetch and prepare player characters
    all_chars_owners = sorted(
        [
            (x, await User.get(x.user_owner))
            async for x in Character.find(
                And(
                    Character.guild == ctx.interaction.guild.id,
                    Character.type_player == True,  # noqa: E712
                    Character.is_alive == True,  # noqa: E712
                ),
                fetch_links=True,
            )
        ],
        key=lambda x: x[0].name,
    )

    options = [
        OptionChoice(
            f"{character.name} [@{owner.name}]"
            if character.is_alive
            else f"{Emoji.DEAD.value} {character.name} [@{owner.name}]",
            str(character.id),
        )
        for character, owner in all_chars_owners
    ]

    # Check if the number of options exceeds the maximum allowed
    if len(options) >= MAX_OPTION_LIST_SIZE:
        instructions = "Keep typing ..." if ctx.value else "Start typing a name."
        return [OptionChoice(f"Too many characters to display. {instructions}", "")]

    return options if options else [OptionChoice("No characters available", "")]


async def select_trait_from_char_option(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of available traits for a character.

    This function takes a character id defined in a previous discord command option, and fetches all the common and custom traits available for that character to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[str]: A list of trait names for the autocomplete list.
    """
    # Determine the argument based on the Discord option
    argument = ctx.options.get("trait") or ctx.options.get("trait_one") or ""

    # Fetch the character from the ctx options
    character = await Character.get(ctx.options["character"], fetch_links=True)

    # Fetch and filter traits
    # Filter and return the character's traits
    # We pass the character id before the trait name for the validation to work
    # Filter and return the character's traits

    options = [
        OptionChoice(t.name, str(t.id))
        for t in character.traits
        if t.name.lower().startswith(argument.lower())
    ][:MAX_OPTION_LIST_SIZE]

    return options if options else [OptionChoice("No traits", "")]


async def select_trait_from_char_option_two(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of available traits for a storyteller character.

    This function fetches all common and custom traits from the database, filters them based on the user's input, and returns a list of trait names to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[str]: A list of trait names for the autocomplete list.
    """
    # Fetch the character from the ctx options
    character = await Character.get(ctx.options["character"], fetch_links=True)

    # Fetch and filter traits
    # Filter and return the character's traits
    options = [
        OptionChoice(t.name, str(t.id))
        for t in character.traits
        if t.name.lower().startswith(ctx.options["trait_two"].lower())
    ][:MAX_OPTION_LIST_SIZE]

    return options if options else [OptionChoice("No traits", "")]


async def select_trait_category(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of available trait categories for autocomplete.

    This function fetches all trait categories from the database, filters them based on the user's input, and returns a list of trait category names to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[str]: A list of trait category names for the autocomplete list.
    """
    return [
        OptionChoice(category.name.title(), category.name)
        for category in TraitCategory
        if category.name.startswith(ctx.options["category"].upper())
    ][:MAX_OPTION_LIST_SIZE]


async def select_vampire_clan(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of available vampire clans for autocomplete.

    This function fetches all vampire clans from the database, filters them based on the user's input,
    and returns a list of vampire clan names to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[str]: A list of vampire clan names for the autocomplete list.
    """
    return [
        OptionChoice(c.name.title(), c.name)
        for c in VampireClan
        if c.name.startswith(ctx.options["vampire_clan"].upper())
    ][:MAX_OPTION_LIST_SIZE]
