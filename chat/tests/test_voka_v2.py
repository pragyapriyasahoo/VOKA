from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

import voka.app as app
import voka.memory.manager as memory_manager
from voka.config.characters import CHARACTERS
from voka.emotion.mapper import normalize_emotion
from voka.llm.client import OllamaError, generate_response
from voka.llm.prompts import detect_language
from voka.memory.extractor import extract_memory
from voka.memory.manager import load_long_memory
from voka.speech.stt import VoiceInputError


ALL_EMOTIONS = {
    "angry", "anxious", "confused", "excited", "guilty", "happy",
    "hopeless", "lonely", "overwhelmed", "sad", "scared", "tired",
}


def test_normal_conversation_runs_emotion_prompt_and_ollama():
    captured = {}
    original_merge_context = app.merge_context
    
    # Create a mock persistence service
    mock_db = MagicMock()
    mock_db.get_recent_messages.return_value = []
    mock_db.get_memories.return_value = [{"memory_type": "preference", "content": "tea"}]
    mock_db.save_message.return_value = "msg-id"
    mock_db.save_memory.return_value = "mem-id"
    
    from voka.database.repositories import PersistenceService
    service = PersistenceService(database=mock_db, require_postgres=False)
    service.using_postgres = True
    service.database = mock_db
    service.start_session("Manya")
    
    # Mock embeddings to avoid loading model
    with patch("voka.rag.context.build_rag_context", return_value={
        "memories_raw": [],
        "knowledge_raw": [],
        "memories_formatted": "No relevant memories found.",
        "knowledge_formatted": "No relevant knowledge found.",
        "has_context": False,
    }):
        with patch.object(app, "detect_safety_trigger", return_value=None), \
             patch.object(app, "predict_emotion", return_value="sad") as emotion, \
             patch.object(app, "extract_memory", return_value=None) as extract, \
             patch.object(app, "generate_response", return_value="Hello back") as ollama, \
             patch("voka.app.get_persistence", return_value=service):
            
            def merge(*args, **kwargs):
                captured["prompt"] = original_merge_context(*args, **kwargs)
                return captured["prompt"]
            
            with patch.object(app, "merge_context", side_effect=merge):
                assert app.respond("Manya", "Hello, how are you?") == "Hello back"

    emotion.assert_called_once_with("Hello, how are you?")
    extract.assert_called_once_with("Hello, how are you?")
    ollama.assert_called_once()
    assert "CURRENT USER EMOTION" in captured["prompt"]
    assert "sad" in captured["prompt"]


def test_crisis_skips_emotion_memory_and_ollama():
    mock_db = MagicMock()
    from voka.database.repositories import PersistenceService
    service = PersistenceService(database=mock_db, require_postgres=False)
    service.using_postgres = True
    service.database = mock_db
    service.start_session("Manya")
    
    with patch("voka.rag.context.build_rag_context", return_value={
        "memories_raw": [],
        "knowledge_raw": [],
        "memories_formatted": "No relevant memories found.",
        "knowledge_formatted": "No relevant knowledge found.",
        "has_context": False,
    }):
        with patch.object(app, "predict_emotion") as emotion, \
             patch.object(app, "extract_memory") as extract, \
             patch.object(app, "generate_response") as ollama, \
             patch("voka.app.get_persistence", return_value=service):
            
            reply = app.respond("Manya", "I want to kill myself")

    assert "help" in reply.lower() or "support" in reply.lower()
    emotion.assert_not_called()
    extract.assert_not_called()
    ollama.assert_not_called()


def test_mapper_handles_all_model_labels():
    assert {normalize_emotion(label) for label in ALL_EMOTIONS} == ALL_EMOTIONS
    assert normalize_emotion("not-a-model-label") == "unknown"


def test_memory_extracts_preference_but_not_crisis():
    assert extract_memory("I like orange ice cream") == "User preference: I like orange ice cream"
    assert extract_memory("My name is Anant") == "User fact: My name is Anant"
    assert extract_memory("I want to kill myself") is None
    assert extract_memory("mujhe chai pasand hai") == "User preference: mujhe chai pasand hai"


