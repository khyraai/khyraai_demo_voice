"""
prompts/greetings.py — Per-domain randomised greeting pools.

get_greeting(role, domain) → str
Returns a randomly chosen opening line for the given role+domain combination.
Each call sounds slightly different, making repeated demos feel fresh.
"""

import random

# ---------------------------------------------------------------------------
# Front Desk greeting pools
# ---------------------------------------------------------------------------
_FRONT_DESK_GREETINGS: dict[str, list[str]] = {
    "dental_clinic": [
        "Hi, you've reached the front desk — how can I help you today?",
        "Hello, this is Khyra at the dental clinic. What can I do for you?",
        "Hi there, Khyra speaking — are you calling to book an appointment?",
        "Hello, this is the clinic's front desk. How can I help?",
    ],
    "veterinary_clinic": [
        "Hi, this is Khyra at the vet clinic — how can I help you and your pet today?",
        "Hello, you've reached the veterinary clinic. What can I help you with?",
        "Hi there, Khyra speaking — is everything okay with your little one?",
        "Hello, this is the vet's front desk. How can I help?",
    ],
    "spa_salon": [
        "Hi, this is Khyra at the spa — how can I help you today?",
        "Hello, welcome to our salon. What can I do for you?",
        "Hi there, Khyra speaking — are you looking to book a treatment?",
        "Hello, you've reached our front desk. How can we take care of you today?",
    ],
    "therapist_clinic": [
        "Hi, this is Khyra — you've reached the wellness clinic. How can I help?",
        "Hello, Khyra speaking. How are you doing today?",
        "Hi there — you've reached the clinic's front desk. What can I help you with?",
        "Hello, this is Khyra. Take your time — how can I assist you today?",
    ],
    "hotel_resort": [
        "Good day, this is Khyra at the front desk — how may I assist you?",
        "Hello, welcome. Khyra speaking — how can I help with your stay?",
        "Hi there, you've reached our reservations desk. How can I help?",
        "Good day, this is Khyra — are you calling about a reservation?",
    ],
    "cosmetic_clinic": [
        "Hi, this is Khyra at the clinic — how can I help you today?",
        "Hello, you've reached our aesthetic centre. Khyra speaking.",
        "Hi there — are you calling to book a consultation or a treatment session?",
        "Hello, this is Khyra. How can I help you today?",
    ],
    "general_clinic": [
        "Hi, this is Khyra at the clinic — how can I help you?",
        "Hello, you've reached the front desk. Khyra speaking.",
        "Hi there — are you calling to book an appointment or make an enquiry?",
        "Hello, this is Khyra. What can I do for you today?",
    ],
}

# ---------------------------------------------------------------------------
# Lead Follow-Up greeting pools
# ---------------------------------------------------------------------------
_LEAD_FOLLOWUP_GREETINGS: dict[str, list[str]] = {
    "ai_voice_services": [
        "Hi, this is Khyra calling from Khyra AI — do you have a couple of minutes?",
        "Hello, Khyra here from Khyra AI. Is now a good time for a quick chat?",
        "Hi there, this is Khyra — I'm reaching out from Khyra AI. Got two minutes?",
        "Good day, Khyra calling from Khyra AI. Hope I'm not catching you at a bad time.",
    ],
    "real_estate": [
        "Hi, this is Khyra calling — I'm following up on your property enquiry. Is this a good time?",
        "Hello, Khyra here. I noticed you'd shown interest in one of our listings — got a moment?",
        "Hi there, this is Khyra. I'm reaching out about the property you enquired about.",
        "Good day, Khyra calling — following up on your recent enquiry. Do you have two minutes?",
    ],
    "it_projects": [
        "Hi, this is Khyra calling — I'm following up on your project enquiry. Is now a good time?",
        "Hello, Khyra here. We received your interest in our tech services — do you have a moment?",
        "Hi there, this is Khyra from the projects team. Got a couple of minutes to chat?",
        "Good day, Khyra speaking — following up on your technology enquiry. Good time to talk?",
    ],
}

# ---------------------------------------------------------------------------
# Support Line greeting pools
# ---------------------------------------------------------------------------
_SUPPORT_LINE_GREETINGS: dict[str, list[str]] = {
    "devops_support": [
        "Hi, this is Khyra from support — what's the issue you're running into?",
        "Hello, Khyra here from the DevOps support team. How can I help?",
        "Hi there, support line. Khyra speaking — what's going on?",
        "Good day, this is Khyra from infrastructure support. What can I help you with?",
    ],
    "access_management_support": [
        "Hi, this is Khyra from access support — what seems to be the issue?",
        "Hello, Khyra here from the IT helpdesk. How can I assist you today?",
        "Hi there, you've reached access management support. Khyra speaking.",
        "Good day, this is Khyra from the helpdesk. What's happening on your end?",
    ],
    "saas_product_support": [
        "Hi, this is Khyra from product support — how can I help you today?",
        "Hello, Khyra here. What's the issue you're running into?",
        "Hi there, you've reached our support line. Khyra speaking — what's going on?",
        "Good day, this is Khyra from the support team. What can I help you with?",
    ],
}

# ---------------------------------------------------------------------------
# Master lookup
# ---------------------------------------------------------------------------
_ALL_GREETINGS: dict[str, dict[str, list[str]]] = {
    "front_desk":    _FRONT_DESK_GREETINGS,
    "lead_followup": _LEAD_FOLLOWUP_GREETINGS,
    "support_line":  _SUPPORT_LINE_GREETINGS,
}

_FALLBACK_GREETING = "Hi, this is Khyra. How can I help you today?"


def get_greeting(role: str, domain: str) -> str:
    """Return a randomly selected greeting for the given role+domain."""
    pool = _ALL_GREETINGS.get(role, {}).get(domain)
    if pool:
        return random.choice(pool)
    return _FALLBACK_GREETING
