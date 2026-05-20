"""
prompts/__init__.py — Public interface for the prompts module.

Consumers (agents.py, main.py) import from here:
    from prompts import get_system_prompt, get_greeting
"""

from .builder import build_prompt, get_greeting


def get_system_prompt(role: str, domain: str, language_code: str) -> str:
    """Return the assembled system prompt for the given role, domain, and language."""
    return build_prompt(role, domain, language_code)


__all__ = ["get_system_prompt", "get_greeting"]
