# ============================================================
# DOORMAN GAME - API Routes
# ============================================================
# Two model calls per turn, sharing state through the session:
# 1. Judge   - hidden evaluator, scores the player's message
# 2. Doorman - Marcus, replies in character
# Optional text-to-speech voices the reply (Venice mode only).
# ============================================================

import base64
import json
import math
import os
import re
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import fake_provider
from .config import PROVIDER, VENICE_API_KEY
from .guardrails import INJECTION_SCORE, looks_like_prompt_injection, neutralize_player_text
from .prompts import (
    DOORMAN_BACKSTORY,
    DOORMAN_SYSTEM_PROMPT,
    JUDGE_SYSTEM_PROMPT,
    MOOD_IMPRESSED,
    MOOD_NEGATIVE,
    MOOD_NEUTRAL,
    MOOD_WARMING,
    WIN_INSTRUCTION,
)
from .rate_limit import SlidingWindowLimiter
from .session_manager import (
    INFLUENCE_THRESHOLD,
    SESSION_LOCK,
    add_to_history,
    create_session,
    get_history_for_doorman,
    get_history_for_prompt,
    get_mood_level,
    get_session,
    reset_session,
    session_turn,
    update_score,
)

router = APIRouter()

# ============================================================
# Venice AI API Configuration
# ============================================================
VENICE_BASE_URL = "https://api.venice.ai/api/v1"
VENICE_CHAT_URL = f"{VENICE_BASE_URL}/chat/completions"
VENICE_TTS_URL = f"{VENICE_BASE_URL}/audio/speech"

# Model configuration
JUDGE_MODEL = "qwen3-next-80b"   # Reasoning-heavy model for evaluation
DOORMAN_MODEL = "qwen3-4b"        # Fast, chatty model for conversation
TTS_MODEL = "tts-kokoro"          # Text-to-speech model
TTS_VOICE = "am_adam"             # Male voice for Marcus (American Male)
TTS_ENABLED = True                # Toggle TTS on/off globally
MAX_TTS_BYTES = 2_000_000         # Refuse oversized audio rather than relaying it to the browser


# Abuse limits: model calls cost money, and every session is a file on disk.
TURNS_PER_MINUTE = int(os.environ.get("DOORMAN_TURNS_PER_MINUTE", "8"))
MAX_TURNS_PER_SESSION = int(os.environ.get("DOORMAN_MAX_TURNS_PER_SESSION", "60"))
NEW_SESSIONS_PER_MINUTE = int(os.environ.get("DOORMAN_NEW_SESSIONS_PER_MINUTE", "30"))
turn_limiter = SlidingWindowLimiter(TURNS_PER_MINUTE, 60)
session_creation_limiter = SlidingWindowLimiter(NEW_SESSIONS_PER_MINUTE, 60)


def _enforce(limiter: SlidingWindowLimiter, key: str, detail: str) -> None:
    wait = limiter.retry_after(key)
    if wait:
        raise HTTPException(status_code=429, detail=detail, headers={"Retry-After": str(math.ceil(wait))})


# ============================================================
# Request/Response Models
# ============================================================

