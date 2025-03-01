"""Blueprint for the dictionary."""

from quart import Blueprint

from .route import Dictionary, DictionaryTermView

blueprint = Blueprint("dictionary", __name__)

blueprint.add_url_rule(
    "/dictionary",
    view_func=Dictionary.as_view("home"),
    methods=["GET"],
)

blueprint.add_url_rule(
    "/dictionary/term/<string:term>",
    view_func=DictionaryTermView.as_view("term"),
    methods=["GET", "POST", "PUT", "DELETE"],
)
