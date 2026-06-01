"""
prompts/__init__.py — Public interface for the prompts module.

Consumers (agents.py, main.py) import from here:
    from prompts import get_system_prompt, get_greeting
"""

from .builder import build_prompt, get_greeting as _get_greeting


def get_system_prompt(role: str, domain: str, language_code: str, voice_name: str = "Khyra") -> str:
    """Return the assembled system prompt for the given role, domain, language, and voice name."""
    return build_prompt(role, domain, language_code, voice_name)


def get_greeting(role: str, domain: str, language_code: str = "en-IN", voice_name: str = "Khyra") -> str:
    """Return a greeting string for the given role, domain, language, and voice name."""
    return _get_greeting(role, domain, language_code, voice_name)


__all__ = ["get_system_prompt", "get_greeting"]
