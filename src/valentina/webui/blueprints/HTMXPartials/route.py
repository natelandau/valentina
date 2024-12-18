"""Routes for handling HTMX partials."""

from dataclasses import dataclass
from typing import assert_never
from uuid import UUID

from loguru import logger
from quart import abort, request, session
from quart.views import MethodView
from quart_wtf import QuartForm

from valentina.controllers import PermissionManager
from valentina.models import (
    Campaign,
    CampaignBook,
    CampaignBookChapter,
    CampaignNPC,
    Character,
    InventoryItem,
    Note,
    User,
    UserMacro,
)
from valentina.utils import random_string, truncate_string
from valentina.webui import catalog
from valentina.webui.constants import TableType, TextType
from valentina.webui.utils import (
    create_toast,
    fetch_active_campaign,
    fetch_active_character,
    fetch_guild,
    sync_channel_to_discord,
    update_session,
)
from valentina.webui.utils.discord import post_to_audit_log

from .forms import (
    AddExperienceForm,
    CampaignChapterForm,
    CampaignDescriptionForm,
    CampaignNPCForm,
    CharacterBioForm,
    InventoryItemForm,
    NoteForm,
    UserMacroForm,
)


class AddExperienceView(MethodView):
    """Handle adding experience to a user."""

    def __init__(self) -> None:
        self.permission_manager = PermissionManager(guild_id=session["GUILD_ID"])

    def _build_success_message(self, experience: int, cool_points: int, target_name: str) -> str:
        """Build success message for experience/cool points addition.

        Args:
            experience: Amount of XP added
            cool_points: Amount of CP added
            target_name: Name of target user

        Returns:
            Formatted message string
        """
        xp_msg = f"{experience} XP" if experience > 0 else ""
        cp_msg = f"{cool_points} CP" if cool_points > 0 else ""

        if xp_msg and cp_msg:
            return f"Add {xp_msg} and {cp_msg} to {target_name}"

        if xp_msg:
            return f"Add {xp_msg} to {target_name}"

        return f"Add {cp_msg} to {target_name}"

    async def render_table(self, target_id: int, success_msg: str = "") -> str:
        """Render the experience table HTML for a target user. This is used to display the experience table in the webui and is called by the get and post methods.

        Args:
            target_id (str): ID of the target user
            success_msg (str): Optional success message to display

        Returns:
            str: HTML snippet containing the experience table with campaign-specific XP,
                total XP, and cool points. Includes success message if provided.
        """
        target = await User.get(target_id)
        if not target:
            abort(404)

        guild = await fetch_guild(fetch_links=True)

        can_grant_xp = await self.permission_manager.can_grant_xp(
            author_id=session["USER_ID"], target_id=target_id
        )

        @dataclass
        class UserCampaignExperience:
            """Experience for a user in a campaign."""

            name: str
            xp: int
            total_xp: int
            cp: int

        campaign_experience = []
        for campaign in guild.campaigns:
            campaign_xp, campaign_total_xp, campaign_cp = target.fetch_campaign_xp(campaign)
            campaign_experience.append(
                UserCampaignExperience(campaign.name, campaign_xp, campaign_total_xp, campaign_cp)  # type: ignore [attr-defined]
            )

        random_id = random_string(4)  # used with success_msg
        return catalog.render(
            "HTMXPartials.AddExperience.ExperienceTableView",
            user=target,
            campaign_experience=campaign_experience,
            can_grant_xp=can_grant_xp,
            success_msg=success_msg,
            random_id=random_id,
        )

    async def get(self, target_id: int) -> str:
        """Render the HTML snippet for the Target's experience table.

        Args:
            target_id (int): ID of the target user

        Returns:
            str: HTML snippet containing the experience table with campaign-specific XP,
                total XP, and cool points.
        """
        return await self.render_table(target_id)

    async def post(self, target_id: int) -> str:
        """Process a form submission to add experience points and cool points to a user.

        Validates permissions, processes the form data, and updates the user's experience
        and cool points for the specified campaign. Returns an updated experience table
        view on success, or the form with errors on failure.

        Args:
            target_id (int): ID of the target user

        Returns:
            str: HTML snippet containing either the updated experience table or form with errors
        """
        target = await User.get(target_id)
        if not target:
            abort(404, "Target user ID not found")

        can_grant_xp = await self.permission_manager.can_grant_xp(
            author_id=session["USER_ID"], target_id=target_id
        )

        if not can_grant_xp:
            abort(403, "You do not have permission to add experience to this user")

        guild = await fetch_guild(fetch_links=True)
        form = await AddExperienceForm().create_form(data={"target_id": target_id})
        form.campaign.choices = [(campaign.id, campaign.name) for campaign in guild.campaigns]  # type: ignore [attr-defined]

        if await form.validate_on_submit() and form.data["submit"]:
            experience = int(form.data["experience"])
            cool_points = int(form.data["cool_points"])
            campaign = await fetch_active_campaign(form.data["campaign"])

            if not campaign:
                abort(400, "Invalid campaign ID")

            if experience > 0:
                await target.add_campaign_xp(campaign=campaign, amount=experience)
            if cool_points > 0:
                await target.add_campaign_cool_points(campaign=campaign, amount=cool_points)

            msg = self._build_success_message(experience, cool_points, target.name)
            await post_to_audit_log(msg=msg, view=self.__class__.__name__)
            return await self.render_table(target_id, success_msg=msg)

        return catalog.render(
            "HTMXPartials.AddExperience.FormPartial", form=form, target_id=target_id
        )


