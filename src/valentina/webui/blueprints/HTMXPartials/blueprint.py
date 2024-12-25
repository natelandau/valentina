"""Blueprints for serving HTMX Partials."""

from quart import Blueprint

from valentina.webui.constants import TableType, TextType

from .others import AddExperienceView, CharacterImageView, SetDesperationOrDanger
from .route import EditTableView, EditTextView
from .sortables import SortBooksView, SortChaptersView

blueprint = Blueprint("partials", __name__, url_prefix="/partials")

# Routes for reuasable partials
for i in TableType:
    blueprint.add_url_rule(
        f"/table/{i.value.route_suffix}",
        view_func=EditTableView.as_view(i.value.route_suffix, table_type=i),
        methods=["GET", "POST", "DELETE", "PUT"],
    )

for t in TextType:
    blueprint.add_url_rule(
        f"/text/{t.value.route_suffix}",
        view_func=EditTextView.as_view(t.value.route_suffix, text_type=t),
        methods=["GET", "POST", "PUT"],
    )

# Routes for specific partials
blueprint.add_url_rule(
    "/addexperience/<int:target_id>",
    view_func=AddExperienceView.as_view("addexperience"),
    methods=["GET", "POST"],
)

blueprint.add_url_rule(
    "/characterimages/<string:character_id>",
    view_func=CharacterImageView.as_view("characterimages"),
    methods=["GET", "POST", "DELETE"],
)

blueprint.add_url_rule(
    "/sortbooks/<string:parent_id>",
    view_func=SortBooksView.as_view("sort_books"),
    methods=["GET", "POST"],
)

blueprint.add_url_rule(
    "/sortchapters/<string:parent_id>",
    view_func=SortChaptersView.as_view("sort_chapters"),
    methods=["GET", "POST"],
)

## Assorted partials
blueprint.add_url_rule(
    "/setdesperation/<string:campaign_id>",
    view_func=SetDesperationOrDanger.as_view("set_desperation"),
    methods=["GET", "POST"],
)
