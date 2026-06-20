# Operations Runbook

## Health checks

- Service state:
  - `docker compose ps`
- Lavalink version endpoint (inside container):
  - `docker compose exec lavalink wget -qO- http://localhost:2333/version`
- Bot logs:
  - `docker compose logs -f bot`

## Common commands

- Restart bot only:
  - `docker compose restart bot`
- Restart Lavalink only:
  - `docker compose restart lavalink`
- Full restart:
  - `docker compose down && docker compose up -d`

## In-Discord diagnostics

- `/ping` - API latency
- `/stats` - queue and node summary
- `/reconnect` - force Lavalink reconnect (admin only)

## Failure scenarios

### Lavalink restart during playback

1. Restart Lavalink container.
2. Run `/reconnect`.
3. Re-queue failed tracks with `/play`.

### Source fails to resolve

- Check bot logs for resolver error.
- Verify Spotify credentials and rate limits.
- Retry query with plain text search.

## Backups

Persisted bot data is in Docker volume `bot_data` (SQLite DB path defaults to `/data/bot.db`).

Backup:

```bash
docker run --rm -v python_music_bot_bot_data:/from -v $(pwd):/to alpine sh -c "cd /from && tar czf /to/bot_data_backup.tgz ."
```

Restore (with services stopped):

```bash
docker run --rm -v python_music_bot_bot_data:/to -v $(pwd):/from alpine sh -c "cd /to && tar xzf /from/bot_data_backup.tgz"
```

## Resource tuning

- JVM memory for Lavalink: set `LAVALINK_JAVA_OPTS`.
- Queue cap: set `BOT_MAX_QUEUE_SIZE`.
- Idle disconnect: set `BOT_IDLE_TIMEOUT_SECONDS`.