class EditTableView(MethodView):
    """Handle CRUD operations for editable table items in the web UI.

    Supports operations specific to each element in the TableType enum.
    Each operation returns appropriate HTML fragments for HTMX integration.
    """

    def __init__(self, table_type: TableType):
        """Initialize view with specified table type.

        Args:
            table_type (TableType): Enum determining which type of table (Notes, Items, NPCs)
                                    this view instance will handle
        """
        self.table_type: TableType = table_type

    async def _get_parent_by_id(
        self, parent_id: str
    ) -> tuple[CampaignBook | None, Campaign | None, Character | None]:
        """Fetch potential parent object by ID, checking all possible parent types.

        Used primarily for Notes, which can belong to a CampaignBook, Campaign,
        or Character. Only one parent type will be non-None in the returned tuple.

        Args:
            parent_id: UUID string identifying the parent object

        Returns:
            Tuple of (CampaignBook, Campaign, Character) where only one is non-None,
            representing the found parent object
        """
        return (
            await CampaignBook.get(parent_id, fetch_links=True),
            await Campaign.get(parent_id, fetch_links=True),
            await Character.get(parent_id, fetch_links=True),
        )

    async def _find_npc(self, parent_id: str, npc_id: str) -> tuple[Campaign, CampaignNPC] | None:
        """Retrieve a campaign NPC and its parent campaign by their IDs.

        Args:
            parent_id (str): Database ID of the campaign
            npc_id (str): NPC UUID string to locate

        Returns:
            tuple containing (Campaign, CampaignNPC) if found, or None if either:
                - IDs are missing
                - Campaign cannot be fetched
                - NPC is not found in campaign

        Note:
            Returns (campaign, None) if campaign exists but npc_id is empty
        """
        if not parent_id and not npc_id:
            return None, None

        campaign = await fetch_active_campaign(parent_id)

        if not campaign:
            return None, None

        if not npc_id:
            return campaign, None

        for npc in campaign.npcs:
            if npc.uuid == UUID(npc_id):
                return campaign, npc

        return None, None

    async def _find_macro(
        self, parent_id: str | int, macro_id: str
    ) -> tuple[User, UserMacro] | None:
        """Retrieve a user macro and its parent user by their IDs.

        Args:
            parent_id (str | int): Database ID of the user
            macro_id (str): Macro UUID string to locate

        Returns:
            tuple containing (User, UserMacro) if found, or None if either:
                - IDs are missing
                - User cannot be fetched
                - Macro is not found for user

        Note:
            Returns (user, None) if user exists but macro_id is empty
        """
        if not parent_id and not macro_id:
            return None, None

        try:
            user = await User.get(int(parent_id))
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error fetching user from database in _find_macro: {e}")
            return None, None

        if not user:
            return None, None

        if not macro_id:
            return user, None

        for macro in user.macros:
            if macro.uuid == UUID(macro_id):
                return user, macro

        return None, None

    async def _build_form(self) -> "QuartForm":  # noqa: C901, PLR0912, PLR0915
        """Construct and populate the appropriate form based on table type.

        Handles form construction for all supported table types as defined in TableType.
        When editing existing items, populates form with current values.
        For new items, provides empty form with any context-specific defaults.

        Returns:
            QuartForm instance specific to the table type, either empty for new items
            or populated with existing data for edits
        """
        data = {}

        match self.table_type:
            case TableType.NOTE:
                if parent_id := request.args.get("parent_id"):
                    campaign_book, campaign, character = await self._get_parent_by_id(parent_id)
                    data["book_id"] = str(campaign_book.id) if campaign_book else ""
                    data["campaign_id"] = str(campaign.id) if campaign else ""
                    data["character_id"] = str(character.id) if character else ""
                else:
                    data["book_id"] = request.args.get("book_id") or ""
                    data["campaign_id"] = request.args.get("campaign_id") or ""
                    data["character_id"] = request.args.get("character_id") or ""

                if item_id := request.args.get("item_id"):
                    note = await Note.get(item_id)
                    data["note_id"] = item_id
                    data["text"] = note.text

                return await NoteForm().create_form(data=data)

            case TableType.CHAPTER:
                if parent_id := request.args.get("parent_id"):
                    data["book_id"] = parent_id

                if item_id := request.args.get("item_id"):
                    chapter = await CampaignBookChapter.get(item_id)
                    data["chapter_id"] = item_id
                    data["name"] = chapter.name
                    data["description_short"] = chapter.description_short
                    data["description_long"] = chapter.description_long

                return await CampaignChapterForm().create_form(data=data)

            case TableType.INVENTORYITEM:
                if parent_id := request.args.get("parent_id"):
                    data["character_id"] = parent_id

                if item_id := request.args.get("item_id"):
                    item = await InventoryItem.get(item_id)
                    data["item_id"] = item_id
                    data["name"] = item.name
                    data["description"] = item.description
                    data["type"] = item.type
                    data["character_id"] = item.character
                return await InventoryItemForm().create_form(data=data)

            case TableType.NPC:
                if parent_id := request.args.get("parent_id"):
                    data["campaign_id"] = parent_id

                    campaign, npc = await self._find_npc(parent_id, request.args.get("item_id"))
                    if npc:
                        data["uuid"] = str(npc.uuid)
                        data["name"] = npc.name
                        data["description"] = npc.description
                        data["npc_class"] = npc.npc_class

                return await CampaignNPCForm().create_form(data=data)

            case TableType.MACRO:
                if parent_id := request.args.get("parent_id"):
                    data["user_id"] = str(parent_id)

                    user, macro = await self._find_macro(parent_id, request.args.get("item_id"))

                    if macro:
                        data["name"] = macro.name
                        data["abbreviation"] = macro.abbreviation
                        data["description"] = macro.description
                        data["trait_one"] = macro.trait_one
                        data["trait_two"] = macro.trait_two
                        data["uuid"] = str(macro.uuid)
                        data["user_id"] = str(user.id)

                return await UserMacroForm().create_form(data=data)

            case _:  # pragma: no cover
                assert_never()

    async def get(self) -> str:
        """Display an editable form row for an existing table item.

        Fetches the requested item based on table type and item_id from request args.
        Renders appropriate template for displaying the item in editable form.

        Returns:
            Rendered HTML fragment containing the item display template
            suitable for HTMX integration
        """
        item: Note | InventoryItem | CampaignNPC | UserMacro
        parent_id = ""
        match self.table_type:
            case TableType.NOTE:
                note = await Note.get(request.args.get("item_id"))
                item = note

            case TableType.CHAPTER:
                chapter = await CampaignBookChapter.get(request.args.get("item_id"))
                item = chapter

            case TableType.INVENTORYITEM:
                item = await InventoryItem.get(request.args.get("item_id"))

            case TableType.NPC:
                parent_id = request.args.get("campaign_id") or request.args.get("parent_id")

                _, npc = await self._find_npc(parent_id, request.args.get("item_id"))
                if not npc:
                    abort(400, "NPC not found in get")

                item = npc

            case TableType.MACRO:
                parent_id = request.args.get("parent_id") or request.args.get("user_id")

                _, macro = await self._find_macro(parent_id, request.args.get("item_id"))
                if not macro:
                    abort(400, "Macro not found in get")

                item = macro

            case _:  # pragma: no cover
                assert_never()

        return catalog.render(
            "HTMXPartials.EditTable.ItemDisplayPartial",
            item=item,
            TableType=self.table_type,
            parent_id=parent_id,
        )

    async def post(self) -> str:  # noqa: PLR0915
        """Process form submission for editing existing table items.

        Validates submitted form data and updates the corresponding database object.
        Records the change in the audit log.

        Returns:
            On success: Rendered HTML fragment showing the updated item
            On validation failure: Re-rendered form with error messages
        """
        parent_id = ""
        item: Note | InventoryItem | CampaignNPC | UserMacro | CampaignBookChapter

        form = await self._build_form()

        if await form.validate_on_submit():
            match self.table_type:
                case TableType.NOTE:
                    item = await Note.get(form.data["note_id"])
                    item.text = form.data["text"]
                    item.guild_id = int(session["GUILD_ID"])
                    await item.save()

                    msg = f"Edit Note: `{truncate_string(item.text, 10)}`"

                case TableType.CHAPTER:
                    item = await CampaignBookChapter.get(form.data["chapter_id"])
                    item.name = form.data["name"]
                    item.description_short = form.data["description_short"]
                    item.description_long = form.data["description_long"]
                    await item.save()

                    msg = f"Update Chapter: `{item.name}`"

                case TableType.INVENTORYITEM:
                    item = await InventoryItem.get(form.data["item_id"])
                    item.name = form.data["name"]
                    item.description = form.data["description"]
                    item.type = form.data["type"]
                    await item.save()

                    msg = f"Update inventory item: `{item.name}`"

                case TableType.NPC:
                    campaign, npc = await self._find_npc(
                        form.data["campaign_id"], form.data["uuid"]
                    )
                    if not npc:
                        abort(400, "NPC not found in post")

                    npc.name = form.data["name"].strip()
                    npc.description = form.data["description"].strip()
                    npc.npc_class = form.data["npc_class"].strip()
                    item = npc
                    parent_id = str(campaign.id)

                    await campaign.save()
                    msg = f"Update NPC: `{npc.name}`"

                case TableType.MACRO:
                    user, macro = await self._find_macro(form.data["user_id"], form.data["uuid"])
                    if not macro:
                        abort(400, "Macro not found in post")

                    macro.name = form.data["name"].strip()
                    macro.abbreviation = form.data["abbreviation"].strip()
                    macro.description = form.data["description"].strip()
                    macro.trait_one = form.data["trait_one"]
                    macro.trait_two = form.data["trait_two"]
                    item = macro
                    parent_id = str(user.id)

                    await user.save()
                    msg = f"Update Macro: `{item.name}`"

                case _:  # pragma: no cover
                    assert_never()

            await post_to_audit_log(
                msg=msg,
                view=self.__class__.__name__,
            )

            return catalog.render(
                "HTMXPartials.EditTable.ItemDisplayPartial",
                item=item,
                TableType=self.table_type,
                parent_id=parent_id,
            )

        return catalog.render(
            "HTMXPartials.EditTable.FormDisplayPartial",
            form=form,
            TableType=self.table_type,
            method="POST",
            item_id=request.args.get("item_id"),
        )

    async def put(self) -> str:  # noqa: C901, PLR0915
        """Process form submission for creating new table items.

        Validates submitted form data, creates new database object,
        establishes proper relationships with parent objects,
        and records the creation in the audit log.

        Returns:
            On success: Rendered HTML fragment showing the newly created item
            On validation failure: Re-rendered form with error messages
        """
        item: Note | InventoryItem | CampaignNPC | UserMacro

        parent_id = ""
        form = await self._build_form()

        if await form.validate_on_submit():
            match self.table_type:
                case TableType.NOTE:
                    parent_id = (
                        form.data["book_id"]
                        or form.data["character_id"]
                        or form.data["campaign_id"]
                    )
                    campaign_book, campaign, character = await self._get_parent_by_id(parent_id)
                    parent = campaign_book or campaign or character

                    if not parent:
                        abort(400, "Invalid parent ID")

                    item = Note(
                        text=form.data["text"].strip(),
                        parent_id=str(parent.id),
                        created_by=session["USER_ID"],
                        guild_id=int(session["GUILD_ID"]),
                    )
                    await item.save()

                    parent.notes.append(item)
                    await parent.save()

                    msg = f"Create Note: `{truncate_string(item.text, 10)}`"

                case TableType.CHAPTER:
                    book = await CampaignBook.get(form.data["book_id"], fetch_links=True)

                    if not book:
                        abort(400, "Invalid book ID")

                    item = CampaignBookChapter(
                        name=form.name.data.strip().title(),
                        description_short=form.description_short.data.strip(),
                        description_long=form.description_long.data.strip(),
                        book=str(book.id),
                        number=max([c.number for c in await book.fetch_chapters()], default=0) + 1,
                    )
                    await item.save()
                    book.chapters.append(item)
                    await book.save()

                    msg = f"Create Chapter: `{form.data['name']}`"

                case TableType.INVENTORYITEM:
                    character = await Character.get(form.data["character_id"])
                    if not character:
                        abort(400, "Invalid character ID")

                    item = InventoryItem(
                        character=str(character.id),
                        name=form.data["name"].strip(),
                        description=form.data["description"].strip(),
                        type=form.data["type"],
                    )
                    await item.save()
                    character.inventory.append(item)
                    await character.save()

                    msg = f"Add `{item.name}` to `{character.name}`"

                case TableType.NPC:
                    campaign = await fetch_active_campaign(form.data["campaign_id"])
                    if not campaign:
                        abort(400, "Invalid campaign ID in put")

                    item = CampaignNPC(
                        name=form.data["name"].strip(),
                        description=form.data["description"].strip(),
                        npc_class=form.data["npc_class"].strip(),
                    )

                    campaign.npcs.append(item)
                    await campaign.save()
                    parent_id = str(campaign.id)
                    msg = f"Create NPC: `{form.data['name']}`"

                case TableType.MACRO:
                    user = await User.get(form.data["user_id"])
                    if not user:
                        abort(400, "Invalid user ID in put")

                    item = UserMacro(
                        name=form.data["name"].strip(),
                        abbreviation=form.data["abbreviation"].strip(),
                        description=form.data["description"].strip(),
                        trait_one=form.data["trait_one"],
                        trait_two=form.data["trait_two"],
                    )

                    user.macros.append(item)
                    await user.save()
                    parent_id = str(user.id)
                    msg = f"Create Macro: `{form.data['name']}`"

                case _:  # pragma: no cover
                    assert_never()

            await post_to_audit_log(
                msg=msg,
                view=self.__class__.__name__,
            )

            return catalog.render(
                "HTMXPartials.EditTable.ItemDisplayPartial",
                item=item,
                TableType=self.table_type,
                parent_id=parent_id,
            )

        return catalog.render(
            "HTMXPartials.EditTable.FormDisplayPartial",
            form=form,
            item_id=request.args.get("item_id"),
            TableType=self.table_type,
            method="PUT",
        )

    async def delete(self) -> str:  # noqa: C901, PLR0912, PLR0915
        """Remove item from database and update related objects.

        Removes the specified item, updates any parent object references,
        and records the deletion in the audit log.
        Handles cascading deletions where necessary.

        Returns:
            Toast notification HTML fragment confirming successful deletion
        """
        item_id = request.args.get("item_id", None)
        if not item_id:
            abort(400)

        match self.table_type:
            case TableType.NOTE:
                note = await Note.get(item_id)
                if character := await Character.get(note.parent_id, fetch_links=True):
                    character.notes.remove(note)
                    await character.save()
                elif book := await CampaignBook.get(note.parent_id, fetch_links=True):
                    book.notes.remove(note)
                    await book.save()
                elif campaign := await Campaign.get(note.parent_id, fetch_links=True):
                    campaign.notes.remove(note)
                    await campaign.save()

                await note.delete()

                truncated_note = truncate_string(note.text, 10)
                msg = f"Delete note: `{truncated_note}`"

            case TableType.CHAPTER:
                chapter = await CampaignBookChapter.get(item_id)
                book = await CampaignBook.get(chapter.book, fetch_links=True)
                book.chapters.remove(chapter)
                await book.save()
                await chapter.delete()
                msg = f"Delete chapter: `{chapter.name}`"

            case TableType.INVENTORYITEM:
                item = await InventoryItem.get(item_id)
                character = await Character.get(item.character, fetch_links=True)
                for char_item in character.inventory:
                    if char_item == item:
                        character.inventory.remove(char_item)
                        break
                await character.save()

                await item.delete()

                msg = f"Delete `{item.name}` from `{character.name}`"

            case TableType.NPC:
                campaign, npc = await self._find_npc(request.args.get("parent_id"), item_id)
                if not npc:
                    abort(400, "NPC not found in delete")

                campaign.npcs.remove(npc)
                await campaign.save()
                msg = f"Delete NPC: `{npc.name}`"

            case TableType.MACRO:
                user, macro = await self._find_macro(request.args.get("parent_id"), item_id)
                if not macro:
                    abort(400, "Macro not found in post")

                user.macros.remove(macro)
                await user.save()
                msg = f"Delete Macro: `{macro.name}`"

            case _:  # pragma: no cover
                assert_never()

        await post_to_audit_log(
            msg=msg,
            view=self.__class__.__name__,
        )

        return create_toast(msg, level="SUCCESS")


