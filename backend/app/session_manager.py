# ============================================================
# DOORMAN GAME - Session Manager with File Persistence
# ============================================================
# Tracks cumulative score, conversation history, and win state
# for each session. Persists to JSON files so sessions survive
# server restarts.
# ============================================================

import os
import json
import re
import secrets
import tempfile
import time
from threading import RLock
from copy import deepcopy
from contextlib import contextmanager
from typing import Optional
from datetime import datetime, timezone
from pathlib import Path

from .guardrails import neutralize_player_text

SESSIONS_DIR = Path(os.environ.get("DOORMAN_SESSION_DIR", str(Path(__file__).parent.parent / "sessions")))
SESSION_TTL_HOURS = float(os.environ.get("DOORMAN_SESSION_TTL_HOURS", "24"))
SESSION_LOCK = RLock()

INFLUENCE_THRESHOLD = 100  # Score needed to win
MIN_SCORE = -50  # Floor for cumulative score

SESSION_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{16,128}")
_CLEANUP_INTERVAL_SECONDS = 3600
_last_cleanup = 0.0


class InvalidSessionId(ValueError):
    pass


class SessionNotFound(LookupError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_session_path(session_id: str) -> Path:
    if not isinstance(session_id, str) or not SESSION_ID_PATTERN.fullmatch(session_id):
        raise InvalidSessionId("Invalid session identifier")
    return SESSIONS_DIR / f"{session_id}.json"


def _load_session_from_file(session_id: str) -> Optional[dict]:
    path = _get_session_path(session_id)
    if path.exists():
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def _save_session_to_file(session: dict) -> None:
    """Write atomically so a crash never leaves a half-written session file."""
    path = _get_session_path(session["session_id"])
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=SESSIONS_DIR, prefix=".session-", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(session, handle, indent=2, default=str)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _delete_session_file(session_id: str) -> None:
    path = _get_session_path(session_id)
    if path.exists():
        path.unlink()


# Active sessions, backed by the JSON files above
_session_cache: dict[str, dict] = {}


def _new_session(session_id: str) -> dict:
    now = _now()
    return {
        "session_id": session_id,
        "cumulative_score": 0,
        "history": [],
        "access_granted": False,
        "created_at": now,
        "updated_at": now,
        "message_count": 0,
    }


def create_session() -> dict:
    """Start a session under a server-generated, unguessable identifier.

    Clients never choose their own ID, so a short or predictable ID cannot
    be planted and later shared or guessed.
    """
    _cleanup_if_due()
    session = _new_session(secrets.token_urlsafe(24))
    _save_session_to_file(session)
    _session_cache[session["session_id"]] = session
    return session


def get_session(session_id: str) -> dict:
    """Return an existing session; raises SessionNotFound for unknown IDs.

    Session structure:
    {
        "session_id": str,
        "cumulative_score": int,
        "history": [{"role": "user"|"assistant", "content": str, "timestamp": str}, ...],
        "access_granted": bool,
        "created_at": str,
        "updated_at": str,
        "message_count": int
    }
    """
    _get_session_path(session_id)
    if session_id in _session_cache:
        return _session_cache[session_id]

    session = _load_session_from_file(session_id)
    if session is None:
        raise SessionNotFound(session_id)

    _session_cache[session_id] = session
    return session


def update_score(session_id: str, score_delta: int) -> dict:
    """Apply a turn's score with the MIN_SCORE floor and set the win flag."""
    session = get_session(session_id)
    session["cumulative_score"] = max(MIN_SCORE, session["cumulative_score"] + score_delta)
    if session["cumulative_score"] >= INFLUENCE_THRESHOLD:
        session["access_granted"] = True
    session["updated_at"] = _now()
    _save_session_to_file(session)
    return session


def add_to_history(session_id: str, role: str, content: str) -> None:
    session = get_session(session_id)
    session["history"].append({
        "role": role,
        "content": content,
        "timestamp": _now(),
    })
    if role == "user":
        session["message_count"] += 1
    session["updated_at"] = _now()
    _save_session_to_file(session)


def get_history_for_prompt(session_id: str, max_messages: int = 30) -> str:
    """Format recent history for the Judge prompt, truncated to avoid context overflow."""
    history = get_session(session_id)["history"]
    if not history:
        return "[This is the start of the conversation]"

    recent = history[-max_messages:]
    formatted = [
        f"{'User' if msg['role'] == 'user' else 'Marcus (Doorman)'}: {neutralize_player_text(msg['content'])}"
        for msg in recent
    ]
    if len(history) > max_messages:
        prefix = f"[...{len(history) - max_messages} earlier messages omitted...]\n\n"
        return prefix + "\n".join(formatted)
    return "\n".join(formatted)


def get_history_for_doorman(session_id: str, max_messages: int = 30) -> list[dict]:
    """Recent history in chat-completion message format (timestamps dropped)."""
    history = get_session(session_id)["history"]
    return [{"role": h["role"], "content": h["content"]} for h in history[-max_messages:]]


def reset_session(session_id: str) -> dict:
    """Clear score and history in place, keeping the same identifier."""
    previous = get_session(session_id)
    session = _new_session(previous["session_id"])
    _save_session_to_file(session)
    _session_cache[session_id] = session
    return session


def get_mood_level(cumulative_score: int) -> str:
    """Map the cumulative score to the Doorman's mood band."""
    if cumulative_score < 0:
        return "negative"
    elif cumulative_score < 30:
        return "neutral"
    elif cumulative_score < 70:
        return "warming"
    else:
        return "impressed"


def cleanup_old_sessions(max_age_hours: float = SESSION_TTL_HOURS) -> int:
    """Delete sessions idle for longer than max_age_hours. Returns count deleted."""
    deleted = 0
    cutoff = datetime.now(timezone.utc)

    for path in SESSIONS_DIR.glob("*.json"):
        try:
            with open(path, "r") as f:
                session = json.load(f)
            updated = datetime.fromisoformat(session.get("updated_at", session["created_at"]))
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            if (cutoff - updated).total_seconds() / 3600 > max_age_hours:
                path.unlink()
                _session_cache.pop(path.stem, None)
                deleted += 1
        except (json.JSONDecodeError, IOError, KeyError, ValueError):
            continue

    return deleted


def _cleanup_if_due() -> None:
    global _last_cleanup
    if time.monotonic() - _last_cleanup >= _CLEANUP_INTERVAL_SECONDS:
        _last_cleanup = time.monotonic()
        cleanup_old_sessions()


@contextmanager
def session_turn(session_id):
    """Serialize local turns and roll state back when a provider/persistence step fails."""
    with SESSION_LOCK:
        original = deepcopy(get_session(session_id))
        try:
            yield
        except Exception:
            _session_cache[session_id] = original
            _save_session_to_file(original)
            raise
