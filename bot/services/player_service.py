from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import Any

import disnake
import wavelink

from bot.models.queue import GuildQueue


class PlayerService:
    def __init__(
        self,
        lavalink_uri: str,
        lavalink_password: str,
        idle_timeout_seconds: int,
        max_queue_size: int,
        cooldown_seconds: int,
    ) -> None:
        self.log = logging.getLogger("musicbot.player")
        self.lavalink_uri = lavalink_uri
        self.lavalink_password = lavalink_password
        self.idle_timeout_seconds = idle_timeout_seconds
        self.max_queue_size = max_queue_size
        self.cooldown_seconds = cooldown_seconds

        self.guild_queues: dict[int, GuildQueue] = {}
        self.idle_tasks: dict[int, asyncio.Task[None]] = {}
        self.last_command_at: dict[int, dict[int, float]] = defaultdict(dict)
        self.connected = False

    async def connect_nodes(self, bot: disnake.Client) -> None:
        if self.connected:
            return
        node = wavelink.Node(uri=self.lavalink_uri, password=self.lavalink_password)
        await wavelink.Pool.connect(nodes=[node], client=bot, cache_capacity=100)
        self.connected = True
        self.log.info("Connected to Lavalink at %s", self.lavalink_uri)

    async def reconnect_nodes(self, bot: disnake.Client) -> None:
        try:
            await wavelink.Pool.close()
        except Exception:
            self.log.exception("Failed to close existing Lavalink pool.")
        self.connected = False
        await self.connect_nodes(bot)

    def get_queue(self, guild_id: int) -> GuildQueue:
        if guild_id not in self.guild_queues:
            self.guild_queues[guild_id] = GuildQueue(guild_id=guild_id)
        return self.guild_queues[guild_id]

    def check_cooldown(self, guild_id: int, user_id: int) -> float:
        now = time.monotonic()
        user_map = self.last_command_at[guild_id]
        previous = user_map.get(user_id, 0.0)
        user_map[user_id] = now
        remaining = self.cooldown_seconds - (now - previous)
        return max(0.0, remaining)

    async def get_or_connect_player(
        self,
        guild: disnake.Guild,
        voice_channel: disnake.VoiceChannel | disnake.StageChannel,
    ) -> wavelink.Player:
        player = guild.voice_client
        if player and isinstance(player, wavelink.Player):
            return player
        connected = await voice_channel.connect(cls=wavelink.Player, self_deaf=True)
        return connected

    async def enqueue(self, guild_id: int, tracks: list[wavelink.Playable]) -> tuple[int, int]:
        queue = self.get_queue(guild_id)
        added = 0
        for track in tracks:
            if len(queue) >= self.max_queue_size:
                break
            queue.add(track)
            added += 1
        return added, len(queue)

    async def play_interrupt(self, guild_id: int, player: wavelink.Player, track: wavelink.Playable) -> None:
        self._cancel_idle_task(guild_id)
        queue = self.get_queue(guild_id)
        current = player.current
        if player.playing and current:
            queue.add_front(current)
        queue.add_front(track)
        if player.playing:
            await self.skip(guild_id, player)
        else:
            await self.play_next(guild_id, player)

    async def maybe_start_playback(self, guild_id: int, player: wavelink.Player) -> bool:
        self._cancel_idle_task(guild_id)
        if player.playing:
            return False
        return await self.play_next(guild_id, player)

    async def play_next(self, guild_id: int, player: wavelink.Player) -> bool:
        queue = self.get_queue(guild_id)
        next_track = queue.pop_next()
        if not next_track:
            self._schedule_idle_disconnect(guild_id, player)
            return False
        await player.play(next_track)
        return True

    async def skip(self, guild_id: int, player: wavelink.Player) -> bool:
        self._cancel_idle_task(guild_id)
        if not player.current and not player.playing:
            return False
        if hasattr(player, "skip"):
            await player.skip(force=True)
        else:
            await player.stop(force=True)
        return True

    async def stop(self, guild_id: int, player: wavelink.Player) -> None:
        queue = self.get_queue(guild_id)
        queue.clear()
        self._cancel_idle_task(guild_id)
        await player.stop(force=True)

    async def leave(self, guild_id: int, player: wavelink.Player) -> None:
        queue = self.get_queue(guild_id)
        queue.clear()
        self._cancel_idle_task(guild_id)
        await player.disconnect()

    async def on_track_end(self, guild_id: int, player: wavelink.Player) -> None:
        await self.play_next(guild_id, player)

    def queue_snapshot(self, guild_id: int, limit: int = 10) -> list[wavelink.Playable]:
        queue = self.get_queue(guild_id)
        return list(queue.tracks)[:limit]

    def stats(self) -> dict[str, Any]:
        queue_depth = sum(len(queue) for queue in self.guild_queues.values())
        return {
            "guilds_with_queues": len(self.guild_queues),
            "total_queued_tracks": queue_depth,
            "connected_nodes": len(wavelink.Pool.nodes),
        }

    def _schedule_idle_disconnect(self, guild_id: int, player: wavelink.Player) -> None:
        self._cancel_idle_task(guild_id)

        async def _job() -> None:
            await asyncio.sleep(self.idle_timeout_seconds)
            queue = self.get_queue(guild_id)
            if queue.tracks:
                return
            if player.playing:
                return
            try:
                await player.disconnect()
                self.log.info("Disconnected guild %s due to idle timeout.", guild_id)
            except Exception:
                self.log.exception("Failed idle disconnect for guild %s", guild_id)

        self.idle_tasks[guild_id] = asyncio.create_task(_job())

    def _cancel_idle_task(self, guild_id: int) -> None:
        task = self.idle_tasks.pop(guild_id, None)
        if task and not task.done():
            task.cancel()