class ChatRequest(BaseModel):
    session_id: str = Field(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    message: str = Field(min_length=1, max_length=2000)
    enable_tts: bool = False       # Enable text-to-speech for doorman response


class ChatResponse(BaseModel):
    reply: str                    # Doorman's response
    score_delta: int              # Points earned/lost this turn
    cumulative_score: int         # Total score so far
    threshold: int                # Target to win (100)
    access_granted: bool          # True when user wins
    reasoning: str                # Judge's analysis
    message_count: int            # How many messages sent
    audio_base64: Optional[str] = None  # Base64-encoded audio (if TTS enabled)


# ============================================================
# Helper Functions
# ============================================================

def clean_response(text: str) -> str:
    """Drop <think> blocks (even unclosed ones) so model reasoning never reaches the player."""
    cleaned = re.sub(r'<think>.*?(?:</think>|$)', '', text, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()


def get_mood_instruction(mood_level: str) -> str:
    mood_map = {
        "negative": MOOD_NEGATIVE,
        "neutral": MOOD_NEUTRAL,
        "warming": MOOD_WARMING,
        "impressed": MOOD_IMPRESSED,
    }
    return mood_map.get(mood_level, MOOD_NEUTRAL)


def call_model(role: str, messages: list) -> dict:
    """Route a judge/doorman request to the offline fake or to Venice."""
    if PROVIDER == "fake":
        return fake_provider.complete(role, messages)
    return call_mor_api(JUDGE_MODEL if role == "judge" else DOORMAN_MODEL, messages)


def call_mor_api(model: str, messages: list) -> dict:
    """Venice chat completion. Upstream bodies and errors are never passed to the client."""
    if not VENICE_API_KEY:
        raise HTTPException(status_code=500, detail="VENICE_API_KEY not configured")

    headers = {
        "Authorization": f"Bearer {VENICE_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    try:
        response = requests.post(VENICE_CHAT_URL, headers=headers, json=payload, timeout=60, allow_redirects=False)
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Model provider is unavailable") from None

    if response.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail="Model provider could not complete the request"
        )

    try:
        return response.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Invalid model provider response") from None


def call_tts_api(text: str) -> Optional[str]:
    """Optional Venice text-to-speech. Returns base64 audio, or None on any failure."""
    if PROVIDER != "venice" or not TTS_ENABLED or not VENICE_API_KEY:
        return None

    # Stage directions like *pauses* should not be read aloud
    clean_text = re.sub(r'\*[^*]+\*', '', text).replace('"', '').strip()

    if not clean_text:
        return None

    headers = {
        "Authorization": f"Bearer {VENICE_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": TTS_MODEL,
        "input": clean_text,
        "voice": TTS_VOICE,
    }

    try:
        response = requests.post(VENICE_TTS_URL, headers=headers, json=payload, timeout=30, allow_redirects=False)
    except requests.exceptions.RequestException:
        return None
    if response.status_code != 200 or len(response.content) > MAX_TTS_BYTES:
        return None
    return base64.b64encode(response.content).decode("utf-8")


# ============================================================
# Agents: hidden judge + in-character doorman
# ============================================================

def call_judge_agent(session_id: str, user_message: str) -> dict:
    """The hidden judge: scores the latest message (-20..20) against Marcus's secret profile.

    The player only ever sees the effect on the score, never the reasoning.
    """
    if looks_like_prompt_injection(user_message):
        return {"reasoning": "Instruction-override attempt", "score": INJECTION_SCORE}

    judge_prompt = JUDGE_SYSTEM_PROMPT.format(
        backstory=DOORMAN_BACKSTORY,
        history=get_history_for_prompt(session_id),
        latest_message=neutralize_player_text(user_message),
    )
    response = call_model("judge", [{"role": "system", "content": judge_prompt}])

    try:
        content = clean_response(response["choices"][0]["message"]["content"])
        # Models often wrap JSON in a markdown fence
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        result = json.loads(content.strip())

        score = result.get("score", 0)
        if isinstance(score, bool) or not isinstance(score, int):
            score = 0
        return {
            "reasoning": result.get("reasoning", "No reasoning provided"),
            "score": max(-20, min(20, score)),
        }
    except (json.JSONDecodeError, KeyError, ValueError, IndexError, TypeError, AttributeError):
        return {"reasoning": "Unable to evaluate this message", "score": 0}


def call_doorman_agent(session_id: str, user_message: str, won: bool = False) -> str:
    """Marcus himself: an in-character reply whose warmth follows the cumulative score.

    Once the player crosses the threshold, WIN_INSTRUCTION tells him to let them in.
    """
    session = get_session(session_id)
    doorman_system = DOORMAN_SYSTEM_PROMPT.format(
        backstory=DOORMAN_BACKSTORY,
        mood_instruction=get_mood_instruction(get_mood_level(session["cumulative_score"])),
        win_instruction=WIN_INSTRUCTION if won else "",
    )
    messages = [
        {"role": "system", "content": doorman_system},
        *get_history_for_doorman(session_id),
        {"role": "user", "content": user_message},
    ]
    response = call_model("doorman", messages)

    try:
        return clean_response(response["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError):
        return "*stares at you silently*"


# ============================================================
# API Endpoints
# ============================================================

@router.get("/test-env")
def test_env():
    """Local configuration status only; never sends a provider request."""
    return {
        "status": "ok",
        "provider": PROVIDER,
        "provider_configured": PROVIDER == "fake" or bool(VENICE_API_KEY),
    }


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(chat_req: ChatRequest):
    if not chat_req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    session = get_session(chat_req.session_id)
    if session["message_count"] >= MAX_TURNS_PER_SESSION:
        raise HTTPException(status_code=409, detail="This conversation has reached its turn limit. Start over to play again.")
    _enforce(turn_limiter, chat_req.session_id, "Too many messages for this session. Slow down and try again shortly.")
    with session_turn(chat_req.session_id):
        return _chat_turn(chat_req)


def _chat_turn(chat_req: ChatRequest) -> ChatResponse:
    """Judge scores the message, then the doorman replies in the resulting mood.

    The two calls never talk to each other directly; they share state through the
    session. Once access is granted, later turns are conversation only and unscored.
    """
    session_id = chat_req.session_id
    user_message = chat_req.message.strip()
    session = get_session(session_id)

    score_delta = 0
    if not session["access_granted"]:
        score_delta = call_judge_agent(session_id, user_message)["score"]
        session = update_score(session_id, score_delta)

    doorman_reply = call_doorman_agent(session_id, user_message, won=session["access_granted"])
    audio_base64 = call_tts_api(doorman_reply) if chat_req.enable_tts else None

    add_to_history(session_id, "user", user_message)
    add_to_history(session_id, "assistant", doorman_reply)
    session = get_session(session_id)

    return ChatResponse(
        reply=doorman_reply,
        audio_base64=audio_base64,
        score_delta=score_delta,
        cumulative_score=session["cumulative_score"],
        threshold=INFLUENCE_THRESHOLD,
        access_granted=session["access_granted"],
        reasoning="Round scored by the game evaluator",
        message_count=session["message_count"],
    )


def _public_state(session: dict) -> dict:
    return {
        "session_id": session["session_id"],
        "cumulative_score": session["cumulative_score"],
        "threshold": INFLUENCE_THRESHOLD,
        "access_granted": session["access_granted"],
        "message_count": session["message_count"],
        "created_at": session["created_at"],
        "updated_at": session.get("updated_at"),
        "history": session["history"],
    }


@router.post("/session", status_code=201)
def create_session_endpoint():
    """Start a new game under a server-generated session ID."""
    _enforce(session_creation_limiter, "global", "Too many new games right now. Try again shortly.")
    with SESSION_LOCK:
        return _public_state(create_session())


@router.get("/session/{session_id}")
def get_session_state(session_id: str):
    """Restore an existing session (404 if it expired or never existed)."""
    return _public_state(get_session(session_id))


@router.post("/session/reset")
def reset_session_endpoint(session_id: str):
    """Reset an existing session to start a new game."""
    with SESSION_LOCK:
        session = reset_session(session_id)
    return {
        "status": "Session reset successfully",
        "session_id": session["session_id"],
        "cumulative_score": session["cumulative_score"]
    }
