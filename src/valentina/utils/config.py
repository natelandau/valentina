"""Gather configuration from environment variables."""

from pathlib import Path
from typing import ClassVar

from confz import BaseConfig, ConfigSources, EnvSource

DIR = Path(__file__).parents[3].absolute()


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
    log_level: str = "INFO"
    mongo_database_name: str = "valentina"
    mongo_uri: str = "mongodb://localhost:27017"
    owner_channels: str
    owner_ids: str | None = None
    s3_bucket_name: str | None = None
    test_mongodb_uri: str = "mongodb://localhost:27017"
    test_mongodb_db: str = "valentina-test-db"

    CONFIG_SOURCES: ClassVar[ConfigSources | None] = [
        EnvSource(prefix="VALENTINA_", file=DIR / ".env", allow_all=True),
        EnvSource(prefix="VALENTINA_", file=DIR / ".env.secrets", allow_all=True),
    ]
