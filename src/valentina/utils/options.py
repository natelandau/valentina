"""Reusable autocomplete options for cogs and commands."""

import discord
from discord.commands import OptionChoice
from loguru import logger
from peewee import DoesNotExist

from valentina.constants import MAX_OPTION_LIST_SIZE
from valentina.models.db_tables import CharacterClass, Trait, TraitCategory, VampireClan
from valentina.utils import errors
from valentina.utils.helpers import truncate_string

MAX_OPTION_LENGTH = 99


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
    try:
        # Fetch the active campaign
        campaign = ctx.bot.campaign_svc.fetch_active(ctx)  # type: ignore [attr-defined]
    except errors.NoActiveCampaignError:
        return ["No active campaign"]

    # Fetch, sort and filter the chapters
    return [
        f"{chapter.chapter_number}: {chapter.name}"
        for chapter in sorted(
            ctx.bot.campaign_svc.fetch_all_chapters(campaign=campaign),  # type: ignore [attr-defined]
            key=lambda c: c.chapter_number,
        )
        if chapter.name.lower().startswith(ctx.options["chapter"].lower())
    ][:MAX_OPTION_LIST_SIZE]


async def select_char_class(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of available character classes.

    This function fetches the available character classes, sorts them by name,
    and filters them based on the starting string of the class name.
    If the number of classes reaches a maximum size, it stops appending more classes.

    Args:
        ctx (discord.AutocompleteContext): The context in which the function is called.

    Returns:
        list[str]: A list of available character class names.
    """
    try:
        # Fetch all character classes and sort by name
        character_classes = CharacterClass.select().order_by(CharacterClass.name.asc())
    except DoesNotExist as e:
        logger.error(f"Error occurred while fetching character classes: {e!s}")
        return []

    # Filter and return character class names
    return [
        char_class.name
        for char_class in character_classes
        if char_class.name.lower().startswith(ctx.options["char_class"].lower())
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
    # Fetch the active character
    try:
        character = ctx.bot.user_svc.fetch_active_character(ctx)  # type: ignore [attr-defined]
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
    # Fetch the active character
    try:
        character = ctx.bot.user_svc.fetch_active_character(ctx)  # type: ignore [attr-defined]
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
    return [
        c.name
        for c in ctx.bot.campaign_svc.fetch_all(ctx)  # type: ignore [attr-defined]
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
    try:
        # Fetch active character
        character = ctx.bot.user_svc.fetch_active_character(ctx)  # type: ignore [attr-defined]
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
    # Attempt to fetch the active character
    try:
        character = ctx.bot.user_svc.fetch_active_character(ctx)  # type: ignore [attr-defined]
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
    guild_prefix = f"{ctx.interaction.guild.id}/"

    return [OptionChoice(x.strip(guild_prefix), x) for x in ctx.bot.aws_svc.list_objects(guild_prefix)][:MAX_OPTION_LIST_SIZE]  # type: ignore [attr-defined]


async def select_macro(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Populate a select list with a user's macros based on the input.

    This function fetches the macros for a given user and guild, filters them based on the user's input,
    and returns a list of OptionChoice objects to populate a select list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects to populate the select list.
    """
    # Filter macros based on user input
    filtered_macros = [
        macro
        for macro in ctx.bot.macro_svc.fetch_macros(  # type: ignore [attr-defined]
            ctx.interaction.guild.id, ctx.interaction.user.id
        )
        if macro.name.lower().startswith(ctx.options["macro"].lower())
    ]

    # Create OptionChoice objects
    options = [
        OptionChoice(f"{macro.name} {macro.abbreviation}", str(macro.id))
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
    try:
        # Fetch the active campaign
        campaign = ctx.bot.campaign_svc.fetch_active(ctx)  # type: ignore [attr-defined]
    except errors.NoActiveCampaignError:
        return ["No active campaign"]

    # Fetch and filter notes
    notes = [
        f"{note.id}: {note.name}"
        for note in ctx.bot.campaign_svc.fetch_all_notes(campaign)  # type: ignore [attr-defined]
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
    try:
        campaign = ctx.bot.campaign_svc.fetch_active(ctx)  # type: ignore [attr-defined]
    except errors.NoActiveCampaignError:
        return ["No active campaign"]

    # Fetch and filter NPCs
    npcs = [
        npc.name
        for npc in ctx.bot.campaign_svc.fetch_all_npcs(campaign=campaign)  # type: ignore [attr-defined]
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
    # Prepare character data
    all_chars = [
        (f"{character.name}", character.id)
        for character in ctx.bot.user_svc.fetch_alive_characters(ctx)  # type: ignore [attr-defined]
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
    all_chars = [
        (f"{character.name}", character.id)
        for character in ctx.bot.char_svc.fetch_all_storyteller_characters(ctx)  # type: ignore [attr-defined]
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
    # Initialize options list
    options = []

    # Fetch all characters
    storyteller_chars = [
        (f"{character.full_name} ({character.char_class.name})", character.id)
        for character in ctx.bot.char_svc.fetch_all_storyteller_characters(ctx)  # type: ignore [attr-defined]
    ]
    player_chars = [
        (f"{character.name}", character.id)
        for character in ctx.bot.char_svc.fetch_all_player_characters(ctx)  # type: ignore [attr-defined]
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
    # Fetch and prepare player characters

    all_chars = [
        (f"{character.name} [Owned by: {character.owned_by.username}]", character.id)
        for character in ctx.bot.char_svc.fetch_all_player_characters(ctx)  # type: ignore [attr-defined]
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


async def select_trait(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of available common traits for autocomplete.

    This function fetches all common traits from the database, filters them based on the user's input,
    and returns a list of trait names to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[str]: A list of trait names for the autocomplete list.
    """
    # Determine the argument based on the Discord option
    argument = ctx.options.get("trait") or ctx.options.get("trait_one") or ""

    # Fetch and filter traits
    options = [
        t.name
        for t in Trait.select().order_by(Trait.name.asc())
        if t.name.lower().startswith(argument.lower())
    ][:MAX_OPTION_LIST_SIZE]

    return options if options else ["No traits"]


async def select_trait_two(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of available common traits for autocomplete.

    This function fetches all common traits from the database, filters them based on the user's input,
    and returns a list of trait names to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[str]: A list of trait names for the autocomplete list.
    """
    # Fetch and filter traits
    options = [
        t.name
        for t in Trait.select().order_by(Trait.name.asc())
        if t.name.lower().startswith(ctx.options["trait_two"].lower())
    ][:MAX_OPTION_LIST_SIZE]

    return options if options else ["No traits"]


async def select_trait_category(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of available trait categories for autocomplete.

    This function fetches all trait categories from the database, filters them based on the user's input, and returns a list of trait category names to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[str]: A list of trait category names for the autocomplete list.
    """
    return [
        category.name
        for category in TraitCategory.select().order_by(TraitCategory.name.asc())
        if category.name.lower().startswith(ctx.options["category"].lower())
    ][:MAX_OPTION_LIST_SIZE]


async def select_vampire_clan(ctx: discord.AutocompleteContext) -> list[str]:
    """Generate a list of available vampire clans for autocomplete.

    This function fetches all vampire clans from the database, filters them based on the user's input,
    and returns a list of vampire clan names to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[str]: A list of vampire clan names for the autocomplete list.
    """
    return [
        clan.name
        for clan in VampireClan.select().order_by(VampireClan.name.asc())
        if clan.name.lower().startswith(ctx.options["vampire_clan"].lower())
    ][:MAX_OPTION_LIST_SIZE]
