"""Smoke tests for the non-OTP FinAccess API."""

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_root_and_health():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_session_lifecycle():
    response = client.post("/sessions", json={"preferred_language": "hi"})
    assert response.status_code == 200
    session_id = response.json()["id"]

    response = client.get(f"/sessions/{session_id}")
    assert response.status_code == 200
    assert response.json()["id"] == session_id

    response = client.patch(f"/sessions/{session_id}/language?language=ta")
    assert response.status_code == 200
    assert response.json()["preferred_language"] == "ta"


def test_schemes_matching():
    response = client.post(
        "/schemes/match?language=en",
        json={
            "age": 45,
            "gender": "male",
            "occupation": "farmer",
            "annual_income": 80000,
            "income_bracket": "60k_1.5L",
            "has_bank_account": True,
            "has_aadhaar": True,
            "land_ownership": "<2ha",
            "area_type": "rural",
            "caste_category": "obc",
            "disability": False,
            "state": "Maharashtra",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "matched_schemes" in data
    assert "explanation_audio_text" in data


def test_fraud_check():
    response = client.post(
        "/fraud/check",
        json={"message_text": "Your account is suspended. Click http://bit.ly/sbi-verify-kyc"},
    )
    assert response.status_code == 200
    assert response.json()["classification"] in {"fraud", "suspicious"}


def test_guidance_ask():
    response = client.post(
        "/guidance/ask",
        json={"question": "How do I open a zero balance bank account?", "language": "en"},
    )
    assert response.status_code == 200
    assert response.json()["answer"]
