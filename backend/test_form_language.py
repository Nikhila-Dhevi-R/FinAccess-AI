"""
Form filling in Hindi / Tamil: labels and questions in the customer's language, answers shown back in
their script, and written on the English form in English letters.
"""

import io

import pypdf
import pytest

from services.form_language import to_english_letters, translate_label, localized_question, form_value
from models import UserSession

HINDI_NAMES = {
    "राम कुमार शर्मा": "Ram Kumar Sharma", "सुनीता देवी": "Sunita Devi", "दीपक": "Deepak", "पूजा": "Pooja",
    "जगदीश": "Jagdish", "मनमोहन सिंह": "Manmohan Singh", "अमरनाथ": "Amarnath", "कृष्ण": "Krishna",
    "लक्ष्मी": "Lakshmi", "आदित्य गुप्ता": "Aditya Gupta", "हरप्रीत कौर": "Harpreet Kaur", "ज़ैनब": "Zainab",
    "12, स्टेशन रोड, बंडेल": "12, Station Road, Bandel",
}
TAMIL_NAMES = {
    "முருகன்": "Murugan", "லட்சுமி": "Lakshmi", "சுரேஷ்": "Suresh", "அன்பு": "Anbu", "கார்த்திக்": "Karthik",
    "மாதவன்": "Madhavan", "விக்னேஷ்": "Vignesh", "சரவணன்": "Saravanan", "செல்வி": "Selvi",
}


@pytest.mark.parametrize("spoken,written", list(HINDI_NAMES.items()) + list(TAMIL_NAMES.items()))
def test_names_are_written_in_english_letters(spoken, written):
    assert to_english_letters(spoken) == written


def test_only_text_fields_are_transliterated():
    assert form_value("राम कुमार", "name") == "Ram Kumar"
    assert form_value("Ram Kumar", "name") == "Ram Kumar"            # already English: unchanged
    assert form_value("९८७६५४३२१०", "phone") == "9876543210"          # Devanagari digits → 0-9
    assert form_value("₹5,000 (Rupees Five Thousand Only)", "cheque_amount") == "₹5,000 (Rupees Five Thousand Only)"


def test_labels_and_questions_in_customer_language():
    assert translate_label("Full Name", "hi") == "पूरा नाम"
    assert translate_label("Account Number", "ta") == "கணக்கு எண்"
    assert translate_label("Full Name", "en") == "Full Name"
    assert "नंबर" in translate_label("Survey / Khasra Number", "hi")
    # a label we have no curated question for still gets a proper Hindi question
    q = localized_question("Mother Tongue", "Please provide your Mother Tongue.", "hi")
    assert q.startswith("कृपया") and "Please provide" not in q


def _answer(client, form_id, field_id, sid, text, language):
    r = client.post(f"/api/v1/forms/{form_id}/fields/{field_id}/answer", json={"transcribed_text": text, "language": language})
    assert r.status_code == 200, r.text
    data = r.json()
    client.post(f"/api/v1/confirmations/{data['nonce_id']}/respond", json={"session_id": sid, "transcribed_text": data["challenge_digits"]})
    return data


def test_hindi_flow_on_english_form_writes_english_letters(client, db_session):
    pdf = client.get("/api/v1/forms/demo-templates/bank_form").content
    sid = client.post("/api/v1/sessions", json={"preferred_language": "en"}).json()["id"]
    up = client.post("/api/v1/forms/upload", data={"session_id": sid, "language": "hi"},
                     files={"file": ("bank_form.pdf", io.BytesIO(pdf), "application/pdf")})
    assert up.status_code == 200, up.text
    fields = up.json()["fields"]
    full_name = next(f for f in fields if f["label"] == "Full Name")
    assert full_name["label_local"] == "पूरा नाम"

    form_id = up.json()["form_id"]
    seen_name = False
    for _ in range(len(fields) + 1):
        nxt = client.get(f"/api/v1/forms/{form_id}/next-field", params={"language": "hi"}).json()
        if nxt["is_complete"]:
            break
        field = nxt["field"]
        assert field["label_local"] and not field["label_local"].isascii() or field["label"] == field["label_local"]
        if field["label"] == "Full Name":
            seen_name = True
            assert nxt["question_audio_text"] == "आपका पूरा नाम क्या है?"
            data = _answer(client, form_id, field["id"], sid, "मेरा नाम राम कुमार है", "hi")
            assert data["interpreted_value"] == "राम कुमार"         # shown back in Hindi
            assert data["form_value"] == "Ram Kumar"                # what goes on the form
            assert data["readback_text"].startswith("मैंने सुना")
        else:
            client.post(f"/api/v1/forms/{form_id}/fields/{field['id']}/skip")
    assert seen_name

    challenge = client.post("/api/v1/confirmations", json={
        "session_id": sid,
        "bound_action": "submit_form",
        "bound_target_id": form_id,
    }).json()
    confirmed = client.post(
        f"/api/v1/confirmations/{challenge['nonce_id']}/respond",
        json={"session_id": sid, "transcribed_text": challenge["challenge_digits"]},
    )
    assert confirmed.json()["action_committed"] is True
    session = db_session.query(UserSession).filter_by(id=sid).one()
    session.state_blob = {
        **(session.state_blob or {}),
        "form_submission_authorized": {"form_id": form_id, "consumed": False},
    }
    db_session.commit()

    assert client.post(f"/api/v1/forms/{form_id}/finalize").status_code == 200
    out = client.get(f"/api/v1/forms/{form_id}/download")
    text = "".join(page.extract_text() or "" for page in pypdf.PdfReader(io.BytesIO(out.content)).pages)
    assert "Ram Kumar" in text
    assert "राम" not in text


def test_english_flow_is_unchanged(client):
    pdf = client.get("/api/v1/forms/demo-templates/pm_kisan").content
    sid = client.post("/api/v1/sessions", json={"preferred_language": "en"}).json()["id"]
    up = client.post("/api/v1/forms/upload", data={"session_id": sid},
                     files={"file": ("pm_kisan.pdf", io.BytesIO(pdf), "application/pdf")}).json()
    nxt = client.get(f"/api/v1/forms/{up['form_id']}/next-field").json()
    assert nxt["field"]["label"] == "Farmer Name"
    # English questions come from the original lookup, exactly as before this feature
    from services import voice_service
    assert nxt["question_audio_text"] == voice_service.build_question_in_language(
        voice_service.build_question_in_language("Farmer Name", "en"), "en")
    assert nxt["field"]["label_local"] == "Farmer Name"
