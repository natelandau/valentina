"""Blueprints for character_create."""

from quart import Blueprint

from .route_create_full import (
    CreateCharacterStep1,
    CreateCharacterStep2,
    CreateCharacterStep3,
)
from .route_rng_player import CreateRNGCharacter
from .route_rng_storyteller import CreateStorytellerRNGCharacter
from .route_start import StartCharacterCreate

blueprint = Blueprint("character_create", __name__)


blueprint.add_url_rule(
    "/create_character", view_func=StartCharacterCreate.as_view("start"), methods=["GET", "POST"]
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
blueprint.add_url_rule(
    "/create_character/rng/player",
    view_func=CreateRNGCharacter.as_view("rng_player"),
    methods=["GET", "POST"],
)
blueprint.add_url_rule(
    "/create_character/rng/storyteller",
    view_func=CreateStorytellerRNGCharacter.as_view("rng_storyteller"),
    methods=["GET", "POST"],
)
