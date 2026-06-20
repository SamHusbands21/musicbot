from __future__ import annotations

import logging

import disnake
import wavelink
from disnake.ext import commands

from bot.services.player_service import PlayerService
from bot.services.source_resolver import SourceResolver, is_url
from bot.services.spotify_service import SpotifyService


class MusicCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot
        self.log = logging.getLogger("musicbot.cog")
        settings = bot.settings
        self.player_service = PlayerService(
            lavalink_uri=settings.lavalink_uri,
            lavalink_password=settings.lavalink_password,
            idle_timeout_seconds=settings.idle_timeout_seconds,
            max_queue_size=settings.max_queue_size,
            cooldown_seconds=settings.command_cooldown_seconds,
        )
        self.resolver = SourceResolver(
            spotify=SpotifyService(settings.spotify_client_id, settings.spotify_client_secret),
            max_queue_size=settings.max_queue_size,
        )

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await self.player_service.connect_nodes(self.bot)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload) -> None:
        if not payload.player or not payload.player.guild:
            return
        await self.player_service.on_track_end(payload.player.guild.id, payload.player)

    async def _preflight(
        self, inter: disnake.ApplicationCommandInteraction
    ) -> tuple[disnake.Guild, disnake.Member, disnake.VoiceChannel | disnake.StageChannel] | None:
        if not inter.guild or not isinstance(inter.author, disnake.Member):
            await inter.response.send_message("This command can only be used in a server.", ephemeral=True)
            return None

        member = inter.author
        if not member.voice or not member.voice.channel:
            await inter.response.send_message(
                "Join a voice channel first, then run this command.", ephemeral=True
            )
            return None
        if inter.guild.voice_client and inter.guild.voice_client.channel != member.voice.channel:
            await inter.response.send_message(
                "You need to be in the same voice channel as the bot.", ephemeral=True
            )
            return None

        cooldown = self.player_service.check_cooldown(inter.guild.id, member.id)
        if cooldown > 0:
            await inter.response.send_message(
                f"Slow down a bit. Try again in `{cooldown:.1f}s`.", ephemeral=True
            )
            return None
        return inter.guild, member, member.voice.channel

    @staticmethod
    def _track_choice(track: wavelink.Playable) -> disnake.OptionChoice:
        label = f"{track.title} — {track.author}".replace("\n", " ")
        if len(label) > 100:
            label = label[:97] + "..."
        value = track.uri or track.title
        if len(value) > 100:
            value = value[:100]
        return disnake.OptionChoice(name=label, value=value)

    @commands.slash_command(description="Play a song from YouTube/Spotify/SoundCloud URL or search query.")
    async def play(self, inter: disnake.ApplicationCommandInteraction, query: str) -> None:
        preflight = await self._preflight(inter)
        if not preflight:
            return
        guild, member, voice_channel = preflight

        await inter.response.defer()

        try:
            player = await self.player_service.get_or_connect_player(guild, voice_channel)
            tracks = await self.resolver.resolve_query(query)
            if not tracks:
                await inter.edit_original_response("No playable results found for that query.")
                return
            added, queue_size = await self.player_service.enqueue(guild.id, tracks)
            started = await self.player_service.maybe_start_playback(guild.id, player)
        except Exception as exc:
            self.log.exception("Failed to process /play")
            await inter.edit_original_response(f"Could not play track(s): `{exc}`")
            return

        if started and player.current:
            current = player.current
            await inter.edit_original_response(
                f"Now playing: **{current.title}** (`{current.author}`)\n"
                f"Added `{added}` track(s). Queue size: `{queue_size}`."
            )
            return

        await inter.edit_original_response(
            f"Added `{added}` track(s) to queue. Current queue size: `{queue_size}`.\n"
            f"Requested by {member.mention}."
        )

    @play.autocomplete("query")
    async def play_query_autocomplete(
        self, inter: disnake.ApplicationCommandInteraction, query: str
    ) -> list[disnake.OptionChoice]:
        if not query or len(query.strip()) < 2 or is_url(query):
            return []
        try:
            tracks = await self.resolver.search_suggestions(query, limit=10)
            return [self._track_choice(track) for track in tracks if track.uri or track.title]
        except Exception:
            self.log.exception("Autocomplete search failed.")
            return []

    @commands.slash_command(description="Pause current playback.")
    async def pause(self, inter: disnake.ApplicationCommandInteraction) -> None:
        preflight = await self._preflight(inter)
        if not preflight:
            return
        guild, _, _ = preflight
        player = guild.voice_client
        if not player or not isinstance(player, wavelink.Player):
            await inter.response.send_message("Nothing is currently playing.", ephemeral=True)
            return
        await player.pause(True)
        await inter.response.send_message("Playback paused.")

    @commands.slash_command(description="Resume paused playback.")
    async def resume(self, inter: disnake.ApplicationCommandInteraction) -> None:
        preflight = await self._preflight(inter)
        if not preflight:
            return
        guild, _, _ = preflight
        player = guild.voice_client
        if not player or not isinstance(player, wavelink.Player):
            await inter.response.send_message("Nothing is currently playing.", ephemeral=True)
            return
        await player.pause(False)
        await inter.response.send_message("Playback resumed.")

    @commands.slash_command(description="Skip the current track.")
    async def skip(self, inter: disnake.ApplicationCommandInteraction) -> None:
        preflight = await self._preflight(inter)
        if not preflight:
            return
        guild, _, _ = preflight
        player = guild.voice_client
        if not player or not isinstance(player, wavelink.Player):
            await inter.response.send_message("Nothing is currently playing.", ephemeral=True)
            return
        skipped = await self.player_service.skip(guild.id, player)
        if skipped:
            await inter.response.send_message("Skipped.")
        else:
            await inter.response.send_message("Nothing to skip.", ephemeral=True)

    @commands.slash_command(description="Show up to 10 queued tracks.")
    async def queue(self, inter: disnake.ApplicationCommandInteraction) -> None:
        if not inter.guild:
            await inter.response.send_message("This command only works in servers.", ephemeral=True)
            return
        snapshot = self.player_service.queue_snapshot(inter.guild.id, limit=10)
        if not snapshot:
            await inter.response.send_message("Queue is empty.")
            return
        lines = [f"{index + 1}. {track.title} - {track.author}" for index, track in enumerate(snapshot)]
        await inter.response.send_message("**Queue:**\n" + "\n".join(lines))

    @commands.slash_command(description="Show the currently playing track.")
    async def nowplaying(self, inter: disnake.ApplicationCommandInteraction) -> None:
        if not inter.guild:
            await inter.response.send_message("This command only works in servers.", ephemeral=True)
            return
        player = inter.guild.voice_client
        if not player or not isinstance(player, wavelink.Player) or not player.current:
            await inter.response.send_message("Nothing is currently playing.")
            return
        current = player.current
        await inter.response.send_message(f"Now playing: **{current.title}** (`{current.author}`)")

    @commands.slash_command(description="Stop playback and clear queue.")
    async def stop(self, inter: disnake.ApplicationCommandInteraction) -> None:
        preflight = await self._preflight(inter)
        if not preflight:
            return
        guild, _, _ = preflight
        player = guild.voice_client
        if not player or not isinstance(player, wavelink.Player):
            await inter.response.send_message("Nothing is currently playing.", ephemeral=True)
            return
        await self.player_service.stop(guild.id, player)
        await inter.response.send_message("Stopped playback and cleared queue.")

    @commands.slash_command(description="Disconnect the bot from your voice channel.")
    async def leave(self, inter: disnake.ApplicationCommandInteraction) -> None:
        preflight = await self._preflight(inter)
        if not preflight:
            return
        guild, _, _ = preflight
        player = guild.voice_client
        if not player or not isinstance(player, wavelink.Player):
            await inter.response.send_message("I'm not in a voice channel.", ephemeral=True)
            return
        await self.player_service.leave(guild.id, player)
        await inter.response.send_message("Left voice channel and cleared queue.")

    @commands.slash_command(description="Latency/health check.")
    async def ping(self, inter: disnake.ApplicationCommandInteraction) -> None:
        await inter.response.send_message(f"Pong: `{self.bot.latency * 1000:.0f} ms`")

    @commands.slash_command(description="Show bot and player stats.")
    async def stats(self, inter: disnake.ApplicationCommandInteraction) -> None:
        data = self.player_service.stats()
        await inter.response.send_message(
            " | ".join(
                [
                    f"Guilds: `{len(self.bot.guilds)}`",
                    f"Queued tracks: `{data['total_queued_tracks']}`",
                    f"Active nodes: `{data['connected_nodes']}`",
                ]
            )
        )

    @commands.slash_command(description="Reconnect to Lavalink node.")
    @commands.has_permissions(administrator=True)
    async def reconnect(self, inter: disnake.ApplicationCommandInteraction) -> None:
        await inter.response.defer(ephemeral=True)
        try:
            await self.player_service.reconnect_nodes(self.bot)
        except Exception as exc:
            self.log.exception("Reconnect command failed.")
            await inter.edit_original_response(f"Reconnect failed: `{exc}`")
            return
        await inter.edit_original_response("Reconnected to Lavalink.")


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(MusicCog(bot))
