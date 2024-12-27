"""Blueprints for character_create."""

from quart import Blueprint

from .route_create_full import CreateFull1, CreateFull2
from .route_rng_player import CreateRNGCharacter
from .route_rng_storyteller import CreateStorytellerRNGCharacter
from .route_start import StartCharacterCreate

blueprint = Blueprint("character_create", __name__)


blueprint.add_url_rule(
    "/create_character", view_func=StartCharacterCreate.as_view("start"), methods=["GET", "POST"]
)

### Create Full Characters
blueprint.add_url_rule(
    "/create_character/create_1",
    view_func=CreateFull1.as_view("create_1"),
    methods=["GET", "POST"],
)
blueprint.add_url_rule(
    "/create_character/2/<string:character_id>/<string:char_class>",
    view_func=CreateFull2.as_view("create_2"),
    methods=["GET", "POST"],
)

### Create RNG Characters
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
