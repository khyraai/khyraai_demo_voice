"""
main.py — Khyra AI Demo Voice Backend

Endpoints:
    GET  /               → serves static/index.html
    GET  /health         → health check
    GET  /config         → returns voices, languages, roles for the UI
    WS   /ws             → browser demo session (STT → LLM → TTS)

WebSocket protocol (client → server):
    {type: "init", role: str, language: str, voice_id: str}  — session setup
    Binary frames                                              — PCM s16le 16kHz audio chunks
    {type: "audio_end"}                                        — user stopped speaking

WebSocket protocol (server → client):
    {type: "transcript",     text: str}   — STT result
    {type: "response_text",  text: str}   — LLM response
    Binary frames                          — PCM s16le 16kHz TTS audio
    {type: "audio_end"}                    — TTS done
    {type: "error",          message: str}
    {type: "ready"}                        — session initialised
"""

import os
import re
import io
import wave
import json
import time
import asyncio
import uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

_SARVAM_API_KEY = lambda: os.getenv("SARVAM_API_KEY", "")

load_dotenv()

from llm import llm_pool, LLM_MODEL
from stt import run_stt_http, pcm16_to_wav_bytes
from tts import run_tts_stream_chunked, close_tts_http_clients
from prompts            import get_system_prompt, get_greeting
from config             import DEMO_VOICES, DEMO_LANGUAGES, DEMO_ROLES
from utils              import check_guardrails
from transcript_logger  import make_logger

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="Khyra AI Demo Voice")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATIC_DIR = Path(__file__).parent.parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

_DEMO_SESSION_TIMEOUT_SEC = int(os.getenv("DEMO_SESSION_TIMEOUT_SEC", "300"))
_MAX_TURNS_PER_SESSION    = int(os.getenv("DEMO_MAX_TURNS", "20"))

# ---------------------------------------------------------------------------
# Voice lookup helper
# ---------------------------------------------------------------------------
_VOICE_MAP       = {v["id"]: v["speaker"] for v in DEMO_VOICES}
_VOICE_LABEL_MAP = {v["id"]: v["label"]   for v in DEMO_VOICES}


def _resolve_speaker(voice_id: str) -> str:
    return _VOICE_MAP.get(voice_id, DEMO_VOICES[0]["speaker"] if DEMO_VOICES else "meera")


# ---------------------------------------------------------------------------
# PCM helper — accumulate raw bytes into a WAV for Sarvam STT
# ---------------------------------------------------------------------------
def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def index():
    html_path = _STATIC_DIR / "index.html"
    if html_path.exists():
        return FileResponse(str(html_path), media_type="text/html")
    return JSONResponse({"message": "Khyra AI Demo — UI not found. Place index.html in /static/"})


@app.get("/health")
def health():
    return {"status": "ok", "service": "Khyra AI Demo Voice"}


@app.get("/config")
def get_config():
    return {
        "voices":    DEMO_VOICES,
        "languages": DEMO_LANGUAGES,
        "roles":     DEMO_ROLES,
    }


# ---------------------------------------------------------------------------
# Greeting helper
# ---------------------------------------------------------------------------
async def _send_greeting(ws: WebSocket, role: str, domain: str, language: str, speaker: str, voice_label: str = "Khyra", tx_log=None):
    """Stream the opening greeting TTS to the client immediately on connect."""
    text = get_greeting(role, domain, language, voice_label)
    if tx_log is not None:
        tx_log.log_greeting(text)

    async def _sb(b):
        try: await ws.send_bytes(b)
        except Exception: pass

    async def _st(t):
        try: await ws.send_text(t)
        except Exception: pass

    await _st(json.dumps({"type": "response_text", "text": text}))
    try:
        first_chunk = True
        async for chunk in run_tts_stream_chunked(text, language=language, speaker=speaker, min_chunk_ms=200):
            if first_chunk:
                first_chunk = False
                await _st(json.dumps({"type": "audio_start", "sample_rate": 16000}))
            await _sb(chunk)
    except Exception as e:
        print(f"[GREETING] TTS error: {e}")
    finally:
        await _st(json.dumps({"type": "audio_end"}))


