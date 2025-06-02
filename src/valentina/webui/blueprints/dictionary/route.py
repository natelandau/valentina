"""Routes for the dictionary."""

from typing import ClassVar

from flask_discord import requires_authorization
from quart import abort, session
from quart.utils import run_sync
from quart.views import MethodView

from valentina.constants import HTTPStatus
from valentina.models import DictionaryTerm
from valentina.webui import catalog
from valentina.webui.constants import TableType
from valentina.webui.utils import link_terms


class Dictionary(MethodView):
    """Route for the dictionary."""

    decorators: ClassVar = [requires_authorization]

    async def get(self) -> str:
        """Get the dictionary home page."""
        terms = (
            await DictionaryTerm.find(DictionaryTerm.guild_id == session["GUILD_ID"])
            .sort(+DictionaryTerm.term)
            .to_list()
        )

        result = await run_sync(
            lambda: catalog.render(
                "dictionary.Home",
                terms=terms,
                table_type_dictionary=TableType.DICTIONARY,
            ),
        )()

        return await link_terms(result, link_type="html")


class DictionaryTermView(MethodView):
    """Route for a dictionary term."""

    decorators: ClassVar = [requires_authorization]

    async def get(self, term: str) -> str:
        """Get the dictionary term."""
        term = await DictionaryTerm.find_one(
            DictionaryTerm.guild_id == session["GUILD_ID"],
            DictionaryTerm.term == term,
        )

        if not term:
            return abort(HTTPStatus.NOT_FOUND.value, f"Term not found: {term}")

        result = await run_sync(
            lambda: catalog.render(
                "dictionary.Term",
                term=term,
            ),
        )()
        return await link_terms(result, link_type="html", excludes=[term.term])
