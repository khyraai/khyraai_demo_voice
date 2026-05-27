# Khyra AI — Demo Voice Backend

Real-time voice AI receptionist demo powering the Khyra AI product page. Visitors select a role, domain, language, and voice — then speak directly to the AI in their browser, with no extra software required.

**Stack:** Python 3.11 · FastAPI · Sarvam STT + TTS (Bulbul v3) · Groq LLM (llama-3.3-70b) · WebSocket · Single-file browser UI

---

## Architecture

```
Browser (index.html)
│
│  Microphone PCM (s16le 16kHz)  ──►  WebSocket /ws
│  ◄──  PCM audio chunks (TTS)
│  ◄──  JSON events (transcript, response_text, ready, error)
│
└─── FastAPI  (main.py)
          │
          ├─ POST audio ──► STT (Sarvam)  ──► user_text
          │                  └─ vad_buffer.py  (VAD + silence detection)
          │                  └─ stt_metrics.py (latency + usage tracking)
          │
          ├─ user_text ──► Guardrails (utils.py)
          │                  └─ jailbreak / meta-question regex filter
          │
          ├─ user_text + history ──► LLM Pool (llm.py)
          │                           └─ Round-robin Groq keys
          │                           └─ Per-key asyncio.Semaphore
          │                           └─ Auto-retry on 429
          │                           └─ Token + cost metrics
          │
          ├─ System Prompt ──► prompts/ (builder.py)
          │                     └─ Role base  (front_desk / lead_followup / support_line)
          │                     └─ Domain fragment (10 domains)
          │                     └─ Shared blocks (realism, interruption, emotion, memory, identity)
          │                     └─ Language instruction (11 Indian languages + English)
          │
          └─ response_text ──► TTS (Sarvam Bulbul v3)
                                └─ Streaming chunks → WebSocket binary frames
```

---

## Roles & Domains

The system supports **3 primary roles**, each with multiple domain specialisations:

### 🏥 Front Desk — Reception & appointment management

| Domain | Description |
|--------|-------------|
| `dental_clinic` | Cleanings, root canals, braces, pain triage |
| `veterinary_clinic` | Pet appointments, emergency handling, multi-pet booking |
| `spa_salon` | Treatments, couples sessions, packages, upsells |
| `therapist_clinic` | Wellness consultations, sensitive emotional handling |
| `hotel_resort` | Room reservations, group bookings, special requests |
| `cosmetic_clinic` | Aesthetic consultations, discreet client handling |
| `general_clinic` | Multispecialty, walk-ins, insurance, prescription queries |

### 📞 Lead Follow-Up — Consultative outbound sales

| Domain | Description |
|--------|-------------|
| `ai_voice_services` | Selling Khyra AI — missed calls, consistency, ROI framing |
| `real_estate` | Property enquiries, site visits, RERA & legal deflection |
| `it_projects` | Custom software, automation, AI/ML, cloud consulting |

### 🛠️ Support Line — Enterprise technical helpdesk

| Domain | Description |
|--------|-------------|
| `devops_support` | K8s, CI/CD, Docker, cloud infra, outages, SSL/DNS |
| `access_management_support` | Login, MFA, VPN, account lockout, provisioning |
| `saas_product_support` | Billing disputes, onboarding, integrations, bug reports |

---

## Prompt Architecture

Prompts are assembled at runtime in `src/prompts/builder.py` by layering 4 tiers:

```
1. Role base prompt        — core workflow + tone for the role
2. Domain fragment         — domain-specific knowledge & behaviour rules
3. Shared behavior blocks  — appended to every prompt, in order:
      SHARED_REALISM        voice-call rules: 1-2 sentences, one question/turn
      SHARED_INTERRUPTION   correction & mid-sentence change handling
      SHARED_PARTIAL_SPEECH garbled / incomplete input recovery
      SHARED_EMOTIONAL      distress, anger & frustration response protocols
      SHARED_MEMORY         name/detail reuse, never re-ask known info
      SHARED_FAILURE_RECOVERY silence, off-topic, system-limit handling
      SHARED_IDENTITY       persona rules — redirect AI-identity questions
4. Language instruction    — forces response language (injected at runtime)
```

