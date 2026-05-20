"""
agents.py — Thin compatibility shim for the Khyra AI Demo.

All prompt logic lives in src/prompts/.
This module re-exports get_system_prompt and get_greeting so that
any code importing from agents still works without modification.
"""

from prompts import get_system_prompt, get_greeting  # noqa: F401

__all__ = ["get_system_prompt", "get_greeting"]
