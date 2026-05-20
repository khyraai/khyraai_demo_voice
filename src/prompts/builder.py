"""
prompts/builder.py — Central prompt assembly.

build_prompt(role, domain, language_code) → str
  Combines: role base + domain fragment + shared realism blocks + language instruction.

get_greeting(role, domain) → str
  Delegates to greetings.py.
"""

from .shared import (
    SHARED_REALISM,
    SHARED_INTERRUPTION,
    SHARED_PARTIAL_SPEECH,
    SHARED_EMOTIONAL,
    SHARED_MEMORY,
    SHARED_FAILURE_RECOVERY,
    SHARED_IDENTITY,
    language_instruction,
)
from .greetings import get_greeting  # noqa: F401 — re-exported

from . import front_desk   as _fd
from . import lead_followup as _lf
from . import support_line  as _sl


# ---------------------------------------------------------------------------
# Role registry — maps role id → (base_prompt, domain_fragments, default_domain)
# ---------------------------------------------------------------------------
_ROLE_REGISTRY: dict[str, tuple[str, dict[str, str], str]] = {
    "front_desk":    (_fd.FRONT_DESK_BASE,    _fd.DOMAIN_FRAGMENTS,    _fd.DEFAULT_DOMAIN),
    "lead_followup": (_lf.LEAD_FOLLOWUP_BASE, _lf.DOMAIN_FRAGMENTS,    _lf.DEFAULT_DOMAIN),
    "support_line":  (_sl.SUPPORT_LINE_BASE,  _sl.DOMAIN_FRAGMENTS,    _sl.DEFAULT_DOMAIN),
}

# Shared blocks — always appended in this order
_SHARED_BLOCKS = [
    SHARED_REALISM,
    SHARED_INTERRUPTION,
    SHARED_PARTIAL_SPEECH,
    SHARED_EMOTIONAL,
    SHARED_MEMORY,
    SHARED_FAILURE_RECOVERY,
    SHARED_IDENTITY,
]


def build_prompt(role: str, domain: str, language_code: str) -> str:
    """
    Assemble the full system prompt for a given role + domain + language.

    Assembly order:
      1. Role base behavior
      2. Domain-specific context
      3. Shared realism/behavioral blocks
      4. Language instruction
    """
    if role not in _ROLE_REGISTRY:
        role = "front_desk"

    base, domain_map, default_domain = _ROLE_REGISTRY[role]

    if domain not in domain_map:
        domain = default_domain

    domain_fragment = domain_map[domain]

    sections = [base, domain_fragment] + _SHARED_BLOCKS
    prompt = "\n\n".join(s.strip() for s in sections if s.strip())
    prompt += language_instruction(language_code)

    return prompt
