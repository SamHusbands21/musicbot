from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import disnake
from disnake.ext import commands
from disnake.ext.commands import CommandSyncFlags

from bot.config import Settings, load_settings
from bot.services.tts_service import TtsService
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
            command_sync_flags=CommandSyncFlags.default(),
        )
        self.settings = settings
        self.log = logging.getLogger("musicbot")
        self.tts_service = TtsService(
            storage_dir=settings.tts_storage_dir,
            public_base_url=settings.tts_public_base_url,
            voice=settings.tts_voice,
            http_port=settings.tts_http_port,
        )
        self._startup_done = False

        self.load_extension("bot.cogs.music")
        self.load_extension("bot.cogs.fun")

        command_names = sorted(self.all_slash_commands)
        self.log.info("Registered slash commands: %s", ", ".join(command_names) or "(none)")

    async def _startup(self) -> None:
        if self._startup_done:
            return
        self._startup_done = True

        await self.tts_service.start()

        if self.settings.guild_ids:
            self.log.info(
                "Syncing slash commands to guild(s): %s",
                ", ".join(map(str, self.settings.guild_ids)),
            )
        else:
            self.log.warning(
                "DISCORD_GUILD_IDS is empty. Slash commands sync globally and may take up to 1 hour to appear."
            )

        await self._sync_application_commands()
        self.log.info("Slash command sync completed.")

    async def on_connect(self) -> None:
        await self._startup()

    async def on_ready(self) -> None:
        for guild in self.guilds:
            self.log.info("Connected guild: %s (%s)", guild.name, guild.id)

        if self.settings.guild_ids:
            configured = set(self.settings.guild_ids)
            connected = {guild.id for guild in self.guilds}
            missing = configured - connected
            if missing:
                self.log.warning(
                    "Bot is NOT in configured guild(s): %s. "
                    "Slash commands will not appear there until the bot is invited.",
                    ", ".join(str(guild_id) for guild_id in sorted(missing)),
                )

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
    await initialize_database(settings.sqlite_path)

    bot = MusicBot(settings)
    await bot.start(settings.discord_token)


def main() -> None:
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
