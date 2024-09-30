"""Blueprints for character_create."""

from quart import Blueprint

from .route import (
    CreateCharacterStart,
    CreateCharacterStep1,
    CreateCharacterStep2,
    CreateCharacterStep3,
)

blueprint = Blueprint("character_create", __name__)
blueprint.add_url_rule(
    "/create_character",
    view_func=CreateCharacterStart.as_view("start"),
    methods=["GET"],
)
blueprint.add_url_rule(
    "/create_character/1",
    view_func=CreateCharacterStep1.as_view("create_1"),
    methods=["GET", "POST"],
)
blueprint.add_url_rule(
    "/create_character/2/<string:character_id>/<string:char_class>",
    view_func=CreateCharacterStep2.as_view("create_2"),
    methods=["GET", "POST"],
)
blueprint.add_url_rule(
    "/create_character/3/<string:character_id>",
    view_func=CreateCharacterStep3.as_view("create_3"),
    methods=["GET", "POST"],
)
