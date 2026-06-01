"""
prompts/greetings.py — Multilingual per-role greeting generator.

get_greeting(role, domain, language_code, voice_name) → str

Each role has three template slots per language:
  - greeting   : language-native salutation
  - intro      : "This is {name}" equivalent
  - cta        : "How may I help you?" equivalent

A short domain context tag (English for en-IN; omitted for other languages)
is inserted between intro and cta to give the agent a natural context hook.
Pre-assumed intent ("are you calling to book?") is deliberately removed — the
agent waits for the caller to state their need.
"""

import random

# ---------------------------------------------------------------------------
# Language phrase parts
# Each entry: {greeting, intro, cta}
# {name} in intro is replaced with voice_name at call time.
# ---------------------------------------------------------------------------
_LANG_PARTS: dict[str, dict[str, str]] = {
    "en-IN": {
        "greeting": "Hello",
        "intro":    "this is {name}",
        "cta":      "How may I help you?",
    },
    "hi-IN": {
        "greeting": "नमस्ते",
        "intro":    "मैं {name} बोल रही हूँ",
        "cta":      "मैं आपकी कैसे मदद कर सकती हूँ?",
    },
    "kn-IN": {
        "greeting": "ನಮಸ್ಕಾರ",
        "intro":    "ನಾನು {name} ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ",
        "cta":      "ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?",
    },
    "ta-IN": {
        "greeting": "வணக்கம்",
        "intro":    "நான் {name} பேசுகிறேன்",
        "cta":      "நான் உங்களுக்கு எவ்வாறு உதவலாம்?",
    },
    "te-IN": {
        "greeting": "నమస్కారం",
        "intro":    "నేను {name} మాట్లాడుతున్నాను",
        "cta":      "నేను మీకు ఎలా సహాయపడగలను?",
    },
    "ml-IN": {
        "greeting": "നമസ്കാരം",
        "intro":    "ഞാൻ {name} സംസാരിക്കുകയാണ്",
        "cta":      "ഞാൻ നിങ്ങളെ എങ്ങനെ സഹായിക്കണം?",
    },
    "bn-IN": {
        "greeting": "নমস্কার",
        "intro":    "আমি {name} বলছি",
        "cta":      "আমি আপনাকে কীভাবে সাহায্য করতে পারি?",
    },
    "gu-IN": {
        "greeting": "નમસ્તે",
        "intro":    "હું {name} બોલું છું",
        "cta":      "હું તમારી કઈ રીતે મદદ કરી શકું?",
    },
    "mr-IN": {
        "greeting": "नमस्कार",
        "intro":    "मी {name} बोलत आहे",
        "cta":      "मी तुमची कशी मदत करू शकतो?",
    },
    "pa-IN": {
        "greeting": "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ",
        "intro":    "ਮੈਂ {name} ਬੋਲ ਰਿਹਾ ਹਾਂ",
        "cta":      "ਮੈਂ ਤੁਹਾਡੀ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?",
    },
    "od-IN": {
        "greeting": "ନମସ୍କାର",
        "intro":    "ମୁଁ {name} କଥା ହଉଛି",
        "cta":      "ମୁଁ ଆପଣଙ୍କୁ କିପରି ସାହାଯ୍ୟ କରିପାରିବି?",
    },
}

# ---------------------------------------------------------------------------
# Domain context tags — English only (shown for en-IN; skipped for others)
# These give a brief clinic/service identity line between intro and cta.
# ---------------------------------------------------------------------------
_FRONT_DESK_CONTEXT: dict[str, list[str]] = {
    "dental_clinic":     ["You've reached the dental clinic.", "You're through to the dental clinic front desk."],
    "veterinary_clinic": ["You've reached the veterinary clinic.", "You're through to the vet clinic."],
    "spa_salon":         ["You've reached our spa and salon.", "You're through to the salon front desk."],
    "therapist_clinic":  ["You've reached the wellness clinic.", "You're through to the clinic front desk."],
    "hotel_resort":      ["You've reached the hotel reservations desk.", "You're through to our front desk."],
    "cosmetic_clinic":   ["You've reached the aesthetic clinic.", "You're through to the clinic front desk."],
    "general_clinic":    ["You've reached the clinic.", "You're through to the clinic front desk."],
}

_LEAD_FOLLOWUP_CONTEXT: dict[str, list[str]] = {
    "ai_voice_services": ["I'm calling from Khyra AI.", "I'm reaching out from the Khyra AI team."],
    "real_estate":       ["I'm following up on your property enquiry.", "I'm reaching out about a property you enquired about."],
    "it_projects":       ["I'm following up on your technology services enquiry.", "I'm reaching out about your project enquiry."],
}

_SUPPORT_LINE_CONTEXT: dict[str, list[str]] = {
    "devops_support":              ["You've reached the DevOps support line.", "You're through to infrastructure support."],
    "access_management_support":   ["You've reached the IT helpdesk.", "You're through to access management support."],
    "saas_product_support":        ["You've reached product support.", "You're through to our support team."],
}

_ALL_CONTEXT: dict[str, dict[str, list[str]]] = {
    "front_desk":    _FRONT_DESK_CONTEXT,
    "lead_followup": _LEAD_FOLLOWUP_CONTEXT,
    "support_line":  _SUPPORT_LINE_CONTEXT,
}

# For lead follow-up, the cta differs — it's permission-seeking, not help-offering
_LEAD_FOLLOWUP_CTA_EN = [
    "Is this a good time to talk?",
    "Do you have a couple of minutes?",
    "Is now a good time for a quick chat?",
]


def get_greeting(
    role: str,
    domain: str,
    language_code: str = "en-IN",
    voice_name: str = "Khyra",
) -> str:
    """
    Return a natural greeting for the given role, domain, language, and voice name.

    Structure (en-IN):  "{Greeting}, {intro with name}. {context}. {CTA}"
    Structure (others): "{Greeting}, {intro with name}. {CTA}"
    """
    parts = _LANG_PARTS.get(language_code) or _LANG_PARTS["en-IN"]
    greeting = parts["greeting"]
    intro    = parts["intro"].replace("{name}", voice_name)
    cta      = parts["cta"]

    # Lead follow-up has a permission-seeking CTA in English; keep language CTA for others
    if role == "lead_followup" and language_code == "en-IN":
        cta = random.choice(_LEAD_FOLLOWUP_CTA_EN)

    # Domain context (English only)
    context = ""
    if language_code == "en-IN":
        ctx_pool = _ALL_CONTEXT.get(role, {}).get(domain)
        if ctx_pool:
            context = random.choice(ctx_pool)

    if context:
        return f"{greeting}, {intro}. {context} {cta}"
    return f"{greeting}, {intro}. {cta}"
