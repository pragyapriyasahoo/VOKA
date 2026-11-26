import json
from voka.config.settings import DATA_DIR


def detect_safety_trigger(text: str):
    entries = json.loads((DATA_DIR / "crisis_redirect.json").read_text(encoding="utf-8"))
    lowered = text.lower()
    for entry in entries:
        if any(pattern in lowered for pattern in entry["patterns"]):
            return entry
    return None
