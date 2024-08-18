"""Routes for the webui module."""

from quart import Blueprint

from valentina.webui.views import (
    CampaignOverviewSnippet,
    CampaignView,
    CharacterEdit,
    CharacterView,
    CreateCharacterStart,
    CreateCharacterStep1,
    CreateCharacterStep2,
    CreateCharacterStep3,
    DiceRollView,
    GameplayView,
)

campaign_bp = Blueprint("campaign", __name__)
campaign_bp.add_url_rule(
    "/campaign/<string:campaign_id>",
    view_func=CampaignView.as_view("campaign_view"),
    methods=["GET", "POST"],
)
campaign_bp.add_url_rule(
    "/campaign/<string:campaign_id>/overview",
    view_func=CampaignOverviewSnippet.as_view("campaign_overview"),
    methods=["GET", "POST"],
)

character_bp = Blueprint("character", __name__)
character_bp.add_url_rule(
    "/create_full",
    view_func=CreateCharacterStart.as_view("create_full_start"),
    methods=["GET"],
)
character_bp.add_url_rule(
    "/create_full/1",
    view_func=CreateCharacterStep1.as_view("create_full_1"),
    methods=["GET", "POST"],
)
character_bp.add_url_rule(
    "/create_full/2/<string:character_id>/<string:char_class>",
    view_func=CreateCharacterStep2.as_view("create_full_2"),
    methods=["GET", "POST"],
)
character_bp.add_url_rule(
    "/create_full/3/<string:character_id>",
    view_func=CreateCharacterStep3.as_view("create_full_3"),
    methods=["GET", "POST"],
)
character_bp.add_url_rule(
    "/character/<string:character_id>",
    view_func=CharacterView.as_view("character_view"),
    methods=["GET", "POST"],
)
character_bp.add_url_rule(
    "/character/<string:character_id>/edit",
    view_func=CharacterEdit.as_view("character_edit"),
    methods=["GET", "POST"],
)

gameplay_bp = Blueprint("gameplay", __name__)
gameplay_bp.add_url_rule("/gameplay", view_func=GameplayView.as_view("gameplay"), methods=["GET"])
gameplay_bp.add_url_rule(
    "/gameplay/diceroll",
    view_func=DiceRollView.as_view("diceroll"),
    methods=["GET", "POST"],
)
