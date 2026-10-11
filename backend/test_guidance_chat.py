"""
The money guide chatbot: answers in en / hi / ta, follows the conversation (yes/no offers, "what documents?",
picking a numbered suggestion, calculators over several turns), remembers what the user said about themselves,
and does not repeat itself in a loop.
"""

import pytest

from services import finance_kb as kb
from services.guidance_service import get_guidance


def chat(turns, lang="en"):
    ctx, history, replies = {}, [], []
    for q in turns:
        r = get_guidance(q, lang, history=history, context=ctx)
        ctx = r["context"]
        history += [{"role": "user", "text": q}, {"role": "bot", "text": r["answer"], "topic": r["topic"]}]
        replies.append(r)
    return replies


def test_every_topic_has_all_three_languages():
    for tid, t in kb.TOPICS.items():
        for lang in ("en", "hi", "ta"):
            assert t["answer"][lang].strip() and t["title"][lang].strip(), (tid, lang)
        for target in list(t["related"]) + list(t["links"].values()):
            assert target in kb.TOPICS, (tid, target)
        if t["offer"]:
            assert t["offer"][0] in kb.TOPICS or t["offer"][0] in kb.CALC_TEXT["title"], tid


@pytest.mark.parametrize("question,lang,topic", [
    ("How do I open a bank account?", "en", "open_account"),
    ("बैंक खाता कैसे खोलें?", "hi", "open_account"),
    ("வங்கி கணக்கு எப்படி திறப்பது?", "ta", "open_account"),
    ("I lost my atm card", "en", "lost_card"),
    ("मेरा एटीएम कार्ड खो गया", "hi", "lost_card"),
    ("தவறுதலாக பணம் அனுப்பிவிட்டேன்", "ta", "upi_wrong_transfer"),
    ("What should I do if someone asks for my OTP?", "en", "otp_safety"),
    ("someone called saying digital arrest", "en", "digital_arrest"),
    ("how to claim insurance", "en", "insurance_claim"),
    ("pensoin", "en", "pension_options"),
    ("sukanya samriddhi", "en", "sukanya"),
    ("recovery agent is threatening me", "en", "recovery_harassment"),
    ("नकद जमा पर पैन चाहिए?", "hi", "pan"),
    ("நகைக் கடன்", "ta", "gold_loan"),
])
def test_questions_reach_the_right_topic(question, lang, topic):
    r = get_guidance(question, lang)
    assert r["topic"] == topic, r["answer"][:100]


def test_answers_are_in_the_users_language():
    hi = get_guidance("UPI kya hai", "hi")
    ta = get_guidance("UPI என்றால் என்ன", "ta")
    assert any("ऀ" <= ch <= "ॿ" for ch in hi["answer"])
    assert any("஀" <= ch <= "௿" for ch in ta["answer"])
    assert all(not s.isascii() for s in hi["follow_up_suggestions"])


def test_yes_follows_the_offer_and_no_closes_it():
    r = chat(["How do I open a bank account?", "yes"])
    assert r[0]["context"]["awaiting"] == {"type": "yes_no", "yes": "kyc_docs"}
    assert r[1]["topic"] == "kyc_docs"
    r = chat(["How do I open a bank account?", "no"])
    assert r[1]["topic"] is None and r[1]["context"]["awaiting"] is None


def test_follow_up_question_uses_the_previous_topic():
    r = chat(["Tell me about Jan Dhan account", "what documents do I need?"])
    assert r[1]["topic"] == "kyc_docs"


def test_numbered_choice_picks_a_suggestion():
    r = chat(["hi", "2"])
    first = r[0]["context"]["suggestions"][1]
    assert r[1]["topic"] == first


def test_emi_calculator_over_several_turns():
    r = chat(["what is emi", "yes", "2 lakh", "10%", "3 years", "what about 5 years"])
    assert "₹6,453" in r[4]["answer"]           # 2,00,000 at 10% for 36 months
    assert "₹4,249" in r[5]["answer"]           # recalculated for 60 months
    r = chat(["EMI कितनी होगी 5 लाख 9% 4 साल"], "hi")
    assert "₹12,443" in r[0]["answer"]


def test_calculator_can_be_cancelled_or_left():
    r = chat(["calculate emi", "cancel"])
    assert r[1]["context"]["awaiting"] is None
    r = chat(["calculate emi", "how do I report fraud"])
    assert r[1]["topic"] == "report_fraud"


def test_fd_calculation():
    r = get_guidance("fd calculate 1 lakh at 7% for 5 years", "en")
    assert "₹1,41,478" in r["answer"]


def test_remembers_who_the_user_is():
    r = chat(["I am a farmer", "what schemes are there for me"])
    assert "farmer" in r[0]["answer"]
    assert "PM Kisan" in r[1]["answer"] or "Kisan" in r[1]["answer"]
    r = chat(["मेरी उम्र 65 साल है", "मेरे लिए योजनाएं"], "hi")
    assert "senior" in r[0]["context"]["profile"]


def test_named_scheme_from_catalogue():
    r = get_guidance("ujjwala yojana", "en")
    assert "Ujjwala" in r["answer"]
    r = chat(["ujjwala yojana", "how do I apply"])
    assert "Ujjwala" in r[1]["answer"]


def test_no_loop_on_repeats_or_misunderstanding():
    r = chat(["How do I open a bank account?", "How do I open a bank account?"])
    assert r[1]["answer"] != r[0]["answer"]
    r = chat(["asdf", "qwer", "zxcv"])
    answers = [x["answer"] for x in r]
    assert len(set(answers)) == 3


def test_bad_context_from_client_is_ignored():
    r = get_guidance("2 lakh", "en", context={"awaiting": {"type": "calc", "calc": "emi", "slots": {"amount": "x", "rate": [1]}}, "discussed": ["nope"]})
    assert r["answer"]


def test_api_returns_context(client):
    r = client.post("/api/v1/guidance/ask", json={"question": "How do I open a bank account?", "language": "en"})
    assert r.status_code == 200
    data = r.json()
    assert data["topic"] == "open_account" and data["context"]["last_topic"] == "open_account"
    r2 = client.post("/api/v1/guidance/ask", json={"question": "yes", "language": "en", "context": data["context"],
                                                   "history": [{"role": "bot", "text": data["answer"], "topic": data["topic"]}]})
    assert r2.json()["topic"] == "kyc_docs"
