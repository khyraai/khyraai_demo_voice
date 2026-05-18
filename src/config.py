"""
config.py — Demo configuration: voices and languages.

Voices are configurable via .env:
    DEMO_VOICE_1_NAME   = Display name  (default: "Voice 1")
    DEMO_VOICE_1_SPEAKER = Sarvam speaker slug  (default: "meera")
    ...repeated for DEMO_VOICE_2, DEMO_VOICE_3, DEMO_VOICE_4

Languages are a fixed list of Sarvam-supported Indian languages + English.
"""

import os


def _voice(idx: int, default_name: str, default_speaker: str) -> dict:
    n = str(idx)
    return {
        "id":      f"voice_{n}",
        "label":   os.getenv(f"DEMO_VOICE_{n}_NAME",    default_name),
        "speaker": os.getenv(f"DEMO_VOICE_{n}_SPEAKER", default_speaker),
    }


DEMO_VOICES: list[dict] = [
    _voice(1, "Priya",  "priya"),
    _voice(2, "Kavya",  "kavya"),
    _voice(3, "Rahul",  "rahul"),
    _voice(4, "Rohan",  "rohan"),
]

DEMO_LANGUAGES: list[dict] = [
    {"code": "en-IN", "label": "English"},
    {"code": "hi-IN", "label": "Hindi"},
    {"code": "kn-IN", "label": "Kannada"},
    {"code": "ta-IN", "label": "Tamil"},
    {"code": "te-IN", "label": "Telugu"},
    {"code": "ml-IN", "label": "Malayalam"},
    {"code": "bn-IN", "label": "Bengali"},
    {"code": "gu-IN", "label": "Gujarati"},
    {"code": "mr-IN", "label": "Marathi"},
    {"code": "pa-IN", "label": "Punjabi"},
    {"code": "od-IN", "label": "Odia"},
]

DEMO_ROLES: list[dict] = [
    {
        "id":          "appointment_booking",
        "label":       "Appointment Booking",
        "description": "Schedule, reschedule, or cancel appointments",
        "icon":        "📅",
    },
    {
        "id":          "lead_followup",
        "label":       "Lead Follow-Up",
        "description": "Qualify and follow up with prospects",
        "icon":        "📞",
    },
    {
        "id":          "tech_support",
        "label":       "Tech Support",
        "description": "Assist customers with technical issues",
        "icon":        "🛠️",
    },
]
