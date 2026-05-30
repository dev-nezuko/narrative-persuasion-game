import json
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from app.main import app
from app import routes
from app import session_manager as sessions

SESSION = "session-synthetic-test-001"
@pytest.fixture(autouse=True)
def local_session_files(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "SESSIONS_DIR", tmp_path)
    sessions._session_cache.clear()
    yield
    sessions._session_cache.clear()

client = TestClient(app)
def request(message="Synthetic hello"):
    return client.post("/chat", json={"session_id":SESSION,"message":message,"enable_tts":False})

def test_status_is_local_and_sessions_not_enumerated():
    with patch("requests.get", side_effect=AssertionError("network forbidden")):
        assert client.get("/test-env").json()["status"] == "ok"
    assert client.get("/sessions").status_code == 404

def test_identifiers_reject_aliases_instead_of_sanitizing():
    for identifier in ["../secret", "x"*129, "", "session-synthetic/001"]:
        assert client.post("/chat",json={"session_id":identifier,"message":"hello"}).status_code == 422
    with pytest.raises(ValueError): sessions.get_session("../secret")

def test_failed_turn_rolls_back_score_and_history():
    with patch.object(routes,"call_judge_agent",return_value={"score":20,"reasoning":"synthetic private evaluation"}), patch.object(routes,"call_doorman_agent",side_effect=HTTPException(502,"Synthetic provider failure")):
        assert request().status_code == 502
    current=sessions.get_session(SESSION)
    assert current["cumulative_score"]==0
    assert current["history"]==[]
    sessions._session_cache.clear()
    assert sessions.get_session(SESSION)["cumulative_score"]==0

def test_successful_turn_and_winning_threshold():
    with patch.object(routes,"call_judge_agent",return_value={"score":20,"reasoning":"synthetic private evaluation"}), patch.object(routes,"call_doorman_agent",return_value="Synthetic response"), patch.object(routes,"call_tts_api",side_effect=AssertionError("TTS disabled")):
        for index in range(5):
            response=request(); assert response.status_code==200
            assert response.json()["cumulative_score"]==(index+1)*20
            assert response.json()["reasoning"]=="Round scored by the game evaluator"
        assert response.json()["access_granted"] is True
    assert sessions.get_session(SESSION)["message_count"]==5

def test_malformed_judge_output_becomes_neutral_and_score_is_clamped():
    for content,expected in [('[]',0),('{"score":true}',0),('{"score":200}',20),('{"score":-200}',-20)]:
        with patch.object(routes,"call_mor_api",return_value={"choices":[{"message":{"content":content}}]}):
            assert routes.call_judge_agent(SESSION,"hello")["score"]==expected

def test_hidden_think_text_is_removed_even_if_unclosed():
    assert routes.clean_response("<think>hidden</think>Visible")=="Visible"
    assert routes.clean_response("<THINK>hidden")==""

def test_input_limit_does_not_call_agents():
    with patch.object(routes,"call_judge_agent",side_effect=AssertionError("must not call")):
        assert request("x"*2001).status_code==422
        assert request("   ").status_code==400

def test_provider_failure_does_not_return_body_or_network_detail(monkeypatch):
    monkeypatch.setattr(routes,"VENICE_API_KEY","synthetic-test-only")
    with patch.object(routes.requests,"post") as post:
        post.return_value.status_code=401
        post.return_value.text="synthetic private upstream detail"
        with pytest.raises(HTTPException) as caught:routes.call_mor_api("synthetic",[])
        assert "private upstream" not in caught.value.detail
