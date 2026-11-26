import argparse

from voka.config.voices import get_voice_profile
from app import CHARACTERS, speak


HINDI_NAMES = {
    "Advit": "अद्वित",
    "Manya": "मान्या",
    "Umesh": "उमेश",
    "Prabhat": "प्रभात",
    "Prakriti": "प्रकृति",
}

ENGLISH_ALTERNATES = {
    "Advit": {
        "voice": "en-US-BrianNeural",
        "rate": "+2%",
        "pitch": "+22Hz",
        "volume": "+0%"
    },
    "Manya": {
        "voice": "en-GB-MaisieNeural",
        "rate": "+2%",
        "pitch": "+0Hz",
        "volume": "+0%"
    },
    "Umesh": {
        "voice": "en-US-AndrewNeural",
        "rate": "-8%",
        "pitch": "-10Hz",
        "volume": "+0%"
    },
    "Prabhat": {
        "voice": "en-IN-PrabhatNeural",
        "rate": "-3%",
        "pitch": "-4Hz",
        "volume": "+0%"
    },
    "Prakriti": {
        "voice": "en-IN-NeerjaExpressiveNeural",
        "rate": "-2%",
        "pitch": "-2Hz",
        "volume": "+0%"
    },
}


def sample_text(character, language):
    if language == "hindi":
        name = HINDI_NAMES.get(character, character)
        return (
            f"नमस्ते, मैं {name} हूँ। "
            "हिंदी में मेरी आवाज़ ऐसी सुनाई देती है।"
        )

    return (
        f"Hello, I am {character}. "
        "This is how I sound when I speak English."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Audition the character voices used by app.py."
    )
    parser.add_argument(
        "--language",
        choices=["english", "hindi", "all"],
        default="all"
    )
    parser.add_argument(
        "--character",
        choices=list(CHARACTERS),
        default=None
    )
    parser.add_argument(
        "--alternate",
        action="store_true",
        help="Play the alternate English voice for each character."
    )
    args = parser.parse_args()

    languages = (
        ["english", "hindi"]
        if args.language == "all"
        else [args.language]
    )

    characters = (
        [args.character]
        if args.character
        else list(CHARACTERS)
    )

    for character in characters:
        for language in languages:
            profile = None

            if args.alternate:
                if language != "english":
                    print(
                        f"Skipping {character} ({language}): "
                        "no alternate profile."
                    )
                    continue
                profile = ENGLISH_ALTERNATES.get(character)

            active = profile or get_voice_profile(
                character,
                language
            )

            print(
                f"\n▶ {character} [{language}] "
                f"voice={active['voice']} "
                f"rate={active['rate']} "
                f"pitch={active['pitch']}"
            )

            try:
                speak(
                    sample_text(character, language),
                    language,
                    character,
                    profile=profile
                )
            except Exception as error:
                print(
                    f"[ERROR] Preview failed for {character} "
                    f"({language}): {error}"
                )


if __name__ == "__main__":
    main()
