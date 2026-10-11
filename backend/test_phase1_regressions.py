"""Focused regression coverage for the Phase 1 correctness fixes."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

from config import Settings
from models import (
    ConfirmationNonce,
    FieldStatus,
    Form,
    FormField,
    FormStatus,
    FraudCheck,
    UserSession,
)
from services.nonce_service import create_nonce
from models import BoundAction


def _make_form(db, field_specs):
    session = UserSession(id=str(uuid.uuid4()), preferred_language="en")
    form = Form(
        id=str(uuid.uuid4()),
        session_id=session.id,
        original_filename="phase1-test.pdf",
        status=FormStatus.IN_PROGRESS,
    )
    db.add_all([session, form])
    db.flush()

    fields = []
    for index, (field_type, status) in enumerate(field_specs):
        field = FormField(
            id=str(uuid.uuid4()),
            form_id=form.id,
            label=f"Field {index + 1}",
            field_type=field_type,
            question_text=f"What is field {index + 1}?",
            order_index=index,
            status=status,
            confirmed_value="Existing value" if status == FieldStatus.CONFIRMED else None,
        )
        db.add(field)
        fields.append(field)

    db.commit()
    return session, form, fields


def test_invalid_answer_stays_active_and_does_not_create_nonce(client, db_session):
    _, form, fields = _make_form(db_session, [("phone", FieldStatus.ASKED)])

    response = client.post(
        f"/forms/{form.id}/fields/{fields[0].id}/answer",
        json={"transcribed_text": "not a phone number", "language": "en"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation_passed"] is False
    assert payload["validation_message"]
    assert payload["nonce_id"] is None
    assert payload["challenge_digits"] is None
    db_session.refresh(fields[0])
    assert fields[0].status == FieldStatus.ASKED
    assert fields[0].confirmed_value is None
    assert db_session.query(ConfirmationNonce).filter_by(bound_target_id=fields[0].id).count() == 0


def test_skip_marks_field_terminal_and_advances_progress(client, db_session):
    _, form, fields = _make_form(
        db_session,
        [("text", FieldStatus.ASKED), ("text", FieldStatus.PENDING)],
    )

    response = client.post(f"/forms/{form.id}/fields/{fields[0].id}/skip")

    assert response.status_code == 200
    assert response.json()["status"] == "skipped"
    next_response = client.get(f"/forms/{form.id}/next-field")
    assert next_response.status_code == 200
    assert next_response.json()["field"]["id"] == fields[1].id
    assert next_response.json()["progress"]["completed"] == 1


def test_reject_and_skip_revoke_active_field_challenges(client, db_session):
    session, form, fields = _make_form(
        db_session,
        [("text", FieldStatus.ASKED), ("text", FieldStatus.ASKED)],
    )
    nonces = []
    for field in fields:
        field.confirmed_value = "Draft value"
        nonces.append(create_nonce(db_session, session.id, BoundAction.CONFIRM_FIELD, field.id))
    db_session.commit()

    rejected = client.post(f"/forms/{form.id}/fields/{fields[0].id}/reject")
    skipped = client.post(f"/forms/{form.id}/fields/{fields[1].id}/skip")
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "asked"
    assert skipped.status_code == 200

    for nonce in nonces:
        replay = client.post(
            f"/confirmations/{nonce.id}/respond",
            json={"session_id": session.id, "transcribed_text": nonce.challenge_digits},
        )
        assert replay.status_code == 200
        assert replay.json()["success"] is False

    db_session.refresh(fields[0])
    db_session.refresh(fields[1])
    assert fields[0].confirmed_value is None
    assert fields[0].status == FieldStatus.ASKED
    assert fields[1].status == FieldStatus.SKIPPED


def test_finalize_requires_successful_final_nonce(client, db_session, monkeypatch):
    session, form, _ = _make_form(
        db_session,
        [("text", FieldStatus.CONFIRMED), ("text", FieldStatus.SKIPPED)],
    )
    monkeypatch.setattr(
        "routers.forms.pdf_service.generate_filled_form_pdf",
        lambda **kwargs: str(Path(kwargs["output_dir"]) / f"form_{kwargs['form_id']}.pdf"),
    )
    monkeypatch.setattr(
        "routers.forms._find_generated_pdf",
        lambda form_id: str(Path("uploads") / f"form_{form_id}.pdf"),
    )

    bypass = client.post(f"/forms/{form.id}/finalize")
    assert bypass.status_code == 409

    challenge = client.post(
        "/confirmations",
        json={
            "session_id": session.id,
            "bound_action": "submit_form",
            "bound_target_id": form.id,
        },
    )
    assert challenge.status_code == 200
    challenge_data = challenge.json()

    confirm = client.post(
        f"/confirmations/{challenge_data['nonce_id']}/respond",
        json={"session_id": session.id, "transcribed_text": challenge_data["challenge_digits"]},
    )
    assert confirm.status_code == 200
    assert confirm.json()["success"] is True
    assert confirm.json()["action_committed"] is True
    db_session.refresh(form)
    assert form.status == FormStatus.COMPLETED

    session.state_blob = {
        **(session.state_blob or {}),
        "form_submission_authorized": {"form_id": form.id, "consumed": False},
    }
    db_session.add(session)
    db_session.commit()

    finalized = client.post(f"/forms/{form.id}/finalize")
    assert finalized.status_code == 200
    assert finalized.json()["pdf_url"] == f"/forms/{form.id}/download"
    db_session.refresh(form)
    assert form.status == FormStatus.FINALIZED

    repeated = client.post(f"/forms/{form.id}/finalize")
    assert repeated.status_code == 200
    assert repeated.json()["pdf_url"] == f"/forms/{form.id}/download"


def test_download_rejects_pdf_until_form_is_finalized(client, db_session):
    _, form, _ = _make_form(db_session, [("text", FieldStatus.CONFIRMED)])
    form.status = FormStatus.COMPLETED
    db_session.commit()

    response = client.get(f"/forms/{form.id}/download")

    assert response.status_code == 409


def test_final_challenge_rejects_unresolved_fields(client, db_session):
    session, form, _ = _make_form(db_session, [("text", FieldStatus.ASKED)])

    response = client.post(
        "/confirmations",
        json={
            "session_id": session.id,
            "bound_action": "submit_form",
            "bound_target_id": form.id,
        },
    )

    assert response.status_code == 409
    db_session.refresh(form)
    assert form.status == FormStatus.IN_PROGRESS


def test_nonce_wrong_expired_and_replay_do_not_commit(client, db_session):
    session, form, fields = _make_form(db_session, [("text", FieldStatus.ASKED)])
    field = fields[0]
    field.confirmed_value = "A valid draft"
    db_session.commit()

    wrong_nonce = create_nonce(db_session, session.id, BoundAction.CONFIRM_FIELD, field.id)
    wrong = client.post(
        f"/confirmations/{wrong_nonce.id}/respond",
        json={"session_id": session.id, "transcribed_text": f"9 {wrong_nonce.challenge_digits} 9"},
    )
    assert wrong.status_code == 200
    assert wrong.json()["success"] is False
    db_session.refresh(field)
    assert field.status == FieldStatus.ASKED

    stale_retry = client.post(
        f"/confirmations/{wrong_nonce.id}/respond",
        json={"session_id": session.id, "transcribed_text": wrong_nonce.challenge_digits},
    )
    assert stale_retry.status_code == 200
    assert stale_retry.json()["success"] is False
    db_session.refresh(field)
    assert field.status == FieldStatus.ASKED

    expired_nonce = create_nonce(db_session, session.id, BoundAction.CONFIRM_FIELD, field.id)
    expired_nonce.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    expired_digits = expired_nonce.challenge_digits
    db_session.commit()
    expired = client.post(
        f"/confirmations/{expired_nonce.id}/respond",
        json={"session_id": session.id, "transcribed_text": expired_digits},
    )
    assert expired.status_code == 200
    assert expired.json()["success"] is False

    valid_nonce = create_nonce(db_session, session.id, BoundAction.CONFIRM_FIELD, field.id)
    first = client.post(
        f"/confirmations/{valid_nonce.id}/respond",
        json={"session_id": session.id, "transcribed_text": valid_nonce.challenge_digits},
    )
    assert first.status_code == 200
    assert first.json()["success"] is True
    replay = client.post(
        f"/confirmations/{valid_nonce.id}/respond",
        json={"session_id": session.id, "transcribed_text": valid_nonce.challenge_digits},
    )
    assert replay.status_code == 200
    assert replay.json()["success"] is False


def test_submit_form_nonce_cannot_target_another_sessions_form(client, db_session):
    owner, form, _ = _make_form(db_session, [("text", FieldStatus.SKIPPED)])
    attacker = UserSession(id=str(uuid.uuid4()), preferred_language="en")
    db_session.add(attacker)
    db_session.commit()

    response = client.post(
        "/confirmations",
        json={
            "session_id": attacker.id,
            "bound_action": "submit_form",
            "bound_target_id": form.id,
        },
    )

    assert response.status_code == 404
    db_session.refresh(form)
    assert form.session_id == owner.id
    assert form.status == FormStatus.IN_PROGRESS


def test_scheme_profile_uses_ration_card_and_rejects_unknown_fields(client):
    valid = client.post(
        "/schemes/match",
        json={"occupation": "farmer", "has_ration_card": True},
    )
    assert valid.status_code == 200
    assert valid.json()["profile"]["has_ration_card"] is True

    drifted = client.post(
        "/schemes/match",
        json={"occupation": "farmer", "is_bpl_or_low_income": True},
    )
    assert drifted.status_code == 422


def test_invalid_or_missing_fraud_session_is_persisted_as_null(client, db_session):
    response = client.post(
        "/fraud/check",
        json={"session_id": "guest-session", "message_text": "You won a prize. Send OTP now."},
    )

    assert response.status_code == 200
    saved = db_session.query(FraudCheck).filter_by(id=response.json()["check_id"]).one()
    assert saved.session_id is None


def test_default_storage_paths_are_backend_relative():
    settings = Settings(_env_file=None)
    backend_dir = Path(__file__).resolve().parent

    database_path = settings.DATABASE_URL.removeprefix("sqlite:///")
    assert Path(database_path).is_absolute()
    assert Path(settings.UPLOAD_DIR).is_absolute()
    assert Path(database_path).resolve() == backend_dir / "finaccess.db"
    assert Path(settings.UPLOAD_DIR).resolve() == backend_dir / "uploads"
