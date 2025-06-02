"""Campaign view."""

from typing import ClassVar, assert_never

from flask_discord import requires_authorization
from quart import Response, abort, flash, request, session, url_for
from quart.utils import run_sync
from quart.views import MethodView
from quart_wtf import QuartForm

from valentina.constants import BrokerTaskType
from valentina.controllers import ChannelManager, PermissionManager, total_campaign_experience
from valentina.models import BrokerTask, Campaign, CampaignBook, Statistics
from valentina.webui import catalog
from valentina.webui.constants import CampaignEditableInfo, CampaignViewTab, TableType, TextType
from valentina.webui.utils import fetch_active_campaign, fetch_discord_guild, link_terms
from valentina.webui.utils.discord import post_to_audit_log

from .forms import CampaignBookForm


class CampaignView(MethodView):
    """View to handle campaign operations."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self) -> None:
        self.is_htmx = bool(request.headers.get("Hx-Request", False))
        self.permission_manager = PermissionManager(guild_id=session["GUILD_ID"])
        self.can_manage_campaign = False

    async def _compute_campaign_data(self, campaign: Campaign) -> dict:
        """Compute the campaign data for display in the overview tab.

        Args:
            campaign (Campaign): The campaign object to compute the data for.

        Returns:
            dict: The computed campaign data.
        """
        books = await campaign.fetch_books()
        player_characters = await campaign.fetch_player_characters()
        available_xp, total_xp, cool_points = await total_campaign_experience(campaign)
        return {
            "available_xp": available_xp,
            "total_xp": total_xp,
            "cool_points": cool_points,
            "num_books": len(books),
            "num_player_characters": len(player_characters),
            "danger": campaign.danger,
            "desperation": campaign.desperation,
        }

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
                campaign_data = await self._compute_campaign_data(campaign)
                result = await run_sync(
                    lambda: catalog.render(
                        "campaign.Overview",
                        campaign=campaign,
                        campaign_data=campaign_data,
                        text_type_campaign_desc=TextType.CAMPAIGN_DESCRIPTION,
                        can_manage_campaign=self.can_manage_campaign,
                    ),
                )()
                return await link_terms(result, link_type="html")

            case CampaignViewTab.BOOKS:
                books = await campaign.fetch_books()
                result = await run_sync(
                    lambda: catalog.render(
                        "campaign.Books",
                        campaign=campaign,
                        books=books,
                        CampaignEditableInfo=CampaignEditableInfo,
                        can_manage_campaign=self.can_manage_campaign,
                        table_type_note=TableType.NOTE,
                        table_type_chapter=TableType.CHAPTER,
                    ),
                )()
                return await link_terms(result, link_type="html")

            case CampaignViewTab.CHARACTERS:
                characters = await campaign.fetch_player_characters()
                result = await run_sync(
                    lambda: catalog.render(
                        "campaign.Characters",
                        campaign=campaign,
                        characters=characters,
                        can_manage_campaign=self.can_manage_campaign,
                        table_type_npc=TableType.NPC,
                    ),
                )()
                return await link_terms(result, link_type="html")

            case CampaignViewTab.STATISTICS:
                stats_engine = Statistics(guild_id=session["GUILD_ID"])
                statistics = await stats_engine.campaign_statistics(campaign, as_json=True)
                result = await run_sync(
                    lambda: catalog.render(
                        "campaign.Statistics",
                        campaign=campaign,
                        statistics=statistics,
                        CampaignEditableInfo=CampaignEditableInfo,
                        can_manage_campaign=self.can_manage_campaign,
                    ),
                )()
                return await link_terms(result, link_type="html")

            case CampaignViewTab.NOTES:
                result = await run_sync(
                    lambda: catalog.render(
                        "campaign.Notes",
                        items=campaign.notes,
                        can_manage_campaign=self.can_manage_campaign,
                        TableType=TableType.NOTE,
                        parent_id=campaign.id,
                    ),
                )()
                return await link_terms(result, link_type="html")

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
            session["USER_ID"],
        )

        if self.is_htmx and request.args.get("tab"):
            return await self.handle_tabs(campaign)

        campaign_data = await self._compute_campaign_data(campaign)
        result = await run_sync(
            lambda: catalog.render(
                "campaign.Main",
                campaign=campaign,
                campaign_data=campaign_data,
                tabs=CampaignViewTab,
                text_type_campaign_desc=TextType.CAMPAIGN_DESCRIPTION,
                can_manage_campaign=self.can_manage_campaign,
            ),
        )()
        return await link_terms(result, link_type="html")


class CampaignEditItem(MethodView):
    """View to handle editing of campaign items."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self, edit_type: CampaignEditableInfo) -> None:
        self.edit_type = edit_type

    async def _build_form(self) -> QuartForm:
        """Build the form for the campaign item."""
        data = {}

        match self.edit_type:
            case CampaignEditableInfo.BOOK:
                if request.args.get("book_id"):
                    existing_book = await CampaignBook.get(request.args.get("book_id"))
                    data["book_id"] = request.args.get("book_id")
                    data["name"] = existing_book.name
                    data["description_short"] = existing_book.description_short
                    data["description_long"] = existing_book.description_long
                return await CampaignBookForm().create_form(data=data)

            case _:
                assert_never(self.edit_type)

    async def _delete_campaign_book(self, campaign: Campaign) -> str:
        """Delete a campaign book and update related resources.

        Delete the specified campaign book, its associated Discord channel, and create tasks to
        reorder remaining book channels. Clean up any existing channel update tasks to prevent
        race conditions.

        Args:
            campaign (Campaign): The campaign containing the book to delete

        Returns:
            str: Success message confirming book deletion

        Raises:
            HTTPException: If book_id is not provided in request args
        """
        book_id = request.args.get("book_id")
        if not book_id:
            abort(400)

        book = await CampaignBook.get(book_id)

        # Delete Discord channel first to avoid orphaned channels if later steps fail
        discord_guild = await fetch_discord_guild(session["GUILD_ID"])
        channel_manager = ChannelManager(guild=discord_guild)
        await channel_manager.delete_book_channel(book=book)

        await campaign.delete_book(book)

        # When a book is deleted, the order of remaining books may change
        # Create tasks to update all book channels to reflect new ordering
        for linked_book in campaign.books:
            # Create new task to update each book's channel position
            task = BrokerTask(
                guild_id=session["GUILD_ID"],
                author_name=session["USER_NAME"],
                task=BrokerTaskType.CONFIRM_BOOK_CHANNEL,
                data={"book_id": linked_book.id, "campaign_id": campaign.id},  # type: ignore [attr-defined]
            )
            await task.insert()

        await post_to_audit_log(
            msg=f"Delete {campaign.name} book - `{book.name}`",
            view=self.__class__.__name__,
        )

        return "Book deleted"

    async def _post_campaign_book(self, campaign: Campaign) -> tuple[bool, str, QuartForm]:
        """Process the campaign book form."""
        form = await self._build_form()

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
                    task = BrokerTask(
                        guild_id=session["GUILD_ID"],
                        author_name=session["USER_NAME"],
                        task=BrokerTaskType.CONFIRM_BOOK_CHANNEL,
                        data={"book_id": existing_book.id, "campaign_id": campaign.id},
                    )
                    await task.insert()

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
                task = BrokerTask(
                    guild_id=session["GUILD_ID"],
                    author_name=session["USER_NAME"],
                    task=BrokerTaskType.CONFIRM_BOOK_CHANNEL,
                    data={"book_id": new_book.id, "campaign_id": campaign.id},
                )
                await task.insert()
                msg = f"Book {new_book.name} created"

            await post_to_audit_log(
                msg=f"{campaign.name} Book - {msg}",
                view=self.__class__.__name__,
            )

            return True, msg, None

        return False, "", form

    async def get(self, campaign_id: str = "") -> str:
        """Handle GET requests for editing a campaign item."""
        campaign = await fetch_active_campaign(campaign_id)

        return catalog.render(
            "campaign.FormPartial",
            campaign=campaign,
            form=await self._build_form(),
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
            case CampaignEditableInfo.BOOK:
                form_is_processed, msg, form = await self._post_campaign_book(campaign)

            case _:
                assert_never(self.edit_type)

        if form_is_processed:
            await flash(msg, "success")
            return f'<script>window.location.href="{url_for("campaign.view", campaign_id=campaign.id)}"</script>'

        # If POST request does not validate, return errors
        return catalog.render(
            "campaign.FormPartial",
            campaign=campaign,
            form=form,
            join_label=False,
            floating_label=True,
            post_url=url_for(self.edit_type.value.route, campaign_id=campaign_id),
            hx_target=f"#{self.edit_type.value.div_id}",
            tab=self.edit_type.value.tab,
        )

    async def delete(self, campaign_id: str = "") -> str:
        """Handle DELETE requests for deleting a campaign item."""
        campaign = await fetch_active_campaign(campaign_id, fetch_links=True)

        match self.edit_type:
            case CampaignEditableInfo.BOOK:
                msg = await self._delete_campaign_book(campaign)
                await flash(msg, "success")
                return f'<script>window.location.href="{url_for("campaign.view", campaign_id=campaign.id)}"</script>'

            case _:
                assert_never(self.edit_type)
