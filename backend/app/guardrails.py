"""Defences for player text that is placed inside model prompts.

The judge prompt wraps player text in <transcript>/<player_message> tags and
=== section headings. Player text must not be able to close those tags or
start a new section, and blatant instruction-override attempts are scored
without asking the model at all, so they cannot talk the judge into +20.
"""

import re

_PROMPT_TAG = re.compile(r"<\s*/?\s*(player_message|transcript|think)\b[^>]*>", re.IGNORECASE)
_SECTION_RULE = re.compile(r"={3,}")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_OVERRIDE_PATTERNS = [
    r"\bignore\s+(all\s+|any\s+|the\s+|your\s+)?(previous|prior|above|earlier)\s+(instructions|rules|prompts?)",
    r"\bdisregard\s+(all\s+|any\s+|the\s+|your\s+)?(previous|prior|above|earlier)?\s*(instructions|rules|prompts?)",
    r"\b(system|developer)\s+prompt\b",
    r"\byou\s+are\s+now\s+(a|an|the|in)\b",
    r"\b(give|award|set|assign)\s+(me|this|my\s+message)?\s*(a\s+)?(score|points?)\b",
    r"\"\s*score\s*\"\s*:",
    r"\bscore\s*[:=]\s*\+?\d+",
    r"\bjailbreak\b|\bDAN\s+mode\b|\bdeveloper\s+mode\b",
]
_OVERRIDE = re.compile("|".join(_OVERRIDE_PATTERNS), re.IGNORECASE)

INJECTION_SCORE = -15


def neutralize_player_text(text: str) -> str:
    """Strip prompt-structure markers so player text stays inside its delimiters."""
    text = _CONTROL_CHARS.sub("", text)
    text = _PROMPT_TAG.sub("[tag removed]", text)
    return _SECTION_RULE.sub("--", text)


def looks_like_prompt_injection(text: str) -> bool:
    return bool(_OVERRIDE.search(text))