Files: `src/prompts/front_desk.py` · `src/prompts/lead_followup.py` · `src/prompts/support_line.py` · `src/prompts/shared.py`

---

## LLM Pool (`src/llm.py`)

Drop-in replacement for a single `AsyncGroq` client with:

- **Round-robin** across multiple Groq API keys (`GROQ_API_KEYS=key1,key2,key3`)
- **Per-key `asyncio.Semaphore`** — configurable concurrency cap (`LLM_MAX_CONCURRENT_PER_KEY`)
- **Auto-retry on 429** — rotates to the next key instantly, other errors back off exponentially
- **Sarvam 105B** — switchable via `LLM_PROVIDER=sarvam` with no code changes
- **Structured metrics** — per-key latency, token usage, USD cost, rate-limit hit counts

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/khyraai/khyraai_demo_voice.git
cd product_demo_voice
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in at minimum:

```env
SARVAM_API_KEY=your_sarvam_key
GROQ_API_KEY=your_groq_key
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
│
├── src/
│   ├── main.py               FastAPI app — HTTP endpoints + WebSocket /ws handler
│   ├── agents.py             Compatibility shim (re-exports from prompts/)
│   ├── config.py             Voices, languages, roles/domains registry
│   ├── llm.py                LLM pool — round-robin Groq/Sarvam, retries, metrics
│   ├── utils.py              Pre-LLM guardrails (jailbreak/meta filter) + JSON parser
│   │
│   ├── prompts/
│   │   ├── __init__.py       Public API: get_system_prompt(), get_greeting()
│   │   ├── builder.py        Assembles role + domain + shared + language into one prompt
│   │   ├── shared.py         Reusable blocks: realism, interruption, emotional, identity
│   │   ├── greetings.py      Per-domain randomised greeting pools
│   │   ├── front_desk.py     Front desk base + 7 domain fragments
│   │   ├── lead_followup.py  Lead follow-up base + 3 domain fragments
│   │   └── support_line.py   Support line base + 3 domain fragments
│   │
│   ├── stt/
│   │   ├── stt_core.py       Sarvam STT HTTP client, audio format converters
│   │   ├── stt_metrics.py    STT latency + usage metrics
│   │   └── vad_buffer.py     VAD speech chunk buffer with silence detection
│   │
│   └── tts/
│       └── tts_core.py       Sarvam Bulbul v3 streaming TTS → PCM chunks
│
├── static/
│   └── index.html            Single-file browser demo UI (no build step)
│
├── simulate_calls.py         Autonomous two-agent LLM stress-test (13 scenarios)
├── simulation_report.md      Latest stress-test results and LLM evaluation scorecard
├── .env.example              Environment variable reference
└── requirements.txt          Python dependencies
```

---

## Configuration Reference

All settings live in `.env`. See `.env.example` for the full list.

### API Keys

| Variable | Required | Description |
|----------|----------|-------------|
| `SARVAM_API_KEY` | ✅ | Sarvam AI key — used for both STT and TTS |
| `GROQ_API_KEY` | ✅ (default) | Single Groq key |
| `GROQ_API_KEYS` | Optional | Comma-separated pool: `key1,key2,key3` |

### LLM Provider

```env
LLM_PROVIDER=groq              # "groq" (default) or "sarvam"
LLM_MODEL=llama-3.3-70b-versatile
LLM_MODEL_SARVAM=sarvam-m      # used when LLM_PROVIDER=sarvam
LLM_MAX_CONCURRENT_PER_KEY=5
LLM_MAX_RETRIES=2
LLM_RETRY_DELAY_SEC=0.3
```

### Demo Voices (Sarvam Bulbul v3 speakers)

Up to 10 voices configurable via `.env`. Defaults shown:

```env
DEMO_VOICE_1_NAME=Priya    DEMO_VOICE_1_SPEAKER=priya
DEMO_VOICE_2_NAME=Kavya    DEMO_VOICE_2_SPEAKER=kavya
DEMO_VOICE_3_NAME=Neha     DEMO_VOICE_3_SPEAKER=neha
# ... up to DEMO_VOICE_10
```

