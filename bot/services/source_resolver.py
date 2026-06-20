from __future__ import annotations

import re
import time
from typing import Iterable

import wavelink

from bot.services.spotify_service import SpotifyService

_URL_PATTERN = re.compile(
    r"^(https?://|www\.)|(youtube\.com|youtu\.be|spotify\.com|soundcloud\.com)",
    re.IGNORECASE,
)
_SUGGESTION_CACHE: dict[tuple[str, str], tuple[float, list[wavelink.Playable]]] = {}
_CACHE_TTL_SECONDS = 30.0


def is_url(query: str) -> bool:
    query = query.strip()
    if not query:
        return False
    if query.startswith("http://") or query.startswith("https://"):
        return True
    return bool(_URL_PATTERN.search(query))


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

        if is_url(query):
            return await self._load_url(query)

        return await self._search_direct(query)

    async def search_suggestions(self, query: str, limit: int = 10) -> list[wavelink.Playable]:
        query = query.strip()
        if len(query) < 2 or is_url(query):
            return []

        cache_key = ("global", query.lower())
        cached = _SUGGESTION_CACHE.get(cache_key)
        now = time.monotonic()
        if cached and now - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1][:limit]

        if not wavelink.Pool.nodes:
            return []

        try:
            results = await wavelink.Playable.search(f"ytsearch:{query}")
        except Exception:
            return []

        tracks: list[wavelink.Playable] = []
        if isinstance(results, wavelink.Playlist):
            tracks = list(results.tracks[:limit])
        else:
            for index, track in enumerate(results):
                if index >= limit:
                    break
                tracks.append(track)

        _SUGGESTION_CACHE[cache_key] = (now, tracks)
        return tracks

    async def _load_url(self, url: str) -> list[wavelink.Playable]:
        results = await wavelink.Playable.search(url)
        if isinstance(results, wavelink.Playlist):
            return list(results.tracks)
        return list(results)

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
        search_query = f"ytsearch:{query}"
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
