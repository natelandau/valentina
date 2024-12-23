"""Reusable autocomplete options for cogs and commands."""

from typing import cast

import discord
import inflect
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
from valentina.discord.bot import Valentina
from valentina.discord.utils import fetch_channel_object
from valentina.models import AWSService, Campaign, ChangelogParser, Character, User
from valentina.utils import errors
from valentina.utils.helpers import truncate_string

MAX_OPTION_LENGTH = 99


################## Character Autocomplete Functions ##################
async def select_any_player_character(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of all player characters in the guild for autocomplete.

    Fetch all player characters for the guild, filter them based on the user's input,
    and return a list of OptionChoice objects to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects containing character names and IDs.
    """
    # Fetch and prepare player characters
    all_chars_owners = sorted(
        [
            (x, await User.get(x.user_owner))
            async for x in Character.find(
                And(
                    Character.guild == ctx.interaction.guild.id,
                    Character.type_player == True,  # noqa: E712
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
        if character.name.lower().startswith(ctx.value.lower())
    ]

    # Check if the number of options exceeds the maximum allowed
    if len(options) >= MAX_OPTION_LIST_SIZE:  # pragma: no cover
        instructions = "Keep typing ..." if ctx.value else "Start typing a name."
        return [OptionChoice(f"Too many characters to display. {instructions}", "")]

    return options or [OptionChoice("No characters available", "")]


async def select_campaign_any_player_character(
    ctx: discord.AutocompleteContext,
) -> list[OptionChoice]:  # pragma: no cover
    """Generate a list of all player characters associated with a specific campaign.

    Fetch all player characters for the campaign, filter them based on the user's input,
    and return a list of OptionChoice objects to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[discord.OptionChoice]: A list of OptionChoice objects containing character names and IDs for the autocomplete list.
    """
    channel_objects = await fetch_channel_object(ctx, raise_error=False)
    campaign = channel_objects.campaign

    if not campaign:
        return [OptionChoice("Rerun in a channel associated with a campaign", "")]

    # Fetch and prepare player characters
    all_chars_owners = sorted(
        [
            (x, await User.get(x.user_owner))
            async for x in Character.find(
                And(
                    Character.campaign == str(campaign.id),
                    Character.type_player == True,  # noqa: E712
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
        if character.name.lower().startswith(ctx.value.lower())
    ]

    # Check if the number of options exceeds the maximum allowed
    if len(options) >= MAX_OPTION_LIST_SIZE:  # pragma: no cover
        instructions = "Keep typing ..." if ctx.value else "Start typing a name."
        return [OptionChoice(f"Too many characters to display. {instructions}", "")]

    return options or [OptionChoice("No characters available", "")]


async def select_campaign_character_from_user(
    ctx: discord.AutocompleteContext,
) -> list[OptionChoice]:
    """Generate a list of the user's available characters for autocomplete.

    Fetch all player characters for the user in the current campaign, filter them based on user input,
    and return a list of OptionChoice objects for autocomplete.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[discord.OptionChoice]: A list of OptionChoice objects for the autocomplete list.
    """
    channel_objects = await fetch_channel_object(ctx, raise_error=False)
    campaign = channel_objects.campaign

    if not campaign:
        return [OptionChoice("Rerun in a channel associated with a campaign", "")]

    user_object = await User.get(ctx.interaction.user.id, fetch_links=True)

    # Prepare character data
    all_chars = [
        (
            f"{character.name}" if character.is_alive else f"{Emoji.DEAD.value} {character.name}",
            character.id,
        )
        for character in user_object.all_characters(ctx.interaction.guild)
        if character.type_player and character.campaign == str(campaign.id)
    ]

    # Generate options
    options = [
        OptionChoice(name, str(char_id))
        for name, char_id in sorted(all_chars)
        if name.lower().startswith(ctx.value.lower())
    ][:MAX_OPTION_LIST_SIZE]

    return options or [OptionChoice("No characters available", "")]


async def select_storyteller_character(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of available storyteller characters for autocomplete.

    This function fetches all storyteller characters, filters them based on the user's input, and returns a list of OptionChoice objects to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects for the autocomplete list which contains character names and ids.
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

    return options or [OptionChoice("No characters available", "")]


async def select_any_character(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of available characters for autocomplete. This list will include all character types.

    This function fetches all storyteller characters, filters them based on the user's input, and returns a list of OptionChoice objects to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects for the autocomplete list which contains character names and ids.
    """
    # Prepare character data
    all_chars = [
        (
            f"{character.name}" if character.is_alive else f"{Emoji.DEAD.value} {character.name}",
            character.id,
        )
        async for character in Character.find_many(
            Character.guild == ctx.interaction.guild.id,
        )
    ]

    # Generate options
    options = [
        OptionChoice(name, str(char_id))
        for name, char_id in sorted(all_chars)
        if name.lower().startswith(ctx.value.lower())
    ][:MAX_OPTION_LIST_SIZE]

    return options or [OptionChoice("No characters available", "")]


################## Autocomplete Functions ##################
async def select_aws_object_from_guild(
    ctx: discord.AutocompleteContext,
) -> list[OptionChoice]:  # pragma: no cover
    """Populate the autocomplete list for the aws_object option based on the user's input.

    Fetch AWS objects associated with the current guild and generate autocomplete options.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction details.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects representing AWS objects,
                            limited to MAX_OPTION_LIST_SIZE.
    """
    aws_svc = AWSService()

    guild_prefix = f"{ctx.interaction.guild.id}/"

    return [OptionChoice(x.strip(guild_prefix), x) for x in aws_svc.list_objects(guild_prefix)][
        :MAX_OPTION_LIST_SIZE
    ]


async def select_changelog_version_1(
    ctx: discord.AutocompleteContext,
) -> list[str]:  # pragma: no cover
    """Populate the autocomplete for the first version option.

    Generate a list of changelog versions that start with the user's input.

    Args:
        ctx: The autocomplete context containing the interaction details.

    Returns:
        A list of version strings matching the user's input, limited to MAX_OPTION_LIST_SIZE.
    """
    bot = cast(Valentina, ctx.bot)
    possible_versions = ChangelogParser(bot).list_of_versions()

    return [version for version in possible_versions if version.startswith(ctx.value)][
        :MAX_OPTION_LIST_SIZE
    ]


async def select_changelog_version_2(
    ctx: discord.AutocompleteContext,
) -> list[str]:  # pragma: no cover
    """Populate the autocomplete for the second version option.

    Generate a list of changelog versions that start with the user's input.

    Args:
        ctx: The autocomplete context containing the interaction details.

    Returns:
        A list of version strings matching the user's input, limited to MAX_OPTION_LIST_SIZE.
    """
    bot = cast(Valentina, ctx.bot)
    possible_versions = ChangelogParser(bot).list_of_versions()

    return [version for version in possible_versions if version.startswith(ctx.value)][
        :MAX_OPTION_LIST_SIZE
    ]


async def select_book(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Populate the autocomplete for the book option.

    Fetch the active campaign, retrieve all books for that campaign, sort them by book number,
    and filter based on the user's input. If no active campaign is found, return a single option
    indicating this. If the number of books exceeds the maximum allowed options, return all
    matching books up to the limit.

    Args:
        ctx (discord.AutocompleteContext): The context of the autocomplete interaction.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects representing available books.
            Each option contains the book number and name as the label, and the book's
            database ID as the value.
    """
    # Fetch the active campaign
    channel_objects = await fetch_channel_object(ctx, raise_error=False)
    campaign = channel_objects.campaign

    if not campaign:
        return [OptionChoice("No active campaign", "")]

    books = await campaign.fetch_books()

    choices = [
        OptionChoice(f"{book.number}. {book.name}", str(book.id))
        for book in sorted(books, key=lambda x: x.number)
        if book.name.lower().startswith(ctx.options["book"].lower())
    ][:MAX_OPTION_LIST_SIZE]

    return choices or [OptionChoice("No books", "")]


async def select_campaign(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of available campaigns for the guild.

    Fetch and sort non-deleted campaigns for the current guild, then filter based on user input.
    If too many options are available, return a single option prompting for more specific input.

    Args:
        ctx (discord.AutocompleteContext): The autocomplete context containing interaction details.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects representing available campaigns.
            Each option contains the campaign name as the label and the campaign's database ID as the value.
    """
    all_campaigns = sorted(
        await Campaign.find(
            Campaign.guild == ctx.interaction.guild.id,
            Campaign.is_deleted == False,  # noqa: E712
            fetch_links=True,
        ).to_list(),
        key=lambda x: x.name,
    )

    options = [
        OptionChoice(f"{campaign.name}", str(campaign.id))
        for campaign in all_campaigns
        if campaign.name.lower().startswith(ctx.value.lower())
    ]

    # Check if the number of options exceeds the maximum allowed
    if len(options) >= MAX_OPTION_LIST_SIZE:  # pragma: no cover
        instructions = "Keep typing ..." if ctx.value else "Start typing a name."
        return [OptionChoice(f"Too many campaigns to display. {instructions}", "")]

    return options or [OptionChoice("No campaigns available", "")]


async def select_chapter(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Populate the autocomplete for the chapter option.

    Fetch the active book for the current channel, retrieve its chapters, sort them by number,
    and filter based on user input. If no active book is found, return a single option indicating this.

    Args:
        ctx (discord.AutocompleteContext): The autocomplete context containing interaction details.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects representing available chapters.
            Each option contains the chapter number and name as the label, and the chapter's
            database ID as the value.
    """
    # Fetch the active campaign
    channel_objects = await fetch_channel_object(ctx, raise_error=False)
    book = channel_objects.book
    if not book:
        return [OptionChoice("Not in book channel", "")]

    choices = [
        OptionChoice(f"{chapter.number}. {chapter.name}", str(chapter.id))
        for chapter in sorted(await book.fetch_chapters(), key=lambda x: x.number)
        if chapter.name.lower().startswith(ctx.options["chapter"].lower())
    ][:MAX_OPTION_LIST_SIZE]

    return choices or [OptionChoice("No chapters", "")]


async def select_char_class(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of available character classes.

    Fetch available character classes, sort them by name, and filter based on user input.

    Args:
        ctx (discord.AutocompleteContext): The autocomplete context containing interaction details.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects representing available character classes.
            Each option contains the class name as both the label and the value.
    """
    # Filter and return character class names
    return [
        OptionChoice(c.value.name, c.name)
        for c in CharClass.playable_classes()
        if c.value.name and c.value.name.lower().startswith(ctx.options["char_class"].lower())
    ][:MAX_OPTION_LIST_SIZE]


async def select_char_concept(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of available character concepts.

    Fetch available character concepts and filter based on user input.

    Args:
        ctx (discord.AutocompleteContext): The autocomplete context containing interaction details.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects representing available character concepts.
            Each option contains the concept name (title-cased) as the label and the concept name (uppercase) as the value.
    """
    # Filter and return character class names
    return [
        OptionChoice(c.name.title(), c.name)
        for c in CharacterConcept
        if c.name.startswith(ctx.options["concept"].upper())
    ][:MAX_OPTION_LIST_SIZE]


async def select_char_inventory_item(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of inventory items and their index for a character.

    This function fetches the active character from the bot's user service,
    retrieves the argument "item" from the context options,
    and filters the character's inventory items based on the starting string of the item name.
    If the number of items reaches a maximum size, it stops appending more items.

    Args:
        ctx (discord.AutocompleteContext): The context in which the function is called.

    Returns:
        list[OptionChoice]: A list of available item names and their index in character.inventory.
    """
    channel_objects = await fetch_channel_object(ctx, raise_error=False)
    character = channel_objects.character

    if not character:
        return [OptionChoice("Rerun command in a character channel", "")]

    # Determine the option to retrieve the argument
    argument = ctx.options.get("item") or ""

    # Filter and return the character's inventory items
    return [
        OptionChoice(t.name, str(t.id))  # type: ignore [attr-defined]
        for t in sorted(character.inventory, key=lambda x: x.name)  # type: ignore [attr-defined]
        if t.name.lower().startswith(argument.lower())  # type: ignore [attr-defined]
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
        if c.name.startswith(ctx.options["level"].upper())
    ][:MAX_OPTION_LIST_SIZE]


async def select_char_trait(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of traits and their index for a character.

    This function fetches the active character from the bot's user service,
    retrieves the argument (either "trait" or "trait_one") from the context options,
    and filters the character's traits based on the starting string of the trait name.
    If the number of traits reaches a maximum size, it stops appending more traits.

    Args:
        ctx (discord.AutocompleteContext): The context in which the function is called.

    Returns:
        list[OptionChoice]: A list of available names and their index in character.traits.
    """
    channel_objects = await fetch_channel_object(ctx, raise_error=False)
    character = channel_objects.character

    if not character:
        return [OptionChoice("Rerun command in a character channel", "")]

    # Determine the option to retrieve the argument
    argument = ctx.options.get("trait") or ctx.options.get("trait_one") or ""

    # Filter and return the character's traits
    return [
        OptionChoice(t.name, str(t.id))  # type: ignore [attr-defined]
        for t in sorted(character.traits, key=lambda x: x.name)  # type: ignore [attr-defined]
        if t.name.lower().startswith(argument.lower())  # type: ignore [attr-defined]
    ][:MAX_OPTION_LIST_SIZE]


async def select_char_trait_two(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Generate a list of available common and custom traits for a character.

    This function fetches the active character from the bot's user service,
    retrieves the argument ("trait_two") from the context options,
    and filters the character's traits based on the starting string of the trait name.
    If the number of traits reaches a maximum size, it stops appending more traits.

    Args:
        ctx (discord.AutocompleteContext): The context in which the function is called.

    Returns:
        list[OptionChoice]: A list of available trait names and their index in character.traits.
    """
    channel_objects = await fetch_channel_object(ctx, raise_error=False)
    character = channel_objects.character

    if not character:
        return [OptionChoice("Rerun command in a character channel", "")]

    # Filter and return the character's traits
    return [
        OptionChoice(t.name, str(t.id))  # type: ignore [attr-defined]
        for t in sorted(character.traits, key=lambda x: x.name)  # type: ignore [attr-defined]
        if t.name.lower().startswith(ctx.options["trait_two"].lower())  # type: ignore [attr-defined]
    ][:MAX_OPTION_LIST_SIZE]


async def select_custom_section(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
    """Fetches and provides a list of the active character's custom sections.

    This function attempts to retrieve an active character for the user, filtering on
    the characters custom sections and displaying a title and id combination. If there
    are too many sections, appropriate instructions are displayed instead.

    Args:
        ctx (discord.AutocompleteContext): The autocomplete context provided by discord.

    Returns:
        list[OptionChoice]: A list of option choices for discord selection containing title and index pairs.
    """
    channel_objects = await fetch_channel_object(ctx, raise_error=False)
    character = channel_objects.character

    if not character:
        return [OptionChoice("Rerun command in a character channel", "")]

    if not character.sheet_sections:
        return [OptionChoice("No custom sections", "")]

    # Create a list of tuples containing display title and list index for each custom section
    options = [
        OptionChoice(truncate_string(section.title, MAX_OPTION_LENGTH), str(index))
        for index, section in enumerate(character.sheet_sections)
        if section.title.lower().startswith(ctx.value.lower())
    ]
    if len(options) > MAX_OPTION_LIST_SIZE:
        instructions = "Keep typing ..." if ctx.value else "Start typing..."
        return [OptionChoice(f"Too many sections to display. {instructions}", "")]

    return options


async def select_country(ctx: discord.AutocompleteContext) -> list[OptionChoice]:  # noqa: ARG001 # pragma: no cover
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


async def select_desperation_dice(
    ctx: discord.AutocompleteContext,
) -> list[OptionChoice]:  # pragma: no cover
    """Populate the autocomplete list for the desperation_dice option based on the user's input.

    This function creates a list of OptionChoice objects to populate the autocomplete list.

    Args:
        ctx (discord.AutocompleteContext): The context object containing interaction and user details.

    Returns:
        list[OptionChoice]: A list of OptionChoice objects to populate the autocomplete list.
    """
    p = inflect.engine()

    # Fetch the active campaign
    channel_objects = await fetch_channel_object(ctx, raise_error=False)
    campaign = channel_objects.campaign

    if not campaign:
        return [OptionChoice("No active campaign", "")]

    if campaign.desperation == 0:
        return [OptionChoice("No desperation dice", "")]

    return [
        OptionChoice(f"{p.number_to_words(i).capitalize()} {p.plural('die', i)}", i)  # type: ignore [arg-type, union-attr]
        for i in range(1, campaign.desperation + 1)
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
    """Populate the autocomplete for selecting a note."""
    try:
        channel_objects = await fetch_channel_object(ctx)
        channel_object = channel_objects.book or channel_objects.character

    except errors.ChannelTypeError:
        return [OptionChoice("No notes found", "")]

    if not channel_object or not channel_object.notes:
        return [OptionChoice("No notes found", "")]

    sorted_notes = sorted(channel_object.notes, key=lambda x: x.date_created)  # type: ignore [attr-defined]

    return [
        OptionChoice(truncate_string(note.text, 99), str(note.id))  # type: ignore [attr-defined]
        for note in sorted_notes
        if ctx.value.lower() in note.text.lower()  # type: ignore [attr-defined]
    ][:MAX_OPTION_LIST_SIZE]


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
    channel_objects = await fetch_channel_object(ctx, raise_error=False)
    campaign = channel_objects.campaign

    if not campaign:
        return [OptionChoice("No active campaign", "")]

    npc_choices = [
        OptionChoice(npc.name, index)
        for index, npc in enumerate(campaign.npcs)
        if npc.name.lower().startswith(ctx.options["npc"].lower())
    ][:MAX_OPTION_LIST_SIZE]

    return npc_choices or [OptionChoice("No npcs", "")]


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

    return options or [OptionChoice("No traits", "")]


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

    return options or [OptionChoice("No traits", "")]


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
