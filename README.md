# Self-Hosted Discord Music Bot

Discord music bot for private servers, built with Python + Disnake + Lavalink and deployed with Docker Compose.

## Features

- Slash commands: `/play`, `/pause`, `/resume`, `/skip`, `/queue`, `/nowplaying`, `/stop`, `/leave`
- Source support:
  - YouTube (search + URL playback through Lavalink plugin)
  - SoundCloud
  - Spotify URLs (track/playlist/album resolved to playable sources)
- Per-guild queue handling with cooldown anti-spam
- Auto-disconnect after idle timeout
- Admin diagnostics: `/ping`, `/stats`, `/reconnect`

## Quick start

1. Copy env template:
   - `cp .env.example .env`
2. Fill required credentials in `.env`:
   - `DISCORD_TOKEN`
   - `LAVALINK_PASSWORD`
   - Optional Spotify credentials for Spotify URL support
3. Start services:
   - `docker compose up -d --build`
4. View logs:
   - `docker compose logs -f bot`

## Required Discord settings

- Enable `MESSAGE CONTENT INTENT` only if you later add prefix/message commands.
- Current implementation uses slash commands and voice states.
- Invite bot with permissions:
  - View Channels
  - Connect
  - Speak
  - Use Application Commands

## Project layout

- `bot/main.py` - bot startup entrypoint
- `bot/cogs/music.py` - slash commands and event handlers
- `bot/services/player_service.py` - queue/player lifecycle
- `bot/services/source_resolver.py` - source resolution logic
- `bot/services/spotify_service.py` - Spotify metadata API integration
- `ops/lavalink/application.yml` - Lavalink + plugin configuration
- `docs/deploy.md` - VPS deployment guide
- `docs/operations.md` - operations, monitoring, and recovery

## Notes on Spotify playback

Spotify audio is not streamed directly. Spotify links are treated as metadata and mapped to playable sources (YouTube/SoundCloud).
