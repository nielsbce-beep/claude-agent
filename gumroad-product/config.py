"""
Central config — edit these values to match your setup.
"""
import os

# ── Calendar ────────────────────────────────────────────────────────────────────
# Name of your iCloud calendar. Must match exactly (case-sensitive).
# Leave empty string "" to disable calendar integration.
CALENDAR_NAME = os.getenv("CALENDAR_NAME", "My AI Agenda")

# ── Model ───────────────────────────────────────────────────────────────────────
# Claude model to use for all AI calls.
# Options: "claude-opus-4-5", "claude-sonnet-4-6", "claude-haiku-4-5"
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# ── Language ────────────────────────────────────────────────────────────────────
# Language for AI responses. Currently used in system prompts.
# "nl" = Dutch, "en" = English
LANGUAGE = os.getenv("AGENT_LANGUAGE", "en")
