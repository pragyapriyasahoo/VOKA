def safety_response(entry, language: str = "english") -> str | None:
    if not entry:
        return None
    return entry["response_hi"] if language == "hindi" else entry["response_en"]
