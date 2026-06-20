from __future__ import annotations

import logging
import random
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ADJECTIVES_FILE = DATA_DIR / "nonsense_adjectives.txt"
NOUNS_FILE = DATA_DIR / "nonsense_nouns.txt"


class NonsenseService:
    def __init__(self) -> None:
        self.log = logging.getLogger("musicbot.nonsense")
        self.adjectives = self._load_words(ADJECTIVES_FILE)
        self.nouns = self._load_words(NOUNS_FILE)
        if not self.adjectives or not self.nouns:
            raise RuntimeError(
                "Nonsense word lists are missing or empty. "
                "Run scripts/build_nonsense_wordlists.py to generate them."
            )
        self.log.info(
            "Loaded nonsense words: %d adjectives, %d nouns",
            len(self.adjectives),
            len(self.nouns),
        )

    @staticmethod
    def _load_words(path: Path) -> list[str]:
        if not path.exists():
            return []
        words = [line.strip().lower() for line in path.read_text(encoding="utf-8").splitlines()]
        return [word for word in words if word.isalpha() and len(word) >= 4]

    def generate_phrase(self) -> str:
        adjective = random.choice(self.adjectives)
        noun = random.choice(self.nouns)
        return f"{adjective.title()} {noun.title()}"
