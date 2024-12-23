"""Configuration for the web UI."""

from valentina.utils import ValentinaConfig

redis_address = (
    f"redis://:{ValentinaConfig().redis_password}@{ValentinaConfig().redis_addr}"
    if {ValentinaConfig().redis_password}
    else f"redis://{ValentinaConfig().redis_addr}"
)


class Config:
    """Base configuration for the web UI."""

    SECRET_KEY = ValentinaConfig().webui_secret_key
    DISCORD_CLIENT_ID = ValentinaConfig().discord_oauth_client_id
    DISCORD_CLIENT_SECRET = ValentinaConfig().discord_oauth_secret
    DISCORD_REDIRECT_URI = f"{ValentinaConfig().webui_base_url}/callback"
    DISCORD_BOT_TOKEN = ValentinaConfig().discord_token
    CLOUDFLARE_ANALYTICS_TOKEN = ValentinaConfig().cloudflare_analytics_token
    GOOGLE_ANALYTICS_ID = ValentinaConfig().google_analytics_id


class Production(Config):
    """Production environment configuration."""

    SESSION_TYPE = "redis"
    SESSION_REVERSE_PROXY = bool(ValentinaConfig().webui_behind_reverse_proxy)
    SESSION_PROTECTION = False
    SESSION_URI = redis_address


class Development(Config):
    """Development environment configuration."""

    DEBUG = True


class Testing(Config):
    """Testing environment configuration."""

    TESTING = True
    SECRET_KEY = "9a2b67970e3b47618342c41210c5e194"  # noqa: S105
    WTF_CSRF_ENABLED = False
