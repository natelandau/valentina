"""Reusable autocomplete options for cogs and commands."""

from typing import cast

import discord
from discord.commands import OptionChoice

from valentina.constants import (
    MAX_OPTION_LIST_SIZE,
    CharClassType,
    CharConcept,
    Emoji,
    RNGCharLevel,
    TraitCategories,
    VampireClanType,
)
from valentina.models.bot import Valentina
from valentina.models.db_tables import Character
from valentina.utils import errors
from valentina.utils.helpers import truncate_string

MAX_OPTION_LENGTH = 99


async def select_changelog_version_1(ctx: discord.AutocompleteContext) -> list[str]:
    """Populate the autocomplete for the version option. This is for the first of two options."""
    bot = cast(Valentina, ctx.bot)
    possible_versions = bot.guild_svc.fetch_changelog_versions()

    return [version for version in possible_versions if version.startswith(ctx.value)][
        :MAX_OPTION_LIST_SIZE
    ]


async def select_changelog_version_2(ctx: discord.AutocompleteContext) -> list[str]:
    """Populate the autocomplete for the version option. This is for the second of two options."""
    bot = cast(Valentina, ctx.bot)
    possible_versions = bot.guild_svc.fetch_changelog_versions()

    return [version for version in possible_versions if version.startswith(ctx.value)][
        :MAX_OPTION_LIST_SIZE
    ]


async def select_chapter(ctx: discord.AutocompleteContext) -> list[str]:
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
    bot = cast(Valentina, ctx.bot)
    try:
        # Fetch the active campaign
        campaign = bot.campaign_svc.fetch_active(ctx)
    except errors.NoActiveCampaignError:
        return ["No active campaign"]

    # Fetch, sort and filter the chapters
    return [
        f"{chapter.chapter_number}: {chapter.name}"
        for chapter in sorted(
            bot.campaign_svc.fetch_all_chapters(campaign=campaign),
            key=lambda c: c.chapter_number,
        )
        if chapter.name.lower().startswith(ctx.options["chapter"].lower())
    ][:MAX_OPTION_LIST_SIZE]


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
        OptionChoice(c.value["name"], c.name)
        for c in CharClassType
        if c.value["name"] and c.value["name"].lower().startswith(ctx.options["char_class"].lower())
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
        OptionChoice(c.value["name"], c.name)
        for c in CharConcept
        if c.value["name"] and c.value["name"].lower().startswith(ctx.options["concept"].lower())
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


