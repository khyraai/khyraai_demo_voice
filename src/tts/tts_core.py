"""
tts_core.py — Sarvam-only Text-to-Speech for the Khyra AI Demo

Provider: Sarvam Bulbul v3 (HTTP streaming) with v2 collect fallback

Exports:
    run_tts_stream_chunked(text, language, speaker, min_chunk_ms)
        async generator → PCM s16le 16kHz bytes

    run_tts_collect(text, language, speaker)
        → bytes (PCM s16le 16kHz)

    close_tts_http_clients()  — clean shutdown
"""

import io
import os
import wave
import base64
import asyncio
from typing import Optional, AsyncGenerator

import aiohttp


# ---------------------------------------------------------------------------
# Shared HTTP session
# ---------------------------------------------------------------------------
_HTTP_SESSION: Optional[aiohttp.ClientSession] = None
_HTTP_SESSION_LOCK = asyncio.Lock()

_REQUEST_TIMEOUT_SEC = float(os.getenv("TTS_REQUEST_TIMEOUT_SEC", "30.0"))
_SARVAM_TTS_URL         = "https://api.sarvam.ai/text-to-speech"
_SARVAM_TTS_STREAM_URL  = "https://api.sarvam.ai/text-to-speech/stream"
_SARVAM_TTS_MODEL_COLLECT = os.getenv("SARVAM_TTS_MODEL_COLLECT", "bulbul:v2")
_SARVAM_TTS_MODEL_STREAM  = os.getenv("SARVAM_TTS_MODEL_STREAM",  "bulbul:v3")
_SARVAM_TTS_PACE          = float(os.getenv("SARVAM_TTS_PACE", "0.95"))


async def _get_http_session() -> aiohttp.ClientSession:
    global _HTTP_SESSION
    if _HTTP_SESSION and not _HTTP_SESSION.closed:
        return _HTTP_SESSION
    async with _HTTP_SESSION_LOCK:
        if _HTTP_SESSION and not _HTTP_SESSION.closed:
            return _HTTP_SESSION
        connector = aiohttp.TCPConnector(
            limit=20,
            limit_per_host=10,
            ttl_dns_cache=300,
            keepalive_timeout=60,        # reuse TCP connection to api.sarvam.ai between TTS calls
            enable_cleanup_closed=True,  # prevent stale half-closed sockets accumulating
        )
        timeout = aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT_SEC)
        _HTTP_SESSION = aiohttp.ClientSession(connector=connector, timeout=timeout)
    return _HTTP_SESSION


async def close_tts_http_clients():
    global _HTTP_SESSION
    async with _HTTP_SESSION_LOCK:
        if _HTTP_SESSION and not _HTTP_SESSION.closed:
            await _HTTP_SESSION.close()
        _HTTP_SESSION = None


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------
def _wav_bytes_to_pcm16_16k(wav_bytes: bytes) -> bytes:
    """Extract raw PCM s16le from a 16kHz WAV."""
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            return wf.readframes(wf.getnframes())
    except Exception:
        return b""


def _lang_code(language: str) -> str:
    lang = (language or "en").lower()
    lang_map = {
        "en": "en-IN", "en-in": "en-IN",
        "hi": "hi-IN", "hi-in": "hi-IN",
        "kn": "kn-IN", "kn-in": "kn-IN",
        "ta": "ta-IN", "ta-in": "ta-IN",
        "te": "te-IN", "te-in": "te-IN",
        "ml": "ml-IN", "ml-in": "ml-IN",
        "bn": "bn-IN", "bn-in": "bn-IN",
        "gu": "gu-IN", "gu-in": "gu-IN",
        "mr": "mr-IN", "mr-in": "mr-IN",
        "pa": "pa-IN", "pa-in": "pa-IN",
        "od": "od-IN", "od-in": "od-IN",
    }
    return lang_map.get(lang, lang if "-" in lang else f"{lang}-IN")


