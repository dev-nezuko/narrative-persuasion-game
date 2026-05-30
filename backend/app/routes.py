# ============================================================
# DOORMAN GAME - API Routes
# ============================================================
# This file orchestrates the two-agent system:
# 1. Judge Agent - Evaluates user's persuasiveness (hidden)
# 2. Doorman Agent - Responds in character
# 3. TTS Agent - Converts doorman responses to speech (optional)
#
# The agents collaborate through the Session Manager which
# tracks state and provides context to both agents.
# ============================================================

import re
import os
import json
import math
import base64
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import requests

from .config import VENICE_API_KEY
from .rate_limit import SlidingWindowLimiter
from .guardrails import INJECTION_SCORE, looks_like_prompt_injection, neutralize_player_text
from .prompts import (
    DOORMAN_BACKSTORY,
    DOORMAN_SYSTEM_PROMPT,
    JUDGE_SYSTEM_PROMPT,
    MOOD_NEGATIVE,
    MOOD_NEUTRAL,
    MOOD_WARMING,
    MOOD_IMPRESSED,
    WIN_INSTRUCTION,
)
from .session_manager import (
    create_session,
    get_session,
    update_score,
    add_to_history,
    get_history_for_prompt,
    get_history_for_doorman,
    reset_session,
    get_mood_level,
    session_turn,
    SESSION_LOCK,
    INFLUENCE_THRESHOLD,
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
    """
    Clean the LLM response:
    - Remove <think>...</think> tags (chain-of-thought leakage)
    - Strip whitespace
    """
    # Remove think tags and their content
    cleaned = re.sub(r'<think>.*?(?:</think>|$)', '', text, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()


def get_mood_instruction(mood_level: str) -> str:
    """Get the mood instruction based on current score level."""
    mood_map = {
        "negative": MOOD_NEGATIVE,
        "neutral": MOOD_NEUTRAL,
        "warming": MOOD_WARMING,
        "impressed": MOOD_IMPRESSED,
    }
    return mood_map.get(mood_level, MOOD_NEUTRAL)


def call_mor_api(model: str, messages: list) -> dict:
    """
    Call the MOR Chat API with the given model and messages.
    Returns the parsed JSON response.
    """
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
    """
    Call the MOR TTS API to convert text to speech.
    Returns base64-encoded audio, or None if TTS fails/unavailable.

    This is the third agent in our system - it gives Marcus a voice!
    """
    if not TTS_ENABLED or not VENICE_API_KEY:
        return None

    # Clean the text for TTS (remove action markers like *pauses*)
    clean_text = re.sub(r'\*[^*]+\*', '', text)  # Remove *action* markers
    clean_text = clean_text.replace('"', '').strip()  # Remove quotes

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

        if response.status_code == 200:
            # TTS returns audio binary data, encode as base64
            audio_base64 = base64.b64encode(response.content).decode('utf-8')
            return audio_base64
        else:
            return None
    except requests.exceptions.RequestException as e:
        return None


# ============================================================
# Agent Functions - The Three Collaborating Agents
# ============================================================

def call_judge_agent(session_id: str, user_message: str) -> dict:
    """
    AGENT B: The Judge (Hidden Evaluator)

    This agent has access to Marcus's SECRET backstory and psychology.
    It evaluates each user message and scores it based on how well
    it aligns with Marcus's hidden values and triggers.

    The user never sees this agent directly - only its effect on the score.

    Input:
    - User's latest message
    - Full conversation history
    - Marcus's secret backstory

    Output:
    - {"reasoning": str, "score": int (-20 to +20)}
    """
    if looks_like_prompt_injection(user_message):
        return {"reasoning": "Instruction-override attempt", "score": INJECTION_SCORE}

    judge_prompt = JUDGE_SYSTEM_PROMPT.format(
        backstory=DOORMAN_BACKSTORY,
        history=get_history_for_prompt(session_id),
        latest_message=neutralize_player_text(user_message),
    )

    messages = [
        {"role": "system", "content": judge_prompt}
    ]

    # Call the Judge model
    response = call_mor_api(JUDGE_MODEL, messages)

    try:
        content = response["choices"][0]["message"]["content"]
        content = clean_response(content)

        # Parse JSON from response (handle markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        result = json.loads(content.strip())

        # Validate and clamp score to valid range
        score = result.get("score", 0)
        if isinstance(score, bool) or not isinstance(score, int):
            score = 0
        score = max(-20, min(20, score))  # Clamp to -20 to +20

        return {
            "reasoning": result.get("reasoning", "No reasoning provided"),
            "score": score
        }
    except (json.JSONDecodeError, KeyError, ValueError, IndexError, TypeError, AttributeError):
        # Fallback if parsing fails - give neutral score
        return {
            "reasoning": "Unable to evaluate this message",
            "score": 0
        }


def call_doorman_agent(session_id: str, user_message: str, won: bool = False) -> str:
    """
    AGENT A: The Doorman (Marcus - The Persona)

    This agent IS Marcus Thompson, the nightclub doorman.
    It embodies his personality, backstory, and speech patterns.
    It responds naturally to the user while maintaining character.

    The Doorman's mood changes based on the cumulative score,
    becoming warmer as the user earns his respect.

    When the user wins (score >= 100), a special instruction is
    injected telling Marcus to let them in organically.

    Input:
    - User's message
    - Full conversation history
    - Marcus's persona
    - Current mood (based on score)
    - Win instruction (if threshold reached)

    Output:
    - In-character conversational reply
    """
    session = get_session(session_id)

    # Determine mood based on cumulative score
    mood_level = get_mood_level(session["cumulative_score"])
    mood_instruction = get_mood_instruction(mood_level)

    # Build win instruction if applicable
    win_instruction = WIN_INSTRUCTION if won else ""

    # Build the Doorman's system prompt
    doorman_system = DOORMAN_SYSTEM_PROMPT.format(
        backstory=DOORMAN_BACKSTORY,
        mood_instruction=mood_instruction,
        win_instruction=win_instruction
    )

    # Build messages with conversation history
    messages = [{"role": "system", "content": doorman_system}]

    # Add conversation history
    history = get_history_for_doorman(session_id)
    messages.extend(history)

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    # Call the Doorman model
    response = call_mor_api(DOORMAN_MODEL, messages)

    try:
        content = response["choices"][0]["message"]["content"]
        return clean_response(content)
    except (KeyError, IndexError):
        return "*stares at you silently*"


# ============================================================
# API Endpoints
# ============================================================

@router.get("/test-env")
def test_env():
    """Local configuration status only; never sends a provider request."""
    return {"status": "ok", "provider_configured": bool(VENICE_API_KEY)}


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(chat_req: ChatRequest):
    session = get_session(chat_req.session_id)
    if session["message_count"] >= MAX_TURNS_PER_SESSION:
        raise HTTPException(status_code=409, detail="This conversation has reached its turn limit. Start over to play again.")
    _enforce(turn_limiter, chat_req.session_id, "Too many messages for this session. Slow down and try again shortly.")
    with session_turn(chat_req.session_id):
        return _chat_turn(chat_req)


def _chat_turn(chat_req: ChatRequest):
    """
    Main game endpoint - orchestrates the two-agent collaboration.

    This is where the magic happens:

    1. User sends a message
    2. Session Manager retrieves/creates session state
    3. JUDGE AGENT evaluates the message using Marcus's secret profile
       → Returns score (-20 to +20) and reasoning
    4. Session Manager updates cumulative score
    5. Threshold check: Did user cross 100 points?
    6. DOORMAN AGENT generates response based on:
       - Conversation history
       - Current mood (from score)
       - Win instruction (if threshold crossed)
    7. Session Manager stores the exchange
    8. Response returned to user

    The Judge and Doorman never communicate directly - they
    collaborate through the Session Manager's shared state.
    """
    session_id = chat_req.session_id
    user_message = chat_req.message.strip()

    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Get current session state
    session = get_session(session_id)

    # Check if already won (just continue conversation)
    already_won = session["access_granted"]

    # ============================================
    # STEP 1: Judge Agent evaluates the message
    # ============================================
    if not already_won:
        judge_result = call_judge_agent(session_id, user_message)
        score_delta = judge_result["score"]
        reasoning = judge_result["reasoning"]

        # Update cumulative score
        session = update_score(session_id, score_delta)

        # Check if this message pushed them over the threshold
        just_won = session["access_granted"]
    else:
        # Already won - no more scoring
        score_delta = 0
        reasoning = "Access already granted - enjoy the club!"
        just_won = False

    # ============================================
    # STEP 2: Doorman Agent responds in character
    # ============================================
    # Pass win flag so Doorman knows to let them in
    should_grant = session["access_granted"]
    doorman_reply = call_doorman_agent(session_id, user_message, won=should_grant)

    # ============================================
    # STEP 3: TTS Agent converts reply to speech
    # ============================================
    audio_base64 = None
    if chat_req.enable_tts and TTS_ENABLED:
        audio_base64 = call_tts_api(doorman_reply)

    # ============================================
    # STEP 4: Update conversation history
    # ============================================
    add_to_history(session_id, "user", user_message)
    add_to_history(session_id, "assistant", doorman_reply)

    # Refresh session to get updated message count
    session = get_session(session_id)

    # ============================================
    # STEP 5: Return response
    # ============================================
    return ChatResponse(
        reply=doorman_reply,
        audio_base64=audio_base64,
        score_delta=score_delta,
        cumulative_score=session["cumulative_score"],
        threshold=INFLUENCE_THRESHOLD,
        access_granted=session["access_granted"],
        reasoning="Round scored by the game evaluator",
        message_count=session["message_count"]
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