# ---------------------------------------------------------------------------
# WebSocket demo session
# ---------------------------------------------------------------------------
@app.websocket("/ws")
async def demo_ws(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())[:8]
    print(f"[WS:{session_id}] Connected")

    role          = "front_desk"
    domain        = "general_clinic"
    language      = "en-IN"
    voice_id      = DEMO_VOICES[0]["id"] if DEMO_VOICES else "voice_1"
    speaker       = _resolve_speaker(voice_id)
    voice_label   = _VOICE_LABEL_MAP.get(voice_id, "Khyra")
    tx_log        = None
    memory: list  = []
    system_prompt: str = ""  # cached at init — role/domain/language don't change mid-session
    turns         = 0
    audio_buffer  = bytearray()
    session_start = time.time()
    initialized   = False

    async def safe_send_text(payload: str):
        try:
            await websocket.send_text(payload)
        except Exception:
            pass

    async def safe_send_bytes(data: bytes):
        try:
            await websocket.send_bytes(data)
        except Exception:
            pass

    async def process_turn(pcm_bytes: bytes):
        nonlocal memory, turns, role, domain, language, speaker, voice_label, system_prompt

        turns += 1
        if turns > _MAX_TURNS_PER_SESSION:
            await safe_send_text(json.dumps({
                "type": "error",
                "message": "Demo session limit reached. Please refresh to start again."
            }))
            return

        # --- STT ---
        t0 = time.time()
        wav = await asyncio.to_thread(_pcm_to_wav, pcm_bytes)  # offload CPU-bound conversion
        try:
            user_text, detected_lang = await asyncio.wait_for(
                run_stt_http(wav, _SARVAM_API_KEY(), language_code=language, session_id=session_id, client_id="demo"),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            await safe_send_text(json.dumps({"type": "error", "message": "STT timeout"}))
            return
        except Exception as e:
            print(f"[WS:{session_id}] STT error: {e}")
            await safe_send_text(json.dumps({"type": "error", "message": "STT failed"}))
            return

        user_text = (user_text or "").strip()
        if not user_text:
            return

        print(f"[WS:{session_id}] STT ({time.time()-t0:.2f}s): '{user_text}'")
        await safe_send_text(json.dumps({"type": "transcript", "text": user_text}))

        # --- Guardrail ---
        blocked, guard_resp = check_guardrails(user_text)
        if blocked:
            response_text = guard_resp
        else:
            # --- LLM (uses cached system_prompt built at init) ---
            messages = [{"role": "system", "content": system_prompt}] + memory + [
                {"role": "user", "content": user_text}
            ]
            t1 = time.time()
            try:
                completion = await asyncio.wait_for(
                    llm_pool.chat.completions.create(
                        model=LLM_MODEL,
                        messages=messages,
                        max_tokens=700,
                        temperature=0.7,
                        _agent_name="demo",
                        _client_id="demo",
                    ),
                    timeout=20.0,
                )
                response_text = (completion.choices[0].message.content or "").strip()
                # Strip complete <think>...</think> blocks (reasoning models like sarvam-m)
                response_text = re.sub(r"<think>[\s\S]*?</think>\s*", "", response_text, flags=re.IGNORECASE).strip()
                # Strip incomplete/truncated <think> block (no closing tag — token limit hit mid-think)
                response_text = re.sub(r"<think>[\s\S]*", "", response_text, flags=re.IGNORECASE).strip()
                # If stripping left nothing, give a safe fallback
                if not response_text:
                    response_text = "I'm sorry, could you repeat that?"
            except asyncio.TimeoutError:
                await safe_send_text(json.dumps({"type": "error", "message": "LLM timeout"}))
                return
            except Exception as e:
                print(f"[WS:{session_id}] LLM error: {e}")
                await safe_send_text(json.dumps({"type": "error", "message": "LLM failed"}))
                return
            print(f"[WS:{session_id}] LLM ({time.time()-t1:.2f}s): '{response_text[:80]}'")

        # Update conversation memory (keep last 10 turns to limit context size)
        memory.append({"role": "user",      "content": user_text})
        memory.append({"role": "assistant", "content": response_text})
        if len(memory) > 20:
            memory = memory[-20:]

        if tx_log is not None:
            tx_log.log_turn(turns, user_text, response_text)
        await safe_send_text(json.dumps({"type": "response_text", "text": response_text}))

        # --- TTS ---
        t2 = time.time()
        try:
            first_chunk = True
            async for chunk in run_tts_stream_chunked(
                response_text,
                language=language,
                speaker=speaker,
                min_chunk_ms=200,
            ):
                if first_chunk:
                    first_chunk = False
                    ttfa = time.time() - t0  # full pipeline: STT start → first audio byte
                    print(f"[TTS] TTFA {ttfa:.3f}s (STT→first audio)  session={session_id}")
                    await safe_send_text(json.dumps({"type": "audio_start", "sample_rate": 16000}))
                await safe_send_bytes(chunk)
        except Exception as e:
            print(f"[WS:{session_id}] TTS error: {e}")
        finally:
            await safe_send_text(json.dumps({"type": "audio_end"}))
            print(f"[WS:{session_id}] TTS done ({time.time()-t2:.2f}s)")

    try:
        while True:
            # Session timeout guard
            if time.time() - session_start > _DEMO_SESSION_TIMEOUT_SEC:
                await safe_send_text(json.dumps({
                    "type": "error",
                    "message": "Session timed out. Please refresh."
                }))
                break

            message = await websocket.receive()

            # Text/JSON messages
            if message.get("type") == "websocket.receive" and message.get("text"):
                try:
                    data = json.loads(message["text"])
                except json.JSONDecodeError:
                    continue

                msg_type = data.get("type", "")

                if msg_type == "init":
                    role     = data.get("role",     role)
                    domain   = data.get("domain",   domain)
                    language = data.get("language", language)
                    voice_id    = data.get("voice_id", voice_id)
                    speaker     = _resolve_speaker(voice_id)
                    voice_label = _VOICE_LABEL_MAP.get(voice_id, "Khyra")
                    initialized = True
                    # Build system prompt once — role/domain/language don't change mid-session
                    system_prompt = get_system_prompt(role, domain, language, voice_label)
                    tx_log      = make_logger(session_id, role, domain, language, voice_label)
                    print(f"[WS:{session_id}] Init: role={role} domain={domain} lang={language} speaker={speaker} voice={voice_label}")
                    await safe_send_text(json.dumps({"type": "ready", "session_id": session_id}))
                    asyncio.create_task(_send_greeting(websocket, role, domain, language, speaker, voice_label, tx_log))


                elif msg_type == "audio_end":
                    if len(audio_buffer) > 0:
                        pcm_snapshot = bytes(audio_buffer)
                        audio_buffer.clear()
                        asyncio.create_task(process_turn(pcm_snapshot))

                elif msg_type == "ping":
                    await safe_send_text(json.dumps({"type": "pong"}))

            # Binary audio frames (PCM s16le 16kHz)
            elif message.get("type") == "websocket.receive" and message.get("bytes"):
                if initialized:
                    audio_buffer.extend(message["bytes"])

    except WebSocketDisconnect:
        print(f"[WS:{session_id}] Disconnected")
    except Exception as e:
        print(f"[WS:{session_id}] Error: {e}")
    finally:
        print(f"[WS:{session_id}] Session ended — turns={turns}")


# ---------------------------------------------------------------------------
# Shutdown
# ---------------------------------------------------------------------------
@app.on_event("shutdown")
async def shutdown():
    await close_tts_http_clients()
