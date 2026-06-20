from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import aiohttp


SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SPOTIFY_ACCOUNTS_BASE = "https://accounts.spotify.com/api/token"


@dataclass(slots=True)
class SpotifyTrack:
    title: str
    artist: str
    isrc: str | None = None

    @property
    def search_query(self) -> str:
        if self.isrc:
            return f'"{self.title}" "{self.artist}" {self.isrc}'
        return f'"{self.title}" "{self.artist}"'


class SpotifyService:
    def __init__(self, client_id: str | None, client_secret: str | None) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: str | None = None
        self._token_expires_at = 0.0

    @property
    def enabled(self) -> bool:
        return bool(self.client_id and self.client_secret)

    async def _ensure_token(self) -> str:
        if not self.enabled:
            raise RuntimeError("Spotify credentials are missing.")
        now = time.time()
        if self._token and now < self._token_expires_at - 30:
            return self._token

        raw = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        auth = base64.b64encode(raw).decode("utf-8")
        headers = {"Authorization": f"Basic {auth}"}
        payload = {"grant_type": "client_credentials"}

        async with aiohttp.ClientSession() as session:
            async with session.post(SPOTIFY_ACCOUNTS_BASE, headers=headers, data=payload) as resp:
                data = await resp.json()
                if resp.status >= 400:
                    message = data.get("error_description") or data.get("error") or "Spotify auth failed"
                    raise RuntimeError(message)
                self._token = data["access_token"]
                self._token_expires_at = now + int(data.get("expires_in", 3600))
                return self._token

    async def _get(self, endpoint: str) -> dict[str, Any]:
        token = await self._ensure_token()
        headers = {"Authorization": f"Bearer {token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SPOTIFY_API_BASE}{endpoint}", headers=headers) as resp:
                data = await resp.json()
                if resp.status >= 400:
                    msg = data.get("error", {}).get("message", "Spotify request failed")
                    raise RuntimeError(msg)
                return data

    @staticmethod
    def parse_spotify_url(url: str) -> tuple[str, str] | None:
        parsed = urlparse(url)
        if "spotify.com" not in parsed.netloc:
            return None
        parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(parts) < 2:
            return None
        entity_type, entity_id = parts[0], parts[1]
        if entity_type not in {"track", "playlist", "album"}:
            return None
        return entity_type, entity_id

    async def resolve_url(self, url: str) -> list[SpotifyTrack]:
        parsed = self.parse_spotify_url(url)
        if not parsed:
            return []
        entity_type, entity_id = parsed
        if entity_type == "track":
            data = await self._get(f"/tracks/{entity_id}")
            return [self._track_from_payload(data)]
        if entity_type == "album":
            data = await self._get(f"/albums/{entity_id}?market=from_token")
            return [self._track_from_payload(item) for item in data.get("tracks", {}).get("items", [])]
        data = await self._get(f"/playlists/{entity_id}?market=from_token")
        tracks: list[SpotifyTrack] = []
        for item in data.get("tracks", {}).get("items", []):
            track_payload = item.get("track")
            if track_payload:
                tracks.append(self._track_from_payload(track_payload))
        return tracks

    @staticmethod
    def _track_from_payload(payload: dict[str, Any]) -> SpotifyTrack:
        artists = payload.get("artists", [])
        primary_artist = artists[0]["name"] if artists else "Unknown Artist"
        external_ids = payload.get("external_ids") or {}
        return SpotifyTrack(
            title=payload.get("name", "Unknown Title"),
            artist=primary_artist,
            isrc=external_ids.get("isrc"),
        )
