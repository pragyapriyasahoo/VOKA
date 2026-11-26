import sys

from voka.config.characters import CHARACTERS
from voka.database.repositories import PersistenceService
from voka.emotion.classifier import predict_emotion
from voka.emotion.mapper import normalize_emotion
from voka.llm.client import OllamaError, generate_response
from voka.llm.prompts import build_prompt, detect_language
from voka.memory.extractor import extract_memory, save_memory_note
from voka.memory.retriever import retrieve_memory
from voka.rag.context import build_rag_context, merge_context
from voka.safety.detector import detect_safety_trigger
from voka.safety.responses import safety_response
from voka.speech.voice_controller import VoiceInputError, get_voice_input, speak

conversation_memory = {character: [] for character in CHARACTERS}
persistence: PersistenceService | None = None


def get_persistence() -> PersistenceService:
    global persistence
    if persistence is None:
        persistence = PersistenceService()
    return persistence


def respond(character: str, user_input: str) -> str:
    store = get_persistence()
    if store.session is None or store.session.character != character:
        store.start_session(character)
    language = detect_language(user_input)
    safety_entry = detect_safety_trigger(user_input)
    reply = safety_response(safety_entry, language)
    if reply is not None:
        store.save_crisis_turn(user_input, reply, language)
        conversation_memory[character].append({"user": user_input, "assistant": reply})
        return reply
    emotion = normalize_emotion(predict_emotion(user_input) or "unknown")
    user_message_id = store.save_user_message(user_input, language, emotion if emotion != "unknown" else None)
    memory_note = extract_memory(user_input)

    # NEW: Build RAG context
    session = store._require_session()
    rag_context = build_rag_context(
        query=user_input,
        user_id=session.user_id,
        character_id=session.character_id,
        include_memories=True,
        include_knowledge=True,
    )

    # Build prompt with RAG context
    prompt = merge_context(
        system_prompt=CHARACTERS[character]["system"],
        history=store.get_history(exclude_latest=True),
        user_input=user_input,
        emotion=emotion,
        rag_context=rag_context,
        long_memory=store.get_memory_text(),  # legacy fallback
    )

    reply = generate_response(prompt)
    store.save_assistant_message(reply, language)
    if memory_note:
        store.save_memory(memory_note, user_message_id)
    conversation_memory[character].append({"user": user_input, "assistant": reply})
    return reply


def main():
    print("Available characters:")
    print("- " + "\n- ".join(CHARACTERS))
    character = input("\nSelect character: ").strip().title()
    if character not in CHARACTERS:
        print("Invalid character.")
        return
    store = get_persistence()
    store.start_session(character)
    print(f"\nChatting with {character}. Type 'exit' to quit.")
    while True:
        mode = input("Type 't' for text, 'v' for voice, or 'exit': ").strip().lower()
        if mode == "exit":
            store.close()
            return
        try:
            user_input = get_voice_input() if mode == "v" else input("You: ").strip() if mode == "t" else None
            if not user_input:
                print("Invalid option or empty input.")
                continue
        except VoiceInputError as error:
            print(f"Voice input error: {error}")
            continue
        except Exception as error:
            print(f"Input error: {error}")
            continue

        language = detect_language(user_input)
        try:
            reply = respond(character, user_input)
        except OllamaError as error:
            print(f"Ollama error: {error}")
            continue
        except Exception as error:
            print(f"Response error: {error}")
            continue

        print(f"\n{character}: {reply}\n")
        try:
            speak(reply, character, language, None)
        except Exception as error:
            print(f"TTS error: {error}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()
