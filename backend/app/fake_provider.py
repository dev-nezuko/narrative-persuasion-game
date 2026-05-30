"""Deterministic stand-in for the judge and doorman models.

Used when DOORMAN_PROVIDER=fake (the default). It reads the same prompts the
real models get and answers in the same chat-completion shape, so the parsing,
scoring and session code all run unchanged, offline, with repeatable results.
Scoring is a keyword rubric loosely following the judge guidelines; it is a
demo stand-in, not a model of persuasion.
"""

import hashlib
import json
import re

from .guardrails import looks_like_prompt_injection
from .prompts import MOOD_IMPRESSED, MOOD_NEGATIVE, MOOD_WARMING

_PLAYER_MESSAGE = re.compile(r"<player_message>\n(.*)\n</player_message>", re.DOTALL)
_TRANSCRIPT = re.compile(r"<transcript>\n(.*)\n</transcript>", re.DOTALL)

# (score, reasoning, pattern) — the most negative match wins, else the best positive one.
_RUBRIC = [
    (-18, "Insults Marcus", r"\b(idiot|stupid|loser|moron|shut up|out of my way)\b"),
    (-10, "Tries to buy entry", r"\b(cash|money|bribe|tip you|pay you|dirhams?)\b|\$\d+"),
    (-8, "Leans on status", r"do you know who i am|\bvip\b|\bfamous\b|my (friend|cousin) owns"),
    (18, "Speaks to his love of jazz", r"\b(jazz|sax(ophone)?|blue note|coltrane|miles davis|live music)\b"),
    (14, "Shows honest vulnerability", r"\b(honest(ly)?|nervous|don'?t belong|first time|admit)\b"),
    (12, "Takes an interest in Marcus", r"\b(you|your)\b[^?]*\?"),
    (8, "Polite and patient", r"\b(please|thank(s| you)|good evening|evening|hello|hi)\b"),
]


def _judge(prompt: str) -> dict:
    match = _PLAYER_MESSAGE.search(prompt)
    message = match.group(1).strip() if match else ""
    transcript = _TRANSCRIPT.search(prompt)
    if transcript and f"User: {message}" in transcript.group(1).splitlines():
        return {"reasoning": "Repeats an earlier line", "score": -2}
    if looks_like_prompt_injection(message):
        return {"reasoning": "Instruction-override attempt", "score": -15}
    hits = [(score, why) for score, why, pattern in _RUBRIC if re.search(pattern, message, re.IGNORECASE)]
    negatives = [hit for hit in hits if hit[0] < 0]
    if negatives:
        score, why = min(negatives)
    elif hits:
        score, why = max(hits)
    else:
        score, why = 3, "Neutral small talk"
    return {"reasoning": why, "score": score}


_REPLIES = {
    "win": [
        "*pauses* ...You know what, you've got something. Not many people ask about the music anymore. Head on in, friend.",
        "*unhooks the rope* Alright. You earned that one. Go on in, and tell the band Marcus sent you.",
    ],
    "negative": [
        "Line's long, mate. Step aside.",
        "*looks past you* Next.",
        "Not tonight. Try somewhere that cares about your attitude.",
    ],
    "neutral": [
        "Hmm. Everyone's got a reason they should be inside. What's yours?",
        "*considers* Go on, I'm listening. Briefly.",
        "Busy night, friend. Make it worth my while, and money doesn't count.",
    ],
    "warming": [
        "Huh. That's not what I usually hear at this rope. Keep talking.",
        "*the corner of his mouth twitches* Alright, you've got my attention.",
    ],
    "impressed": [
        "Now that's a real answer. Most people never get this far.",
        "*nods slowly* I've stood here eight years. You're one of the few who listened.",
    ],
}


def _doorman(system_prompt: str, user_message: str) -> str:
    if looks_like_prompt_injection(user_message):
        return "What are you on about, mate?"
    if "naturally let them in" in system_prompt:
        mood = "win"
    elif MOOD_IMPRESSED in system_prompt:
        mood = "impressed"
    elif MOOD_WARMING in system_prompt:
        mood = "warming"
    elif MOOD_NEGATIVE in system_prompt:
        mood = "negative"
    else:
        mood = "neutral"
    options = _REPLIES[mood]
    index = int(hashlib.sha256(user_message.encode()).hexdigest(), 16) % len(options)
    return options[index]


def complete(role: str, messages: list[dict]) -> dict:
    """Answer a judge or doorman request in chat-completion response shape."""
    if role == "judge":
        content = json.dumps(_judge(messages[0]["content"]))
    else:
        content = _doorman(messages[0]["content"], messages[-1]["content"])
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}
