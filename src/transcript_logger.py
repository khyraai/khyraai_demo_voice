"""
transcript_logger.py — Session transcript file logger for test runs.

Creates one JSON log per WebSocket session under /logs/.
Only active when TEST_LOGGING=true in the environment.
"""

import json
import os
from datetime import datetime
from pathlib import Path

_ENABLED = os.getenv("TEST_LOGGING", "false").lower() in ("1", "true", "yes")
_LOGS_DIR = Path(__file__).parent.parent / "logs"


class TranscriptLogger:
    """
    Logs greeting + conversation turns to logs/session_{id}_{ts}.json.
    No-op when TEST_LOGGING is not set.
    """

    def __init__(self, session_id: str, role: str, domain: str, language: str, voice_label: str):
        self.enabled = _ENABLED
        if not self.enabled:
            return

        _LOGS_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = _LOGS_DIR / f"session_{session_id}_{ts}.json"
        self._data: dict = {
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
        }
        self._flush()
        print(f"[TRANSCRIPT_LOG] Writing to {self.path}")

    def log_greeting(self, text: str) -> None:
        if not self.enabled:
            return
        self._data["greeting"] = {"agent": text, "time": datetime.now().isoformat()}
        self._flush()

    def log_turn(self, turn: int, user_text: str, agent_text: str) -> None:
        if not self.enabled:
            return
        self._data["turns"].append({
            "turn":  turn,
            "user":  user_text,
            "agent": agent_text,
            "time":  datetime.now().isoformat(),
        })
        self._flush()

    def _flush(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)


class _NullLogger:
    """Returned when TEST_LOGGING is off — all methods are no-ops."""
    def log_greeting(self, *_): pass
    def log_turn(self, *_): pass


def make_logger(session_id: str, role: str, domain: str, language: str, voice_label: str) -> "TranscriptLogger | _NullLogger":
    """Factory: returns a real logger when TEST_LOGGING=true, else a no-op."""
    if _ENABLED:
        return TranscriptLogger(session_id, role, domain, language, voice_label)
    return _NullLogger()
