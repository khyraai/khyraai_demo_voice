"""
config.py — Demo configuration: voices, languages, and two-level roles.

Voices are configurable via .env:
    DEMO_VOICE_1_NAME    = Display name  (default: "Priya")
    DEMO_VOICE_1_SPEAKER = Sarvam speaker slug  (default: "priya")
    ...repeated for DEMO_VOICE_2 through DEMO_VOICE_10

Languages are a fixed list of Sarvam-supported Indian languages + English.

Roles are two-level: each primary role has a list of domain specialisations.
The UI uses this to drive the two-step role → domain selection flow.
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
    _voice(1,  "Priya",   "priya"),
    _voice(2,  "Kavya",   "kavya"),
    _voice(3,  "Neha",    "neha"),
    _voice(4,  "Simran",  "simran"),
    _voice(5,  "Pooja",   "pooja"),
    _voice(6,  "Rahul",   "rahul"),
    _voice(7,  "Rohan",   "rohan"),
    _voice(8,  "Aditya",  "aditya"),
    _voice(9,  "Amit",    "amit"),
    _voice(10, "Ratan",   "ratan"),
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

# ---------------------------------------------------------------------------
# Two-level role structure
# Each primary role contains a list of domain specialisations.
# ---------------------------------------------------------------------------
DEMO_ROLES: list[dict] = [
    {
        "id":          "front_desk",
        "label":       "Front Desk",
        "description": "Reception & appointment management",
        "icon":        "🏥",
        "domains": [
            {
                "id":          "dental_clinic",
                "label":       "Dental Clinic",
                "description": "Cleanings, braces, root canals & more",
                "icon":        "🦷",
            },
            {
                "id":          "veterinary_clinic",
                "label":       "Veterinary Clinic",
                "description": "Pet health appointments & checkups",
                "icon":        "🐾",
            },
            {
                "id":          "spa_salon",
                "label":       "Spa & Salon",
                "description": "Treatments, packages & bookings",
                "icon":        "💆",
            },
            {
                "id":          "therapist_clinic",
                "label":       "Therapist & Wellness",
                "description": "Counselling & wellness consultations",
                "icon":        "🧘",
            },
            {
                "id":          "hotel_resort",
                "label":       "Hotel & Resort",
                "description": "Reservations, check-in & amenities",
                "icon":        "🏨",
            },
            {
                "id":          "cosmetic_clinic",
                "label":       "Cosmetic Clinic",
                "description": "Aesthetic treatments & consultations",
                "icon":        "✨",
            },
            {
                "id":          "general_clinic",
                "label":       "General Clinic",
                "description": "Multispecialty consultations & bookings",
                "icon":        "🩺",
            },
        ],
    },
    {
        "id":          "lead_followup",
        "label":       "Lead Follow-Up",
        "description": "Consultative outbound sales",
        "icon":        "📞",
        "domains": [
            {
                "id":          "ai_voice_services",
                "label":       "AI Voice Services",
                "description": "Selling Khyra AI voice solutions",
                "icon":        "🤖",
            },
            {
                "id":          "real_estate",
                "label":       "Real Estate",
                "description": "Property enquiries & site visits",
                "icon":        "🏠",
            },
            {
                "id":          "it_projects",
                "label":       "IT Projects",
                "description": "Software, automation & AI consulting",
                "icon":        "�",
            },
        ],
    },
    {
        "id":          "support_line",
        "label":       "Support Line",
        "description": "Enterprise technical support desk",
        "icon":        "🛠️",
        "domains": [
            {
                "id":          "devops_support",
                "label":       "DevOps Support",
                "description": "CI/CD, Docker, K8s & cloud infra",
                "icon":        "⚙️",
            },
            {
                "id":          "access_management_support",
                "label":       "Access Management",
                "description": "Login, MFA, permissions & VPN",
                "icon":        "🔐",
            },
            {
                "id":          "saas_product_support",
                "label":       "SaaS Product Support",
                "description": "Billing, onboarding & integrations",
                "icon":        "�",
            },
        ],
    },
]
