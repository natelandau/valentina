"""Sort items using sortable.js and HTMLX."""

from quart import request, session, url_for
from quart.utils import run_sync
from quart.views import MethodView

from valentina.constants import BrokerTaskType
from valentina.models import BrokerTask, Campaign, CampaignBook, CampaignBookChapter
from valentina.webui import catalog
from valentina.webui.utils.discord import post_to_audit_log


class SortBooksView(MethodView):
    """View to handle sorting of items."""

    async def get(self, parent_id: str) -> str:
        """Get a sortable list of books for a campaign.

        Fetch all books belonging to a campaign and render them in a sortable list view.
        The list allows drag-and-drop reordering of books.

        Args:
            parent_id (str): The ID of the parent campaign to get books for.

        Returns:
            str: Rendered HTML template containing the sortable book list.

        Raises:
            HTTPException: If campaign is not found or user lacks permissions.
        """
        books = await CampaignBook.find(CampaignBook.campaign == parent_id).to_list()
        page_title = "Sort Books"

        post_url = url_for("partials.sort_books", parent_id=parent_id)

        return await run_sync(
            lambda: catalog.render(
                "HTMXPartials.Sortable.Sortable",
                items=books,
                page_title=page_title,
                post_url=post_url,
            )
        )()

    async def post(self, parent_id: str) -> str:
        """Process book reordering requests and update positions in database.

        Handle POST requests containing new book sort orders. Update book positions in the database
        and create broker tasks to update Discord channels accordingly.

        Args:
            parent_id (str): ID of the campaign containing the books to sort

        Returns:
            str: Rendered HTML template containing the updated book list

        Raises:
            HTTPException: If campaign is not found or user lacks permissions
        """
        # Get all books for this campaign to ensure we have the complete set for reordering
        books = await CampaignBook.find(CampaignBook.campaign == parent_id).to_list()
        parent_campaign = await Campaign.get(parent_id)

        form_data = await request.form

        # Form data preserves order of elements as they were dragged, so we can use enumeration
        # to generate new sequential positions starting from 1
        new_order = {item_id: idx + 1 for idx, (item_id, _) in enumerate(form_data.items())}

        for item in books:
            if item.number != int(new_order[str(item.id)]):
                item.number = int(new_order[str(item.id)])
                await item.save()

                # Create new task to update Discord channels since book order affects channel sorting
                task = BrokerTask(
                    guild_id=session["GUILD_ID"],
                    author_name=session["USER_NAME"],
                    task=BrokerTaskType.CONFIRM_BOOK_CHANNEL,
                    data={"book_id": item.id, "campaign_id": item.campaign},
                )
                await task.save()

        await post_to_audit_log(
            msg=f"Sort books for campaign {parent_campaign.name}", view=self.__class__.__name__
        )

        return await run_sync(lambda: catalog.render("HTMXPartials.Sortable.Items", items=books))()


class SortChaptersView(MethodView):
    """View to handle sorting of chapters."""

    async def get(self, parent_id: str) -> str:
        """Get a sortable list of chapters for a campaign."""
        chapters = await CampaignBookChapter.find(CampaignBookChapter.book == parent_id).to_list()
        page_title = "Sort Chapters"

        post_url = url_for("partials.sort_chapters", parent_id=parent_id)

        return await run_sync(
            lambda: catalog.render(
                "HTMXPartials.Sortable.Sortable",
                items=chapters,
                page_title=page_title,
                post_url=post_url,
            )
        )()

    async def post(self, parent_id: str) -> str:
        """Process chapter reordering requests and update positions in database.

        Handle POST requests containing new chapter sort orders. Update chapter positions in the database
        and create broker tasks to update Discord channels accordingly.

        Args:
            parent_id (str): ID of the book containing the chapters to sort

        Returns:
            str: Rendered HTML template containing the updated chapter list

        Raises:
            HTTPException: If campaign is not found or user lacks permissions
        """
        # Get all books for this campaign to ensure we have the complete set for reordering
        chapters = await CampaignBookChapter.find(CampaignBookChapter.book == parent_id).to_list()
        parent_book = await CampaignBook.get(parent_id)

        form_data = await request.form

        # Form data preserves order of elements as they were dragged, so we can use enumeration
        # to generate new sequential positions starting from 1
        new_order = {item_id: idx + 1 for idx, (item_id, _) in enumerate(form_data.items())}

        for item in chapters:
            if item.number != int(new_order[str(item.id)]):
                item.number = int(new_order[str(item.id)])
                await item.save()

        await post_to_audit_log(
            msg=f"Sort chapters for book {parent_book.name}", view=self.__class__.__name__
        )

        return await run_sync(
            lambda: catalog.render("HTMXPartials.Sortable.Items", items=chapters)
        )()
