from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(slots=True, frozen=True)
class Settings:
    discord_token: str
    guild_ids: tuple[int, ...]
    bot_prefix: str
    log_level: str
    sqlite_path: str

    lavalink_host: str
    lavalink_port: int
    lavalink_password: str
    lavalink_secure: bool

    spotify_client_id: str | None
    spotify_client_secret: str | None

    idle_timeout_seconds: int
    max_queue_size: int
    command_cooldown_seconds: int

    @property
    def lavalink_uri(self) -> str:
        scheme = "https" if self.lavalink_secure else "http"
        return f"{scheme}://{self.lavalink_host}:{self.lavalink_port}"


def load_settings() -> Settings:
    raw_guild_ids = os.getenv("DISCORD_GUILD_IDS", "")
    guild_ids = tuple(
        int(value.strip()) for value in raw_guild_ids.split(",") if value.strip().isdigit()
    )
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise ValueError("DISCORD_TOKEN is required")

    return Settings(
        discord_token=token,
        guild_ids=guild_ids,
        bot_prefix=os.getenv("BOT_PREFIX", "!"),
        log_level=os.getenv("BOT_LOG_LEVEL", "INFO").upper(),
        sqlite_path=os.getenv("SQLITE_PATH", "/data/bot.db"),
        lavalink_host=os.getenv("LAVALINK_HOST", "localhost"),
        lavalink_port=_as_int(os.getenv("LAVALINK_PORT"), 2333),
        lavalink_password=os.getenv("LAVALINK_PASSWORD", "changeme"),
        lavalink_secure=_as_bool(os.getenv("LAVALINK_SECURE"), False),
        spotify_client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        spotify_client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        idle_timeout_seconds=_as_int(os.getenv("BOT_IDLE_TIMEOUT_SECONDS"), 180),
        max_queue_size=_as_int(os.getenv("BOT_MAX_QUEUE_SIZE"), 200),
        command_cooldown_seconds=_as_int(os.getenv("BOT_COMMAND_COOLDOWN_SECONDS"), 3),
    )
