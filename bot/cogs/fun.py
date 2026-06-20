from __future__ import annotations

import logging

import disnake
import wavelink
from disnake.ext import commands

from bot.services.nonsense_service import NonsenseService


class FunCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot
        self.log = logging.getLogger("musicbot.fun")
        self.nonsense = NonsenseService()

    def _music_cog(self):
        cog = self.bot.get_cog("MusicCog")
        if cog is None:
            raise RuntimeError("Music cog is not loaded.")
        return cog

    async def _voice_preflight(
        self, inter: disnake.ApplicationCommandInteraction
    ) -> tuple[disnake.Guild, disnake.VoiceChannel | disnake.StageChannel] | None:
        if not inter.guild or not isinstance(inter.author, disnake.Member):
            await inter.response.send_message("This command can only be used in a server.", ephemeral=True)
            return None
        member = inter.author
        if not member.voice or not member.voice.channel:
            await inter.response.send_message(
                "Join a voice channel first, then run this command.", ephemeral=True
            )
            return None
        return inter.guild, member.voice.channel

    @commands.slash_command(description="Spout a nonsense phrase in voice using Scrabble words.")
    async def spoutnonsense(self, inter: disnake.ApplicationCommandInteraction) -> None:
        preflight = await self._voice_preflight(inter)
        if not preflight:
            return
        guild, voice_channel = preflight

        tts_service = getattr(self.bot, "tts_service", None)
        if tts_service is None:
            await inter.response.send_message("TTS service is not available.", ephemeral=True)
            return

        await inter.response.defer()

        try:
            phrase = self.nonsense.generate_phrase()
            audio_url = await tts_service.synthesize(phrase)
            music = self._music_cog()
            player = await music.player_service.get_or_connect_player(guild, voice_channel)
            tracks = await wavelink.Playable.search(audio_url)
            if isinstance(tracks, wavelink.Playlist):
                track = tracks.tracks[0] if tracks.tracks else None
            else:
                track = next(iter(tracks), None)
            if not track:
                await inter.edit_original_response("Could not load TTS audio.")
                return
            await music.player_service.play_interrupt(guild.id, player, track)
        except Exception as exc:
            self.log.exception("Failed to process /spoutnonsense")
            await inter.edit_original_response(f"Could not spout nonsense: `{exc}`")
            return

        await inter.edit_original_response(f"**Spouted nonsense:** {phrase}")


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(FunCog(bot))
