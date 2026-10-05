import os
from pathlib import Path

os.environ["CONTEXTLENS_DB"] = str(Path(__file__).parent / "test.db")

from fastapi.testclient import TestClient
from backend.main import app
from backend.storage import clear_all, init_db

client = TestClient(app)


def setup_module():
    init_db()
    clear_all()


def test_health_is_honest():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "available" in body["ai"]


def test_full_thinking_flow_and_replay():
    start = client.post("/api/v1/analyze", json={"problem": "My workload is too high and I want to eventually switch jobs, but I need to keep my income stable.", "about": "me", "mode": "challenge", "use_personal_context": False})
    assert start.status_code == 200
    body = start.json()
    case_id = body["case"]["id"]
    assert body["context"]["goal"]
    assert body["question"]["options"]

    continued = client.post("/api/v1/analyze/continue", json={"case_id": case_id, "answer": "Lack of energy", "skipped": False})
    assert continued.status_code == 200
    analysis = continued.json()["analysis"]
    for key in ["perspectives", "connections", "contradictions", "blind_spots", "reframe", "options", "synthesis"]:
        assert analysis[key]

    decision = client.post("/api/v1/analyze/decision", json={"case_id": case_id, "decision": "I will protect one weekly preparation window and gather workload evidence."})
    assert decision.status_code == 200
    assert decision.json()["case"]["status"] == "decision_saved"

    replay = client.get(f"/api/v1/cases/{case_id}/replay")
    assert replay.status_code == 200
    assert len(replay.json()["events"]) >= 3


def test_skip_preserves_unknown():
    start = client.post("/api/v1/analyze", json={"problem": "I am unsure whether to take a new opportunity or stay where I am for now."})
    case_id = start.json()["case"]["id"]
    response = client.post("/api/v1/analyze/continue", json={"case_id": case_id, "skipped": True, "answer": ""})
    assert response.status_code == 200
    assert response.json()["analysis"]["question_skipped"] is True


def test_personal_context_round_trip():
    saved = client.post("/api/v1/memory/personal", json={"content": "I prefer evidence-grounded analysis.", "enabled": True})
    assert saved.status_code == 200
    loaded = client.get("/api/v1/memory/personal")
    assert loaded.json()["personal_context"]["enabled"] is True
    assert "evidence" in loaded.json()["personal_context"]["content"]
