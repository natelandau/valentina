"""Gather configuration from environment variables."""

from pathlib import Path
from typing import Annotated, ClassVar

from confz import BaseConfig, ConfigSources, EnvSource
from pydantic import BeforeValidator

DIR = Path(__file__).parents[3].absolute()


def convert_to_boolean(value: str) -> bool:
    """Confz does not work well with Typer options. Confz requires a value for each CLI option, but Typer does not. To workaround this, for example, if --log-to-file is passed, we set the value to "True" regardless of what follows the CLI option."""
    return bool(value.lower() in ["true", "t", "1"])


ENV_BOOLEAN = Annotated[
    bool,
    BeforeValidator(convert_to_boolean),
]


#### NEW CONFIG ####
class ValentinaConfig(BaseConfig):  # type: ignore [misc]
    """Valentina configuration."""

    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    discord_token: str
    github_repo: str | None = None
    github_token: str | None = None
    guilds: str
    log_file: str = "/valentina/valentina.log"
    log_level_aws: str = "INFO"
    log_level_http: str = "WARNING"
    log_level_pymongo: str = "WARNING"
    log_level: str = "INFO"
    mongo_database_name: str = "valentina"
    mongo_uri: str = "mongodb://localhost:27017"
    owner_channels: str
    owner_ids: str | None = None
    s3_bucket_name: str | None = None
    test_mongo_uri: str = "mongodb://localhost:27017"
    test_mongo_database_name: str = "test_db"

    # WebUI Configuration
    webui_enable: ENV_BOOLEAN = False
    webui_host: str = "127.0.0.1"
    webui_port: str = "8000"
    webui_log_level: str = "INFO"
    webui_debug: ENV_BOOLEAN = False
    webui_base_url: str = ""
    discord_oauth_secret: str = ""
    discord_oauth_client_id: str = ""
    redis_password: str = ""
    redis_addr: str = "127.0.0.1:6379"
    webui_secret_key: str = ""

    CONFIG_SOURCES: ClassVar[ConfigSources | None] = [
        EnvSource(prefix="VALENTINA_", file=DIR / ".env", allow_all=True),
        EnvSource(prefix="VALENTINA_", file=DIR / ".env.secrets", allow_all=True),
    ]
