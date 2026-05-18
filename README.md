# Khyra AI — Demo Voice Backend

Backend for the live voice AI demo embedded in the Khyra AI landing page.
Visitors can pick a role, language, and voice, then speak to the AI in real time.

**Stack:** Python · FastAPI · Sarvam STT + TTS · Groq LLM · Browser WebSocket

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in SARVAM_API_KEY and GROQ_API_KEY
```

### 3. Run the server

```bash
cd src
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000` — the demo UI loads automatically.

---

## Project Structure

```
product_demo_voice/
├── src/
│   ├── main.py        FastAPI app + /ws WebSocket handler
│   ├── agents.py      Role-based LLM system prompts (edit these)
│   ├── config.py      Voices, languages, roles config
│   ├── llm.py         Groq LLM pool
│   ├── utils.py       Guardrails + JSON parser
│   ├── stt/           Sarvam STT module
│   └── tts/           Sarvam TTS module (streaming + collect)
├── static/
│   └── index.html     Single-file demo UI
├── .env.example
└── requirements.txt
```

---

## Configuration

All settings are in `.env` (see `.env.example`).

### API Keys

| Variable | Description |
|---|---|
| `SARVAM_API_KEY` | Sarvam AI API key (STT + TTS) |
| `GROQ_API_KEY` | Groq API key (LLM) |

### Demo Voices

Configure up to 4 Sarvam Bulbul voices shown in the UI:

```env
DEMO_VOICE_1_NAME=Meera
DEMO_VOICE_1_SPEAKER=meera
DEMO_VOICE_2_NAME=Arvind
DEMO_VOICE_2_SPEAKER=arvind
```

### Session Limits

```env
DEMO_SESSION_TIMEOUT_SEC=300   # max session duration
DEMO_MAX_TURNS=20              # max conversation turns
```

---

## Customising Role Prompts

Edit `src/agents.py` — each role has a placeholder prompt:

- `_APPOINTMENT_BOOKING_PROMPT`
- `_LEAD_FOLLOWUP_PROMPT`
- `_TECH_SUPPORT_PROMPT`

The language is automatically injected at runtime.

---

## WebSocket Protocol

**Client → Server**

| Message | Description |
|---|---|
| `{type:"init", role, language, voice_id}` | Start session |
| Binary frame (PCM s16le 16kHz) | Audio chunk from microphone |
| `{type:"audio_end"}` | User stopped speaking |

**Server → Client**

| Message | Description |
|---|---|
| `{type:"ready"}` | Session ready |
| `{type:"transcript", text}` | STT result |
| `{type:"response_text", text}` | LLM response |
| Binary frame (PCM s16le 16kHz) | TTS audio chunk |
| `{type:"audio_end"}` | TTS playback complete |
| `{type:"error", message}` | Error |