### Languages Supported

`en-IN` · `hi-IN` · `kn-IN` · `ta-IN` · `te-IN` · `ml-IN` · `bn-IN` · `gu-IN` · `mr-IN` · `pa-IN` · `od-IN`

### Session Limits

```env
DEMO_SESSION_TIMEOUT_SEC=300   # hard session timeout (seconds)
DEMO_MAX_TURNS=20              # max conversation turns per session
```

---

## HTTP Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves `static/index.html` |
| `GET` | `/health` | `{"status": "ok"}` health check |
| `GET` | `/config` | Returns voices, languages, and roles config for the UI |
| `WS` | `/ws` | Live voice session (see protocol below) |

---

## WebSocket Protocol

### Client → Server

| Message | Description |
|---------|-------------|
| `{type: "init", role, domain, language, voice_id}` | Initialise session — triggers greeting |
| Binary frame (PCM s16le 16kHz) | Raw microphone audio chunks |
| `{type: "audio_end"}` | User stopped speaking — trigger STT → LLM → TTS |
| `{type: "ping"}` | Keepalive ping |

### Server → Client

| Message | Description |
|---------|-------------|
| `{type: "ready", session_id}` | Session initialised |
| `{type: "response_text", text}` | Greeting or LLM response text |
| `{type: "transcript", text}` | STT transcription of user speech |
| Binary frames (PCM s16le 16kHz) | Streaming TTS audio (200ms chunks) |
| `{type: "audio_end"}` | TTS playback stream complete |
| `{type: "error", message}` | Error (STT/LLM/TTS timeout or failure) |

---

## Security — Guardrails (`src/utils.py`)

All user input passes through a pre-LLM regex filter before hitting the model:

- **Jailbreak patterns** — blocks attempts to override instructions, persona reassignment, DAN-style prompts
- **Meta-question patterns** — blocks "who built you", "what model are you", "are you GPT" etc.

Blocked inputs return a fixed safe response immediately; the LLM is never called.

---

## Stress-Test Simulation (`simulate_calls.py`)

Autonomous two-agent LLM evaluation tool — no voice required.

```bash
python simulate_calls.py
```

Runs **13 scripted scenarios** (all roles × all domains) using two LLM agents:
- **Khyra agent** — the full production system prompt
- **Caller agent** — a crafted realistic human persona with injected edge cases

Each scenario covers difficulty levels from `MEDIUM` to `CHAOTIC`, with edge cases including: bad network, wrong dates, mid-call request changes, angry callers, emergency situations, AI-identity questions, multi-language mixing, and incomplete information.

**Output:**
- `simulation_report.md` — full transcripts + per-scenario scores
- `simulation_results.json` — raw evaluation data

**Last run result: 8.0 / 10 overall** across 10 evaluation dimensions.

| Dimension | Score |
|-----------|-------|
| Memory Retention | 9.0 |
| Task Completion | 8.8 |
| Conversation Flow | 8.1 |
| Error Recovery | 8.1 |
| Naturalness | 8.0 |
| Human-likeness | 8.0 |
| Overall Impression | 7.9 |
| Clarification Quality | 7.8 |
| Interrupt Handling | 7.3 |
| Emotional Handling | 7.3 |

---

## Customising Prompts

All prompt logic is in `src/prompts/`. No other files need editing.

| File | What to edit |
|------|-------------|
| `front_desk.py` | Add/modify front desk domains or base receptionist behaviour |
| `lead_followup.py` | Adjust sales conversation flow or add new lead domains |
| `support_line.py` | Change support escalation rules or add new support domains |
| `shared.py` | Modify voice-call rules, emotional handling, or identity behaviour — applies globally |
| `greetings.py` | Add or change opening greetings per domain |
| `config.py` | Add new roles or domains to the UI picker |

To add a new domain:
1. Add the prompt fragment in the relevant role file
2. Register it in the file's `DOMAIN_FRAGMENTS` dict
3. Add the entry to `DEMO_ROLES` in `config.py`
