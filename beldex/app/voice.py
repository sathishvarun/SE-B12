"""Voice: speech-to-text (questions by voice) and text-to-speech (answers read aloud), English + Tamil.

Uses the OpenAI audio API with the key from .env. If no key is set the web app falls back to the
browser's own speech features, so voice still works (with lower quality).
"""
from __future__ import annotations

import hashlib
import re

from app.config import settings

STT_MODEL = __import__("os").getenv("STT_MODEL", "gpt-4o-mini-transcribe")
TTS_MODEL = __import__("os").getenv("TTS_MODEL", "gpt-4o-mini-tts")
TTS_VOICE = __import__("os").getenv("TTS_VOICE", "alloy")
CACHE = settings.data_dir / "tts_cache"
MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_TTS_CHARS = 1800


def available() -> bool:
    """Server-side voice needs a real OpenAI key (other providers don't share the same audio API)."""
    return bool(settings.openai_api_key) and (not settings.openai_base_url or "openai.com" in settings.openai_base_url)


def _client():
    from openai import OpenAI
    return OpenAI(api_key=settings.openai_api_key)


def transcribe(audio: bytes, mime: str, lang: str) -> str:
    ext = "mp4" if "mp4" in mime or "m4a" in mime else "ogg" if "ogg" in mime else "wav" if "wav" in mime else "webm"
    kw = {"model": STT_MODEL, "file": (f"question.{ext}", audio, mime or "audio/webm")}
    if lang == "ta":
        kw["language"] = "ta"
        kw["prompt"] = "Beldex, BDX, BChat, BelNet, BNS, masternode, hardfork"  # keeps product names right
    else:
        kw["prompt"] = "Beldex, BDX, BChat, BelNet, BNS, masternode, Obscura hardfork, Bulletproofs++"
    res = _client().audio.transcriptions.create(**kw)
    return (getattr(res, "text", "") or "").strip()


def speakable(text: str) -> str:
    """Turn an answer (markdown with [1] citations) into clean text for reading aloud."""
    t = re.sub(r"\[(\d{1,2})\]", "", text)
    t = re.sub(r"[*_`#>]", "", t)
    t = re.sub(r"^\s*[-•]\s*", "", t, flags=re.M)
    t = re.sub(r"\n{2,}", "\n", t).strip()
    return t[:MAX_TTS_CHARS]


def speak(text: str, lang: str) -> tuple[bytes, bool]:
    """Returns (mp3 bytes, from_cache). Same text is never paid for twice."""
    clean = speakable(text)
    key = hashlib.sha1(f"{TTS_MODEL}|{TTS_VOICE}|{lang}|{clean}".encode()).hexdigest()
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{key}.mp3"
    if path.exists():
        return path.read_bytes(), True
    kw = {"model": TTS_MODEL, "voice": TTS_VOICE, "input": clean, "response_format": "mp3"}
    if "tts-1" not in TTS_MODEL:
        kw["instructions"] = ("Speak in clear, natural Tamil as spoken in Tamil Nadu. Say product names like "
                              "Beldex, BChat and BelNet in English." if lang == "ta" else
                              "Speak clearly and warmly, like a helpful product expert.")
    data = _client().audio.speech.create(**kw).content
    path.write_bytes(data)
    return data, False