class EditTextView(MethodView):
    """Handle CRUD operations for text items."""

    def __init__(self, text_type: TextType):
        """Initialize view with specified text type."""
        self.text_type: TextType = text_type

    async def _build_form(self) -> "QuartForm":
        """Build the appropriate form based on text type."""
        data = {}

        match self.text_type:
            case TextType.BIOGRAPHY:
                character = await fetch_active_character(request.args.get("parent_id"))
                data["bio"] = character.bio
                data["character_id"] = str(character.id)

                return await CharacterBioForm().create_form(data=data)

            case TextType.CAMPAIGN_DESCRIPTION:
                campaign = await fetch_active_campaign(request.args.get("parent_id"))
                data["name"] = campaign.name
                data["description"] = campaign.description
                data["campaign_id"] = str(campaign.id)

                return await CampaignDescriptionForm().create_form(data=data)

            case _:  # pragma: no cover
                assert_never(self.text_type)

    async def _update_character_bio(self, form: QuartForm) -> tuple[str, str]:
        """Update the character bio.

        Args:
            form: The form data

        Returns:
            A tuple containing the updated text and message
        """
        character = await fetch_active_character(request.args.get("parent_id"))
        character.bio = form.data["bio"]
        await character.save()
        text = character.bio
        msg = f"{character.name} bio updated"
        return text, msg

    async def _update_campaign_description(self, form: QuartForm) -> tuple[str, str]:
        """Update the campaign description and name.

        Args:
            form: The form data

        Returns:
            A tuple containing the updated text and message
        """
        campaign = await fetch_active_campaign(request.args.get("parent_id"))

        is_renamed = campaign.name.strip().lower() != form.data["name"].strip().lower()

        campaign.name = form.data["name"].strip().title()
        campaign.description = form.data["campaign_description"].strip()
        await campaign.save()
        text = form.data["campaign_description"].strip()
        msg = f"{campaign.name} description updated"

        if is_renamed:
            await sync_channel_to_discord(obj=campaign, update_type="update")
            await update_session()

        return text, msg

    async def get(self) -> str:
        """Return just the text for a text item.

        Returns:
            Rendered HTML fragment containing the text suitable for HTMX integration
        """
        match self.text_type:
            case TextType.BIOGRAPHY:
                character = await fetch_active_character(request.args.get("parent_id"))
                text = character.bio

            case TextType.CAMPAIGN_DESCRIPTION:
                campaign = await fetch_active_campaign(request.args.get("parent_id"))
                text = campaign.description

            case _:  # pragma: no cover
                assert_never(self.text_type)

        return catalog.render(
            "HTMXPartials.EditText.TextDisplayPartial",
            TextType=self.text_type,
            text=text,
        )

    async def put(self) -> str:
        """Put the text item."""
        form = await self._build_form()

        if await form.validate_on_submit():
            match self.text_type:
                case TextType.BIOGRAPHY:
                    text, msg = await self._update_character_bio(form)

                case TextType.CAMPAIGN_DESCRIPTION:
                    text, msg = await self._update_campaign_description(form)

            await post_to_audit_log(
                msg=msg,
                view=self.__class__.__name__,
            )

            return catalog.render(
                "HTMXPartials.EditText.TextDisplayPartial",
                TextType=self.text_type,
                text=text,
            )

        return catalog.render(
            "HTMXPartials.EditText.TextFormPartial",
            TextType=self.text_type,
            form=form,
            method="PUT",
        )

    async def post(self) -> str:
        """Post the text item."""
        form = await self._build_form()

        if await form.validate_on_submit():
            match self.text_type:
                case TextType.BIOGRAPHY:
                    text, msg = await self._update_character_bio(form)

                case TextType.CAMPAIGN_DESCRIPTION:
                    text, msg = await self._update_campaign_description(form)

            await post_to_audit_log(
                msg=msg,
                view=self.__class__.__name__,
            )

            return catalog.render(
                "HTMXPartials.EditText.TextDisplayPartial",
                TextType=self.text_type,
                text=text,
            )

        return catalog.render(
            "HTMXPartials.EditText.TextFormPartial",
            TextType=self.text_type,
            form=form,
            method="POST",
        )
