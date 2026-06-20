from __future__ import annotations

import asyncio
import logging
import time
import uuid
from pathlib import Path

import edge_tts
from aiohttp import web

DEFAULT_VOICE = "en-GB-RyanNeural"
TTS_MAX_AGE_SECONDS = 3600


class TtsService:
    def __init__(
        self,
        storage_dir: str,
        public_base_url: str,
        voice: str = DEFAULT_VOICE,
        http_port: int = 8080,
    ) -> None:
        self.log = logging.getLogger("musicbot.tts")
        self.storage_dir = Path(storage_dir)
        self.public_base_url = public_base_url.rstrip("/")
        self.voice = voice
        self.http_port = http_port
        self._runner: web.AppRunner | None = None
        self._site: web.BaseSite | None = None

    async def start(self) -> None:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        app = web.Application()
        app.router.add_get("/tts/{filename}", self._handle_tts_file)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, "0.0.0.0", self.http_port)
        await self._site.start()
        self.log.info("TTS HTTP server listening on 0.0.0.0:%s", self.http_port)

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
            self._site = None

    async def synthesize(self, text: str) -> str:
        self._cleanup_old_files()
        filename = f"{uuid.uuid4().hex}.mp3"
        output_path = self.storage_dir / filename
        communicate = edge_tts.Communicate(text=text, voice=self.voice)
        await communicate.save(str(output_path))
        return f"{self.public_base_url}/tts/{filename}"

    async def _handle_tts_file(self, request: web.Request) -> web.StreamResponse:
        filename = request.match_info["filename"]
        if ".." in filename or "/" in filename or "\\" in filename:
            raise web.HTTPBadRequest()
        file_path = self.storage_dir / filename
        if not file_path.exists() or not file_path.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(path=file_path, headers={"Content-Type": "audio/mpeg"})

    def _cleanup_old_files(self) -> None:
        cutoff = time.time() - TTS_MAX_AGE_SECONDS
        for path in self.storage_dir.glob("*.mp3"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
            except OSError:
                self.log.exception("Failed to delete old TTS file: %s", path)