# ---------------------------------------------------------------------------
# Sarvam streaming TTS (bulbul:v3)
# ---------------------------------------------------------------------------
async def _sarvam_stream_chunked(
    text: str,
    language: str,
    speaker: str,
    min_chunk_ms: int = 200,
) -> AsyncGenerator[bytes, None]:
    """Async generator yielding PCM s16le 16kHz from Sarvam streaming TTS."""
    key = os.getenv("SARVAM_API_KEY", "").strip()
    if not key:
        print("[TTS] SARVAM_API_KEY not set")
        return

    lc = _lang_code(language)
    headers = {"api-subscription-key": key, "Content-Type": "application/json"}
    payload = {
        "text":                 text,
        "target_language_code": lc,
        "speaker":              speaker,
        "model":                _SARVAM_TTS_MODEL_STREAM,
        "output_audio_codec":   "linear16",
        "speech_sample_rate":   16000,
        "pace":                 _SARVAM_TTS_PACE,
        "enable_preprocessing": True,
    }

    bytes_per_ms = 32  # 16kHz s16le = 32000 bytes/sec = 32 bytes/ms
    min_chunk_bytes = bytes_per_ms * min_chunk_ms
    buffer: list[bytes] = []
    buf_size = 0

    try:
        session = await _get_http_session()
        async with session.post(_SARVAM_TTS_STREAM_URL, headers=headers, json=payload) as resp:
            if resp.status != 200:
                body = await resp.text()
                print(f"[TTS][SARVAM-STREAM] HTTP {resp.status}: {body[:200]}")
                return
            async for chunk in resp.content.iter_chunked(8192):
                if not chunk:
                    continue
                buffer.append(chunk)
                buf_size += len(chunk)
                if buf_size >= min_chunk_bytes:
                    yield b"".join(buffer)
                    buffer = []
                    buf_size = 0
    except asyncio.TimeoutError:
        print("[TTS][SARVAM-STREAM] Timeout")
        return
    except Exception as exc:
        print(f"[TTS][SARVAM-STREAM] Exception: {exc}")
        return

    if buffer:
        yield b"".join(buffer)


# ---------------------------------------------------------------------------
# Sarvam collect TTS (bulbul:v2) — fallback / short texts
# ---------------------------------------------------------------------------
async def _sarvam_collect(
    text: str,
    language: str,
    speaker: str,
) -> bytes:
    """Returns PCM s16le 16kHz bytes via Sarvam HTTP collect endpoint."""
    key = os.getenv("SARVAM_API_KEY", "").strip()
    if not key:
        print("[TTS] SARVAM_API_KEY not set")
        return b""

    lc = _lang_code(language)
    headers = {"api-subscription-key": key, "Content-Type": "application/json"}
    payload = {
        "inputs":               [text],
        "target_language_code": lc,
        "speaker":              speaker,
        "model":                _SARVAM_TTS_MODEL_COLLECT,
        "speech_sample_rate":   16000,
        "enable_preprocessing": True,
    }

    try:
        session = await _get_http_session()
        async with session.post(_SARVAM_TTS_URL, headers=headers, json=payload) as resp:
            if resp.status != 200:
                body = await resp.text()
                print(f"[TTS][SARVAM-COLLECT] HTTP {resp.status}: {body[:200]}")
                return b""
            data = await resp.json(content_type=None)
            audios = data.get("audios", [])
            if not audios:
                print("[TTS][SARVAM-COLLECT] Empty audios field")
                return b""
            wav_bytes = base64.b64decode(audios[0])
            return _wav_bytes_to_pcm16_16k(wav_bytes)
    except asyncio.TimeoutError:
        print("[TTS][SARVAM-COLLECT] Timeout")
        return b""
    except Exception as exc:
        print(f"[TTS][SARVAM-COLLECT] Exception: {exc}")
        return b""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def run_tts_stream_chunked(
    text: str,
    language: str = "en",
    speaker: str = "meera",
    min_chunk_ms: int = 200,
) -> AsyncGenerator[bytes, None]:
    """
    Async generator yielding PCM s16le 16kHz chunks.

    Tries Sarvam streaming first; falls back to collect mode if it yields nothing.
    """
    if not (text or "").strip():
        return

    yielded = False
    async for chunk in _sarvam_stream_chunked(text, language, speaker, min_chunk_ms):
        yield chunk
        yielded = True

    if not yielded:
        print("[TTS] Streaming yielded nothing — falling back to collect")
        pcm = await _sarvam_collect(text, language, speaker)
        if pcm:
            yield pcm


async def run_tts_collect(
    text: str,
    language: str = "en",
    speaker: str = "meera",
) -> bytes:
    """Returns complete PCM s16le 16kHz bytes for the given text."""
    if not (text or "").strip():
        return b""
    return await _sarvam_collect(text, language, speaker)
