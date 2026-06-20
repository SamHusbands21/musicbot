from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import disnake
from disnake.ext import commands

from bot.config import Settings, load_settings
from bot.utils.logging import configure_logging
from bot.utils.storage import initialize_database


class MusicBot(commands.InteractionBot):
    def __init__(self, settings: Settings) -> None:
        intents = disnake.Intents.default()
        intents.guilds = True
        intents.voice_states = True
        intents.guild_messages = True
        super().__init__(
            intents=intents,
            test_guilds=list(settings.guild_ids) if settings.guild_ids else None,
        )
        self.settings = settings
        self.log = logging.getLogger("musicbot")

    async def setup_hook(self) -> None:
        await initialize_database(self.settings.sqlite_path)
        await self.load_extension("bot.cogs.music")

    async def on_ready(self) -> None:
        self.log.info(
            "Connected as %s (%s). Guilds=%d",
            self.user,
            self.user.id if self.user else "unknown",
            len(self.guilds),
        )


async def run_bot() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)

    sqlite_parent = Path(settings.sqlite_path).parent
    sqlite_parent.mkdir(parents=True, exist_ok=True)

    bot = MusicBot(settings)
    await bot.start(settings.discord_token)


def main() -> None:
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
