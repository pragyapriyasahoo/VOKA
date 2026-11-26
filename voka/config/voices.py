DEFAULT_VOICE_PROFILES = {
    "english": {
        "voice": "en-US-AriaNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "volume": "+0%"
    },
    "hindi": {
        "voice": "hi-IN-SwaraNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "volume": "+0%"
    }
}

CHARACTER_VOICES = {
    "Advit": {
        "english": {
            "voice": "en-GB-ThomasNeural",
            "rate": "-2%",
            "pitch": "+10Hz",
            "volume": "+0%"
        },
        "hindi": {
            "voice": "hi-IN-MadhurNeural",
            "rate": "+5%",
            "pitch": "+18Hz",
            "volume": "+0%"
        }
    },
    "Manya": {
        "english": {
            "voice": "en-US-AnaNeural",
            "rate": "+2%",
            "pitch": "+0Hz",
            "volume": "+0%"
        },
        "hindi": {
            "voice": "hi-IN-SwaraNeural",
            "rate": "+4%",
            "pitch": "+18Hz",
            "volume": "+0%"
        }
    },
    "Umesh": {
        "english": {
            "voice": "en-US-ChristopherNeural",
            "rate": "-10%",
            "pitch": "-12Hz",
            "volume": "+0%"
        },
        "hindi": {
            "voice": "hi-IN-MadhurNeural",
            "rate": "-10%",
            "pitch": "-12Hz",
            "volume": "+0%"
        }
    },
    "Prabhat": {
        "english": {
            "voice": "en-US-GuyNeural",
            "rate": "-3%",
            "pitch": "-4Hz",
            "volume": "+0%"
        },
        "hindi": {
            "voice": "hi-IN-MadhurNeural",
            "rate": "-3%",
            "pitch": "-3Hz",
            "volume": "+0%"
        }
    },
    "Prakriti": {
        "english": {
            "voice": "en-US-EmmaNeural",
            "rate": "-2%",
            "pitch": "-2Hz",
            "volume": "+0%"
        },
        "hindi": {
            "voice": "hi-IN-SwaraNeural",
            "rate": "-4%",
            "pitch": "-5Hz",
            "volume": "+0%"
        }
    }
}


def get_voice_profile(character, language):
    """
    Return the voice profile for a character in a language.
    """

    language = "hindi" if language == "hindi" else "english"

    profiles = CHARACTER_VOICES.get(character, {})
    profile = profiles.get(language)

    if profile is None:
        profile = DEFAULT_VOICE_PROFILES[language]

    return dict(profile)


def get_voice(language: str, character: str | None = None, emotion: str | None = None) -> str:
    """
    Get the base voice name for a language/character/emotion.
    """
    profile = get_voice_profile(character, language)
    return profile["voice"]