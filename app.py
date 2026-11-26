import os

import requests

from characters import CHARACTERS
from voka.database.repositories import PersistenceService
from voka.emotion.classifier import predict_emotion
from voka.emotion.mapper import normalize_emotion
from voka.llm.prompts import build_prompt, detect_language
from voka.memory.extractor import save_relevant_memory as extract_memory_note
from voka.speech.stt import get_voice_input
from voka.speech.tts import speak

# ============================================================
# CONFIGURATION
# ============================================================

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "gemma3"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_DIR = os.path.join(BASE_DIR, "memory")

os.makedirs(MEMORY_DIR, exist_ok=True)

MAX_TURNS = 6


# ============================================================
# LEGACY FILE-BASED MEMORY (fallback only)
# ============================================================

def memory_file(character):
    return os.path.join(MEMORY_DIR, f"{character}.txt")


def load_long_memory(character):
    path = memory_file(character)
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        print("[ERROR] Memory loading error:", e)
        return ""


def append_long_memory(character, note):
    try:
        with open(memory_file(character), "a", encoding="utf-8") as f:
            f.write(note.strip() + "\n")
    except Exception as e:
        print("[ERROR] Memory saving error:", e)


# ============================================================
# OLLAMA
# ============================================================

def generate_response(prompt):
    payload = {"model": MODEL_NAME, "prompt": prompt, "stream": False}
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data["response"].strip()


# ============================================================
# MAIN
# ============================================================

def main():
    # Initialize persistence service (PostgreSQL required)
    try:
        persistence = PersistenceService(require_postgres=True)
    except RuntimeError as e:
        print(f"\n[ERROR] {e}")
        print("Please ensure PostgreSQL is running and .env is configured.")
        return

    print("\nAvailable characters:")
    for name in CHARACTERS:
        print("-", name)

    # Character selection
    character = input("\nSelect character: ").strip().title()
    if character not in CHARACTERS:
        print("[ERROR] Invalid character.")
        return

    print(f"\nChatting with {character}.")
    print("Type 'exit' to quit.\n")

    # Start database session
    session = persistence.start_session(character)

    try:
        while True:
            mode = input("Type 't' for text, 'v' for voice, or 'exit': ").strip().lower()

            if mode == "exit":
                break

            if mode == "v":
                user_input = get_voice_input()
                if not user_input:
                    continue
            elif mode == "t":
                user_input = input("You: ").strip()
                if not user_input:
                    continue
            else:
                print("[ERROR] Invalid option. Use 't', 'v', or 'exit'.")
                continue

            # Determine language
            language = detect_language(user_input)

            # Load conversation history and long-term memory from PostgreSQL
            history = persistence.get_history()
            long_memory = persistence.get_memory_text()

            # Analyze emotion
            raw_emotion = predict_emotion(user_input)
            user_emotion = normalize_emotion(raw_emotion) if raw_emotion else None
            confidence = 0.8 if user_emotion and user_emotion != "unknown" else None

            # Build prompt
            prompt = build_prompt(
                CHARACTERS[character]["system"],
                history,
                long_memory,
                user_input,
                emotion=user_emotion
            )

            try:
                reply = generate_response(prompt)

                print(f"\n{character}: {reply}\n")

                # Speak response
                speak(reply, language, character)

                # Extract memory note
                memory_note = extract_memory_note(character, user_input)

                # Atomically save the complete turn to PostgreSQL
                persistence.save_turn(
                    user_content=user_input,
                    assistant_content=reply,
                    language=language,
                    user_emotion=user_emotion,
                    confidence=confidence,
                    memory_note=memory_note
                )

            except requests.exceptions.ConnectionError:
                print("\n[ERROR] Could not connect to Ollama. Make sure Ollama is running.")
            except requests.exceptions.Timeout:
                print("\n[ERROR] Ollama request timed out.")
            except Exception as e:
                print(f"\n[ERROR] Error: {e}")

    finally:
        persistence.close()


# ============================================================
# PROGRAM ENTRY
# ============================================================

if __name__ == "__main__":
    main()