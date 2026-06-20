#!/usr/bin/env python3
"""Build Scrabble-style nonsense word lists for /spoutnonsense."""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

import nltk
from nltk.corpus import cmudict, wordnet as wn

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "bot" / "data"
ADJECTIVES_OUT = DATA_DIR / "nonsense_adjectives.txt"
NOUNS_OUT = DATA_DIR / "nonsense_nouns.txt"
DENYLIST_PATH = ROOT / "scripts" / "denylist.txt"
SCRABBLE_URL = "https://raw.githubusercontent.com/redbo/scrabble/master/dictionary.txt"


def ensure_nltk_data() -> None:
    for resource in ("corpora/cmudict", "corpora/wordnet", "corpora/omw-1.4"):
        try:
            nltk.data.find(resource)
        except LookupError:
            package = resource.split("/", 1)[1]
            nltk.download(package, quiet=True)


def load_scrabble_words() -> set[str]:
    with urllib.request.urlopen(SCRABBLE_URL, timeout=30) as response:
        words = {line.decode("utf-8").strip().lower() for line in response if line.strip()}
    return {word for word in words if word.isalpha() and len(word) >= 4}


def load_denylist() -> set[str]:
    if not DENYLIST_PATH.exists():
        return set()
    return {line.strip().lower() for line in DENYLIST_PATH.read_text(encoding="utf-8").splitlines() if line.strip()}


def syllable_count(word: str, pronunciations: dict[str, list[list[str]]]) -> int:
    if word in pronunciations:
        phones = pronunciations[word][0]
        return sum(1 for phone in phones if phone[-1].isdigit())

    groups = re.findall(r"[aeiouy]+", word.lower())
    return max(1, len(groups))


def is_adjective(word: str) -> bool:
    return bool(wn.synsets(word, pos=wn.ADJ))


def is_noun(word: str) -> bool:
    return bool(wn.synsets(word, pos=wn.NOUN))


def build_lists(min_syllables: int = 3) -> tuple[list[str], list[str]]:
    ensure_nltk_data()
    pronunciations = cmudict.dict()
    scrabble_words = load_scrabble_words()
    denylist = load_denylist()

    adjectives: list[str] = []
    nouns: list[str] = []

    for word in sorted(scrabble_words):
        if word in denylist:
            continue
        if syllable_count(word, pronunciations) < min_syllables:
            continue
        if is_adjective(word):
            adjectives.append(word)
        if is_noun(word):
            nouns.append(word)

    return adjectives, nouns


def write_lists(adjectives: list[str], nouns: list[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ADJECTIVES_OUT.write_text("\n".join(adjectives) + "\n", encoding="utf-8")
    NOUNS_OUT.write_text("\n".join(nouns) + "\n", encoding="utf-8")
    print(f"Wrote {len(adjectives)} adjectives -> {ADJECTIVES_OUT}")
    print(f"Wrote {len(nouns)} nouns -> {NOUNS_OUT}")


def main() -> None:
    adjectives, nouns = build_lists()
    if not adjectives or not nouns:
        raise SystemExit("No words generated. Check dictionary sources and filters.")
    write_lists(adjectives, nouns)


if __name__ == "__main__":
    main()
