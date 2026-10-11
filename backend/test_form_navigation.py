"""
Form filling navigation: Skip really moves on (the field is left blank), Back / tapping a field asks that
field again with its answer kept, a changed answer must be re-confirmed, and a form with skipped fields
can still be finished.
"""

import io

import pypdf
from models import FieldStatus, Form, FormField, FormStatus, UserSession


def _upload(client):
    pdf = client.get("/api/v1/forms/demo-templates/bank_form").content
    sid = client.post("/api/v1/sessions", json={"preferred_language": "en"}).json()["id"]
    up = client.post("/api/v1/forms/upload", data={"session_id": sid},
                     files={"file": ("bank_form.pdf", io.BytesIO(pdf), "application/pdf")}).json()
    return sid, up["form_id"], up["fields"]


def _answer_and_confirm(client, form_id, field_id, sid, text):
    data = client.post(f"/api/v1/forms/{form_id}/fields/{field_id}/answer",
                       json={"transcribed_text": text, "language": "en"}).json()
    r = client.post(f"/api/v1/confirmations/{data['nonce_id']}/respond",
                    json={"session_id": sid, "transcribed_text": data["challenge_digits"]})
    assert r.status_code == 200


def test_skip_moves_to_the_next_field(client):
    _, form_id, fields = _upload(client)
    first = client.get(f"/api/v1/forms/{form_id}/next-field").json()["field"]
    r = client.post(f"/api/v1/forms/{form_id}/fields/{first['id']}/skip")
    assert r.status_code == 200 and r.json()["status"] == "skipped"
    second = client.get(f"/api/v1/forms/{form_id}/next-field").json()["field"]
    assert second["id"] != first["id"]


def test_back_asks_a_confirmed_field_again_and_change_needs_reconfirming(client):
    sid, form_id, _ = _upload(client)
    first = client.get(f"/api/v1/forms/{form_id}/next-field").json()["field"]
    _answer_and_confirm(client, form_id, first["id"], sid, "Ram Kumar")

    back = client.get(f"/api/v1/forms/{form_id}/next-field", params={"field_id": first["id"]}).json()
    assert back["field"]["id"] == first["id"]
    assert back["field"]["status"] == "confirmed"          # just looking does not undo the answer

    changed = client.post(
        f"/api/v1/forms/{form_id}/fields/{first['id']}/answer",
        json={"transcribed_text": "Sita Devi", "language": "en"},
    )
    assert changed.status_code == 200
    changed_data = changed.json()
    assert changed_data["interpreted_value"] == "Sita Devi"

    # A changed value is provisional until its new voice challenge succeeds.
    review = client.get(
        f"/api/v1/forms/{form_id}/next-field", params={"field_id": first["id"]}
    ).json()
    assert review["field"]["status"] == "asked"
    confirmed = client.post(
        f"/api/v1/confirmations/{changed_data['nonce_id']}/respond",
        json={"session_id": sid, "transcribed_text": changed_data["challenge_digits"]},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["action_committed"] is True

    again = client.get(f"/api/v1/forms/{form_id}/next-field").json()
    assert again["field"]["id"] != first["id"]


def test_unknown_field_id_is_404(client):
    _, form_id, _ = _upload(client)
    assert client.get(f"/api/v1/forms/{form_id}/next-field", params={"field_id": "nope"}).status_code == 404
    assert client.post(f"/api/v1/forms/{form_id}/fields/nope/skip").status_code == 404


def test_finish_with_skipped_fields_left_blank(client, db_session):
    sid, form_id, fields = _upload(client)
    skipped = next(field for field in fields if field["label"] != "Full Name")
    skipped_label = skipped["label"]
    client.post(f"/api/v1/forms/{form_id}/fields/{skipped['id']}/skip")

    for field in db_session.query(FormField).filter(FormField.form_id == form_id):
        if field.id != skipped["id"]:
            field.status = FieldStatus.CONFIRMED
            field.confirmed_value = "Ram Kumar" if field.label == "Full Name" else "Test"
    form = db_session.query(Form).filter_by(id=form_id).one()
    form.status = FormStatus.COMPLETED
    session = db_session.query(UserSession).filter_by(id=sid).one()
    session.state_blob = {"form_submission_authorized": {"form_id": form_id, "consumed": False}}
    db_session.commit()
    assert skipped_label
    r = client.post(f"/api/v1/forms/{form_id}/finalize")
    assert r.status_code == 200, r.text
    assert r.json()["confirmed_fields"] == len(fields) - 1
    out = client.get(f"/api/v1/forms/{form_id}/download")
    text = "".join(page.extract_text() or "" for page in pypdf.PdfReader(io.BytesIO(out.content)).pages)
    assert "Ram Kumar" in text


def test_cannot_finish_with_unanswered_fields(client):
    _, form_id, _ = _upload(client)
    assert client.post(f"/api/v1/forms/{form_id}/finalize").status_code == 400
