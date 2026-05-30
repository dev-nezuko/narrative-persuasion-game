# ============================================================
# DOORMAN GAME - Session Manager with File Persistence
# ============================================================
# Tracks cumulative score, conversation history, and win state
# for each user session. Persists to JSON files so sessions
# survive server restarts.
# ============================================================

import os
import json
from typing import Optional
from datetime import datetime
from pathlib import Path

# ============================================================
# Configuration
# ============================================================

# Directory to store session files
SESSIONS_DIR = Path(__file__).parent.parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

# Game configuration
INFLUENCE_THRESHOLD = 100  # Score needed to win
MIN_SCORE = -50  # Floor for cumulative score


# ============================================================
# Session Persistence Functions
# ============================================================

def _get_session_path(session_id: str) -> Path:
    """Get the file path for a session."""
    # Sanitize session_id to prevent path traversal
    safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
    return SESSIONS_DIR / f"{safe_id}.json"


def _load_session_from_file(session_id: str) -> Optional[dict]:
    """Load a session from disk if it exists."""
    path = _get_session_path(session_id)
    if path.exists():
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def _save_session_to_file(session: dict) -> None:
    """Save a session to disk."""
    path = _get_session_path(session["session_id"])
    try:
        with open(path, "w") as f:
            json.dump(session, f, indent=2, default=str)
    except IOError as e:
        print(f"Error saving session: {e}")


def _delete_session_file(session_id: str) -> None:
    """Delete a session file from disk."""
    path = _get_session_path(session_id)
    if path.exists():
        path.unlink()


# ============================================================
# In-Memory Cache (with file backing)
# ============================================================

# Cache for active sessions (reduces file I/O)
_session_cache: dict[str, dict] = {}


def get_session(session_id: str) -> dict:
    """
    Get or create a session. Returns the session state.
    Checks cache first, then disk, then creates new.
    
    Session structure:
    {
        "session_id": str,
        "cumulative_score": int,
        "history": [{"role": "user"|"assistant", "content": str}, ...],
        "access_granted": bool,
        "created_at": str,
        "updated_at": str,
        "message_count": int
    }
    """
    # Check cache first
    if session_id in _session_cache:
        return _session_cache[session_id]
    
    # Try loading from file
    session = _load_session_from_file(session_id)
    
    if session is None:
        # Create new session
        session = {
            "session_id": session_id,
            "cumulative_score": 0,
            "history": [],
            "access_granted": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "message_count": 0
        }
        _save_session_to_file(session)
    
    # Cache it
    _session_cache[session_id] = session
    return session


def update_score(session_id: str, score_delta: int) -> dict:
    """
    Update the cumulative score for a session.
    Returns the updated session with new score.
    
    - Applies floor (MIN_SCORE) to prevent going too negative
    - Checks if threshold is reached and sets access_granted
    """
    session = get_session(session_id)
    
    # Update score with floor
    new_score = session["cumulative_score"] + score_delta
    session["cumulative_score"] = max(MIN_SCORE, new_score)
    
    # Check win condition
    if session["cumulative_score"] >= INFLUENCE_THRESHOLD:
        session["access_granted"] = True
    
    # Update timestamp and persist
    session["updated_at"] = datetime.now().isoformat()
    _save_session_to_file(session)
    
    return session


def add_to_history(session_id: str, role: str, content: str) -> None:
    """
    Add a message to the conversation history.
    role: "user" or "assistant" (doorman)
    """
    session = get_session(session_id)
    session["history"].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    if role == "user":
        session["message_count"] += 1
    
    # Update timestamp and persist
    session["updated_at"] = datetime.now().isoformat()
    _save_session_to_file(session)


def get_history_for_prompt(session_id: str, max_messages: int = 30) -> str:
    """
    Format conversation history for inclusion in Judge prompt.
    Limits to last N messages to avoid context overflow.
    """
    session = get_session(session_id)
    history = session["history"]
    
    if not history:
        return "[This is the start of the conversation]"
    
    # Take last N messages
    recent = history[-max_messages:] if len(history) > max_messages else history
    
    # Format for prompt
    formatted = []
    for msg in recent:
        speaker = "User" if msg["role"] == "user" else "Marcus (Doorman)"
        formatted.append(f"{speaker}: {msg['content']}")
    
    # Add note if history was truncated
    if len(history) > max_messages:
        prefix = f"[...{len(history) - max_messages} earlier messages omitted...]\n\n"
        return prefix + "\n".join(formatted)
    
    return "\n".join(formatted)


def get_history_for_doorman(session_id: str, max_messages: int = 30) -> list[dict]:
    """
    Get conversation history in OpenAI message format for the Doorman.
    This preserves the actual message structure for the LLM.
    """
    session = get_session(session_id)
    history = session["history"]
    
    # Extract just role and content (remove timestamp for API)
    clean_history = [{"role": h["role"], "content": h["content"]} for h in history]
    
    if len(clean_history) > max_messages:
        return clean_history[-max_messages:]
    return clean_history


def reset_session(session_id: str) -> dict:
    """Reset a session to start fresh."""
    # Remove from cache
    if session_id in _session_cache:
        del _session_cache[session_id]
    
    # Delete file
    _delete_session_file(session_id)
    
    # Create fresh session
    return get_session(session_id)


def get_mood_level(cumulative_score: int) -> str:
    """
    Determine the Doorman's mood based on cumulative score.
    This affects how warmly/coldly he responds.
    """
    if cumulative_score < 0:
        return "negative"
    elif cumulative_score < 30:
        return "neutral"
    elif cumulative_score < 70:
        return "warming"
    else:
        return "impressed"


def get_all_sessions() -> list[dict]:
    """Get summary of all sessions (for debugging/admin)."""
    sessions = []
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            with open(path, "r") as f:
                session = json.load(f)
                sessions.append({
                    "session_id": session["session_id"],
                    "cumulative_score": session["cumulative_score"],
                    "message_count": session["message_count"],
                    "access_granted": session["access_granted"],
                    "created_at": session["created_at"],
                    "updated_at": session.get("updated_at", session["created_at"])
                })
        except (json.JSONDecodeError, IOError, KeyError):
            continue
    return sessions


def cleanup_old_sessions(max_age_hours: int = 24) -> int:
    """Delete sessions older than max_age_hours. Returns count deleted."""
    deleted = 0
    cutoff = datetime.now()
    
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            with open(path, "r") as f:
                session = json.load(f)
            
            updated = datetime.fromisoformat(session.get("updated_at", session["created_at"]))
            age_hours = (cutoff - updated).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                path.unlink()
                deleted += 1
        except (json.JSONDecodeError, IOError, KeyError, ValueError):
            continue
    
    return deleted