def test_existing_root_memory_is_loaded():
    assert "orange ice cream" in load_long_memory("Manya")


def test_preference_is_persisted():
    mock_db = MagicMock()
    mock_db.get_recent_messages.return_value = []
    mock_db.get_memories.return_value = []
    mock_db.save_message.return_value = "msg-id"
    mock_db.save_memory.return_value = "mem-id"
    
    from voka.database.repositories import PersistenceService
    service = PersistenceService(database=mock_db, require_postgres=False)
    service.using_postgres = True
    service.database = mock_db
    service.start_session("Manya")
    
    with patch("voka.rag.context.build_rag_context", return_value={
        "memories_raw": [],
        "knowledge_raw": [],
        "memories_formatted": "No relevant memories found.",
        "knowledge_formatted": "No relevant knowledge found.",
        "has_context": False,
    }):
        with patch.object(app, "predict_emotion", return_value=None), \
             patch.object(app, "generate_response", return_value="Okay"), \
             patch("voka.app.get_persistence", return_value=service):
            
            app.respond("Manya", "I like mangoes!")
    
    # Verify save_memory was called with the preference
    mock_db.save_memory.assert_called()


def test_crisis_is_not_persisted():
    mock_db = MagicMock()
    from voka.database.repositories import PersistenceService
    service = PersistenceService(database=mock_db, require_postgres=False)
    service.using_postgres = True
    service.database = mock_db
    service.start_session("Manya")
    
    with patch("voka.rag.context.build_rag_context", return_value={
        "memories_raw": [],
        "knowledge_raw": [],
        "memories_formatted": "No relevant memories found.",
        "knowledge_formatted": "No relevant knowledge found.",
        "has_context": False,
    }):
        with patch("voka.app.get_persistence", return_value=service):
            app.respond("Manya", "I want to kill myself")
    
    # Crisis should not save memory
    mock_db.save_memory.assert_not_called()


def test_language_routing():
    assert detect_language("How are you?") == "english"
    assert detect_language("मैं आज बहुत उदास हूँ") == "hindi"
    assert detect_language("mujhe aaj bahut accha lag raha hai") == "hindi"
    assert detect_language("mujhe chai pasand hai!!!") == "hindi"
    assert detect_language("mujhe, aaj, bahut accha lag raha hai.") == "hindi"


def test_tts_failure_does_not_fail_text_response():
    with patch("builtins.input", side_effect=["Manya", "t", "Hello", "exit"]), \
         patch.object(app, "respond", return_value="Text reply"), \
         patch.object(app, "speak", side_effect=RuntimeError("TTS unavailable")):
        app.main()


def test_stt_failure_returns_to_loop():
    mock_db = MagicMock()
    from voka.database.repositories import PersistenceService
    service = PersistenceService(database=mock_db, require_postgres=False)
    service.using_postgres = True
    service.database = mock_db
    service.start_session("Manya")
    
    with patch("builtins.input", side_effect=["Manya", "v", "exit"]), \
         patch.object(app, "get_voice_input", side_effect=VoiceInputError("microphone unavailable")), \
         patch("voka.app.get_persistence", return_value=service):
        app.main()


def test_ollama_connection_failure_is_reported():
    import requests

    with patch("voka.llm.client.requests.post", side_effect=requests.exceptions.ConnectionError("refused")):
        try:
            generate_response("test")
        except OllamaError as error:
            assert "connect" in str(error).lower()
        else:
            raise AssertionError("Expected OllamaError")


def test_ollama_timeout_is_reported():
    import requests

    with patch("voka.llm.client.requests.post", side_effect=requests.exceptions.Timeout("slow")):
        try:
            generate_response("test")
        except OllamaError as error:
            assert "timed out" in str(error).lower()
        else:
            raise AssertionError("Expected OllamaError")


def test_all_characters_load():
    assert set(app.CHARACTERS) == {"Manya", "Umesh", "Prabhat", "Prakriti", "Advit"}
    assert all(character["voice_profile"] for character in CHARACTERS.values())