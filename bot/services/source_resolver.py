from __future__ import annotations

from typing import Iterable

import wavelink

from bot.services.spotify_service import SpotifyService


class SourceResolver:
    def __init__(self, spotify: SpotifyService, max_queue_size: int) -> None:
        self.spotify = spotify
        self.max_queue_size = max_queue_size

    async def resolve_query(self, query: str) -> list[wavelink.Playable]:
        query = query.strip()
        if not query:
            return []

        spotify_match = SpotifyService.parse_spotify_url(query)
        if spotify_match:
            return await self._resolve_spotify(query)

        return await self._search_direct(query)

    async def _resolve_spotify(self, url: str) -> list[wavelink.Playable]:
        if not self.spotify.enabled:
            raise RuntimeError(
                "Spotify links are not configured. Add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET."
            )
        spotify_tracks = await self.spotify.resolve_url(url)
        if not spotify_tracks:
            return []

        resolved: list[wavelink.Playable] = []
        for metadata in spotify_tracks[: self.max_queue_size]:
            search = f"ytsearch:{metadata.search_query}"
            tracks = await wavelink.Playable.search(search)
            first = self._first_track(tracks)
            if first:
                resolved.append(first)
        return resolved

    async def _search_direct(self, query: str) -> list[wavelink.Playable]:
        # Lavalink handles source-specific URL routing and search prefixes.
        search_query = query if query.startswith("http") else f"ytsearch:{query}"
        results = await wavelink.Playable.search(search_query)
        if isinstance(results, wavelink.Playlist):
            return list(results.tracks)
        return list(results)

    @staticmethod
    def _first_track(results: Iterable[wavelink.Playable] | wavelink.Playlist) -> wavelink.Playable | None:
        if isinstance(results, wavelink.Playlist):
            return results.tracks[0] if results.tracks else None
        for track in results:
            return track
        return None