async def select_char_trait(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of available common and custom traits for a character.

    This function fetches the active character from the bot's user service,
    retrieves the argument (either "trait" or "trait_one") from the context options,
    and filters the character's traits based on the starting string of the trait name.
    If the number of traits reaches a maximum size, it stops appending more traits.
    If there is no active character, it returns a list with a single string "No active character".

    Args:
        ctx (discord.AutocompleteContext): The context in which the function is called.

    Returns:
        list[str]: A list of available common and custom trait names.
    """
    bot = cast(Valentina, ctx.bot)
    # Fetch the active character
    try:
        character = await bot.user_svc.fetch_active_character(ctx)
    except errors.NoActiveCharacterError:
        return ["No active character"]

    # Determine the option to retrieve the argument
    argument = ctx.options.get("trait") or ctx.options.get("trait_one") or ""

    # Filter and return the character's traits
    return [t.name for t in character.traits_list if t.name.lower().startswith(argument.lower())][
        :MAX_OPTION_LIST_SIZE
    ]


async def select_char_trait_two(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of available common and custom traits for a character.

    This function fetches the active character from the bot's user service,
    retrieves the argument ("trait_two") from the context options,
    and filters the character's traits based on the starting string of the trait name.
    If the number of traits reaches a maximum size, it stops appending more traits.
    If there is no active character, it returns a list with a single string "No active character".

    Args:
        ctx (discord.AutocompleteContext): The context in which the function is called.

    Returns:
        list[str]: A list of available common and custom trait names.
    """
    bot = cast(Valentina, ctx.bot)
    # Fetch the active character
    try:
        character = await bot.user_svc.fetch_active_character(ctx)
    except errors.NoActiveCharacterError:
        return ["No active character"]

    # Filter and return the character's traits
    return [
        t.name
        for t in character.traits_list
        if t.name.lower().startswith(ctx.options["trait_two"].lower())
    ][:MAX_OPTION_LIST_SIZE]


async def select_campaign(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of available campaigns.

    This function fetches all campaigns from the bot's campaign service,
    filters them based on the starting string of the campaign name,
    and returns a list of campaign names.
    If the number of campaigns reaches a maximum size, it stops appending more campaigns.

    Args:
        ctx (discord.AutocompleteContext): The context in which the function is called.

    Returns:
        list[str]: A list of available campaign names.
    """
    bot = cast(Valentina, ctx.bot)
    return [
        c.name
        for c in bot.campaign_svc.fetch_all(ctx)
        if c.name.lower().startswith(ctx.options["campaign"].lower())
    ][:MAX_OPTION_LIST_SIZE]


async def select_custom_section(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Fetches and provides a list of the user's custom sections.

    This function attempts to retrieve an active character for the user, filtering on
    the characters custom sections and displaying a title and id combination. If there
    are too many sections, appropriate instructions are displayed instead.

    Args:
        ctx (discord.AutocompleteContext): The autocomplete context provided by discord.

    Returns:
        list[OptionChoice]: A list of option choices for discord selection
                            containing title and id pairs.
    """
    bot = cast(Valentina, ctx.bot)
    try:
        # Fetch active character
        character = await bot.user_svc.fetch_active_character(ctx)
    except errors.NoActiveCharacterError:
        # Return descriptive OptionChoice in case of absence
        return [OptionChoice("No active character", "")]

    # Create a list of tuples containing display title and ids for each custom section
    possible_sections = [
        (truncate_string(section.title, MAX_OPTION_LENGTH), str(section.id))
        for section in character.custom_sections
    ]

    # Sort the possible options and filtering to match initial string in ctx.value
    options = [
        OptionChoice(display_title, title)
        for display_title, title in sorted(possible_sections)
        if display_title.casefold().startswith((ctx.value or "").casefold())
    ]

    # Construct appropriate message if options are too many and  it
    if len(options) > MAX_OPTION_LIST_SIZE:
        instructions = "Keep typing ..." if ctx.value else "Start typing..."
        return [OptionChoice(f"Too many sections to display. {instructions}", "")]

    return options


async def select_custom_trait(ctx: discord.AutocompleteContext) -> list[str]:
    """Return a list containing names of active character's custom traits filtered based on initial string in user's suggestion.

    Attempt to retrieve an active character for the user. Once obtained, filter the
    custom traits and spill out their names that match the initial string in
    `ctx.options["trait"]`. Stop adding names when the maximum limit is met or
    all traits are processed.

    Args:
        ctx (discord.AutocompleteContext): The autocomplete context from Discord.

    Returns:
        List[str]: List containing names of filtered traits up to a predefined limit.
                   If no character is active, return a list with 'No active character'.
    """
    bot = cast(Valentina, ctx.bot)
    # Attempt to fetch the active character
    try:
        character = await bot.user_svc.fetch_active_character(ctx)
    except errors.NoActiveCharacterError:
        return ["No active character"]

    # Generate list of trait names that start with the string in `ctx.options["trait"]`, up to MAX_OPTION_LIST_SIZE
    return [
        trait.name
        for trait in character.custom_traits
        if trait.name.lower().startswith(ctx.options["trait"].lower())
    ][:MAX_OPTION_LIST_SIZE]


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
        OptionChoice("United States", "us"),
        OptionChoice("African", "ng,ke,za"),
        OptionChoice("Arabia", "da,mn,ta,jo,tn,ma,eg"),
        OptionChoice("Asian", "cn,jp,kr"),
        OptionChoice("Brazil", "br"),
        OptionChoice("France", "fr"),
        OptionChoice("Germany", "de"),
        OptionChoice("Greece", "gr"),
        OptionChoice("India", "in"),
        OptionChoice("Italy", "it"),
        OptionChoice("Mexico", "mx"),
        OptionChoice("Russia", "ru"),
        OptionChoice("Scaninavia", "nl,se,no,dk,fi"),
        OptionChoice("South American", "ar,cl,co,pe,ve"),
        OptionChoice("Spain", "es"),
        OptionChoice("Turkey", "tr"),
    ]


async def select_aws_object_from_guild(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Populate the autocomplete list for the aws_object option based on the user's input."""
    bot = cast(Valentina, ctx.bot)
    guild_prefix = f"{ctx.interaction.guild.id}/"

    return [OptionChoice(x.strip(guild_prefix), x) for x in bot.aws_svc.list_objects(guild_prefix)][
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
    bot = cast(Valentina, ctx.bot)
    user = await bot.user_svc.fetch_user(ctx)

    # Filter macros based on user input
    filtered_macros = [
        macro
        for macro in bot.macro_svc.fetch_macros(user)
        if macro.abbreviation.lower().startswith(ctx.options["macro"].lower())
    ]

    # Create OptionChoice objects
    options = [
        OptionChoice(f"{macro.abbreviation} ({macro.name})", str(macro.id))
        for macro in filtered_macros
    ]

    # Check if the number of options exceeds the maximum allowed
    if len(options) >= MAX_OPTION_LIST_SIZE:
        instructions = "Keep typing ..." if ctx.value else "Start typing a name."
        return [OptionChoice(f"Too many characters to display. {instructions}", "")]

    return options


async def select_note(ctx: discord.AutocompleteContext) -> list[str]:
    """Populate the autocomplete list for the note option based on the user's input.

    This function fetches all notes for the active campaign, filters them based on the user's input,
    and returns a list of note IDs and names to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[str]: A list of note IDs and names for the autocomplete list.
    """
    bot = cast(Valentina, ctx.bot)
    try:
        # Fetch the active campaign
        campaign = bot.campaign_svc.fetch_active(ctx)
    except errors.NoActiveCampaignError:
        return ["No active campaign"]

    # Fetch and filter notes
    notes = [
        f"{note.id}: {note.name}"
        for note in bot.campaign_svc.fetch_all_notes(campaign)
        if note.name.lower().startswith(ctx.options["note"].lower())
    ][:MAX_OPTION_LIST_SIZE]

    return notes if notes else ["No Notes"]


async def select_npc(ctx: discord.AutocompleteContext) -> list[str]:
    """Populate the autocomplete list for the NPC option based on the user's input.

    This function fetches all NPCs for the active campaign, filters them based on the user's input,
    and returns a list of NPC names to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[str]: A list of NPC names for the autocomplete list.
    """
    bot = cast(Valentina, ctx.bot)
    try:
        campaign = bot.campaign_svc.fetch_active(ctx)
    except errors.NoActiveCampaignError:
        return ["No active campaign"]

    # Fetch and filter NPCs
    npcs = [
        npc.name
        for npc in bot.campaign_svc.fetch_all_npcs(campaign=campaign)
        if npc.name.lower().startswith(ctx.options["npc"].lower())
    ][:MAX_OPTION_LIST_SIZE]

    return npcs if npcs else ["No NPCs"]


async def select_player_character(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of the user's available characters for autocomplete.

    This function fetches all alive player characters for the user, filters them based on the user's input, and returns a list of OptionChoice objects to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects for the autocomplete list.
    """
    bot = cast(Valentina, ctx.bot)

    # Prepare character data
    all_chars = [
        (
            f"{character.name}" if character.is_alive else f"{Emoji.DEAD.value} {character.name}",
            character.id,
        )
        for character in await bot.user_svc.fetch_player_characters(ctx)
    ]

    # Perform case-insensitive search
    name_search = ctx.value.casefold() if ctx.value else ""

    # Generate options
    options = [
        OptionChoice(name, str(char_id))
        for name, char_id in sorted(all_chars)
        if name.casefold().startswith(name_search)
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
    bot = cast(Valentina, ctx.bot)
    all_chars = [
        (f"{character.name}", character.id)
        for character in bot.char_svc.fetch_all_storyteller_characters(ctx)
    ]

    # Perform case-insensitive search
    name_search = ctx.value.casefold() if ctx.value else ""

    # Generate options
    options = [
        OptionChoice(name, str(char_id))
        for name, char_id in sorted(all_chars)
        if name.casefold().startswith(name_search)
    ][:MAX_OPTION_LIST_SIZE]

    return options if options else [OptionChoice("No characters available", "")]


async def select_any_character(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of all characters for the guild, including both player and storyteller characters.

    This function fetches all characters for the guild, filters them based on the user's input,
    and returns a list of OptionChoice objects to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects for the autocomplete list.
    """
    bot = cast(Valentina, ctx.bot)
    # Initialize options list
    options = []
    # Fetch all characters
    storyteller_chars = [
        (
            f"{character.full_name} ({character.char_class.name})"
            if character.is_alive
            else f"{Emoji.DEAD.value} {character.full_name} ({character.char_class.name})",
            character.id,
        )
        for character in bot.char_svc.fetch_all_storyteller_characters(ctx)
    ]
    player_chars = [
        (f"{character.name}", character.id)
        for character in bot.char_svc.fetch_all_player_characters(ctx)
    ]

    # Combine both lists
    all_chars = storyteller_chars + player_chars

    # Perform case-insensitive search
    name_search = ctx.value.casefold() if ctx.value else ""

    # Generate options
    options = [
        OptionChoice(
            f"{name} [{'Storyteller' if char_id in [char[1] for char in storyteller_chars] else 'Player'}]",
            str(char_id),
        )
        for name, char_id in sorted(all_chars)
        if name.casefold().startswith(name_search)
    ]

    # Check if the number of options exceeds the maximum allowed
    if len(options) >= MAX_OPTION_LIST_SIZE:
        instructions = "Keep typing ..." if ctx.value else "Start typing a name."
        return [OptionChoice(f"Too many characters to display. {instructions}", "")]

    return options if options else [OptionChoice("No characters available", "")]


async def select_any_player_character(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of all player characters in the guild for autocomplete.

    This function fetches all player characters for the guild, filters them based on the user's input,
    and returns a list of OptionChoice objects to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects for the autocomplete list.
    """
    bot = cast(Valentina, ctx.bot)

    # Fetch and prepare player characters
    all_chars = [
        (
            f"{character.name} [@{character.owned_by.data['display_name']}]"
            if character.is_alive
            else f"{Emoji.DEAD.value} {character.name} [@{character.owned_by.data['display_name']}]",
            character.id,
        )
        for character in bot.char_svc.fetch_all_player_characters(ctx)
    ]

    # Perform case-insensitive search
    name_search = ctx.value.casefold() if ctx.value else ""

    # Generate options
    options = [
        OptionChoice(name, str(char_id))
        for name, char_id in sorted(all_chars)
        if name.casefold().startswith(name_search)
    ]

    # Check if the number of options exceeds the maximum allowed
    if len(options) >= MAX_OPTION_LIST_SIZE:
        instructions = "Keep typing ..." if ctx.value else "Start typing a name."
        return [OptionChoice(f"Too many characters to display. {instructions}", "")]

    return options if options else [OptionChoice("No characters available", "")]


async def select_trait_from_char_option(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of available traits for a storyteller character.

    This function takes a character id defined in a previous discord command option, and fetches all the common and custom traits available for that character to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[str]: A list of trait names for the autocomplete list.
    """
    # Determine the argument based on the Discord option
    argument = ctx.options.get("trait") or ctx.options.get("trait_one") or ""

    # Fetch the character from the ctx options
    character = Character.get_by_id(int(ctx.options["character"]))

    # Fetch and filter traits
    # Filter and return the character's traits
    # We pass the character id before the trait name for the validation to work

    options = [
        OptionChoice(t.name, f"{character.id}_{t.name}")
        for t in character.traits_list
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
    character = Character.get_by_id(int(ctx.options["character"]))

    # Fetch and filter traits
    # Filter and return the character's traits
    options = [
        OptionChoice(t.name, f"{character.id}_{t.name}")
        for t in character.traits_list
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
        OptionChoice(category.value["name"], category.name)
        for category in TraitCategories
        if category.name.lower().startswith(ctx.options["category"].lower())
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
        OptionChoice(c.value["name"], c.name)
        for c in VampireClanType
        if c.value["name"].lower().startswith(ctx.options["vampire_clan"].lower())
    ][:MAX_OPTION_LIST_SIZE]
