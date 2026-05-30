import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import routes
from app import session_manager as sessions
from app.main import app


@pytest.fixture(autouse=True)
def local_session_files(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "SESSIONS_DIR", tmp_path)
    sessions._session_cache.clear()
    routes.turn_limiter.clear()
    routes.session_creation_limiter.clear()
    yield
    sessions._session_cache.clear()


client = TestClient(app)


@pytest.fixture
def session_id():
    response = client.post("/session")
    assert response.status_code == 201
    return response.json()["session_id"]


def chat(session_id, message="Synthetic hello"):
    return client.post("/chat", json={"session_id": session_id, "message": message, "enable_tts": False})


def test_status_is_local_and_sessions_not_enumerated():
    with patch("requests.get", side_effect=AssertionError("network forbidden")):
        assert client.get("/test-env").json()["status"] == "ok"
    assert client.get("/sessions").status_code == 404


def test_identifiers_reject_aliases_instead_of_sanitizing(session_id):
    for identifier in ["../secret", "x" * 129, "", "session-synthetic/001"]:
        assert client.post("/chat", json={"session_id": identifier, "message": "hello"}).status_code == 422
    with pytest.raises(ValueError):
        sessions.get_session("../secret")


def test_server_issues_unguessable_session_ids():
    first = client.post("/session").json()
    second = client.post("/session").json()
    assert first["session_id"] != second["session_id"]
    assert len(first["session_id"]) == 32
    assert first["cumulative_score"] == 0 and first["history"] == []
    assert client.get(f"/session/{first['session_id']}").status_code == 200


def test_client_chosen_ids_are_not_created_on_read_or_chat(tmp_path):
    planted = "aaaaaaaaaaaaaaaa"
    with patch.object(routes, "call_judge_agent", side_effect=AssertionError("must not call")):
        assert client.get(f"/session/{planted}").status_code == 404
        assert chat(planted).status_code == 404
        assert client.post(f"/session/reset?session_id={planted}").status_code == 404
    assert list(tmp_path.glob("*.json")) == []


def test_reset_keeps_the_id_and_clears_progress(session_id):
    with patch.object(routes, "call_judge_agent", return_value={"score": 20, "reasoning": "x"}), \
         patch.object(routes, "call_doorman_agent", return_value="Synthetic response"):
        assert chat(session_id).status_code == 200
    reset = client.post(f"/session/reset?session_id={session_id}")
    assert reset.status_code == 200
    state = client.get(f"/session/{session_id}").json()
    assert state["cumulative_score"] == 0 and state["history"] == [] and state["message_count"] == 0


def test_idle_sessions_are_cleaned_up(session_id, tmp_path):
    path = tmp_path / f"{session_id}.json"
    stale = json.loads(path.read_text())
    stale["updated_at"] = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    path.write_text(json.dumps(stale))
    assert sessions.cleanup_old_sessions(max_age_hours=24) == 1
    assert client.get(f"/session/{session_id}").status_code == 404


def test_failed_turn_rolls_back_score_and_history(session_id):
    with patch.object(routes, "call_judge_agent", return_value={"score": 20, "reasoning": "synthetic private evaluation"}), \
         patch.object(routes, "call_doorman_agent", side_effect=HTTPException(502, "Synthetic provider failure")):
        assert chat(session_id).status_code == 502
    current = sessions.get_session(session_id)
    assert current["cumulative_score"] == 0
    assert current["history"] == []
    sessions._session_cache.clear()
    assert sessions.get_session(session_id)["cumulative_score"] == 0


def test_successful_turn_and_winning_threshold(session_id):
    with patch.object(routes, "call_judge_agent", return_value={"score": 20, "reasoning": "synthetic private evaluation"}), \
         patch.object(routes, "call_doorman_agent", return_value="Synthetic response"), \
         patch.object(routes, "call_tts_api", side_effect=AssertionError("TTS disabled")):
        for index in range(5):
            response = chat(session_id)
            assert response.status_code == 200
            assert response.json()["cumulative_score"] == (index + 1) * 20
            assert response.json()["reasoning"] == "Round scored by the game evaluator"
        assert response.json()["access_granted"] is True
    assert sessions.get_session(session_id)["message_count"] == 5


def test_malformed_judge_output_becomes_neutral_and_score_is_clamped(session_id):
    for content, expected in [('[]', 0), ('{"score":true}', 0), ('{"score":200}', 20), ('{"score":-200}', -20)]:
        with patch.object(routes, "call_mor_api", return_value={"choices": [{"message": {"content": content}}]}):
            assert routes.call_judge_agent(session_id, "hello")["score"] == expected


def test_hidden_think_text_is_removed_even_if_unclosed():
    assert routes.clean_response("<think>hidden</think>Visible") == "Visible"
    assert routes.clean_response("<THINK>hidden") == ""


def test_input_limit_does_not_call_agents(session_id):
    with patch.object(routes, "call_judge_agent", side_effect=AssertionError("must not call")):
        assert chat(session_id, "x" * 2001).status_code == 422
        assert chat(session_id, "   ").status_code == 400


def test_provider_failure_does_not_return_body_or_network_detail(monkeypatch):
    monkeypatch.setattr(routes, "VENICE_API_KEY", "synthetic-test-only")
    with patch.object(routes.requests, "post") as post:
        post.return_value.status_code = 401
        post.return_value.text = "synthetic private upstream detail"
        with pytest.raises(HTTPException) as caught:
            routes.call_mor_api("synthetic", [])
        assert "private upstream" not in caught.value.detail
