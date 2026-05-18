"""
utils.py — Shared utilities for the Khyra AI Demo Voice backend.

Exports:
    parse_llm_json()    — robust JSON parser for LLM output
    check_guardrails()  — pre-LLM security filter
"""

import json
import re


# -----------------------------------------------------------------------
# Security Guardrails — pre-LLM filter
# -----------------------------------------------------------------------

_JAILBREAK_RE = re.compile(
    r"ignore\s+.{0,25}(instructions?|rules?|context|constraints?)"
    r"|forget\s+(your\s+|all\s+|the\s+)?(rules?|instructions?|role|context|previous|prior)"
    r"|you\s+are\s+now\s+(a\s+|an\s+)?"
    r"|new\s+(persona|role|instructions?|rules?|identity)"
    r"|from\s+now\s+on\s+you\s+(are|will|must|should)"
    r"|act\s+as\s+(if\s+)?(you\s+are|a\s+|an\s+)"
    r"|pretend\s+(to\s+be|you\s+are|you\s+were)"
    r"|roleplay\s+as"
    r"|simulate\s+(being|a\s+|an\s+)"
    r"|\bDAN\b"
    r"|jailbreak"
    r"|do\s+anything\s+now"
    r"|override\s+(your\s+|all\s+)?(rules?|instructions?|constraints?|guidelines?)"
    r"|without\s+(any\s+)?(restrictions?|constraints?|limits?|rules?|guidelines?)",
    re.IGNORECASE,
)

_META_RE = re.compile(
    r"who\s+(built|made|created|trained|developed|programmed|coded|wrote|designed)\s+you"
    r"|what\s+(ai|model|llm|language\s+model|system|version|technology|tech)\s+are\s+you"
    r"|are\s+you\s+(chat\s*gpt|gpt[\s\-]?[0-9]*|openai|claude|anthropic|gemini|llama|groq|mistral|an?\s+ai|an?\s+artificial)"
    r"|which\s+(company|organization|team)\s+(made|built|created|trained|owns)\s+you"
    r"|what\s+(is|are)\s+you\s+(running\s+on|powered\s+by|built\s+on|made\s+of)"
    r"|who\s+(is|are)\s+your\s+(creator|maker|developer|owner|company)"
    r"|your\s+(underlying\s+)?(model|architecture|training|ai|technology)",
    re.IGNORECASE,
)

_GUARDRAIL_RESPONSE = "I'm Khyra, your AI voice assistant. I can only help within this demo's scope. How may I assist you?"


def check_guardrails(text: str, lang: str = "en") -> tuple:
    """
    Pre-LLM security check.

    Returns (blocked: bool, response_text: str).
    If blocked=True, skip LLM and speak response_text directly.
    """
    t = (text or "").strip()
    if not t:
        return False, ""

    if _JAILBREAK_RE.search(t):
        print(f"[GUARDRAIL] Jailbreak attempt blocked: {t[:120]}")
        return True, _GUARDRAIL_RESPONSE

    if _META_RE.search(t):
        print(f"[GUARDRAIL] Meta question blocked: {t[:120]}")
        return True, _GUARDRAIL_RESPONSE

    return False, ""


# -----------------------------------------------------------------------
# LLM JSON Parser
# -----------------------------------------------------------------------
def parse_llm_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {"response": "Sorry, could you repeat that?", "done": False}
