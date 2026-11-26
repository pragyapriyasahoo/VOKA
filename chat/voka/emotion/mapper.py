EMOTION_LABELS = {
    "angry",
    "anxious",
    "confused",
    "excited",
    "guilty",
    "happy",
    "hopeless",
    "lonely",
    "overwhelmed",
    "sad",
    "scared",
    "tired",
}


def normalize_emotion(emotion: str) -> str:
    normalized = emotion.strip().lower()
    return normalized if normalized in EMOTION_LABELS else "unknown"
