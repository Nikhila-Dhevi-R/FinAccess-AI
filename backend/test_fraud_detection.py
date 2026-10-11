"""
Scam / fraud message detection tests (services/scam_detector.py via fraud_service.classify_message).

* Every labelled scam in fraud_test_messages.py must be rated "fraud"; every genuine message "safe".
* Focused behaviour tests: warning sentences, official vs look-alike links, Hindi/Tamil/Hinglish,
  localized output, and the API passing language / returning scam_type.
"""

import pytest

from fraud_test_messages import SCAM, LEGIT
from services.fraud_service import classify_message
from services.scam_detector import analyse_links


# ─── Labelled messages ──────────────────────────────────────────────────────
@pytest.mark.parametrize("category,text", SCAM, ids=[f"scam-{i}-{c}" for i, (c, _) in enumerate(SCAM)])
def test_scam_messages_are_rated_fraud(category, text):
    result = classify_message(text)
    assert result["classification"] == "fraud", (text, result["fraud_indicators"])
    assert result["fraud_indicators"], "a fraud verdict must explain why"
    assert result["scam_type"]


@pytest.mark.parametrize("category,text", LEGIT, ids=[f"legit-{i}-{c}" for i, (c, _) in enumerate(LEGIT)])
def test_genuine_messages_are_safe(category, text):
    result = classify_message(text)
    assert result["classification"] == "safe", (text, result["fraud_indicators"])
    assert result["scam_type"] is None


# ─── Behaviour ──────────────────────────────────────────────────────────────
def test_warning_sentences_do_not_trigger_but_requests_do():
    assert classify_message("Your OTP is 482913. Do not share it with anyone.")["classification"] == "safe"
    assert classify_message("Never share your OTP or PIN with anyone, including bank staff.")["classification"] == "safe"
    assert classify_message("Please share the OTP you received with our agent.")["classification"] == "fraud"


@pytest.mark.parametrize("url,risk", [
    ("https://www.onlinesbi.sbi", "official"),
    ("https://myaadhaar.uidai.gov.in/status", "official"),
    ("https://www.hdfcbank.com", "official"),
    ("http://sbi-kyc-update.xyz/login", "risky"),
    ("https://onlinesbi.sbi.kyc-verify.com", "risky"),   # brand as a sub-domain of someone else's site
    ("netfIix-account.com/update", "risky"),             # capital I instead of l
    ("bit.ly/abc", "risky"),
    ("http://192.168.10.5/secure", "risky"),
    ("http://site.example/app.apk", "risky"),
    ("wa.me/919876543210", "chat"),
])
def test_link_analysis(url, risk):
    links = analyse_links(f"Visit {url} today")
    assert links and links[0]["risk"] == risk, links


def test_kyc_mention_alone_is_not_flagged_but_kyc_with_ask_is():
    assert classify_message("Please visit your branch with documents to complete re-KYC. - SBI")["classification"] == "safe"
    assert classify_message("Your KYC is pending. Call our KYC officer on 9876543210 now.")["classification"] == "fraud"


@pytest.mark.parametrize("text", [
    "Aapka SBI khata band ho jayega. Turant KYC update karein: bit.ly/sbi-kyc",
    "आपके फोन पर आया ओटीपी बताएं, ताकि आपका खाता चालू रहे।",
    "உங்கள் மொபைலுக்கு வந்த OTP எண்ணை எங்களிடம் பகிரவும்.",
])
def test_indian_languages_are_detected(text):
    assert classify_message(text)["classification"] == "fraud"


@pytest.mark.parametrize("language,marker", [("en", "Warning"), ("hi", "चेतावनी"), ("ta", "எச்சரிக்கை")])
def test_output_is_in_the_customers_language(language, marker):
    result = classify_message("Congratulations! You won Rs 25 lakh in KBC lottery. Pay Rs 5000 processing fee.", language)
    assert result["classification"] == "fraud"
    assert marker in result["explanation_audio_text"]
    if language != "en":
        assert all(not ind.isascii() for ind in result["fraud_indicators"])  # translated warning signs


def test_risk_levels_and_likelihood():
    fraud = classify_message("Install AnyDesk so our engineer can fix your bank app.")
    assert fraud["risk_level"] in ("critical", "high") and fraud["confidence"] >= 0.85
    safe = classify_message("Happy birthday! Have a wonderful year ahead.")
    assert safe["risk_level"] == "low" and safe["confidence"] < 0.2


# ─── API ────────────────────────────────────────────────────────────────────
def test_api_returns_scam_type_in_requested_language(client):
    resp = client.post("/fraud/check", json={
        "message_text": "Your electricity will be disconnected tonight. Call officer 9123456780 immediately.",
        "language": "hi",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["classification"] == "fraud"
    assert data["scam_type"] == "नकली बिजली / बिल धोखा"
    assert "चेतावनी" in data["explanation_audio_text"]


def test_api_safe_message_has_no_scam_type(client):
    resp = client.post("/api/v1/fraud/check", json={"message_text": "Reminder: your appointment is tomorrow at 10 AM."})
    assert resp.status_code == 200
    assert resp.json()["classification"] == "safe"
    assert resp.json()["scam_type"] is None
