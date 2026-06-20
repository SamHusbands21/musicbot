# Deployment Guide (Linux VPS + Docker Compose)

## 1) Provision host

- Ubuntu 22.04+ (or similar) with at least:
  - 2 vCPU
  - 2 GB RAM
  - 10 GB disk
- Install Docker Engine + Docker Compose plugin.

## 2) Clone and configure

1. Place repository on host.
2. Create `.env` from template:
   - `cp .env.example .env`
3. Set at minimum:
   - `DISCORD_TOKEN`
   - `LAVALINK_PASSWORD`
4. Optional (recommended for Spotify link handling):
   - `SPOTIFY_CLIENT_ID`
   - `SPOTIFY_CLIENT_SECRET`

## 3) Start services

```bash
docker compose up -d --build
```

Validate:

```bash
docker compose ps
docker compose logs -f lavalink
docker compose logs -f bot
```

## 4) Firewall and networking

- Discord bot does not require inbound HTTP from public internet.
- Port `2333` is exposed in compose by default for debugging; remove external mapping if not needed.
- Keep host updated and lock down SSH (keys only, disable password auth).

## 5) Auto-start on reboot

Compose uses `restart: unless-stopped`, so services restart with Docker daemon on reboot.

## 6) Update procedure

```bash
git pull
docker compose up -d --build
docker image prune -f
```
