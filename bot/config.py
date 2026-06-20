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

    tts_voice: str
    tts_http_port: int
    tts_public_base_url: str
    tts_storage_dir: str

    @property
    def lavalink_uri(self) -> str:
        scheme = "https" if self.lavalink_secure else "http"
        return f"{scheme}://{self.lavalink_host}:{self.lavalink_port}"


def _parse_guild_ids(raw: str) -> tuple[int, ...]:
    guild_ids: list[int] = []
    for part in raw.split(","):
        cleaned = part.strip().strip('"').strip("'")
        if not cleaned:
            continue
        if cleaned.isdigit():
            guild_ids.append(int(cleaned))
    return tuple(guild_ids)


def load_settings() -> Settings:
    raw_guild_ids = os.getenv("DISCORD_GUILD_IDS", "")
    guild_ids = _parse_guild_ids(raw_guild_ids)
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
        tts_voice=os.getenv("TTS_VOICE", "en-GB-RyanNeural"),
        tts_http_port=_as_int(os.getenv("TTS_HTTP_PORT"), 8080),
        tts_public_base_url=os.getenv("TTS_PUBLIC_BASE_URL", "http://bot:8080"),
        tts_storage_dir=os.getenv("TTS_STORAGE_DIR", "/data/tts"),
    )
