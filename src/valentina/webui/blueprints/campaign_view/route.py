"""Campaign view."""

from typing import ClassVar, assert_never

from flask_discord import requires_authorization
from quart import Response, abort, request, session, url_for
from quart.views import MethodView
from quart_wtf import QuartForm

from valentina.constants import DBSyncUpdateType
from valentina.controllers import PermissionManager
from valentina.models import Campaign, CampaignBook, CampaignBookChapter, Note, Statistics
from valentina.webui import catalog
from valentina.webui.constants import CampaignEditableInfo, CampaignViewTab
from valentina.webui.utils.discord import post_to_audit_log
from valentina.webui.utils.helpers import (
    fetch_active_campaign,
    sync_book_to_discord,
    sync_campaign_to_discord,
    update_session,
)

from .forms import CampaignBookForm, CampaignChapterForm, CampaignDescriptionForm, CampaignNoteForm


class CampaignView(MethodView):
    """View to handle campaign operations."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self) -> None:
        self.is_htmx = bool(request.headers.get("Hx-Request", False))
        self.permission_manager = PermissionManager(guild_id=session["GUILD_ID"])
        self.can_manage_campaign = False

    async def handle_tabs(self, campaign: Campaign) -> str:
        """Handle rendering of HTMX tab content for the campaign view.

        Determine the requested tab from the "tab" query parameter and render
        the corresponding template for the campaign view. Supported tabs include
        'overview', 'books', 'characters', and 'statistics'.

        Args:
            campaign (Campaign): The campaign object to use for rendering the view.

        Returns:
            str: The rendered HTML content for the selected tab.

        Raises:
            404: If the requested tab is not recognized or supported.

        Note:
            This method is designed to work with HTMX requests for dynamic
            tab content loading in the campaign view.
        """
        tab = CampaignViewTab.get_member_by_value(request.args.get("tab", None))
        match tab:
            case CampaignViewTab.OVERVIEW:
                return catalog.render(
                    "campaign_view.Overview",
                    campaign=campaign,
                    CampaignEditableInfo=CampaignEditableInfo,
                    can_manage_campaign=self.can_manage_campaign,
                )

            case CampaignViewTab.BOOKS:
                return catalog.render(
                    "campaign_view.Books",
                    campaign=campaign,
                    books=await campaign.fetch_books(),
                    CampaignEditableInfo=CampaignEditableInfo,
                    can_manage_campaign=self.can_manage_campaign,
                )

            case CampaignViewTab.CHARACTERS:
                return catalog.render(
                    "campaign_view.Characters",
                    campaign=campaign,
                    characters=await campaign.fetch_player_characters(),
                    CampaignEditableInfo=CampaignEditableInfo,
                    can_manage_campaign=self.can_manage_campaign,
                )

            case CampaignViewTab.STATISTICS:
                stats_engine = Statistics(guild_id=session["GUILD_ID"])
                return catalog.render(
                    "campaign_view.Statistics",
                    campaign=campaign,
                    statistics=await stats_engine.campaign_statistics(campaign, as_json=True),
                    CampaignEditableInfo=CampaignEditableInfo,
                    can_manage_campaign=self.can_manage_campaign,
                )

            case CampaignViewTab.NOTES:
                return catalog.render(
                    "campaign_view.Notes",
                    campaign=campaign,
                    CampaignEditableInfo=CampaignEditableInfo,
                    can_manage_campaign=self.can_manage_campaign,
                )

            case _:
                assert_never(tab)

    async def get(self, campaign_id: str = "") -> str:
        """Handle GET requests for a specific campaign view.

        Fetch the campaign using the provided campaign ID and render the appropriate view.
        Process the request based on whether it's an HTMX request or a regular GET request.

        For HTMX requests:
        - Delegate rendering to the `handle_tabs` method.
        - Return content specific to the selected tab.

        For regular GET requests:
        - Render the main campaign view.

        Args:
            campaign_id (str): The unique identifier of the campaign to retrieve.

        Returns:
            str: The rendered HTML content for the campaign view. This can be either
                 tab-specific content for HTMX requests or the full campaign view for
                 regular GET requests.

        Raises:
            401: If no campaign is found with the provided ID.
            404: If an invalid tab is requested in an HTMX request (raised by `handle_tabs`).

        Note:
            This method uses the `request` object to determine if it's an HTMX request
            and to access any query parameters for tab selection.
        """
        campaign = await fetch_active_campaign(campaign_id, fetch_links=True)
        self.can_manage_campaign = await self.permission_manager.can_manage_campaign(
            session["USER_ID"]
        )

        if self.is_htmx:
            return await self.handle_tabs(campaign)

        return catalog.render(
            "campaign_view.Main",
            campaign=campaign,
            tabs=CampaignViewTab,
            CampaignEditableInfo=CampaignEditableInfo,
            can_manage_campaign=self.can_manage_campaign,
            error_msg=request.args.get("error_msg", ""),
            success_msg=request.args.get("success_msg", ""),
            info_msg=request.args.get("info_msg", ""),
            warning_msg=request.args.get("warning_msg", ""),
        )


class CampaignEditItem(MethodView):
    """View to handle editing of campaign items."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self, edit_type: CampaignEditableInfo) -> None:
        self.edit_type = edit_type

    async def _build_form(self, campaign: Campaign) -> QuartForm:
        """Build the form for the campaign item."""
        data = {}

        match self.edit_type:
            case CampaignEditableInfo.DESCRIPTION:
                data["name"] = campaign.name
                data["description"] = campaign.description
                return await CampaignDescriptionForm().create_form(data=data)

            case CampaignEditableInfo.BOOK:
                if request.args.get("book_id"):
                    existing_book = await CampaignBook.get(request.args.get("book_id"))
                    data["book_id"] = request.args.get("book_id")
                    data["name"] = existing_book.name
                    data["description_short"] = existing_book.description_short
                    data["description_long"] = existing_book.description_long
                return await CampaignBookForm().create_form(data=data)

            case CampaignEditableInfo.CHAPTER:
                if request.args.get("chapter_id"):
                    existing_chapter = await CampaignBookChapter.get(request.args.get("chapter_id"))
                    data["chapter_id"] = request.args.get("chapter_id")
                    data["name"] = existing_chapter.name
                    data["description_short"] = existing_chapter.description_short
                    data["description_long"] = existing_chapter.description_long
                    data["book_id"] = existing_chapter.book

                return await CampaignChapterForm().create_form(data=data)

            case CampaignEditableInfo.NOTE:
                data["book_id"] = request.args.get("book_id") or ""
                data["chapter_id"] = request.args.get("chapter_id") or ""
                data["campaign_id"] = request.args.get("campaign_id") or ""

                if request.args.get("note_id"):
                    existing_note = await Note.get(request.args.get("note_id"))
                    data["note_id"] = request.args.get("note_id")
                    data["text"] = existing_note.text
                return await CampaignNoteForm().create_form(data=data)

            case _:
                assert_never(self.edit_type)

    async def _delete_campaign_book(self, campaign: Campaign) -> str:
        """Delete a campaign book."""
        book_id = request.args.get("book_id")
        if not book_id:
            abort(400)

        book = await CampaignBook.get(book_id)
        campaign.books.remove(book)
        await campaign.save()
        await book.delete()
        await sync_book_to_discord(book, DBSyncUpdateType.DELETE)

        await post_to_audit_log(
            msg=f"Delete {campaign.name} book - `{book.name}`",
            view=self.__class__.__name__,
        )

        return "Book deleted"

    async def _delete_campaign_chapter(self) -> str:
        """Delete a campaign chapter."""
        chapter_id = request.args.get("chapter_id")
        if not chapter_id:
            abort(400)

        chapter = await CampaignBookChapter.get(chapter_id)
        book = await CampaignBook.get(chapter.book, fetch_links=True)
        book.chapters.remove(chapter)
        await book.save()
        await chapter.delete()
        await post_to_audit_log(
            msg=f"Delete chapter - `{chapter.name}`",
            view=self.__class__.__name__,
        )

        return "Chapter deleted"

    async def _delete_note(self, campaign: Campaign) -> str:
        """Delete the note."""
        note_id = request.args.get("note_id", None)
        if not note_id:
            abort(400)

        existing_note = await Note.get(note_id)
        if request.args.get("book_id"):
            book = await CampaignBook.get(request.args.get("book_id"), fetch_links=True)
            book.notes.remove(existing_note)
            await book.save()
        else:
            campaign.notes.remove(existing_note)

        await existing_note.delete()

        await post_to_audit_log(
            msg=f"Delete {campaign.name} note - `{existing_note.text}`",
            view=self.__class__.__name__,
        )
        await campaign.save()

        return "Note deleted"

    async def _post_campaign_book(self, campaign: Campaign) -> tuple[bool, str, QuartForm]:
        """Process the campaign book form."""
        form = await self._build_form(campaign)

        if await form.validate_on_submit():
            if form.data.get("book_id"):
                update_discord = campaign.name.strip() != form.name.data.strip()

                existing_book = await CampaignBook.get(form.data.get("book_id"))
                existing_book.name = form.name.data.strip()
                existing_book.description_short = form.description_short.data.strip()
                existing_book.description_long = form.description_long.data.strip()
                await existing_book.save()
                msg = f"Book {existing_book.name} updated"
                if update_discord:
                    await sync_book_to_discord(existing_book, DBSyncUpdateType.UPDATE)

            else:
                books = await campaign.fetch_books()
                new_book = CampaignBook(
                    name=form.name.data.strip(),
                    description_short=form.description_short.data.strip(),
                    description_long=form.description_long.data.strip(),
                    number=max([b.number for b in books], default=0) + 1,
                    campaign=str(campaign.id),
                )
                await new_book.save()
                campaign.books.append(new_book)
                await campaign.save()
                await sync_book_to_discord(new_book, DBSyncUpdateType.CREATE)
                msg = f"Book {new_book.name} created"

            await post_to_audit_log(
                msg=f"{campaign.name} Book - {msg}",
                view=self.__class__.__name__,
            )

            return True, msg, None

        return False, "", form

    async def _post_campaign_chapter(self, campaign: Campaign) -> tuple[bool, str, QuartForm]:
        """Process the campaign chapter form."""
        form = await self._build_form(campaign)

        if await form.validate_on_submit():
            if form.data.get("chapter_id"):
                existing_chapter = await CampaignBookChapter.get(form.data.get("chapter_id"))

                existing_chapter.name = form.name.data.strip().title()
                existing_chapter.description_short = form.description_short.data.strip()
                existing_chapter.description_long = form.description_long.data.strip()
                await existing_chapter.save()
                msg = "Chapter updated"

            else:
                book = await CampaignBook.get(form.data.get("book_id"), fetch_links=True)
                new_chapter = CampaignBookChapter(
                    name=form.name.data.strip().title(),
                    description_short=form.description_short.data.strip(),
                    description_long=form.description_long.data.strip(),
                    book=str(book.id),
                    number=max([c.number for c in await book.fetch_chapters()], default=0) + 1,
                )
                await new_chapter.save()
                book.chapters.append(new_chapter)
                await book.save()
                msg = "Chapter created"

            await post_to_audit_log(
                msg=f"{campaign.name} Chapter - {msg}",
                view=self.__class__.__name__,
            )

            return True, msg, None

        return False, "", form

    async def _post_campaign_description(self, campaign: Campaign) -> tuple[bool, str, QuartForm]:
        """Process the campaign description form."""
        form = await self._build_form(campaign)
        if await form.validate_on_submit():
            do_update_session = campaign.name.strip() != form.name.data.strip()
            campaign.name = form.name.data.strip()
            campaign.description = form.description.data.strip()
            await campaign.save()

            if do_update_session:
                await sync_campaign_to_discord(campaign, DBSyncUpdateType.UPDATE)
                await update_session()

            return True, "Campaign updated", None

        return False, "", form

    async def _post_note(self, campaign: Campaign) -> tuple[bool, str, QuartForm]:
        """Process the note form."""
        form = await self._build_form(campaign)

        if await form.validate_on_submit():
            if not form.data.get("note_id"):
                if form.data["book_id"]:
                    parent = await CampaignBook.get(form.data["book_id"], fetch_links=True)
                else:
                    parent = campaign

                new_note = Note(
                    text=form.data["text"].strip(),
                    parent_id=str(parent.id),
                    created_by=session["USER_ID"],
                )
                await new_note.save()
                parent.notes.append(new_note)
                await parent.save()
                msg = "Note Added"
            else:
                existing_note = await Note.get(form.data["note_id"])
                existing_note.text = form.data["text"]
                await existing_note.save()
                msg = "Note Updated"

            await post_to_audit_log(
                msg=f"{campaign.name} Note - {msg}",
                view=self.__class__.__name__,
            )

            return True, msg, None

        return False, "", form

    async def get(self, campaign_id: str = "") -> str:
        """Handle GET requests for editing a campaign item."""
        campaign = await fetch_active_campaign(campaign_id)

        return catalog.render(
            "campaign_view.FormPartial",
            campaign=campaign,
            form=await self._build_form(campaign),
            join_label=False,
            floating_label=True,
            post_url=url_for(self.edit_type.value.route, campaign_id=campaign_id),
            hx_target=f"#{self.edit_type.value.div_id}",
            tab=self.edit_type.value.tab,
        )

    async def post(self, campaign_id: str = "") -> Response | str:
        """Handle POST requests for editing a campaign item."""
        campaign = await fetch_active_campaign(campaign_id, fetch_links=True)

        match self.edit_type:
            case CampaignEditableInfo.DESCRIPTION:
                form_is_processed, msg, form = await self._post_campaign_description(campaign)

            case CampaignEditableInfo.BOOK:
                form_is_processed, msg, form = await self._post_campaign_book(campaign)

            case CampaignEditableInfo.CHAPTER:
                form_is_processed, msg, form = await self._post_campaign_chapter(campaign)

            case CampaignEditableInfo.NOTE:
                form_is_processed, msg, form = await self._post_note(campaign)

            case _:
                assert_never(self.edit_type)

        if form_is_processed:
            return Response(
                headers={
                    "HX-Redirect": url_for(
                        "campaign.view",
                        campaign_id=campaign_id,
                        success_msg=msg,
                    ),
                }
            )

        # If POST request does not validate, return errors
        return catalog.render(
            "campaign_view.FormPartial",
            campaign=campaign,
            form=form,
            join_label=False,
            floating_label=True,
            post_url=url_for(self.edit_type.value.route, campaign_id=campaign_id),
            hx_target=f"#{self.edit_type.value.div_id}",
            tab=self.edit_type.value.tab,
        )

    async def delete(self, campaign_id: str = "") -> Response:
        """Handle DELETE requests for deleting a campaign item."""
        campaign = await fetch_active_campaign(campaign_id, fetch_links=True)

        match self.edit_type:
            case CampaignEditableInfo.DESCRIPTION:
                pass

            case CampaignEditableInfo.BOOK:
                msg = await self._delete_campaign_book(campaign)

            case CampaignEditableInfo.CHAPTER:
                msg = await self._delete_campaign_chapter()

            case CampaignEditableInfo.NOTE:
                msg = await self._delete_note(campaign)
            case _:
                assert_never(self.edit_type)

        return Response(
            headers={
                "HX-Redirect": url_for(
                    "campaign.view",
                    campaign_id=campaign.id,
                    success_msg=msg,
                ),
            }
        )
