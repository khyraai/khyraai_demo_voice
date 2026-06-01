"""
transcript_logger.py — Session transcript file logger for test runs.

All sessions in a test run are appended to ONE shared file:
    logs/test_run_YYYYMMDD_HHMMSS.json

Structure:
    {
      "test_run": "<iso timestamp>",
      "sessions": [
        { session 1 (front_desk) ... },
        { session 2 (support_line) ... },
        { session 3 (lead_followup) ... }
      ]
    }

Only active when TEST_LOGGING=true in the environment.
"""

import json
import os
from datetime import datetime
from pathlib import Path

_ENABLED  = os.getenv("TEST_LOGGING", "false").lower() in ("1", "true", "yes")
_LOGS_DIR = Path(__file__).parent.parent / "logs"

# Shared file for the entire test run — created on first session, reused for all.
_RUN_FILE: "Path | None" = None


def _get_run_file() -> Path:
    global _RUN_FILE
    if _RUN_FILE is None:
        _LOGS_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        _RUN_FILE = _LOGS_DIR / f"test_run_{ts}.json"
        _write({"test_run": datetime.now().isoformat(), "sessions": []})
        print(f"[TRANSCRIPT_LOG] Test run file: {_RUN_FILE}")
    return _RUN_FILE


def _read() -> dict:
    with open(_get_run_file(), encoding="utf-8") as f:
        return json.load(f)


def _write(data: dict) -> None:
    with open(_get_run_file(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class TranscriptLogger:
    """
    Appends a new session entry to the shared test_run_*.json file.
    Updates that entry in-place as greeting and turns arrive.
    """

    def __init__(self, session_id: str, role: str, domain: str, language: str, voice_label: str):
        self.enabled = _ENABLED
        if not self.enabled:
            return

        run = _read()
        self._idx = len(run["sessions"])
        run["sessions"].append({
            "session_id": session_id,
            "started_at": datetime.now().isoformat(),
            "metadata": {
                "role":     role,
                "domain":   domain,
                "language": language,
                "voice":    voice_label,
            },
            "greeting": None,
            "turns":    [],
        })
        _write(run)
        print(f"[TRANSCRIPT_LOG] Session #{self._idx + 1} — role={role} domain={domain} voice={voice_label}")

    def log_greeting(self, text: str) -> None:
        if not self.enabled:
            return
        run = _read()
        run["sessions"][self._idx]["greeting"] = {
            "agent": text,
            "time":  datetime.now().isoformat(),
        }
        _write(run)

    def log_turn(self, turn: int, user_text: str, agent_text: str) -> None:
        if not self.enabled:
            return
        run = _read()
        run["sessions"][self._idx]["turns"].append({
            "turn":  turn,
            "user":  user_text,
            "agent": agent_text,
            "time":  datetime.now().isoformat(),
        })
        _write(run)


class _NullLogger:
    """Returned when TEST_LOGGING is off — all methods are no-ops."""
    def log_greeting(self, *_): pass
    def log_turn(self, *_): pass


def make_logger(session_id: str, role: str, domain: str, language: str, voice_label: str) -> "TranscriptLogger | _NullLogger":
    """Factory: returns a real logger when TEST_LOGGING=true, else a no-op."""
    if _ENABLED:
        return TranscriptLogger(session_id, role, domain, language, voice_label)
    return _NullLogger()
