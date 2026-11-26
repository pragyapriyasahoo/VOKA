import asyncio
import concurrent.futures
import tempfile
from pathlib import Path

import pygame

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

from voka.config.voices import get_voice, get_voice_profile


def clean_for_speech(text: str) -> str:
    import re
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = re.sub(
        r"[\U0001F000-\U0001FAFF"
        r"\U00002600-\U000027BF"
        r"\U00002B00-\U00002BFF"
        r"\U0000FE00-\U0000FE0F"
        r"\U0000200D\U000020E3]",
        "",
        text,
    )
    text = re.sub(r"[*_`#]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _generate_speech_edge_sync(text: str, voice: str, output_file: str, rate: str = "+0%", pitch: str = "+0Hz", volume: str = "+0%"):
    """Synchronous wrapper for Edge TTS with timeout."""
    import asyncio
    async def _inner():
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch, volume=volume)
        await communicate.save(output_file)
    
    # Run with timeout in new event loop
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(asyncio.wait_for(_inner(), timeout=10.0))
    finally:
        loop.close()


def generate_speech_pyttsx3(text: str, voice: str, output_file: str, rate: str = "+0%", pitch: str = "+0Hz", volume: str = "+0%"):
    """Generate speech using local pyttsx3 engine."""
    engine = pyttsx3.init()
    
    # Set properties (pyttsx3 uses different format)
    # Rate: default ~200, parse +0% as multiplier
    try:
        rate_val = int(rate.replace("+", "").replace("%", ""))
        engine.setProperty('rate', 200 + (rate_val * 2))
    except:
        engine.setProperty('rate', 200)
    
    # Volume: parse +0% as 0.0-1.0
    try:
        vol_val = int(volume.replace("+", "").replace("%", ""))
        engine.setProperty('volume', max(0.0, min(1.0, 0.5 + vol_val * 0.01)))
    except:
        engine.setProperty('volume', 1.0)
    
    # Voice selection - try to match
    voices = engine.getProperty('voices')
    for v in voices:
        if voice.lower() in v.name.lower() or voice.lower() in v.id.lower():
            engine.setProperty('voice', v.id)
            break
    
    # pyttsx3 on Windows only outputs WAV format
    # Always use .wav extension
    wav_file = Path(output_file).with_suffix('.wav')
    
    print(f"[TTS] Generating WAV to: {wav_file}")
    engine.save_to_file(text, str(wav_file))
    engine.runAndWait()
    
    # Verify file was created
    if not wav_file.exists():
        raise RuntimeError(f"pyttsx3 failed to create output file: {wav_file}")
    
    print(f"[TTS] Generated WAV file size: {wav_file.stat().st_size} bytes")
    
    return wav_file


def speak(text: str, language: str = "english", character: str | None = None, emotion: str | None = None):
    text = clean_for_speech(text)
    if not text:
        return
    
    profile = get_voice_profile(character, language) if character else get_voice_profile(None, language)
    voice = profile["voice"]
    rate = profile.get("rate", "+0%")
    pitch = profile.get("pitch", "+0Hz")
    volume = profile.get("volume", "+0%")

    print(f"[TTS] language: {language}")
    print(f"[TTS] character: {character or 'default'}")
    print(f"[TTS] voice: {voice} (rate {rate}, pitch {pitch})")

    # Use .mp3 for Edge TTS, .wav for pyttsx3
    output = Path(tempfile.mktemp(suffix=".mp3"))
    actual_output = output
    try:
        # Try Edge TTS first (cloud) with thread timeout
        if EDGE_TTS_AVAILABLE:
            try:
                print("[TTS] Trying Edge TTS (cloud)...")
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_generate_speech_edge_sync, text, voice, str(output), rate, pitch, volume)
                    future.result(timeout=15)  # 15 second timeout
                print("[TTS] Using Edge TTS (cloud)")
                actual_output = output
            except concurrent.futures.TimeoutError:
                print("[TTS] Edge TTS timeout, falling back to local...")
                if PYTTSX3_AVAILABLE:
                    actual_output = generate_speech_pyttsx3(text, voice, str(output), rate, pitch, volume)
                    print("[TTS] Using pyttsx3 (local)")
                else:
                    raise
            except Exception as e:
                print(f"[TTS] Edge TTS failed: {e}")
                if PYTTSX3_AVAILABLE:
                    print("[TTS] Falling back to local pyttsx3...")
                    actual_output = generate_speech_pyttsx3(text, voice, str(output), rate, pitch, volume)
                    print("[TTS] Using pyttsx3 (local)")
                else:
                    raise
        elif PYTTSX3_AVAILABLE:
            actual_output = generate_speech_pyttsx3(text, voice, str(output), rate, pitch, volume)
            print("[TTS] Using pyttsx3 (local)")
        else:
            print("[TTS] No TTS engine available")
            return
        
        pygame.mixer.init()
        pygame.mixer.music.load(str(actual_output))
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.quit()
    finally:
        output.unlink(missing_ok=True)
        actual_output.unlink(missing_ok=True)