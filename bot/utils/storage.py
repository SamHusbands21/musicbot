from __future__ import annotations

import aiosqlite


SCHEMA = """
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id INTEGER PRIMARY KEY,
    default_volume INTEGER NOT NULL DEFAULT 100,
    autoplay_enabled INTEGER NOT NULL DEFAULT 0
);
"""


async def initialize_database(path: str) -> None:
    async with aiosqlite.connect(path) as db:
        await db.executescript(SCHEMA)
        await db.commit()
