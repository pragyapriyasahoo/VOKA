import json
from pathlib import Path

from voka.config.settings import DATA_DIR


def _load(name: str):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def get_character_rules(character: str) -> dict:
    return _load("character_rules.json").get(character, {})


def memory_specification() -> list[dict]:
    return _load("preferences_and_memory.json")