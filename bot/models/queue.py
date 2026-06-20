from __future__ import annotations

from dataclasses import dataclass, field
from typing import Deque
from collections import deque

import wavelink


@dataclass(slots=True)
class GuildQueue:
    guild_id: int
    tracks: Deque[wavelink.Playable] = field(default_factory=deque)

    def add(self, track: wavelink.Playable) -> None:
        self.tracks.append(track)

    def add_front(self, track: wavelink.Playable) -> None:
        self.tracks.appendleft(track)

    def pop_next(self) -> wavelink.Playable | None:
        if not self.tracks:
            return None
        return self.tracks.popleft()

    def clear(self) -> None:
        self.tracks.clear()

    def __len__(self) -> int:
        return len(self.tracks)
