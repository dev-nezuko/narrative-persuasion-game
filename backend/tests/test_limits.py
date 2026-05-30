from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import routes
from app import session_manager as sessions
from app.main import app
from app.rate_limit import SlidingWindowLimiter

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "SESSIONS_DIR", tmp_path)
    sessions._session_cache.clear()
    routes.turn_limiter.clear()
    routes.session_creation_limiter.clear()
    yield
    sessions._session_cache.clear()


def test_sliding_window_frees_slots_as_time_passes():
    now = [0.0]
    limiter = SlidingWindowLimiter(2, 60, clock=lambda: now[0])
    assert limiter.retry_after("a") == 0 and limiter.retry_after("a") == 0
    assert limiter.retry_after("a") == 60
    assert limiter.retry_after("b") == 0
    now[0] = 45.0
    assert limiter.retry_after("a") == 15
    now[0] = 60.0
    assert limiter.retry_after("a") == 0


def test_turns_are_rate_limited_per_session(monkeypatch):
    monkeypatch.setattr(routes, "turn_limiter", SlidingWindowLimiter(2, 60))
    first = client.post("/session").json()["session_id"]
    second = client.post("/session").json()["session_id"]
    with patch.object(routes, "call_judge_agent", return_value={"score": 1, "reasoning": "x"}), \
         patch.object(routes, "call_doorman_agent", return_value="Synthetic"):
        body = {"session_id": first, "message": "hello"}
        assert client.post("/chat", json=body).status_code == 200
        assert client.post("/chat", json=body).status_code == 200
        limited = client.post("/chat", json=body)
        assert limited.status_code == 429 and int(limited.headers["Retry-After"]) > 0
        assert client.post("/chat", json={"session_id": second, "message": "hello"}).status_code == 200
    assert sessions.get_session(first)["message_count"] == 2


def test_long_conversations_hit_a_turn_cap(monkeypatch):
    monkeypatch.setattr(routes, "MAX_TURNS_PER_SESSION", 1)
    session_id = client.post("/session").json()["session_id"]
    with patch.object(routes, "call_judge_agent", return_value={"score": 1, "reasoning": "x"}), \
         patch.object(routes, "call_doorman_agent", return_value="Synthetic"):
        assert client.post("/chat", json={"session_id": session_id, "message": "hi"}).status_code == 200
        assert client.post("/chat", json={"session_id": session_id, "message": "hi"}).status_code == 409


def test_session_creation_is_rate_limited(monkeypatch):
    monkeypatch.setattr(routes, "session_creation_limiter", SlidingWindowLimiter(3, 60))
    codes = [client.post("/session").status_code for _ in range(4)]
    assert codes == [201, 201, 201, 429]
