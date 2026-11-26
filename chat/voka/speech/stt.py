import speech_recognition as sr


class VoiceInputError(RuntimeError):
    """A recoverable microphone or speech-recognition failure."""


def recognize_audio(recognizer: sr.Recognizer, audio):
    request_error = None
    for language in ("en-US", "hi-IN"):
        try:
            text = recognizer.recognize_google(audio, language=language)
            if text:
                return text, language
        except sr.UnknownValueError:
            continue
        except sr.RequestError as error:
            request_error = error
            continue
    if request_error:
        raise VoiceInputError(f"Speech recognition service error: {request_error}") from request_error
    raise VoiceInputError("Could not understand the audio.")


def get_voice_input(
    timeout: float = 10.0,
    phrase_time_limit: float | None = 15.0
) -> str | None:
    """
    Listen for voice input with configurable timeouts.
    
    Args:
        timeout: Maximum seconds to wait for speech to start.
        phrase_time_limit: Maximum seconds for a single phrase (None = no limit).
    
    Returns:
        Recognized text, or None if recognition failed.
    """
    recognizer = sr.Recognizer()

    print("\n[LISTENING] Speak in English, Hindi, or Hinglish.")

    try:
        with sr.Microphone() as source:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        text, _ = recognize_audio(recognizer, audio)

        print(f"[VOICE] You: {text}")

        return text

    except VoiceInputError as e:
        print(f"[ERROR] {e}")
        return None
    except sr.WaitTimeoutError:
        print("[ERROR] Listening timed out while waiting for speech.")
        return None
    except (AttributeError, OSError) as error:
        print(f"[ERROR] Microphone is unavailable: {error}")
        return None